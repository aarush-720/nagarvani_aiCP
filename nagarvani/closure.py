"""Closure verification (v2.0, M9 light): a ticket closes only when the citizen confirms the fix.

    open (auto_routed | review | routed | reopened)
        --officer "Mark resolved" (note required, photo optional)-->  pending_confirmation
    pending_confirmation --citizen "Yes, fixed"-->  closed
    pending_confirmation --citizen "No"-->          reopened  (priority up one band, deadline restarted)

This answers the PMC Standing Committee directive that no complaint be closed without the
complainant's feedback. Every change goes through transition(), which allows only the moves in
TRANSITIONS, so no officer or system action can reach 'closed'. A ticket left waiting longer
than config.CONFIRMATION_WINDOW_HOURS is only flagged; it is never closed automatically.
Merged reports follow their parent when it closes. Every change is written to ticket_events.

Not implemented from the PBL-3 design: before/after image comparison, geotag checks and a
visual defect detector. The officer's photo is stored and shown, not analysed.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from pathlib import Path

from . import config, data
from .tickets import OPEN_STATUSES, Store, iso, parse, utcnow

PENDING, CLOSED, REOPENED = "pending_confirmation", "closed", "reopened"
BANDS = ["P1", "P2", "P3", "P4"]

# action -> (actor, statuses it may start from, status it leads to)
TRANSITIONS = {
    "resolve": ("officer", set(OPEN_STATUSES), PENDING),
    "confirm_fixed": ("citizen", {PENDING}, CLOSED),
    "report_not_fixed": ("citizen", {PENDING}, REOPENED),
}

PHOTO_TYPES = {b"\xff\xd8\xff": "jpg", b"\x89PNG\r\n\x1a\n": "png"}   # plus WebP, checked below


class ClosureError(ValueError):
    pass


def photo_type(head: bytes) -> str | None:
    """File type from the leading bytes, not the file name: jpg, png, webp or None."""
    for magic, ext in PHOTO_TYPES.items():
        if head.startswith(magic):
            return ext
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return None


def save_photo(content: bytes, folder: Path) -> str:
    """Check and store a resolution photo; returns its path. Raises ClosureError if unsuitable."""
    if len(content) > config.RESOLUTION_PHOTO_MAX_BYTES:
        raise ClosureError(f"photo is larger than {config.RESOLUTION_PHOTO_MAX_BYTES // (1024 * 1024)} MB")
    ext = photo_type(content[:16])
    if ext is None:
        raise ClosureError("photo must be a JPEG, PNG or WebP image")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{uuid.uuid4().hex}.{ext}"
    path.write_bytes(content)
    return str(path)


def raise_band(band: str | None) -> str | None:
    return BANDS[max(BANDS.index(band) - 1, 0)] if band in BANDS else band


def transition(store: Store, tid: int, action: str, *, note: str = "", photo: str | None = None,
               now: datetime | None = None) -> str:
    """Apply one closure action; returns the new status. The only way to change closure state."""
    if action not in TRANSITIONS:
        raise ClosureError(f"unknown action {action!r}")
    actor, allowed, target = TRANSITIONS[action]
    t = store.get(tid)
    if t is None:
        raise ClosureError(f"no ticket #{tid}")
    if t["status"] not in allowed:
        raise ClosureError(f"ticket #{tid} is '{t['status']}'; '{action}' is not allowed from that status")
    note = (note or "").strip()
    now = now or utcnow()
    fields = {"status": target}
    if action == "resolve":
        if not note:
            raise ClosureError("a resolution note is required: say what was done")
        fields.update(resolution_note=note, resolution_photo=photo, pending_since_utc=iso(now), citizen_comment=None)
    elif action == "confirm_fixed":
        fields.update(closed_utc=iso(now), citizen_comment=note or None)
    else:                                                    # report_not_fixed
        band = raise_band(t["priority"])
        fields.update(priority=band, reopen_count=(t["reopen_count"] or 0) + 1, pending_since_utc=None,
                      citizen_comment=note or None,
                      deadline_utc=iso(now + timedelta(hours=data.sla_hours()[band])) if band else t["deadline_utc"])
        if band != t["priority"]:
            fields["escalation"] = f"citizen reported not fixed: {t['priority']} → {band}"
    store.update(tid, **fields)
    store.add_event(tid, actor, t["status"], target, note, now=now)
    if target == CLOSED:
        for c in store.children(tid):
            if c["status"] == "merged":
                store.update(c["id"], status=CLOSED, closed_utc=iso(now))
                store.add_event(c["id"], actor, "merged", CLOSED, f"parent #{tid} confirmed fixed", now=now)
    return target


def awaiting(t, now: datetime | None = None) -> bool:
    """Resolved by an officer, and no citizen answer within the confirmation window."""
    if t["status"] != PENDING or not t["pending_since_utc"]:
        return False
    return (now or utcnow()) - parse(t["pending_since_utc"]) > timedelta(hours=config.CONFIRMATION_WINDOW_HOURS)
