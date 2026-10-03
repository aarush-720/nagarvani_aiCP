"""Headline figures derived from results/results.json (written by experiments/run_eval.py).

Used by the /about page and scripts/write_results_md.py, so no number is typed by hand.
Rates are returned with the counts they come from.
"""
from __future__ import annotations

import json

from . import config

PROPOSED = "Char + word TF-IDF + LogReg (proposed)"


def rate(k, n):
    return {"count": int(k), "total": int(n), "rate": (k / n) if n else None}


def load(path=None):
    p = path or config.RESULTS_JSON
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def summary(R: dict) -> dict:
    n = R["data"]["n_test"]
    e1 = R["E1_dept"]
    prop = e1[PROPOSED]
    n_correct = round(prop["acc"] * n)
    e8 = R["E8_end_to_end"]
    c8 = e8["counts"]
    n_auto = c8.get("auto_correct", 0) + c8.get("auto_wrong_dept", 0) + c8.get("auto_wrong_ward", 0)
    n_err = n - n_correct
    e4 = R["E4_ward"]
    sev = R["E5_severity"]
    e7 = {round(x["cer"], 2): x for x in R["E7_asr_noise"]}
    n_p1 = R["data"]["test_sev"]["P1"]
    return {
        "n_test": n, "n_train": R["data"]["n_train"],
        "dept_acc": rate(n_correct, n),
        "dept_macro_f1": prop["macro_f1"],
        "dept_top3": rate(round(prop["top3"] * n), n),
        "dept_by_lang": prop["by_lang"],
        "keyword_acc": rate(round(e1["Keyword lexicon (no ML)"]["acc"] * n), n),
        "char_only_acc": rate(round(e1["Char n-gram TF-IDF + LogReg"]["acc"] * n), n),
        "models": {k: v["acc"] for k, v in e1.items()},
        "cv_template_acc": R["E1_cv_template"]["acc"],
        "c_search": R["E1_C_search"],
        "ward_correct": rate(e4["counts"].get("correct", 0), e4["n_with_locality"]),
        "ward_correctly_unresolved": rate(e4["counts"].get("correctly_unresolved", 0), e4["n_without"]),
        "ward_false_resolution": e4["counts"].get("false_resolution", 0),
        "auto_rate": rate(n_auto, n),
        "auto_correct": rate(c8.get("auto_correct", 0), n_auto),
        "dept_errors_caught": rate(n_err - c8.get("auto_wrong_dept", 0), n_err),
        "sev_acc_pred": rate(round(sev["rules_pred_dept"]["acc"] * n), n),
        "sev_acc_gold": rate(round(sev["rules_gold_dept"]["acc"] * n), n),
        "p1_recall_pred": rate(round(sev["rules_pred_dept"]["p1_recall"] * n_p1), n_p1),
        "sev_learned": rate(round(sev["learned_logreg"]["acc"] * n), n),
        "sev_majority": rate(round(sev["majority_P3"]["acc"] * n), n),
        "dedup_merge": R["E6_dedup"]["merge_block"],
        "dedup_n_pairs": len(R["E6_dedup"]["pairs"]),
        "noise10": e7.get(0.1), "noise20": e7.get(0.2),
        "template_gap_points": 100 * (R["E1_cv_template"]["acc"] - prop["acc"]),
    }
