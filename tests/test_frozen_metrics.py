"""Guard: the evaluation reproduces the numbers reported in the PBL-4 report and PBL-5 paper.

Runs experiments/run_eval.py (the prototype's own evaluation, with its end-to-end stream
routed through nagarvani.triage.triage) into a temporary folder, then
  1. asserts every reported value (counts exactly, rates to the precision reported), and
  2. checks that the whole results.json equals both the committed results/results.json and the
     prototype's shipped results/results_shipped.json (timings excluded; floats to 1e-12).
If this fails, something changed behaviour on the frozen data. Do not edit the expected values
to make it pass (see CLAUDE.md).
"""
import json
import math
import os
import subprocess
import sys

import pytest

from nagarvani import results_view
from tests.conftest import ROOT


@pytest.fixture(scope="module")
def R(tmp_path_factory):
    out = tmp_path_factory.mktemp("results")
    env = dict(os.environ, NAGARVANI_RESULTS_DIR=str(out))
    r = subprocess.run([sys.executable, str(ROOT / "experiments" / "run_eval.py")], cwd=ROOT, env=env,
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr[-3000:]
    return json.loads((out / "results.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def S(R):
    return results_view.summary(R)


@pytest.mark.parametrize("key,count,total", [
    ("dept_acc", 139, 160),                 # 86.9%
    ("dept_top3", 153, 160),                # 95.6%
    ("keyword_acc", 131, 160),              # 81.9%
    ("char_only_acc", 142, 160),            # 88.8% (reported, not adopted)
    ("auto_rate", 112, 160),                # 70%
    ("auto_correct", 109, 112),             # 97.3%
    ("dept_errors_caught", 18, 21),         # 18 of 21
    ("sev_acc_pred", 153, 160),             # 95.6%
    ("p1_recall_pred", 34, 36),             # 94.4%
    ("sev_learned", 123, 160),              # 76.9%
])
def test_reported_counts(S, key, count, total):
    assert (S[key]["count"], S[key]["total"]) == (count, total)


def test_reported_rates(S, R):
    assert round(100 * S["dept_acc"]["rate"], 1) == 86.9
    assert round(S["dept_macro_f1"], 3) == 0.870
    assert round(100 * S["dept_top3"]["rate"], 1) == 95.6
    assert round(100 * S["keyword_acc"]["rate"], 1) == 81.9
    assert round(100 * S["char_only_acc"]["rate"], 1) == 88.8
    assert round(100 * S["cv_template_acc"], 1) == 99.8
    assert round(100 * S["auto_rate"]["rate"]) == 70
    assert round(100 * S["auto_correct"]["rate"], 1) == 97.3
    assert round(100 * S["sev_acc_pred"]["rate"], 1) == 95.6
    assert round(100 * S["p1_recall_pred"]["rate"], 1) == 94.4
    assert round(100 * S["sev_learned"]["rate"], 1) == 76.9
    n10 = S["noise10"]
    assert round(n10["dept_macro_f1"], 3) == 0.811
    assert round(100 * n10["ward_acc_exact"]) == 49
    assert round(100 * n10["ward_acc"]) == 93
    assert R["E1_C_search"]["10"] == max(R["E1_C_search"].values())     # C=10 chosen by CV on train


def _flat(d, p=""):
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(_flat(v, f"{p}/{k}"))
    elif isinstance(d, list):
        for i, v in enumerate(d):
            out.update(_flat(v, f"{p}[{i}]"))
    else:
        out[p] = d
    return out


def _same(a, b):
    fa, fb = _flat(a), _flat(b)
    assert set(fa) == set(fb)
    bad = []
    for k in fa:
        if "second" in k or "latency" in k:
            continue
        x, y = fa[k], fb[k]
        if isinstance(x, float) and isinstance(y, float):
            if not ((math.isnan(x) and math.isnan(y)) or abs(x - y) <= 1e-12):
                bad.append((k, x, y))
        elif x != y:
            bad.append((k, x, y))
    return bad


def test_matches_committed_results(R):
    committed = json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))
    assert _same(R, committed) == []


def test_matches_prototype_shipped_results(R):
    shipped = json.loads((ROOT / "results" / "results_shipped.json").read_text(encoding="utf-8"))
    assert _same(R, shipped) == []
