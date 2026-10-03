"""Unit tests for the wrapper layer (explanations, hint, live duplicates, R32), on hand-made
examples that are not test-set items."""
import inspect
from datetime import datetime, timezone

import pytest

from nagarvani import config
from nagarvani import triage as T
from nagarvani.classifier import char_word_lr
from nagarvani.dedup import DuplicateDetector
from nagarvani.location import WardResolver
from nagarvani.pipeline import Triage
from nagarvani.tickets import Store


def default(fn, name):
    return inspect.signature(fn).parameters[name].default


def test_display_constants_mirror_the_frozen_code():
    assert config.GATE_MIN_CONFIDENCE == default(Triage.__init__, "tau") == T.TAU
    assert config.FUZZY_MIN_RATIO == default(WardResolver.__init__, "fuzzy_threshold")
    assert config.DUP_MERGE == default(DuplicateDetector.__init__, "theta_high")
    assert config.DUP_REVIEW == default(DuplicateDetector.__init__, "theta_low")
    assert config.CLASSIFIER_C == default(char_word_lr, "C")


def test_result_fields_and_deadline():
    r = T.triage("कोथरूडमध्ये रस्त्यावर मोठा खड्डा आहे", now=datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert len(r.top3) == 3 and r.ward.ward == "KOB" and r.ward.method == "exact"
    assert r.ward.matched_alias and r.duplicate["decision"] == "skipped"
    assert r.severity["band"] == "P3" and r.deadline_utc.startswith("2026-01-08")


def test_life_safety_rule_with_cue_terms():
    r = T.triage("धनकवडीत मॅनहोलचे झाकण उघडे आहे")
    fired = {f["rule"]: f for f in r.severity["fired"]}
    assert r.department == "DRAIN" and r.severity["band"] == "P1" and "R02" in fired
    assert set(fired["R02"]["cues"]) >= {"COVER", "OPEN"}


def test_overridden_rules_are_reported():
    r = T.triage("धनकवडीत मॅनहोलचे झाकण उघडे आहे, खूप धोका आहे")
    over = {o["rule"] for o in r.severity["overridden"]}
    assert r.severity["band"] == "P1" and "R10" in over


def test_fuzzy_score_is_shown():
    r = T.triage("कोतरूड मध्ये रस्त्यावर खड्डा")
    if r.ward.method == "fuzzy":
        assert r.ward.score >= config.FUZZY_MIN_RATIO and r.ward.ward == "KOB"
    else:
        pytest.skip("this spelling resolved exactly")


def test_ward_hint_only_fills_a_gap():
    r = T.triage("रस्त्यावर मोठा खड्डा आहे", ward_hint="BIB")
    assert r.ward.method == "hint" and r.ward.ward == "BIB" and r.route_original == "NODAL_REVIEW"
    r = T.triage("कोथरूडमध्ये रस्त्यावर मोठा खड्डा आहे", ward_hint="BIB")
    assert r.ward.ward == "KOB" and not r.ward.hint_used


def test_unresolved_ward_goes_to_review():
    r = T.triage("रस्त्यावर मोठा खड्डा आहे")
    assert r.ward.ward is None and r.gate.decision == "SENT_TO_REVIEW"


def test_empty_text_rejected():
    with pytest.raises(ValueError):
        T.triage("!!! 123")


def test_live_triple_duplicate_escalates():
    s = Store(":memory:")
    text = "हडपसर येथे रस्त्यावर खूप मोठे खड्डे पडले आहेत"
    first = T.triage(text, store=s)
    assert first.gate.decision == "AUTO_ROUTED" and first.duplicate["decision"] == "new"
    tid = s.create(channel="typed", text=text, status="auto_routed", department=first.department,
                   ward=first.ward.ward, priority=first.severity["band"])
    second = T.triage(text, store=s)
    assert second.gate.decision == "MERGED" and second.duplicate["report_count"] == 2
    s.create(channel="typed", text=text, status="merged", department=second.department, ward=second.ward.ward,
             parent_id=tid)
    s.update(tid, report_count=2)
    third = T.triage(text, store=s)
    assert third.duplicate["report_count"] == 3 and "R32" in [f["rule"] for f in third.severity["fired"]]
