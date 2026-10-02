"""Leakage and shape checks on the frozen data (see docs/DECISIONS.md D2)."""
from collections import Counter

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from nagarvani import data
from nagarvani.normalise import normalise


def test_no_test_sentence_near_copies_training():
    tr = [normalise(r["text"]) for r in data.load_train()]
    te = [normalise(r["text"]) for r in data.load_test()]
    v = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4)).fit(tr)
    assert cosine_similarity(v.transform(te), v.transform(tr)).max() < 0.75


def test_test_set_shape():
    rows = data.load_test()
    assert len(rows) == 160
    assert set(Counter(r["department"] for r in rows).values()) == {16}
    assert Counter(r["language"] for r in rows) == {"mr": 80, "hi": 20, "rom": 30, "mix": 30}
    wards = set(data.ward_names()) | {"UNRESOLVED"}
    assert all(r["ward"] in wards and r["severity"] in {"P1", "P2", "P3", "P4"} for r in rows)


def test_train_set_shape():
    rows = data.load_train()
    assert len(rows) == 2000
    assert Counter(r["language"] for r in rows) == {"mr": 907, "hi": 336, "rom": 388, "mix": 369}


def test_gazetteer_wards_exist():
    wards = set(data.ward_names())
    g = data.gazetteer()
    assert len(wards) == 15
    assert all(loc["ward"] in wards for loc in g["localities"])
    assert all(set(a["wards"]) <= wards for a in g["ambiguous"])
