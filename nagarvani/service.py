"""What the web app does with a submission and with officer actions.

Order for every submission: (1) persist the complaint as status 'received', (2) run
triage(), (3) write the outcome. If step 2 or 3 fails, the ticket goes to the review queue
with the failure written on it, so no submission is lost.
"""
from __future__ import annotations

import json
import logging
import traceback
from datetime import datetime, timedelta, timezone

from . import data, severity
from .pipeline import triage
from .store import Store, iso, parse, trace_dumps, utcnow

log = logging.getLogger("nagarvani")
IST = timezone(timedelta(hours=5, minutes=30), "IST")   # fixed offset: India has no DST (no tzdata needed)
STATUS_FROM_GATE = {"AUTO_ROUTED": "auto_routed", "SENT_TO_REVIEW": "review", "MERGED": "merged"}


def to_ist(s: str | None) -> str:
    dt = parse(s)
    return dt.astimezone(IST).strftime("%d %b %Y, %H:%M IST") if dt else "—"


# ---- submissions ----------------------------------------------------------------------------
def submit(store: Store, *, text: str, channel: str, language: str = "mr", ward_hint: str | None = None,
           raw_transcript: str | None = None, asr_info: dict | None = None, audio_path: str | None = None,
           submission_key: str | None = None, now: datetime | None = None) -> tuple[int, bool]:
    """Returns (ticket id, created). created=False means this submission key was already used."""
    if submission_key:
        existing = store.by_submission_key(submission_key)
        if existing:
            return existing["id"], False
    now = now or utcnow()
    tid = store.create(now=now, channel=channel, language=language, text=text, raw_transcript=raw_transcript,
                       asr_json=json.dumps(asr_info, ensure_ascii=False) if asr_info else None,
                       audio_path=audio_path, ward_hint=ward_hint or None, submission_key=submission_key,
                       transcript_uncertain=int(bool(asr_info and asr_info.get("uncertain"))))
    process(store, tid, now=now)
    return tid, True


def record_failure(store: Store, tid: int, stage: str, exc: BaseException | str):
    msg = exc if isinstance(exc, str) else f"{type(exc).__name__}: {exc}"
    log.error("ticket %s failed at %s: %s", tid, stage, msg)
    store.update(tid, status="review", failure=f"{stage}: {msg}",
                 review_reason=f"Automatic processing failed at the {stage} step; an officer must triage this by hand.")


def process(store: Store, tid: int, now: datetime | None = None):
    t = store.get(tid)
    try:
        result = triage(t["text"], ward_hint=t["ward_hint"], now=now or parse(t["created_utc"]), store=store,
                        exclude_ticket=tid)
    except ValueError as e:                      # no words at all
        return record_failure(store, tid, "classification", str(e))
    except Exception as e:  # noqa: BLE001 - any failure must still leave a ticket in review
        log.debug(traceback.format_exc())
        return record_failure(store, tid, "triage", e)
    try:
        apply_result(store, tid, result)
    except Exception as e:  # noqa: BLE001
        log.debug(traceback.format_exc())
        return record_failure(store, tid, "saving the result", e)


def apply_result(store: Store, tid: int, r):
    dup = r.duplicate
    status = STATUS_FROM_GATE[r.gate.decision]
    fields = dict(status=status, department=r.department, confidence=round(r.confidence, 4), ward=r.ward.ward,
                  priority=r.severity["band"], deadline_utc=r.deadline_utc, masked_text=r.masked_text,
                  trace_json=trace_dumps(r.to_dict()), review_reason=r.gate.reason if status == "review" else None,
                  dup_score=dup["score"], dup_candidate_id=dup["ticket_id"] if dup["decision"] != "new" else None,
                  dup_pending=int(status == "review" and dup["decision"] in ("merge", "review")))
    if status == "merged":
        fields["parent_id"] = dup["ticket_id"]
    store.update(tid, **fields)
    if status == "merged":
        merge_into(store, child_id=tid, parent_id=dup["ticket_id"], band=r.severity["band"],
                   report_count=dup["report_count"], fired=[f["rule"] for f in r.severity["fired"]])


def merge_into(store: Store, *, child_id: int, parent_id: int, band: str, report_count: int, fired: list):
    """Attach a report to an open ticket. If R32 fired, the parent's priority escalates."""
    p = store.get(parent_id)
    new_band = severity.more_urgent(p["priority"] or band, band)
    fields = {"report_count": report_count}
    if new_band != p["priority"]:
        hours = data.sla_hours()[new_band]
        new_deadline = parse(p["created_utc"]) + timedelta(hours=hours)
        fields.update(priority=new_band, deadline_utc=iso(min(new_deadline, parse(p["deadline_utc"]))
                                                          if p["deadline_utc"] else new_deadline))
        why = "R32" if "R32" in fired else "a more urgent merged report"
        fields["escalation"] = f"{why} at report {report_count} (ticket #{child_id}): {p['priority']} → {new_band}"
    store.update(parent_id, **fields)


