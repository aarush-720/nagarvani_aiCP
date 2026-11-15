"""Every demo input still shows the behaviour docs/DEMO_SCRIPT.md claims, on top of the
reset_demo seed data (so seeding cannot break the live duplicate demo)."""
import pytest

from nagarvani import service
from nagarvani.examples import EXAMPLES
from nagarvani.tickets import Store
from scripts import reset_demo

EX = {e["key"]: e["text"] for e in EXAMPLES}


@pytest.fixture(scope="module")
def seeded():
    s = Store(":memory:")
    chosen = reset_demo.seed(s)
    assert len(chosen) == 25
    return s


def run(store, key):
    tid, _ = service.submit(store, text=EX[key], channel="typed")
    return store.get(tid)


def test_seed_mix(seeded):
    st = {t["status"] for t in seeded.tickets()}
    assert {"auto_routed", "review", "closed"} <= st
    assert any(r["overdue"] for r in service.queue(seeded))
    assert {"reopened", "pending_confirmation", "merged"} <= st      # dashboard seed (P4)
    assert len(seeded.corrections()) == 2


def test_seed_for_dashboard(seeded):
    from nagarvani import dashboard
    d = dashboard.build(seeded)
    assert [c["size"] for c in d["clusters"]] == [4] and "R32" in d["clusters"][0]["escalation"]
    T = d["totals"]
    assert T["reopened"] == 2 and T["pending"] == 2 and T["awaiting"] == 1 and T["breached"] > 0
    assert d["override"]["overridden"] == 2


def test_demo_behaviours(seeded):
    import json
    s = seeded
    for key in ("clean_marathi", "romanised", "code_mixed"):
        assert run(s, key)["status"] == "auto_routed", key
    t = run(s, "life_safety")
    assert t["priority"] == "P1" and '"rule": "R02"' in t["trace_json"]
    t = run(s, "fuzzy")
    assert json.loads(t["trace_json"])["ward"]["method"] == "fuzzy" and t["status"] == "auto_routed"
    t = run(s, "unknown_place")
    assert t["status"] == "review" and t["ward"] is None
    t = run(s, "low_confidence")
    assert t["status"] == "review" and t["confidence"] < 0.5 and t["ward"]
    a, b, c = run(s, "dup1"), run(s, "dup2"), run(s, "dup3")
    assert a["status"] == "auto_routed" and b["status"] == c["status"] == "merged"
    parent = s.get(a["id"])
    assert parent["report_count"] == 3 and parent["priority"] == "P2" and "R32" in parent["escalation"]
    t = run(s, "failure")
    assert t["department"] == "SWM" and t["status"] == "auto_routed"        # gold is DRAIN (T054): an uncaught error


def test_run_sheet_v2_examples():
    """Phase 6b run-sheet inputs: Hindi routes, 'झाकण गायब' is P1 via R02 (F2), the vague
    complaint is deferred with NO_ISSUE_STATED (F6), and a citizen's No reopens one band higher."""
    from nagarvani import closure
    s = Store(":memory:")             # own store: the run sheet's order, on top of the seed
    reset_demo.seed(s)
    t = run(s, "clean_marathi")
    tid1 = t["id"]
    t = run(s, "hindi")
    assert t["status"] == "auto_routed" and t["department"] == "SWM" and t["ward"] == "YKD"
    t = run(s, "cover_missing")
    assert t["status"] == "auto_routed" and t["priority"] == "P1" and '"rule": "R02"' in t["trace_json"]
    t = run(s, "vague")
    assert t["status"] == "review" and "NO_ISSUE_STATED" in t["trace_json"]
    closure.transition(s, tid1, "resolve", note="pipeline repaired")
    closure.transition(s, tid1, "report_not_fixed")
    r = s.get(tid1)
    assert r["status"] == "reopened" and r["priority"] == "P1"


def test_run_sheet_generates():
    from scripts import run_demo_script
    ex = {e["key"]: e for e in EXAMPLES}
    text = "\n".join(run_demo_script.run_sheet(ex))
    for step in range(1, 8):
        assert f"### Step {step}" in text
    assert "Fallback" in text and "NO_ISSUE_STATED" in text and "reopened" in text
