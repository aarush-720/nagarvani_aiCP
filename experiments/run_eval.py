"""Reproduce every number and figure reported in the PBL-4 report and PBL-5 paper.

    python experiments/run_eval.py      ->  results/results.json, results/figures/*.png
"""
import json, os, pickle, random, sys, time
from collections import Counter, defaultdict

# [build change] Reproducibility: one reported value (simulated-noise ward accuracy at 20% CER)
# depends on Python's per-process string-hash order (docs/DECISIONS.md F4). Re-run under the
# PYTHONHASHSEED that reproduces the shipped results. No logic below is changed by this.
_SEED = "3"
if os.environ.get("PYTHONHASHSEED") != _SEED:
    import subprocess
    sys.exit(subprocess.call([sys.executable] + sys.argv, env=dict(os.environ, PYTHONHASHSEED=_SEED)))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import (accuracy_score, f1_score, precision_recall_fscore_support,
                             confusion_matrix, classification_report)
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from nagarvani.pipeline import load_tsv, Triage
from nagarvani.classifier import (char_word_lr, char_lr, word_lr, word_nb, KeywordBaseline, DEPARTMENTS)
from nagarvani.location import WardResolver
from nagarvani.severity import infer
from nagarvani.dedup import DuplicateDetector
from nagarvani.asr import simulate_asr_noise
from nagarvani.normalise import normalise

# [build change] NAGARVANI_RESULTS_DIR lets the tests write to a temporary folder.
OUT = os.environ.get("NAGARVANI_RESULTS_DIR", os.path.join(ROOT, "results"))
FIG = os.path.join(OUT, "figures"); os.makedirs(FIG, exist_ok=True)
R = {}
train = load_tsv(os.path.join(ROOT, "corpus", "train_template.tsv"))
test = load_tsv(os.path.join(ROOT, "corpus", "test_handwritten.tsv"))
Xtr, ytr = [r["text"] for r in train], [r["dept"] for r in train]
Xte, yte = [r["text"] for r in test], [r["dept"] for r in test]
LABELS = sorted(DEPARTMENTS)
R["data"] = dict(n_train=len(train), n_test=len(test),
                 train_lang=Counter(r["lang"] for r in train), test_lang=Counter(r["lang"] for r in test),
                 train_sev=Counter(r["sev"] for r in train), test_sev=Counter(r["sev"] for r in test),
                 test_loc_none=sum(r["loc"] == "NONE" for r in test))

plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "font.family": "DejaVu Sans"})
C1, C2, C3, C4 = "#2a6f97", "#e07a2f", "#6a994e", "#8d6a9f"

# ------------------------------------------------ E1  department classification
models = {"Keyword lexicon (no ML)": KeywordBaseline(),
          "Word TF-IDF + Naive Bayes": word_nb(),
          "Word TF-IDF + LogReg": word_lr(),
          "Char n-gram TF-IDF + LogReg": char_lr(),
          "Char + word TF-IDF + LogReg (proposed)": char_word_lr()}
E1 = {}
fitted = {}
for name, m in models.items():
    t0 = time.perf_counter(); m.fit(Xtr, ytr); fit_s = time.perf_counter() - t0
    p = m.predict(Xte); P = m.predict_proba(Xte)
    top3 = np.mean([yte[i] in [m.classes_[j] for j in P[i].argsort()[::-1][:3]] for i in range(len(yte))])
    by_lang = {}
    for lg in ["mr", "hi", "mr-rom", "mix"]:
        idx = [i for i, r in enumerate(test) if r["lang"] == lg]
        by_lang[lg] = accuracy_score([yte[i] for i in idx], [p[i] for i in idx])
    E1[name] = dict(acc=accuracy_score(yte, p), macro_f1=f1_score(yte, p, average="macro"),
                    top3=float(top3), by_lang=by_lang, fit_seconds=fit_s)
    fitted[name] = m
