"""Closure verification (nagarvani/closure.py): every transition, and that 'closed' is reachable
only through the citizen's confirmation."""
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from nagarvani import closure, config, service
from nagarvani.closure import CLOSED, PENDING, REOPENED, ClosureError, transition
from nagarvani.tickets import SCHEMA, Store, iso

T0 = datetime(2026, 10, 30, 9, 0, tzinfo=timezone.utc)


@pytest.fixture
def s():
    return Store(":memory:")


def ticket(s, status="auto_routed", priority="P3", **kw):
    return s.create(now=T0, channel="seed", text="कोथरूडमध्ये रस्त्यावर खड्डे", status=status,
                    department="ROAD", ward="KOB", priority=priority,
                    deadline_utc=iso(T0 + timedelta(hours=168)), **kw)


@pytest.mark.parametrize("start", ["auto_routed", "review", "routed", "reopened"])
def test_officer_resolve_waits_for_the_citizen(s, start):
    tid = ticket(s, start)
    assert transition(s, tid, "resolve", note="खड्डा बुजवला", now=T0) == PENDING
    t = s.get(tid)
    assert t["status"] == PENDING and t["resolution_note"] == "खड्डा बुजवला" and t["closed_utc"] is None
    assert t["pending_since_utc"] == iso(T0)


def test_resolve_needs_a_note(s):
    tid = ticket(s)
    with pytest.raises(ClosureError):
        transition(s, tid, "resolve", note="   ")
    assert s.get(tid)["status"] == "auto_routed"


def test_citizen_yes_closes(s):
    tid = ticket(s)
    transition(s, tid, "resolve", note="done", now=T0)
    assert transition(s, tid, "confirm_fixed", now=T0 + timedelta(hours=5)) == CLOSED
    assert s.get(tid)["closed_utc"] == iso(T0 + timedelta(hours=5))


def test_citizen_no_reopens_raises_priority_and_restarts_the_deadline(s):
    tid = ticket(s, priority="P3")
    transition(s, tid, "resolve", note="done", now=T0)
    later = T0 + timedelta(days=2)
    assert transition(s, tid, "report_not_fixed", note="खड्डा अजून आहे", now=later) == REOPENED
    t = s.get(tid)
    assert t["priority"] == "P2" and t["deadline_utc"] == iso(later + timedelta(hours=72))
    assert t["reopen_count"] == 1 and t["citizen_comment"] == "खड्डा अजून आहे" and "P3 → P2" in t["escalation"]
    assert t["status"] in service.OPEN_STATUSES                       # back in the queue
    transition(s, tid, "resolve", note="again", now=later)            # can be resolved again
    transition(s, tid, "report_not_fixed", now=later)
    assert s.get(tid)["priority"] == "P1"


def test_p1_stays_p1_when_reopened(s):
    tid = ticket(s, priority="P1")
    transition(s, tid, "resolve", note="done", now=T0)
    transition(s, tid, "report_not_fixed", now=T0)
    assert s.get(tid)["priority"] == "P1"


@pytest.mark.parametrize("start", ["auto_routed", "review", "routed", "reopened", "merged", "received", CLOSED])
@pytest.mark.parametrize("action", ["confirm_fixed", "report_not_fixed"])
def test_citizen_can_only_answer_a_pending_ticket(s, start, action):
    tid = ticket(s, start)
    with pytest.raises(ClosureError):
        transition(s, tid, action)
    assert s.get(tid)["status"] == start


@pytest.mark.parametrize("start", [PENDING, CLOSED, "merged", "received"])
def test_officer_cannot_resolve_from(s, start):
    tid = ticket(s, start)
    with pytest.raises(ClosureError):
        transition(s, tid, "resolve", note="x")


def test_closed_is_reachable_only_through_the_citizen():
    targets = {action: (actor, to) for action, (actor, _, to) in closure.TRANSITIONS.items()}
    assert [a for a, (actor, to) in targets.items() if to == CLOSED] == ["confirm_fixed"]
    assert targets["confirm_fixed"][0] == "citizen"
    with pytest.raises(ClosureError):
        transition(Store(":memory:"), 1, "close")


def test_no_officer_action_closes(s):
    tid = ticket(s, "review")
    service.correct(s, tid, department="ROAD", ward="KOB", priority="P2", note="x")
    service.confirm(s, tid)
    service.resolve(s, tid, note="fixed")
    with pytest.raises(service.ActionError):
        service.resolve(s, tid, note="fixed again")
    assert s.get(tid)["status"] == PENDING


def test_merged_reports_follow_the_parent_when_closed(s):
    parent = ticket(s)
    child = ticket(s, "merged", parent_id=parent)
    transition(s, parent, "resolve", note="done", now=T0)
    assert s.get(child)["status"] == "merged"
    transition(s, parent, "report_not_fixed", now=T0)
    assert s.get(child)["status"] == "merged"
    transition(s, parent, "resolve", note="done", now=T0)
    transition(s, parent, "confirm_fixed", now=T0)
    assert s.get(child)["status"] == CLOSED


def test_awaiting_flag_after_the_window_but_never_closed(s):
    tid = ticket(s)
    transition(s, tid, "resolve", note="done", now=T0)
    window = timedelta(hours=config.CONFIRMATION_WINDOW_HOURS)
    assert not closure.awaiting(s.get(tid), T0 + window - timedelta(minutes=1))
    assert closure.awaiting(s.get(tid), T0 + window + timedelta(minutes=1))
    rows = service.queue(s, status=PENDING, now=T0 + 10 * window)
    assert rows[0]["awaiting"] and not rows[0]["overdue"] and s.get(tid)["status"] == PENDING


def test_every_state_change_is_recorded_with_its_actor(s):
    tid = ticket(s, "review")
    service.correct(s, tid, department="ROAD", ward="KOB", priority="P3")
    service.confirm(s, tid, note="ok")
    transition(s, tid, "resolve", note="done", now=T0)
    transition(s, tid, "report_not_fixed", note="no", now=T0)
    transition(s, tid, "resolve", note="done properly", now=T0)
    transition(s, tid, "confirm_fixed", now=T0)
    ev = [(e["actor"], e["from_status"], e["to_status"]) for e in s.events(tid)]
    assert ev == [("officer", "review", "routed"), ("officer", "routed", PENDING), ("citizen", PENDING, REOPENED),
                  ("officer", REOPENED, PENDING), ("citizen", PENDING, CLOSED)]
    assert all(e["at_utc"] for e in s.events(tid))


def test_triage_records_the_first_event(s):
    tid, _ = service.submit(s, text="कोथरूडमध्ये रस्त्यावर मोठे खड्डे पडले आहेत", channel="typed")
    (e,) = s.events(tid)
    assert (e["actor"], e["from_status"], e["to_status"]) == ("system", "received", s.get(tid)["status"])


def test_old_database_gains_the_new_columns(tmp_path):
    db = tmp_path / "old.sqlite3"
    con = sqlite3.connect(db)
    con.executescript(SCHEMA.split("CREATE TABLE IF NOT EXISTS ticket_events")[0])     # the v1.0 schema
    con.execute("INSERT INTO tickets (created_utc, updated_utc, channel, text, status) VALUES ('x','x','seed','t','resolved')")
    con.commit(); con.close()
    s = Store(db)
    t = s.get(1)
    assert t["status"] == "resolved" and t["reopen_count"] == 0 and t["resolution_note"] is None
    assert s.events(1) == []