# ---- officer actions -------------------------------------------------------------------------
class ActionError(ValueError):
    pass


def confirm(store: Store, tid: int, note: str = ""):
    t = store.get(tid)
    if not t["department"] or not t["ward"] or not t["priority"]:
        raise ActionError("Set the department, ward office and priority before confirming.")
    store.add_correction(tid, "confirm", t["status"], f"{t['department']}|{t['ward']}|{t['priority']}", t["text"], note)
    store.update(tid, status="routed" if t["status"] == "review" else t["status"], confirmed=1)


def correct(store: Store, tid: int, *, department=None, ward=None, priority=None, note=""):
    t = store.get(tid)
    changes = {}
    if department and department != t["department"]:
        if department not in data.dept_codes():
            raise ActionError("unknown department")
        changes["department"] = department
    if ward and ward != t["ward"]:
        if ward not in data.ward_names():
            raise ActionError("unknown ward office")
        changes["ward"] = ward
    if priority and priority != t["priority"]:
        if priority not in severity.BANDS:
            raise ActionError("unknown priority")
        changes["priority"] = priority
        changes["deadline_utc"] = iso(parse(t["created_utc"]) + timedelta(hours=data.sla_hours()[priority]))
    for f in ("department", "ward", "priority"):
        if f in changes:
            store.add_correction(tid, f, t[f], changes[f], t["text"], note)
    if changes:
        store.update(tid, **changes)
    return changes


def decide_duplicate(store: Store, tid: int, merge: bool, note=""):
    t = store.get(tid)
    cand = t["dup_candidate_id"]
    if not t["dup_pending"] or not cand:
        raise ActionError("no pending duplicate decision on this ticket")
    if merge:
        parent = store.get(cand)
        if parent["parent_id"]:
            parent = store.get(parent["parent_id"])
        count = parent["report_count"] + 1
        sev = severity.assess(parent["text"], parent["department"], count)
        store.add_correction(tid, "duplicate", "pending", f"merged into #{parent['id']}", t["text"], note)
        store.update(tid, status="merged", parent_id=parent["id"], dup_pending=0)
        merge_into(store, child_id=tid, parent_id=parent["id"], band=sev.band, report_count=count,
                   fired=sev.rule_ids)
    else:
        store.add_correction(tid, "duplicate", "pending", "kept separate", t["text"], note)
        store.update(tid, dup_pending=0)


def resolve(store: Store, tid: int, note=""):
    t = store.get(tid)
    store.add_correction(tid, "resolve", t["status"], "resolved", t["text"], note)
    store.update(tid, status="resolved", resolved_utc=iso(utcnow()))
    for c in store.children(tid):
        store.update(c["id"], status="resolved", resolved_utc=iso(utcnow()))


# ---- queue ------------------------------------------------------------------------------------
def queue(store: Store, *, ward=None, department=None, status=None, now: datetime | None = None):
    now = now or utcnow()
    where, params = ["status != 'received'"], []
    if ward:
        where.append("ward = ?")
        params.append(ward)
    if department:
        where.append("department = ?")
        params.append(department)
    if status and status != "all":
        where.append("status = ?")
        params.append(status)
    elif not status:
        where.append("status IN ('review', 'auto_routed', 'routed')")
    rows = store.tickets(" AND ".join(where), params)

    def key(r):
        p = severity.BANDS.index(r["priority"]) if r["priority"] in severity.BANDS else 9
        return (p, r["deadline_utc"] or "9999")
    out = []
    for r in sorted(rows, key=key):
        d = dict(r)
        d["overdue"] = bool(r["deadline_utc"] and r["status"] not in ("resolved", "merged")
                            and parse(r["deadline_utc"]) < now)
        out.append(d)
    return out


def export_rows(store: Store, ward: str, now=None):
    return [r for r in queue(store, ward=ward, now=now) if r["status"] in ("review", "auto_routed", "routed")]


def corrections_jsonl(store: Store) -> str:
    lines = []
    for c in store.corrections():
        lines.append(json.dumps({k: c[k] for k in c.keys()}, ensure_ascii=False))
    return "\n".join(lines) + ("\n" if lines else "")