R["E1_dept"] = E1
prop = fitted["Char + word TF-IDF + LogReg (proposed)"]
pickle.dump(prop, open(os.path.join(OUT, "model.pkl"), "wb"))

# in-distribution 5-fold CV on the template corpus (to expose the template-leakage gap)
cvp = cross_val_predict(char_word_lr(), Xtr, ytr, cv=StratifiedKFold(5, shuffle=True, random_state=0))
R["E1_cv_template"] = dict(acc=accuracy_score(ytr, cvp), macro_f1=f1_score(ytr, cvp, average="macro"))

# hyper-parameter C chosen by CV on the training set only
cv_C = {}
for C in [0.3, 1, 3, 10, 30]:
    pr = cross_val_predict(char_word_lr(C), Xtr, ytr, cv=StratifiedKFold(5, shuffle=True, random_state=0))
    cv_C[C] = f1_score(ytr, pr, average="macro")
R["E1_C_search"] = cv_C

# ------------------------------------------------ E2  per-class report + confusion
pp = prop.predict(Xte); PP = prop.predict_proba(Xte)
prf = precision_recall_fscore_support(yte, pp, labels=LABELS, zero_division=0)
R["E2_per_class"] = {c: dict(p=float(prf[0][i]), r=float(prf[1][i]), f1=float(prf[2][i]), n=int(prf[3][i]))
                     for i, c in enumerate(LABELS)}
cm = confusion_matrix(yte, pp, labels=LABELS)
R["E2_confusions"] = [dict(id=test[i]["id"], gold=yte[i], pred=pp[i], text=Xte[i],
                           conf=round(float(PP[i].max()), 3)) for i in range(len(yte)) if yte[i] != pp[i]]
fig, ax = plt.subplots(figsize=(5.2, 4.4))
im = ax.imshow(cm, cmap="Blues")
ax.set_xticks(range(10)); ax.set_yticks(range(10))
ax.set_xticklabels(LABELS, rotation=60, ha="right"); ax.set_yticklabels(LABELS)
for i in range(10):
    for j in range(10):
        if cm[i, j]: ax.text(j, i, cm[i, j], ha="center", va="center",
                             color="white" if cm[i, j] > 8 else "black", fontsize=8)
ax.set_xlabel("Predicted department"); ax.set_ylabel("True department")
ax.spines[:].set_visible(False)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_confusion.png"), dpi=200); plt.close(fig)

# model comparison bar
fig, ax = plt.subplots(figsize=(6.2, 2.8))
names = list(E1); short = ["Keyword\nlexicon", "Word\nNB", "Word\nLogReg", "Char\nLogReg", "Char+word\nLogReg"]
x = np.arange(len(names)); w = 0.38
b1 = ax.bar(x - w/2, [E1[n]["acc"] for n in names], w, color=C1, label="Accuracy")
b2 = ax.bar(x + w/2, [E1[n]["macro_f1"] for n in names], w, color=C2, label="Macro-F1")
for b in list(b1) + list(b2):
    ax.text(b.get_x() + b.get_width()/2, b.get_height() + 0.01, f"{b.get_height():.2f}", ha="center", fontsize=7)
ax.set_xticks(x); ax.set_xticklabels(short); ax.set_ylim(0, 1.05); ax.set_ylabel("Score (hand-written test set, n=160)")
ax.legend(frameon=False, loc="upper left", ncol=2)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_models.png"), dpi=200); plt.close(fig)

# ------------------------------------------------ E3  calibration + abstention
conf = PP.max(1); correct = (pp == np.array(yte))
bins = np.linspace(0, 1, 11); ece = 0
for lo, hi in zip(bins[:-1], bins[1:]):
    m = (conf > lo) & (conf <= hi)
    if m.any(): ece += m.mean() * abs(correct[m].mean() - conf[m].mean())
