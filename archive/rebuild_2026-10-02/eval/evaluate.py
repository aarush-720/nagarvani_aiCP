"""Offline evaluation on the frozen test data. Writes results/eval.json and results/eval.md.

    python eval/evaluate.py           # run and write
    python eval/evaluate.py --check   # run and compare with the committed results/eval.json

Everything that the demo shows is measured through nagarvani.pipeline.triage (store=None),
so the numbers come from the same code path as the web app. Baselines use separate code.
The output contains no timestamps, so a re-run gives a byte-identical file.
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import sklearn  # noqa: E402
from sklearn.metrics import accuracy_score, f1_score  # noqa: E402

from nagarvani import classifier, config, data, dedup, location, severity  # noqa: E402
from nagarvani.console import safe_console  # noqa: E402
from nagarvani.normalise import normalise  # noqa: E402
from nagarvani.pipeline import triage  # noqa: E402

OUT_JSON = config.RESULTS / "eval.json"
OUT_MD = config.RESULTS / "eval.md"
NOISE_RATE = 0.10
NOISE_SEED = 7
EXTERNAL_MAP = {"roads": {"ROAD"}, "solid_waste": {"SWM"}, "water_supply": {"WATER"}, "drainage": {"DRAIN"},
                "street_lights": {"ELEC"}, "trees_garden": {"TREE"}, "encroachment": {"ENCROACH", "BUILD"},
                "health_mosquito": {"HEALTH", "VET"}}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rate(k, n):
    return {"count": int(k), "total": int(n), "rate": round(k / n, 4) if n else None}


# ---------------------------------------------------------------------------------------
def keyword_baseline(text):
    norm = normalise(text)
    kw = data.keywords()
    scores = {d: sum(k in norm for k in kw[d]) for d in data.dept_codes()}
    best = max(data.dept_codes(), key=lambda d: scores[d])   # first department wins ties
    return best


def add_noise(text, rng, p=NOISE_RATE):
    """Simulated recognition errors: each character is, with probability p, substituted,
    deleted, or followed by an inserted character from the same script. A SIMULATION, not ASR."""
    dev = [chr(c) for c in range(0x0905, 0x0939)] + [chr(c) for c in range(0x093E, 0x094D)]
    lat = list("abcdefghijklmnopqrstuvwxyz")
    out = []
    for ch in text:
        if ch.isspace() or rng.random() >= p:
            out.append(ch)
            continue
        pool = dev if "ऀ" <= ch <= "ॿ" else lat
        op = rng.choice(("sub", "del", "ins"))
        if op == "sub":
            out.append(rng.choice(pool))
        elif op == "ins":
            out.extend([ch, rng.choice(pool)])
    return "".join(out)


def ward_outcome(pred_ward, gold_ward):
    if gold_ward == "UNRESOLVED":
        return "correctly_unresolved" if pred_ward is None else "wrongly_resolved"
    if pred_ward is None:
        return "unresolved"
    return "correct" if pred_ward == gold_ward else "wrong"


# ---------------------------------------------------------------------------------------
def evaluate():
    test = data.load_test()
    depts = data.dept_codes()
    model, meta = classifier.load()
    y = [r["department"] for r in test]

    results = [triage(r["text"]) for r in test]
    pred = [res.department for res in results]
    conf = [res.confidence for res in results]
    top3 = [[d for d, _ in res.top3] for res in results]
    correct = [p == g for p, g in zip(pred, y)]

    out = {"_provenance": {
        "generated_by": "eval/evaluate.py", "sklearn": sklearn.__version__,
        "classifier_C": meta["C"], "classifier_selection": meta["selection"],
        "train_sha256": sha(config.TRAIN_CSV), "test_sha256": sha(config.TEST_CSV),
        "pairs_sha256": sha(config.PAIRS_CSV), "rules_sha256": sha(config.DATA / "severity_rules.json"),
        "gazetteer_sha256": sha(config.DATA / "gazetteer.json"),
        "thresholds": {"gate_min_confidence": config.GATE_MIN_CONFIDENCE, "fuzzy_min_ratio": config.FUZZY_MIN_RATIO,
                       "dup_merge": config.DUP_MERGE, "dup_review": config.DUP_REVIEW}}}

    # ---- department -------------------------------------------------------------------
    by_lang = defaultdict(lambda: [0, 0])
    for r, c in zip(test, correct):
        by_lang[r["language"]][0] += c
        by_lang[r["language"]][1] += 1
    per_class = f1_score(y, pred, labels=depts, average=None, zero_division=0)
    confusion = {g: dict(Counter(p for p, gg in zip(pred, y) if gg == g)) for g in depts}
    errors = [{"id": r["id"], "text": r["text"], "gold": g, "pred": p, "confidence": round(c, 4),
               "top3": t3} for r, g, p, c, t3 in zip(test, y, pred, conf, top3) if g != p]
    out["department"] = {
        "n_test": len(test),
        "accuracy": rate(sum(correct), len(test)),
        "macro_f1": round(float(f1_score(y, pred, labels=depts, average="macro", zero_division=0)), 4),
        "top3_accuracy": rate(sum(g in t for g, t in zip(y, top3)), len(test)),
        "accuracy_by_language": {k: rate(*v) for k, v in sorted(by_lang.items())},
        "f1_by_department": {d: round(float(f), 4) for d, f in zip(depts, per_class)},
        "confusion": confusion,
        "errors": errors,
        "cv_accuracy_on_train": round(meta["cv_accuracy"], 4),
        "cv_by_C": meta["cv_by_C"],
    }

    # ---- baselines ----------------------------------------------------------------------
    kw_pred = [keyword_baseline(r["text"]) for r in test]
    char_model, char_meta = classifier.fit(char_only=True)
    char_pred = list(char_model.predict([normalise(r["text"]) for r in test]))
    out["baselines"] = {
        "keyword": {"accuracy": rate(sum(p == g for p, g in zip(kw_pred, y)), len(test)),
                    "macro_f1": round(float(f1_score(y, kw_pred, labels=depts, average="macro", zero_division=0)), 4)},
        "char_only_logreg": {"C": char_meta["C"],
                             "accuracy": rate(sum(p == g for p, g in zip(char_pred, y)), len(test)),
                             "macro_f1": round(float(f1_score(y, char_pred, labels=depts, average="macro",
                                                              zero_division=0)), 4),
                             "note": "reported for comparison only; the adopted model was fixed before this ran"},
    }

    # ---- ward ---------------------------------------------------------------------------
    outcomes = [ward_outcome(res.ward.ward, r["ward"]) for res, r in zip(results, test)]
    gold_known = [o for o, r in zip(outcomes, test) if r["ward"] != "UNRESOLVED"]
    gold_unres = [o for o, r in zip(outcomes, test) if r["ward"] == "UNRESOLVED"]
    by_case = defaultdict(Counter)
    for o, r in zip(outcomes, test):
        by_case[r["loc_case"]][o] += 1
    methods = Counter(res.ward.method for res in results)
    out["ward"] = {
        "items_with_known_ward": len(gold_known),
        "correct": rate(gold_known.count("correct"), len(gold_known)),
        "wrong": rate(gold_known.count("wrong"), len(gold_known)),
        "unresolved": rate(gold_known.count("unresolved"), len(gold_known)),
        "items_without_resolvable_ward": len(gold_unres),
        "correctly_left_unresolved": rate(gold_unres.count("correctly_unresolved"), len(gold_unres)),
        "wrongly_resolved": rate(gold_unres.count("wrongly_resolved"), len(gold_unres)),
        "resolution_rate_all": rate(sum(res.ward.ward is not None for res in results), len(test)),
        "method_counts": dict(methods),
        "outcomes_by_location_case": {k: dict(v) for k, v in sorted(by_case.items())},
    }

    # ---- gate ---------------------------------------------------------------------------
    auto = [res.gate.decision == "AUTO_ROUTED" for res in results]
    ward_ok = [res.ward.ward == r["ward"] for res, r in zip(results, test)]
    auto_both = sum(a and c and w for a, c, w in zip(auto, correct, ward_ok))
    n_err = len(test) - sum(correct)
    caught = sum((not a) and (not c) for a, c in zip(auto, correct))
    low_conf = sum(c < config.GATE_MIN_CONFIDENCE for c in conf)
    out["gate"] = {
        "auto_routed": rate(sum(auto), len(test)),
        "sent_to_review": rate(len(test) - sum(auto), len(test)),
        "auto_routed_correct_department_and_ward": rate(auto_both, sum(auto)),
        "auto_routed_wrong_department": rate(sum(a and not c for a, c in zip(auto, correct)), sum(auto)),
        "auto_routed_wrong_ward": rate(sum(a and not w for a, w in zip(auto, ward_ok)), sum(auto)),
        "department_errors_caught_by_gate": rate(caught, n_err),
        "review_reasons": {"confidence_below_threshold": low_conf,
                           "ward_unresolved": sum(res.ward.ward is None for res in results),
                           "both": sum(c < config.GATE_MIN_CONFIDENCE and res.ward.ward is None
                                       for c, res in zip(conf, results))},
    }

    # ---- severity -----------------------------------------------------------------------
    gold_band = [r["severity"] for r in test]
    band_pred = [res.severity["band"] for res in results]
    band_gold_dept = [severity.assess(r["text"], r["department"]).band for r in test]
    p1_gold = [b == "P1" for b in gold_band]
    p1_pred = [b == "P1" for b in band_pred]
    sev_conf = {g: dict(Counter(p for p, gg in zip(band_pred, gold_band) if gg == g)) for g in severity.BANDS}
    train_rows = data.load_train()
    Xs, ys = [normalise(r["text"]) for r in train_rows], [r["severity"] for r in train_rows]
    sC, _ = classifier.select_c(Xs, ys)
    sev_model = classifier.build(sC).fit(Xs, ys)
    sev_learned = list(sev_model.predict([normalise(r["text"]) for r in test]))
    rule_counts = Counter(f["rule"] for res in results for f in res.severity["fired"])
    out["severity"] = {
        "band_accuracy_predicted_department": rate(sum(a == b for a, b in zip(band_pred, gold_band)), len(test)),
        "band_accuracy_gold_department": rate(sum(a == b for a, b in zip(band_gold_dept, gold_band)), len(test)),
        "p1_recall": rate(sum(g and p for g, p in zip(p1_gold, p1_pred)), sum(p1_gold)),
        "p1_precision": rate(sum(g and p for g, p in zip(p1_gold, p1_pred)), sum(p1_pred)),
        "within_one_band": rate(sum(abs(severity.BANDS.index(a) - severity.BANDS.index(b)) <= 1
                                    for a, b in zip(band_pred, gold_band)), len(test)),
        "confusion_gold_to_predicted": sev_conf,
        "learned_logreg_baseline": {"C": sC, "accuracy": rate(sum(a == b for a, b in zip(sev_learned, gold_band)),
                                                              len(test)),
                                    "note": "trained on template severity labels in data/train.csv"},
        "rule_fire_counts": dict(sorted(rule_counts.items())),
        "in_sample_warning": "rules and labels were written by the same author; agreement is in-sample",
    }

    # ---- duplicates ---------------------------------------------------------------------
    pairs = data.read_csv(config.PAIRS_CSV)
    pair_rows = []
    for p in pairs:
        s = dedup.cosine(dedup.masked(p["text_a"]), dedup.masked(p["text_b"]))
        pair_rows.append({"pair_id": p["pair_id"], "is_duplicate": int(p["is_duplicate"]),
                          "cross_script": int(p["cross_script"]), "score": round(s, 4), "decision": dedup.decide(s)})
    pos = [r for r in pair_rows if r["is_duplicate"]]
    neg = [r for r in pair_rows if not r["is_duplicate"]]
    same_script_pos = [r for r in pos if not r["cross_script"]]
    out["duplicates"] = {
        "true_duplicate_pairs": {d: sum(r["decision"] == d for r in pos) for d in ("merge", "review", "new")},
        "true_duplicates_same_script": {d: sum(r["decision"] == d for r in same_script_pos)
                                        for d in ("merge", "review", "new")},
        "true_duplicates_cross_script": {d: sum(r["decision"] == d for r in pos if r["cross_script"])
                                         for d in ("merge", "review", "new")},
        "non_duplicate_pairs": {d: sum(r["decision"] == d for r in neg) for d in ("merge", "review", "new")},
        "merge_precision": rate(sum(r["decision"] == "merge" for r in pos),
                                sum(r["decision"] == "merge" for r in pair_rows)),
        "merge_recall": rate(sum(r["decision"] == "merge" for r in pos), len(pos)),
        "wrong_merges": sum(r["decision"] == "merge" for r in neg),
        "pairs": pair_rows,
        "note": "pairs are pre-blocked (same ward office and department); location words are masked before comparison",
    }

    # ---- simulated noise (NOT real ASR) ---------------------------------------------------
    rng = random.Random(NOISE_SEED)
    noisy = [add_noise(r["text"], rng) for r in test]
    n_pred = [classifier.predict(t, model).top3[0][0] for t in noisy]
    known = [i for i, r in enumerate(test) if r["ward"] != "UNRESOLVED"]
    exact_only = [location.resolve(noisy[i], allow_fuzzy=False).ward for i in known]
    with_fuzzy = [location.resolve(noisy[i]).ward for i in known]
    gold_w = [test[i]["ward"] for i in known]
    out["simulated_noise"] = {
        "LABEL": "SIMULATION: random character substitutions/deletions/insertions, not speech recognition output",
        "character_error_probability": NOISE_RATE, "seed": NOISE_SEED,
        "department_accuracy": rate(sum(p == g for p, g in zip(n_pred, y)), len(test)),
        "department_macro_f1": round(float(f1_score(y, n_pred, labels=depts, average="macro", zero_division=0)), 4),
        "ward_accuracy_exact_only": rate(sum(a == b for a, b in zip(exact_only, gold_w)), len(known)),
        "ward_accuracy_with_fuzzy": rate(sum(a == b for a, b in zip(with_fuzzy, gold_w)), len(known)),
        "clean_ward_accuracy_exact_only": rate(sum(location.resolve(test[i]["text"], allow_fuzzy=False).ward == test[i]["ward"]
                                                   for i in known), len(known)),
    }

    # ---- external set (team's midsem seed data) ------------------------------------------
    ext = data.read_csv(config.EXTERNAL_CSV)
    ext8 = [r for r in ext if r["department"] in EXTERNAL_MAP]
    ext_pred = [classifier.predict(r["text"], model).top3[0][0] for r in ext8]
    ext_ok = [p in EXTERNAL_MAP[r["department"]] for p, r in zip(ext_pred, ext8)]
    by_dept = {d: rate(sum(ok for ok, r in zip(ext_ok, ext8) if r["department"] == d),
                       sum(r["department"] == d for r in ext8)) for d in EXTERNAL_MAP}
    labelled = [r for r in ext if r["severity_label"]]
    ext_band = [severity.assess(r["text"], classifier.predict(r["text"], model).top3[0][0]).band for r in labelled]
    ext_gold = [r["severity_label"] for r in labelled]
    out["external_midsem"] = {
        "source": "data/external/midsem_seed_AB.csv (team's midsem seed set; AI-drafted, human-checked; different style)",
        "department_accuracy_coarse": rate(sum(ext_ok), len(ext8)),
        "department_accuracy_by_midsem_label": by_dept,
        "label_mapping": {k: sorted(v) for k, v in EXTERNAL_MAP.items()},
        "severity_band_agreement": rate(sum(a == b for a, b in zip(ext_band, ext_gold)), len(labelled)),
        "severity_p1_recall": rate(sum(a == "P1" and b == "P1" for a, b in zip(ext_band, ext_gold)),
                                   ext_gold.count("P1")),
        "severity_note": "labels written by the team, rules written in this build: out-of-sample for authorship",
    }
    return out


# ---------------------------------------------------------------------------------------
def pct(r):
    return f"{100 * r['rate']:.1f}% ({r['count']}/{r['total']})" if r["total"] else "n/a"


def to_markdown(o):
    d, g, w, s, b, n, x, du = (o["department"], o["gate"], o["ward"], o["severity"], o["baselines"],
                               o["simulated_noise"], o["external_midsem"], o["duplicates"])
    L = ["# Evaluation results", "",
         "Generated by `python eval/evaluate.py` from the frozen data. Do not edit by hand.", "",
         f"Classifier: TF-IDF char_wb 2-5 + word 1-2, class-balanced logistic regression, C = {o['_provenance']['classifier_C']} "
         f"({o['_provenance']['classifier_selection']}).", "",
         "## Department (160 test complaints)", "",
         "| Quantity | Value |", "|---|---|",
         f"| Accuracy | {pct(d['accuracy'])} |",
         f"| Macro-F1 | {d['macro_f1']:.3f} |",
         f"| Top-3 accuracy | {pct(d['top3_accuracy'])} |",
         f"| Keyword baseline accuracy | {pct(b['keyword']['accuracy'])} |",
         f"| Char-only logistic regression accuracy (not adopted) | {pct(b['char_only_logreg']['accuracy'])} |",
         f"| 5-fold CV accuracy inside the template training data | {100 * d['cv_accuracy_on_train']:.1f}% |", "",
         "Accuracy by language: " + ", ".join(f"{k} {pct(v)}" for k, v in d["accuracy_by_language"].items()), "",
         "## Ward office", "",
         f"* Items whose text names a resolvable place: {w['items_with_known_ward']}. Correct {pct(w['correct'])}, "
         f"wrong {pct(w['wrong'])}, unresolved {pct(w['unresolved'])}.",
         f"* Items with no place, an unknown place or an ambiguous place: {w['items_without_resolvable_ward']}. "
         f"Correctly left unresolved {pct(w['correctly_left_unresolved'])}.",
         f"* Methods used: {w['method_counts']}", "",
         "## Gate (confidence ≥ 0.50 and ward resolved)", "",
         "| Quantity | Value |", "|---|---|",
         f"| Auto-routed share | {pct(g['auto_routed'])} |",
         f"| Auto-routed with correct department and ward | {pct(g['auto_routed_correct_department_and_ward'])} |",
         f"| Department errors caught by the gate | {pct(g['department_errors_caught_by_gate'])} |", "",
         "## Severity (expert system)", "",
         "| Quantity | Value |", "|---|---|",
         f"| Band accuracy, predicted department | {pct(s['band_accuracy_predicted_department'])} |",
         f"| Band accuracy, gold department | {pct(s['band_accuracy_gold_department'])} |",
         f"| P1 recall | {pct(s['p1_recall'])} |",
         f"| P1 precision | {pct(s['p1_precision'])} |",
         f"| Learned logistic-regression severity baseline | {pct(s['learned_logreg_baseline']['accuracy'])} |", "",
         f"In-sample warning: {s['in_sample_warning']}.", "",
         "## Duplicates (60 pre-blocked pairs)", "",
         f"* True duplicates (30): {du['true_duplicate_pairs']} — same script {du['true_duplicates_same_script']}, "
         f"cross-script {du['true_duplicates_cross_script']}",
         f"* Non-duplicates (30): {du['non_duplicate_pairs']}",
         f"* Merge precision {pct(du['merge_precision'])}, merge recall {pct(du['merge_recall'])}", "",
         "## Simulated character noise (SIMULATION, not ASR)", "",
         f"10% character error probability, seed {n['seed']}.",
         f"* Department macro-F1 {n['department_macro_f1']:.3f}, accuracy {pct(n['department_accuracy'])}",
         f"* Ward accuracy exact-only {pct(n['ward_accuracy_exact_only'])}, with fuzzy fallback {pct(n['ward_accuracy_with_fuzzy'])}", "",
         "## External check: team's midsem seed set", "",
         f"* Department accuracy (coarse label mapping, 435 rows without 'other'): {pct(x['department_accuracy_coarse'])}",
         f"* Severity band agreement with the team's labels: {pct(x['severity_band_agreement'])}; "
         f"P1 recall {pct(x['severity_p1_recall'])}", ""]
    return "\n".join(L)


def main():
    safe_console()
    o = evaluate()
    text = json.dumps(o, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    if "--check" in sys.argv:
        same = OUT_JSON.exists() and OUT_JSON.read_text(encoding="utf-8") == text
        print("results/eval.json reproduced exactly" if same else "results/eval.json DIFFERS from this run")
        sys.exit(0 if same else 1)
    config.RESULTS.mkdir(exist_ok=True)
    OUT_JSON.write_text(text, encoding="utf-8")
    OUT_MD.write_text(to_markdown(o), encoding="utf-8")
    print(to_markdown(o))


if __name__ == "__main__":
    main()
