"""Unit tests for each pipeline component, on hand-made examples (not test-set items)."""
from datetime import datetime, timezone

import pytest

from nagarvani import dedup, location, severity
from nagarvani.normalise import normalise
from nagarvani.pipeline import triage
from nagarvani.store import Store


# ---- normalisation ----------------------------------------------------------------------
def test_normalise_basic():
    assert normalise("  Kothrud मध्ये, ROAD!! १२ ") == "kothrud मध्ये road 12"
    assert normalise("a‍b") == "ab"


# ---- location ---------------------------------------------------------------------------
@pytest.mark.parametrize("text,ward,method", [
    ("कोथरूडमध्ये खड्डा", "W08", "exact"),
    ("सदाशिव पेठेत कचरा", "W06", "exact"),
    ("vimannagar la pani nahi", "W09", "exact"),
    ("कोतरूड मध्ये खड्डा", "W08", "fuzzy"),
])
def test_resolve(text, ward, method):
    r = location.resolve(text)
    assert (r.ward, r.method) == (ward, method)


def test_longest_alias_wins_over_ambiguous_prefix():
    assert location.resolve("वडगाव शेरीत पाणी नाही").ward == "W09"


def test_ambiguous_and_unknown_are_not_guessed():
    assert location.resolve("वडगावमध्ये कचरा").status == "ambiguous"
    assert location.resolve("Kothrud ani Baner madhe").status == "ambiguous"
    assert location.resolve("रस्त्यावर खड्डा आहे").status == "unknown"


def test_fuzzy_can_be_disabled():
    assert location.resolve("कोतरूड मध्ये खड्डा", allow_fuzzy=False).ward is None


# ---- severity rules -----------------------------------------------------------------------
@pytest.mark.parametrize("text,dept,band,rule", [
    ("मॅनहोल उघडे आहे", "DRAIN", "P1", "R01"),
    ("wire latkat ahe khamba var", "ELEC", "P1", "R02"),
    ("खांबाला करंट येतो", "ELEC", "P1", "R03"),
    ("झाड रस्त्यावर पडले", "TREE", "P1", "R04"),
    ("सांडपाणी घरात शिरत आहे", "DRAIN", "P1", "R07"),
    ("कुत्र्याने चावा घेतला", "VET", "P1", "R10"),
    ("नळाला पाणी आलेले नाही", "WATER", "P2", "R21"),
    ("कचरा जाळला जात आहे", "SWM", "P2", "R24"),
    ("पथदिवे दिवसा सुरू असतात, विजेची नासाडी", "ELEC", "P4", "R40"),
    ("कचरा गाडी आली नाही", "SWM", "P3", "R00"),
])
def test_rules(text, dept, band, rule):
    r = severity.assess(text, dept)
    assert r.band == band and rule in r.rule_ids


def test_sweeping_does_not_trigger_tree_rule():
    assert "R04" not in severity.assess("रस्ता झाडला जात नाही, झाडू मारत नाहीत", "SWM").rule_ids


def test_vulnerable_raise_and_duplicate_escalation():
    assert severity.assess("शाळेसमोर कचरा आहे", "SWM").band == "P2"
    r = severity.assess("रस्त्यावर खड्डा आहे", "ROAD", report_count=3)
    assert r.band == "P2" and r.rule_ids[-1] == "R32"
    assert severity.assess("मॅनहोल उघडे आहे", "DRAIN", report_count=5).band == "P1"


def test_override_is_recorded():
    r = severity.assess("मॅनहोल उघडे आहे, फक्त विनंती", "DRAIN")
    assert {"rule": "R40", "proposed": "P4", "by": "R01"} in r.overridden


def test_firing_order_follows_salience():
    r = severity.assess("शाळेजवळ मॅनहोल उघडे आहे", "DRAIN")
    assert r.rule_ids[0] == "R01" and r.rule_ids.index("R00") < len(r.rule_ids)


# ---- duplicates ---------------------------------------------------------------------------
def test_dedup_masks_locations_and_thresholds():
    a, b = dedup.masked("कोथरूडमध्ये रस्त्यावर खड्डा आहे"), dedup.masked("हडपसरमध्ये रस्त्यावर खड्डा आहे")
    assert a == b
    assert dedup.decide(0.45) == "merge" and dedup.decide(0.30) == "review" and dedup.decide(0.2999) == "new"


# ---- pipeline -----------------------------------------------------------------------------
def test_triage_result_fields():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    r = triage("कोथरूडमध्ये रस्त्यावर मोठा खड्डा आहे", now=now)
    assert len(r.top3) == 3 and r.ward.ward == "W08" and r.duplicate["decision"] == "skipped"
    assert r.deadline_utc.startswith("2026-01-08")       # P3 = 168 h
    assert r.gate.decision in ("AUTO_ROUTED", "SENT_TO_REVIEW")


def test_ward_hint_used_only_when_text_fails():
    assert triage("रस्त्यावर मोठा खड्डा आहे", ward_hint="W03").ward.method == "hint"
    r = triage("कोथरूडमध्ये रस्त्यावर मोठा खड्डा आहे", ward_hint="W03")
    assert r.ward.ward == "W08" and not r.ward.hint_used


def test_unresolved_ward_goes_to_review():
    r = triage("रस्त्यावर मोठा खड्डा आहे")
    assert r.ward.ward is None and r.gate.decision == "SENT_TO_REVIEW"


def test_empty_text_rejected():
    with pytest.raises(ValueError):
        triage("!!! 123")


def test_triple_duplicate_merges_and_escalates():
    s = Store(":memory:")
    text = "हडपसर येथे रस्त्यावर खूप मोठे खड्डे पडले आहेत"
    first = triage(text, store=s)
    assert first.gate.decision == "AUTO_ROUTED"
    tid = s.create(channel="typed", text=text, status="auto_routed", department=first.department,
                   ward=first.ward.ward, masked_text=first.masked_text, priority=first.severity["band"])
    second = triage(text, store=s)
    assert second.gate.decision == "MERGED" and second.duplicate["report_count"] == 2
    s.update(tid, report_count=2)
    third = triage(text, store=s)
    assert third.duplicate["report_count"] == 3
    assert [f["rule"] for f in third.severity["fired"]][-1] == "R32"
