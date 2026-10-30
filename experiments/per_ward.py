"""Per-ward breakdown of the end-to-end results (the per-ward audit of PBL-1 objective 10).

    python experiments/per_ward.py              # test_v1 -> results/per_ward.json
    python experiments/per_ward.py --test v2    # test_v2 -> results/test_v2/per_ward.json

Each test complaint is grouped by the ward office of its gold locality ("NONE" when it names no
place) and run through triage() as experiments/run_eval.py does. Per group: department
accuracy, correct ward, auto-route rate and correct-when-routed. The totals equal the E8 counts
in results.json (checked by tests/test_per_ward.py). It changes no reported number. With 5 to
15 complaints per ward, one complaint moves a ward's rate by 7 to 20 points.
"""
import argparse
import glob
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nagarvani import config, data  # noqa: E402
from nagarvani.console import safe_console  # noqa: E402
from nagarvani.pipeline import load_tsv  # noqa: E402
from nagarvani.triage import triage  # noqa: E402


def test_rows(which):
    if which == "v2":
        files = sorted(f for f in glob.glob(str(config.CORPUS / "test_v2_*.tsv")) if "TEMPLATE" not in f)
        if not files:
            sys.exit("No corpus/test_v2_<writer>.tsv files yet (see docs/TEST_V2_GUIDE.md).")
    else:
        files = [str(config.TEST_TSV)]
    return [r for f in files for r in load_tsv(f)]


def per_ward(rows):
    loc2ward = {k: v["ward"] for k, v in data.gazetteer()["localities"].items()}
    g = defaultdict(lambda: dict(n=0, dept_correct=0, ward_correct=0, auto=0, auto_correct=0))
    for r in rows:
        gold_w = loc2ward.get(r["loc"]) if r["loc"] != "NONE" else None
        t = triage(r["text"])
        c = g[gold_w or "NONE"]
        dept_ok, ward_ok = t.department == r["dept"], t.ward.ward == gold_w
        c["n"] += 1
        c["dept_correct"] += dept_ok
        c["ward_correct"] += ward_ok
        if t.route_original == "AUTO_ROUTED":
            c["auto"] += 1
            c["auto_correct"] += dept_ok and ward_ok
    order = list(data.gazetteer()["ward_offices"]) + ["NONE"]
    return {w: g[w] for w in order if w in g}


def main():
    safe_console()
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", choices=["v1", "v2"], default="v1")
    a = ap.parse_args()
    out = config.RESULTS / ("test_v2" if a.test == "v2" else "") / "per_ward.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    res = {"test_set": a.test, "wards": per_ward(test_rows(a.test))}
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for w, c in res["wards"].items():
        print(f"{w:5} n={c['n']:3}  dept {c['dept_correct']:3}/{c['n']:<3}  auto {c['auto']:3}  "
              f"correct when routed {c['auto_correct']}/{c['auto']}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
