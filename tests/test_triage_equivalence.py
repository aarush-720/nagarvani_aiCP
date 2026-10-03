"""The wrapper nagarvani.triage.triage makes exactly the decisions of the original
nagarvani.pipeline.Triage.triage (frozen prototype code) on every test complaint."""
from datetime import datetime, timezone

import pytest

from nagarvani import data
from nagarvani import triage as T
from nagarvani.pipeline import Triage


@pytest.fixture(scope="module")
def original():
    return Triage(db_path=":memory:", tau=0.50, model=T.model())


@pytest.mark.parametrize("row", data.load_test(), ids=lambda r: r["id"])
def test_same_decisions(original, row):
    o = original.triage(row["text"], persist=False, now=datetime(2026, 9, 28, 9, 0))
    w = T.triage(row["text"], now=datetime(2026, 9, 28, 9, 0, tzinfo=timezone.utc))
    assert w.department == o["dept"]
    assert round(w.confidence, 4) == o["dept_conf"]
    assert [d for d, _ in w.top3] == [d for d, _ in o["top3"]]
    assert w.ward.ward == o["ward"] and w.ward.locality == o["locality"] and w.ward.status == o["ward_status"]
    assert w.severity["band"] == o["priority"]
    assert [f["rule"] for f in w.severity["fired"]] == (o["rules_fired"].split(",") if o["rules_fired"] else [])
    assert w.route_original == o["route_status"]
    assert (w.gate.decision == "AUTO_ROUTED") == (o["route_status"] == "AUTO_ROUTED")
    assert w.deadline_utc[:16] == o["sla_due"]
