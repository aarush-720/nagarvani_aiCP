"""The single triage entry point used by the evaluation scripts AND the web app.

    triage(text, *, ward_hint=None, now=None, store=None) -> TriageResult

With store=None duplicate lookup is skipped (that is how the offline evaluation runs).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone

from . import classifier, config, data, dedup, location, severity
from .normalise import normalise


@dataclass
class WardResult:
    ward: str | None
    method: str                  # exact | fuzzy | hint | unresolved
    status: str                  # resolved | ambiguous | unknown (from the text resolver)
    locality: str | None
    matched_alias: str | None
    matched_text: str | None
    score: float | None
    candidates: list
    reason: str
    hint_used: bool = False
    hint: str | None = None


@dataclass
class GateResult:
    decision: str        # AUTO_ROUTED | SENT_TO_REVIEW | MERGED
    gate_passed: bool    # the frozen gate: confidence >= 0.50 and ward known
    reason: str


@dataclass
class TriageResult:
    text: str
    normalised: str
    top3: list
    confidence: float
    department: str
    ward: WardResult
    severity: dict
    sla_hours: int
    deadline_utc: str
    duplicate: dict
    gate: GateResult
    created_utc: str
    masked_text: str
    pipeline_version: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


def _resolve_ward(text: str, ward_hint: str | None) -> WardResult:
    loc = location.resolve(text)
    if loc.status == "resolved":
        reason = loc.reason
        if ward_hint and ward_hint != loc.ward:
            reason += f" (dropdown choice {ward_hint} ignored: the text names a place)"
        return WardResult(loc.ward, loc.method, loc.status, loc.locality, loc.matched_alias, loc.matched_text,
                          loc.score, loc.candidates, reason, False, ward_hint)
    if ward_hint and ward_hint in data.ward_names():
        why = loc.reason + "; used the ward office the citizen chose in the dropdown"
        if loc.candidates and ward_hint not in loc.candidates:
            why += " (note: it is not one of the candidates named in the text)"
        return WardResult(ward_hint, "hint", loc.status, None, loc.matched_alias, loc.matched_text, loc.score,
                          loc.candidates, why, True, ward_hint)
    return WardResult(None, "unresolved", loc.status, None, loc.matched_alias, loc.matched_text, loc.score,
                      loc.candidates, loc.reason, False, ward_hint)


def triage(text: str, *, ward_hint: str | None = None, now: datetime | None = None, store=None,
           exclude_ticket: int | None = None) -> TriageResult:
    norm = normalise(text)
    if not any(ch.isalpha() for ch in norm):
        raise ValueError("no words to classify")
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)

    # 1. department
    pred = classifier.predict(text)
    dept = pred.top3[0][0]

    # 2. ward office
    ward = _resolve_ward(text, ward_hint)

    # 3. duplicates (live path only)
    if store is None:
        dup = dedup.DuplicateResult("skipped", reason="offline run: no ticket store")
    elif ward.ward is None:
        dup = dedup.DuplicateResult("skipped", reason="ward office unknown, so there is no block to compare in")
    else:
        dup = dedup.find(text, store.open_in_block(ward.ward, dept, exclude_ticket))

    # 4. gate (frozen): confidence >= 0.50 AND ward known
    conf_ok = pred.confidence >= config.GATE_MIN_CONFIDENCE
    gate_passed = conf_ok and ward.ward is not None
    conds = (f"confidence {pred.confidence:.2f} {'≥' if conf_ok else '<'} {config.GATE_MIN_CONFIDENCE}; "
             f"ward office {'known (' + ward.method + ')' if ward.ward else 'not resolved'}")
    if not gate_passed:
        decision, reason = "SENT_TO_REVIEW", f"Gate failed: {conds}."
        if dup.decision in ("merge", "review"):
            reason += f" Possible duplicate of #{dup.ticket_id} (similarity {dup.score:.2f}) left for the officer."
    elif dup.decision == "merge":
        decision, reason = "MERGED", f"Gate passed ({conds}); {dup.reason}."
    elif dup.decision == "review":
        decision, reason = "SENT_TO_REVIEW", f"Gate passed ({conds}), but {dup.reason}."
    else:
        decision, reason = "AUTO_ROUTED", f"Gate passed: {conds}."
    gate = GateResult(decision, gate_passed, reason)

    # 5. severity (R32 sees the report count only when this complaint is merged)
    reports = dup.report_count if decision == "MERGED" else 1
    sev = severity.assess(text, dept, reports)
    hours = data.sla_hours()[sev.band]
    deadline = now + timedelta(hours=hours)

    _, meta = classifier.load()
    return TriageResult(
        text=text, normalised=norm, top3=pred.top3, confidence=pred.confidence, department=dept, ward=ward,
        severity={"band": sev.band, "base_band": sev.base_band,
                  "fired": [asdict(f) for f in sev.fired], "overridden": sev.overridden, "cues": sev.cues},
        sla_hours=hours, deadline_utc=deadline.isoformat(timespec="seconds"),
        duplicate=asdict(dup), gate=gate, created_utc=now.isoformat(timespec="seconds"),
        masked_text=dedup.masked(text),
        pipeline_version={"classifier_C": meta["C"], "train_sha256": meta["train_sha256"][:12]},
    )