curve = []
for tau in np.round(np.arange(0.0, 0.96, 0.05), 2):
    keep = conf >= tau
    curve.append(dict(tau=float(tau), coverage=float(keep.mean()),
                      acc_auto=float(correct[keep].mean()) if keep.any() else None,
                      misroute_rate_auto=float(1 - correct[keep].mean()) if keep.any() else None))
R["E3_calibration"] = dict(ece=float(ece), mean_conf=float(conf.mean()),
                           mean_conf_correct=float(conf[correct].mean()),
                           mean_conf_wrong=float(conf[~correct].mean()) if (~correct).any() else None)
R["E3_abstention_curve"] = curve
fig, ax = plt.subplots(figsize=(5.0, 3.0))
ax.plot([c["tau"] for c in curve], [c["coverage"] for c in curve], "-o", ms=3, color=C1, label="Coverage (auto-routed share)")
ax.plot([c["tau"] for c in curve], [c["acc_auto"] for c in curve], "-s", ms=3, color=C2, label="Accuracy on auto-routed")
ax.axvline(0.5, color="grey", ls="--", lw=0.8); ax.text(0.51, 0.08, "τ = 0.50", color="grey")
ax.set_xlabel("Confidence threshold τ"); ax.set_ylim(0, 1.03); ax.legend(frameon=False, loc="lower left")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_abstention.png"), dpi=200); plt.close(fig)

# ------------------------------------------------ E4  ward resolution
res = WardResolver()
res_exact = WardResolver(fuzzy=False)
def ward_eval(rs):
    c = Counter()
    for r in test:
        o = rs.resolve(r["text"]); gw = rs.loc2ward.get(r["loc"]) if r["loc"] != "NONE" else None
        c["correct" if (gw and o["ward"] == gw) else "correctly_unresolved" if (gw is None and o["ward"] is None)
          else "false_resolution" if gw is None else "missed" if o["ward"] is None else "wrong_ward"] += 1
    return c
R["E4_ward_exact_only"] = ward_eval(res_exact)
wr = Counter(); werr = []
for r in test:
    o = res.resolve(r["text"])
    gold_w = res.loc2ward.get(r["loc"]) if r["loc"] != "NONE" else None
    if gold_w is None:
        k = "correctly_unresolved" if o["ward"] is None else "false_resolution"
    else:
        k = "correct" if o["ward"] == gold_w else ("missed" if o["ward"] is None else "wrong_ward")
    wr[k] += 1
    if k not in ("correct", "correctly_unresolved"): werr.append(dict(id=r["id"], kind=k, text=r["text"], got=o))
n_loc = sum(1 for r in test if r["loc"] != "NONE")
R["E4_ward"] = dict(counts=wr, n_with_locality=n_loc, n_without=len(test) - n_loc,
                    acc_with_locality=wr["correct"] / n_loc,
                    overall_acc=(wr["correct"] + wr["correctly_unresolved"]) / len(test), errors=werr)

# ------------------------------------------------ E5  severity
BANDS = ["P1", "P2", "P3", "P4"]
def sev_eval(gold, pred):
    g = np.array([int(x[1]) for x in gold]); p = np.array([int(x[1]) for x in pred])
    p1 = [i for i in range(len(g)) if g[i] == 1]
    return dict(acc=float((g == p).mean()), within1=float((abs(g - p) <= 1).mean()), mae=float(abs(g - p).mean()),
                macro_f1=float(f1_score(gold, pred, average="macro", labels=BANDS)),
                p1_recall=float(np.mean([p[i] == 1 for i in p1])),
                p1_precision=float(np.mean([g[i] == 1 for i in range(len(p)) if p[i] == 1])),
                under_triage=float(np.mean(p > g)), over_triage=float(np.mean(p < g)))
