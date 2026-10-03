"""Shape checks on the frozen data: what the report says the data is."""
from collections import Counter

from nagarvani import data
from nagarvani.classifier import DEPARTMENTS
from nagarvani.severity import CUES, RULES


def test_train_corpus():
    rows = data.load_train()
    assert len(rows) == 2000
    assert Counter(r["lang"] for r in rows) == {"mr": 907, "hi": 336, "mr-rom": 388, "mix": 369}
    assert {r["dept"] for r in rows} == set(DEPARTMENTS)


def test_test_set():
    rows = data.load_test()
    assert len(rows) == 160
    assert set(Counter(r["dept"] for r in rows).values()) == {16}
    assert Counter(r["lang"] for r in rows) == {"mr": 80, "hi": 20, "mr-rom": 30, "mix": 30}
    assert {r["sev"] for r in rows} <= {"P1", "P2", "P3", "P4"}
    locs = set(data.gazetteer()["localities"]) | {"NONE"}
    assert all(r["loc"] in locs for r in rows)


def test_no_test_text_in_training():
    train = {r["text"] for r in data.load_train()}
    assert not any(r["text"] in train for r in data.load_test())


def test_duplicate_pairs():
    pairs = data.load_pairs()
    assert len(pairs) == 30
    test_ids = {r["id"] for r in data.load_test()}
    assert all(p["a_id"] in test_ids for p in pairs)


def test_gazetteer_and_rules():
    g = data.gazetteer()
    assert len(g["ward_offices"]) == 15 and len(g["localities"]) == 59
    assert all(v["ward"] in g["ward_offices"] for v in g["localities"].values())
    assert len(RULES) == 19 and len(CUES) == 23
