"""Guard: the evaluation must reproduce the numbers frozen at the end of Phase 1.

Counts are asserted exactly; rates to the precision they are reported at. If this test
fails, something changed the pipeline's behaviour on the frozen data. Do not edit the
expected values to make it pass: find what changed (see CLAUDE.md).
"""
import pytest

from eval import evaluate as ev

EXPECTED_COUNTS = {
    ("department", "accuracy"): (151, 160),
    ("department", "top3_accuracy"): (157, 160),
    ("baselines", "keyword", "accuracy"): (115, 160),
    ("baselines", "char_only_logreg", "accuracy"): (150, 160),
    ("ward", "correct"): (135, 137),
    ("ward", "correctly_left_unresolved"): (22, 23),
    ("gate", "auto_routed"): (122, 160),
    ("gate", "auto_routed_correct_department_and_ward"): (118, 122),
    ("gate", "department_errors_caught_by_gate"): (5, 9),
    ("severity", "band_accuracy_predicted_department"): (135, 160),
    ("severity", "band_accuracy_gold_department"): (135, 160),
    ("severity", "p1_recall"): (29, 30),
    ("severity", "p1_precision"): (29, 32),
    ("severity", "learned_logreg_baseline", "accuracy"): (118, 160),
    ("duplicates", "merge_recall"): (18, 30),
    ("duplicates", "merge_precision"): (18, 18),
    ("simulated_noise", "department_accuracy"): (126, 160),
    ("simulated_noise", "ward_accuracy_exact_only"): (43, 137),
    ("simulated_noise", "ward_accuracy_with_fuzzy"): (117, 137),
    ("external_midsem", "department_accuracy_coarse"): (370, 435),
    ("external_midsem", "severity_band_agreement"): (151, 260),
    ("external_midsem", "severity_p1_recall"): (17, 25),
}
EXPECTED_VALUES = {
    ("department", "macro_f1"): 0.944,
    ("department", "cv_accuracy_on_train"): 0.999,
    ("simulated_noise", "department_macro_f1"): 0.787,
}


@pytest.fixture(scope="module")
def results():
    return ev.evaluate()


def dig(d, path):
    for k in path:
        d = d[k]
    return d


@pytest.mark.parametrize("path,expected", EXPECTED_COUNTS.items(), ids=lambda x: str(x))
def test_counts(results, path, expected):
    r = dig(results, path)
    assert (r["count"], r["total"]) == expected


@pytest.mark.parametrize("path,expected", EXPECTED_VALUES.items(), ids=lambda x: str(x))
def test_values(results, path, expected):
    assert round(dig(results, path), 3) == expected


def test_classifier_choice(results):
    assert results["_provenance"]["classifier_C"] == 100.0


def test_duplicate_decisions(results):
    d = results["duplicates"]
    assert d["true_duplicate_pairs"] == {"merge": 18, "review": 6, "new": 6}
    assert d["non_duplicate_pairs"] == {"merge": 0, "review": 6, "new": 24}


def test_committed_results_match(results):
    """results/eval.json in the repo is exactly what this code produces."""
    import json
    text = json.dumps(results, ensure_ascii=False, indent=2) + "\n"
    assert ev.OUT_JSON.read_text(encoding="utf-8") == text