gs = [r["sev"] for r in test]
E5 = {}
E5["rules_gold_dept"] = sev_eval(gs, [infer(r["text"], r["dept"])["band"] for r in test])
E5["rules_pred_dept"] = sev_eval(gs, [infer(r["text"], d)["band"] for r, d in zip(test, pp)])
E5["rules_no_escalation"] = sev_eval(gs, [infer(r["text"], r["dept"], use_escalation=False)["band"] for r in test])
sev_lr = Pipeline([("t", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, min_df=2,
                                        preprocessor=normalise)),
                   ("c", LogisticRegression(C=10, max_iter=4000, class_weight="balanced"))])
sev_lr.fit(Xtr, [r["sev"] for r in train])
E5["learned_logreg"] = sev_eval(gs, list(sev_lr.predict(Xte)))
E5["majority_P3"] = sev_eval(gs, ["P3"] * len(gs))
E5["rules_on_template_set_gold_dept"] = sev_eval([r["sev"] for r in train], [infer(r["text"], r["dept"])["band"] for r in train])
rule_pred = [infer(r["text"], r["dept"])["band"] for r in test]
R["E5_severity"] = E5
R["E5_confusion_rules"] = confusion_matrix(gs, rule_pred, labels=BANDS).tolist()
R["E5_errors"] = [dict(id=r["id"], gold=r["sev"], pred=p, text=r["text"], fired=infer(r["text"], r["dept"])["fired"])
                  for r, p in zip(test, rule_pred) if p != r["sev"]]
fire = Counter(x for r in test for x in infer(r["text"], r["dept"])["fired"])
R["E5_rule_fire_counts"] = dict(sorted(fire.items()))
fig, ax = plt.subplots(figsize=(6.2, 2.8))
keys = ["majority_P3", "learned_logreg", "rules_no_escalation", "rules_pred_dept", "rules_gold_dept"]
lab = ["Always P3", "Learned\nLogReg", "Rules w/o\nescalation", "Rules\n(pred. dept)", "Rules\n(gold dept)"]
x = np.arange(len(keys))
b1 = ax.bar(x - w/2, [E5[k]["acc"] for k in keys], w, color=C1, label="Band accuracy")
b2 = ax.bar(x + w/2, [E5[k]["p1_recall"] for k in keys], w, color=C3, label="P1 recall")
for b in list(b1) + list(b2):
    ax.text(b.get_x() + b.get_width()/2, b.get_height() + 0.01, f"{b.get_height():.2f}", ha="center", fontsize=7)
ax.set_xticks(x); ax.set_xticklabels(lab); ax.set_ylim(0, 1.08); ax.legend(frameon=False, loc="upper left", ncol=2)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_severity.png"), dpi=200); plt.close(fig)

# ------------------------------------------------ E6  duplicate detection
import csv
pairs = list(csv.DictReader(open(os.path.join(ROOT, "corpus", "dup_pairs.tsv"), encoding="utf-8"), delimiter="\t"))
byid = {r["id"]: r for r in test}
dd = DuplicateDetector(res).fit(Xtr)
rows6 = []
for pr in pairs:
    a = byid[pr["a_id"]]["text"]; b = pr["b_text"]
    da, db = prop.predict([a])[0], prop.predict([b])[0]
    wa, wb = res.resolve(a)["ward"], res.resolve(b)["ward"]
    s = dd.similarity(a, b)
    blocked_in = (da == db) and wa is not None and wa == wb
    rows6.append(dict(pair=pr["pair_id"], kind=pr["kind"], gold=int(pr["is_dup"]), sim=round(s, 3),
                      blocked_in=blocked_in, same_dept_pred=da == db, same_ward=wa == wb))
def dup_metrics(th, use_block=True):
    tp = fp = fn = tn = 0
    for r in rows6:
        pred = (r["sim"] >= th) and (r["blocked_in"] or not use_block)
        if pred and r["gold"]: tp += 1
        elif pred: fp += 1
        elif r["gold"]: fn += 1
        else: tn += 1
    P = tp / (tp + fp) if tp + fp else 0; Rr = tp / (tp + fn)
    return dict(th=th, tp=tp, fp=fp, fn=fn, tn=tn, precision=P, recall=Rr, f1=2*P*Rr/(P+Rr) if P+Rr else 0)
