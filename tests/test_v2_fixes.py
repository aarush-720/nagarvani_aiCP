"""Defects F1-F6 (docs/DECISIONS.md), fixed in v2.0. Each test reproduces the reported input."""
from nagarvani.location import WardResolver


def test_f4_alias_order_is_deterministic():
    r = WardResolver()
    assert r.aliases == sorted(r.aliases, key=lambda p: (-len(p[0]), p))


def test_f1_common_words_never_fuzzy_match_a_locality():
    r = WardResolver()
    loc = r.resolve("डीपी बॉक्सचं दार उघडं आहे आणि वायर बाहेर आलेत, मुलं जवळ खेळतात")   # T080: बाहेर ≈ बाणेर
    assert loc["status"] == "unresolved" and loc["ward"] is None
    for text in ["kara kahitari", "undir khup zale aahet", "road bandh aahe", "baher kachra padla aahe",
                 "illegal banners lagle aahet"]:
        assert r.resolve(text)["ward"] is None, text


def test_f1_misspelt_places_still_fuzzy_match():
    r = WardResolver()
    loc = r.resolve("हडप्सर मध्ये कचऱ्याचा मोठा ढीग साचला आहे")
    assert loc["ward"] == "HMU" and loc.get("fuzzy")
    assert r.resolve("baner madhe kachra")["ward"] == "AUB"                 # exact match is unaffected


import pytest  # noqa: E402

from nagarvani.severity import infer  # noqa: E402


@pytest.mark.parametrize("text", [
    "मॅनहोलचे झाकण गायब आहे",                    # the reported input
    "chamber cha jhakan gayab aahe",
    "गटाराचं झाकण चोरीला गेलं आहे",
    "मैनहोल का ढक्कन टूट गया है",
    "manhole cha jhakan missing aahe",
])
def test_f2_missing_or_broken_cover_is_an_open_manhole(text):
    r = infer(text, "DRAIN")
    assert r["band"] == "P1" and "R02" in r["fired"]


@pytest.mark.parametrize("text", [
    "मॅनहोलचे झाकण नवीन बसवले, आता काही समस्या नाही",   # the reported input: resolved, not a hazard
    "गटाराचे झाकण तुटलेलं नाही पण घाण वास येतो",          # "not broken"
    "चेंबरचं झाकण उघडं नाही, फक्त थोडं हललेलं आहे",        # "not open"
])
def test_f3_negated_or_unrelated_nahi_is_not_an_open_manhole(text):
    assert "R02" not in infer(text, "DRAIN")["fired"]


@pytest.mark.parametrize("text", [
    "मॅनहोलचे झाकण नाही, मुलं पडू शकतात",                 # "no cover" is still the hazard
    "झाकणच नाही",
    "chamber cha jhakan nahi aahe",
    "मैनहोल का ढक्कन नहीं है",
    "drainage chya chamber la slab नाही",
    "मॅनहोलचे झाकण उघडे आहे, कोणी लक्ष देत नाही",         # open, and a later unrelated नाही
])
def test_f3_no_cover_is_still_an_open_manhole(text):
    r = infer(text, "DRAIN")
    assert r["band"] == "P1" and "R02" in r["fired"]


def test_f3_trace_names_the_no_cover_phrase():
    from nagarvani.triage import triage
    fired = triage("कोथरूडमध्ये मॅनहोलचे झाकण नाही, मुलं पडू शकतात").severity["fired"]
    r02 = next(f for f in fired if f["rule"] == "R02")
    assert r02["cues"]["OPEN"] == "झाकण नाही"


@pytest.mark.parametrize("text", [
    "चार दिवसांपासून नळाला पाणी आलेले नाही",              # the reported input (standard spelling)
    "तीन दिवसांपासून पाणी आलं नाही",
    "दोन दिवसांपासून पाणीच नाही",
    "4 divas pasun pani aala nahi",
    "तीन दिन से पानी नहीं है",
])
def test_f5_outage_spellings_fire_r12(text):
    r = infer(text, "WATER")
    assert r["band"] == "P2" and "R12" in r["fired"]
