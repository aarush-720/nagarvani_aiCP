"""Ward dashboard (v2.0, M11): aggregate views of the ticket store for the ward office.

Every figure is counted from the SQLite ticket store at request time; nothing is cached or typed in.

* per_ward():   open tickets, P1 open, deadline breached, waiting for the citizen (and how many of
                those are past the confirmation window), deferred to the nodal officer, reopened.
* clusters():   duplicate clusters with at least `min_size` reports, largest first.
* heat():       department x ward office table of open tickets.
* override():   officer override rate = auto-routed tickets an officer later corrected
                (department, ward or priority) / all tickets the gate auto-routed.
                This is the metric PBL-4 proposes for a pilot: it measures how often the
                automatic routing had to be overruled.

"Open" means OPEN_STATUSES (auto_routed, review, routed, reopened). A ticket waiting for the
citizen's confirmation is not open (its deadline has stopped) and is counted separately.
"""
from __future__ import annotations

from datetime import datetime

from . import closure, data
from .service import is_overdue
from .tickets import OPEN_STATUSES, Store, utcnow

OVERRIDE_FIELDS = ("department", "ward", "priority")


def _filtered(store: Store, ward: str | None, department: str | None):
    where, params = ["status != 'received'"], []
    if ward:
        where.append("ward = ?")
        params.append(ward)
    if department:
        where.append("department = ?")
        params.append(department)
    return store.tickets(" AND ".join(where), params)


def per_ward(store: Store, *, ward=None, department=None, now: datetime | None = None) -> list[dict]:
    """One row per ward office (all 15, in gazetteer order, even if empty), plus a row for
    tickets with no ward office yet (the gate could not place them)."""
    now = now or utcnow()
    names = data.ward_names()
    keys = [w for w in names if not ward or w == ward] + ([None] if not ward else [])
    rows = {k: dict(ward=k, open=0, p1_open=0, breached=0, pending=0, awaiting=0, deferred=0, reopened=0,
                    closed=0) for k in keys}
    for t in _filtered(store, ward, department):
        r = rows.get(t["ward"])
        if r is None:
            continue
        s = t["status"]
        if s in OPEN_STATUSES:
            r["open"] += 1
            r["p1_open"] += t["priority"] == "P1"
            r["breached"] += is_overdue(t, now)
            r["deferred"] += s == "review"
            r["reopened"] += s == closure.REOPENED
        elif s == closure.PENDING:
            r["pending"] += 1
            r["awaiting"] += closure.awaiting(t, now)
        elif s == closure.CLOSED:
            r["closed"] += 1
    out = list(rows.values())
    if None in rows and not any(v for k, v in rows[None].items() if k != "ward"):
        out = [r for r in out if r["ward"] is not None]
    return out


def totals(rows: list[dict]) -> dict:
    keys = [k for k in rows[0] if k != "ward"] if rows else []
    return {k: sum(r[k] for r in rows) for k in keys}


def clusters(store: Store, *, ward=None, department=None, min_size: int = 3) -> list[dict]:
    """Root tickets with report_count >= min_size that are still open or awaiting the citizen."""
    out = []
    for t in _filtered(store, ward, department):
        if t["parent_id"] is None and (t["report_count"] or 1) >= min_size and \
                (t["status"] in OPEN_STATUSES or t["status"] == closure.PENDING):
            out.append(dict(id=t["id"], size=t["report_count"], department=t["department"], ward=t["ward"],
                            priority=t["priority"], status=t["status"], escalation=t["escalation"],
                            text=t["text"]))
    return sorted(out, key=lambda c: (-c["size"], c["id"]))


def heat(store: Store, *, ward=None, department=None) -> dict:
    """Open tickets by department x ward office. Returns depts, wards, cells[dept][ward], max."""
    depts = [d for d in data.dept_codes() if not department or d == department]
    wards = [w for w in data.ward_names() if not ward or w == ward]
    cells = {d: {w: 0 for w in wards} for d in depts}
    for t in _filtered(store, ward, department):
        if t["status"] in OPEN_STATUSES and t["department"] in cells and t["ward"] in cells[t["department"]]:
            cells[t["department"]][t["ward"]] += 1
    mx = max((v for row in cells.values() for v in row.values()), default=0)
    return dict(depts=depts, wards=wards, cells=cells, max=mx)


def override(store: Store, *, ward=None, department=None) -> dict:
    """Officer override rate among auto-routed tickets.

    Denominator: tickets whose triage decision (the system's first event) was auto_routed.
    Numerator: those of them with at least one correction to department, ward or priority.
    Filters apply to the ticket's current ward and department.
    """
    auto = {r["ticket_id"] for r in store.conn.execute(
        "SELECT ticket_id FROM ticket_events WHERE actor = 'system' AND from_status = 'received'"
        " AND to_status = 'auto_routed'")}
    if ward or department:
        keep = {t["id"] for t in _filtered(store, ward, department)}
        auto &= keep
    by_field = {f: set() for f in OVERRIDE_FIELDS}
    for c in store.corrections():
        if c["ticket_id"] in auto and c["field"] in by_field:
            by_field[c["field"]].add(c["ticket_id"])
    overridden = set().union(*by_field.values())
    n = len(auto)
    return dict(auto_routed=n, overridden=len(overridden), rate=(len(overridden) / n) if n else None,
                by_field={f: len(v) for f, v in by_field.items()})


def build(store: Store, *, ward=None, department=None, now: datetime | None = None) -> dict:
    rows = per_ward(store, ward=ward, department=department, now=now)
    return dict(rows=rows, totals=totals(rows), clusters=clusters(store, ward=ward, department=department),
                heat=heat(store, ward=ward, department=department),
                override=override(store, ward=ward, department=department))
