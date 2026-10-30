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
