"""Ward dashboard (M11): aggregation queries and the /dashboard page."""
from datetime import timedelta

import pytest

from nagarvani import closure, dashboard as dash, service
from nagarvani.app import create_app
from nagarvani.tickets import Store, iso, utcnow

TEXT = "कोथरूडमध्ये रस्त्यावर मोठे खड्डे पडले आहेत"


def mk(s, *, status="auto_routed", dept="ROAD", ward="KOB", prio="P3", deadline_h=24, **kw):
    tid = s.create(channel="seed", text=TEXT, status="received", department=dept, ward=ward, priority=prio,
                   deadline_utc=iso(utcnow() + timedelta(hours=deadline_h)), **kw)
    s.add_event(tid, "system", "received", status if status in ("auto_routed", "review") else "auto_routed")
    s.update(tid, status=status)
    return tid


@pytest.fixture
def s():
    return Store(":memory:")


def row(rows, ward):
    return next(r for r in rows if r["ward"] == ward)


def test_per_ward_counts(s):
    mk(s)                                           # open
    mk(s, prio="P1")                                # P1 open
    mk(s, deadline_h=-5)                            # breached
    mk(s, status="review", ward="AUB")              # deferred
    t = mk(s)
    closure.transition(s, t, "resolve", note="done", now=utcnow() - timedelta(hours=100))   # awaiting > 72 h
    t2 = mk(s)
    closure.transition(s, t2, "resolve", note="done")
    closure.transition(s, t2, "report_not_fixed")                                           # reopened
    t3 = mk(s)
    closure.transition(s, t3, "resolve", note="done")
    closure.transition(s, t3, "confirm_fixed")                                              # closed
    rows = dash.per_ward(s)
    k = row(rows, "KOB")
    assert k["open"] == 4 and k["p1_open"] == 1 and k["breached"] == 1   # reopened t2 is open again (P3 -> P2)
    assert k["reopened"] == 1 and k["pending"] == 1 and k["awaiting"] == 1 and k["closed"] == 1
    assert row(rows, "AUB")["deferred"] == 1 and row(rows, "AUB")["open"] == 1
    assert len(rows) == 15                          # all ward offices, no "no ward" row when empty
    assert dash.totals(rows)["open"] == 5


def test_p1_open_after_reopen_counts_new_band(s):
    t = mk(s, prio="P2")
    closure.transition(s, t, "resolve", note="done")
    closure.transition(s, t, "report_not_fixed")
    assert row(dash.per_ward(s), "KOB")["p1_open"] == 1


def test_no_ward_row_and_filters(s):
    mk(s, status="review", ward=None)
    mk(s, dept="SWM", ward="AUB")
    rows = dash.per_ward(s)
    assert rows[-1]["ward"] is None and rows[-1]["deferred"] == 1
    only = dash.per_ward(s, ward="AUB")
    assert [r["ward"] for r in only] == ["AUB"] and only[0]["open"] == 1
    assert dash.totals(dash.per_ward(s, department="ROAD"))["open"] == 1


def test_clusters_min_size_and_order(s):
    a = mk(s, report_count=4)
    b = mk(s, report_count=3, dept="SWM")
    mk(s, report_count=2)
    c = mk(s, report_count=5)
    closure.transition(s, c, "resolve", note="x")
    closure.transition(s, c, "confirm_fixed")         # closed clusters drop out
    got = dash.clusters(s)
    assert [x["id"] for x in got] == [a, b] and got[0]["size"] == 4
    assert [x["id"] for x in dash.clusters(s, department="SWM")] == [b]


def test_heat_table(s):
    mk(s)
    mk(s)
    mk(s, dept="SWM", ward="AUB")
    t = mk(s, dept="SWM", ward="AUB")
    closure.transition(s, t, "resolve", note="x")     # waiting for citizen: not open
    h = dash.heat(s)
    assert h["cells"]["ROAD"]["KOB"] == 2 and h["cells"]["SWM"]["AUB"] == 1 and h["max"] == 2
    assert len(h["depts"]) == 10 and len(h["wards"]) == 15
    assert dash.heat(s, ward="KOB")["wards"] == ["KOB"]


def test_override_rate(s):
    a, b, c = mk(s), mk(s), mk(s)
    r = mk(s, status="review")                        # not auto-routed: not in the denominator
    service.correct(s, a, department="SWM")
    service.correct(s, a, priority="P1")              # two fields, counted once
    service.correct(s, r, department="SWM")
    o = dash.override(s)
    assert o["auto_routed"] == 3 and o["overridden"] == 1 and o["rate"] == pytest.approx(1 / 3)
    assert o["by_field"] == {"department": 1, "ward": 0, "priority": 1}
    assert dash.override(Store(":memory:"))["rate"] is None


def test_dashboard_page(tmp_path):
    app = create_app(tmp_path / "t.sqlite3", load_asr=False, upload_dir=tmp_path / "u")
    s = app.extensions["nagarvani"]["store"]
    mk(s, report_count=3)
    c = app.test_client()
    r = c.get("/dashboard")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "Ward dashboard" in body and "3 reports" in body and "override rate" in body
    assert c.get("/dashboard?ward=KOB&department=ROAD").status_code == 200
    assert c.get("/dashboard?ward=NOPE&department=<x>").status_code == 200    # bad filters ignored
    assert "cdn" not in body.lower() and "http://" not in body and "https://" not in body
