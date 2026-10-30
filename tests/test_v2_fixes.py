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