R["E6_dedup"] = dict(pairs=rows6,
                     merge_block=dup_metrics(dd.theta_high), merge_noblock=dup_metrics(dd.theta_high, False),
                     review_block=dup_metrics(dd.theta_low),
                     sweep=[dup_metrics(t) for t in [0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6]])
fig, ax = plt.subplots(figsize=(5.0, 2.6))
for kind, col, off in [("paraphrase", C3, 0), ("same-ward-diff-dept", C2, 1), ("same-ward-same-dept", C1, 2)]:
    v = [r["sim"] for r in rows6 if r["kind"] == kind]
    ax.scatter(v, [off + random.Random(i).uniform(-0.15, 0.15) for i in range(len(v))], color=col, s=18)
ax.axvline(dd.theta_low, color="grey", ls=":", lw=0.8); ax.axvline(dd.theta_high, color="grey", ls="--", lw=0.8)
ax.text(dd.theta_low, 2.45, "θ_low", fontsize=7, color="grey", ha="center")
ax.text(dd.theta_high, 2.45, "θ_high", fontsize=7, color="grey", ha="center")
ax.set_yticks([0, 1, 2]); ax.set_yticklabels(["True duplicate", "Diff. dept,\nsame ward", "Same dept,\nsame ward"])
ax.set_xlabel("Location-masked char n-gram cosine similarity"); ax.set_ylim(-0.5, 2.7)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_dedup.png"), dpi=200); plt.close(fig)

# ------------------------------------------------ E7  robustness to simulated ASR error
E7 = []
for cer in [0.0, 0.05, 0.10, 0.15, 0.20, 0.30]:
    f1s, accs, wards, sevs, wards_e = [], [], [], [], []
    for seed in range(5):
        rng = random.Random(seed)
        Xn = [simulate_asr_noise(x, cer, rng) for x in Xte]
        pn = prop.predict(Xn)
        f1s.append(f1_score(yte, pn, average="macro")); accs.append(accuracy_score(yte, pn))
        ok, oke = [], []
        for r, x in zip(test, Xn):
            if r["loc"] == "NONE": continue
            ok.append(res.resolve(x)["ward"] == res.loc2ward[r["loc"]])
            oke.append(res_exact.resolve(x)["ward"] == res.loc2ward[r["loc"]])
        wards.append(np.mean(ok)); wards_e.append(np.mean(oke))
        sevs.append(np.mean([infer(x, d)["band"] == r["sev"] for x, d, r in zip(Xn, pn, test)]))
    E7.append(dict(cer=cer, dept_macro_f1=float(np.mean(f1s)), dept_macro_f1_sd=float(np.std(f1s)),
                   dept_acc=float(np.mean(accs)), ward_acc=float(np.mean(wards)), ward_acc_exact=float(np.mean(wards_e)), sev_acc=float(np.mean(sevs))))
R["E7_asr_noise"] = E7
fig, ax = plt.subplots(figsize=(5.0, 3.0))
cx = [e["cer"] * 100 for e in E7]
ax.plot(cx, [e["dept_macro_f1"] for e in E7], "-o", ms=3, color=C1, label="Department macro-F1")
ax.plot(cx, [e["ward_acc"] for e in E7], "-s", ms=3, color=C2, label="Ward resolution (exact + fuzzy)")
ax.plot(cx, [e["ward_acc_exact"] for e in E7], ":s", ms=3, color=C2, alpha=0.6, label="Ward resolution (exact only)")
ax.plot(cx, [e["sev_acc"] for e in E7], "-^", ms=3, color=C3, label="Severity band accuracy")
ax.set_xlabel("Simulated transcription character error rate (%)"); ax.set_ylim(0, 1.03)
ax.legend(frameon=False, loc="lower left")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_asr_noise.png"), dpi=200); plt.close(fig)

# ------------------------------------------------ E8  end-to-end on the stream of 160 complaints
# [build change] The stream is routed through nagarvani.triage.triage (the entry point the web
# app uses), with live duplicate lookup against a ticket store. The original Triage is run on
# the same stream alongside, and every decision is asserted equal, so both give the same counts.
_db = os.path.join(OUT, "nagarvani_demo.db")
if os.path.exists(_db): os.remove(_db)
tri = Triage(db_path=_db, tau=0.50, model=prop)
tri.store.db.execute("DELETE FROM tickets"); tri.store.db.commit()
from datetime import datetime, timedelta, timezone
from nagarvani import triage as _triage_mod
from nagarvani.tickets import Store as _Store
from nagarvani import config as _cfg
_cfg.MODEL_PATH = type(_cfg.MODEL_PATH)(os.path.join(OUT, "model.pkl"))
_triage_mod.model.cache_clear()   # use the model.pkl saved above
_live = _Store(":memory:")
t0 = datetime(2026, 9, 28, 9, 0)
lat = []; e2e = Counter(); per = []; stream_dups = Counter()
for i, r in enumerate(test):
    now = t0 + timedelta(minutes=7 * i)
    s = time.perf_counter()
    w = _triage_mod.triage(r["text"], now=now.replace(tzinfo=timezone.utc), store=_live)
    lat.append((time.perf_counter() - s) * 1000)
    o = tri.triage(r["text"], channel="whatsapp-text", now=now)
    assert (w.department, w.ward.ward, w.severity["band"], w.route_original) == \
           (o["dept"], o["ward"], o["priority"], o["route_status"]), (r["id"], w.department, o["dept"])
    assert [f["rule"] for f in w.severity["fired"]] == (o["rules_fired"].split(",") if o["rules_fired"] else []), r["id"]
    dupd = w.duplicate["decision"] if w.duplicate["decision"] != "skipped" else "new"
    assert dupd == o["dup_decision"], (r["id"], dupd, o["dup_decision"])
    stream_dups[dupd] += 1
    _live.create(channel="eval", text=r["text"], department=w.department, ward=w.ward.ward,
                 status="auto_routed" if w.route_original == "AUTO_ROUTED" else "review",
                 parent_id=None, report_count=1)
    gold_w = res.loc2ward.get(r["loc"]) if r["loc"] != "NONE" else None
    dept_ok = w.department == r["dept"]; ward_ok = (w.ward.ward == gold_w)
    if w.route_original == "AUTO_ROUTED":
        e2e["auto_correct" if (dept_ok and ward_ok) else ("auto_wrong_dept" if not dept_ok else "auto_wrong_ward")] += 1
    else:
        e2e["deferred"] += 1
        e2e["deferred_would_have_been_wrong" if not (dept_ok and ward_ok) else "deferred_would_have_been_right"] += 1
    per.append(dict(id=r["id"], route=w.route_original, dept=w.department, ok=dept_ok and ward_ok))
files = tri.store.export_ward_queues(os.path.join(OUT, "queues"))
n_auto = sum(v for k, v in e2e.items() if k.startswith("auto"))
R["E8_end_to_end"] = dict(counts=e2e, n=len(test), auto_rate=n_auto / len(test),
                          auto_precision=e2e["auto_correct"] / n_auto,
                          latency_ms_mean=float(np.mean(lat)), latency_ms_p95=float(np.percentile(lat, 95)),
                          queue_files=[os.path.basename(f) for f in files])
# dedup inside the stream
R["E8_stream_dups"] = stream_dups

json.dump(R, open(os.path.join(OUT, "results.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1, default=lambda o: dict(o) if isinstance(o, Counter) else float(o))
print(json.dumps({k: v for k, v in R.items() if k not in ("E2_confusions", "E5_errors", "E4_ward", "E6_dedup", "E3_abstention_curve")},
                 ensure_ascii=False, indent=1, default=lambda o: dict(o) if isinstance(o, Counter) else float(o)))
