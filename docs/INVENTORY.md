# Inventory

## History

| Date | What happened |
|---|---|
| 2026-10-02 | The repository was empty, then held only the midsem Colab notebook. Believing that was the final prototype, a from-scratch rebuild was made. That rebuild is now in `archive/rebuild_2026-10-02/` and is superseded. |
| 2026-10-03 | The original prototype was supplied as `NagarVani_prototype_code.zip`, with the PBL-5 paper draft. It was verified, and the project was restructured to wrap it, as the build brief intended. |

## What the original prototype contains, and where it now lives

| Original path (zip) | Now | Status |
|---|---|---|
| `nagarvani/{normalise,classifier,location,severity,dedup,store,pipeline,asr}.py` | `nagarvani/` (same names) | **Frozen, byte-identical** (checksummed) |
| `corpus/train_template.tsv`, `test_handwritten.tsv`, `dup_pairs.tsv`, `generate_train.py` | `corpus/` | **Frozen, byte-identical** |
| `data/gazetteer.json` | `data/gazetteer.json` | **Frozen, byte-identical** |
| `results/results.json`, `results/model.pkl` | `results/results_shipped.json`, `results/model_shipped.pkl` | Frozen, kept as shipped for comparison |
| `experiments/run_eval.py` | `experiments/run_eval.py` | Kept; three marked `[build change]` edits (hash-seed pin, output folder, E8 through `triage()`) |
| `experiments/make_architecture.py` | `experiments/` | Unchanged |
| `results/figures/*.png` | `results/figures/` | Regenerated identically in content by `run_eval.py` |
| `docs/annotation_guideline.md` | `docs/annotation_guideline.md` | Unchanged |
| `app/` (a minimal Flask console), `experiments/demo_scenario.py`, `docs_build/`, `README.md` | `docs/prototype/` | Kept for reference. Replaced by the new web app. |

## Entry points

* **Evaluation:** `python experiments/run_eval.py` writes `results/results.json`, the figures, the per-ward queues and `results/model.pkl`.
* **Classifier artefact:** `python -m nagarvani.train` rebuilds `results/model.pkl`. It is identical to the one `run_eval.py` writes.
* **Pipeline:** `nagarvani.triage.triage()` wraps the original `pipeline.Triage.triage` logic and is used by both the evaluation and the app.
* **Web app:** `python run.py`.

## Reported vs reproduced

Reproduced with `python experiments/run_eval.py`, scikit-learn 1.8.0, on 2026-10-03.

| Quantity | Reported (brief, paper) | Reproduced (`results/results.json`) |
|---|---|---|
| Department accuracy | 86.9% (139/160) | 0.86875 = 139/160 |
| Department macro-F1 | 0.870 | 0.8698 |
| Top-3 accuracy | 95.6% (153/160) | 0.95625 = 153/160 |
| Keyword baseline | 81.9% | 0.81875 |
| Char-only logistic regression | 88.8% | 0.8875 |
| CV accuracy inside template data | 99.8% | 0.998 |
| Auto-routed share | 70% | 112/160 |
| Auto-routed with correct department and ward | 97.3% | 109/112 |
| Department errors caught by the gate | 18 of 21 | 21 errors, 3 auto-routed → 18 |
| Severity band accuracy (predicted department) | 95.6% | 0.95625 |
| P1 recall | 94.4% | 34/36 |
| Learned severity baseline | 76.9% | 0.76875 |
| Macro-F1 at simulated 10% character error | 0.811 | 0.8112 |
| Ward accuracy at 10% noise, exact only / with fuzzy | 49% / 93% | 0.494 / 0.926 |

**Every reported number reproduces.** The full `results.json` (789 values) equals the shipped
one, with floats within 1e-12 and only the timing fields excluded. That holds both with the
original code path and with the end-to-end stream routed through `triage()`.

The PBL-5 paper draft was also checked against `results.json`. Its other figures match too:
- Table I, including the per-variety columns
- confidence 0.814 / 0.454 and ECE 0.111
- 81.3% / 96.9% at τ = 0.50
- the whole severity table
- duplicate precision 1.00 / recall 0.73, and 14 of 15 duplicates merged or reviewed
- 0.755 macro-F1 and 61% severity at 20% noise
- 48 deferrals (25 low confidence + 23 location)
- 226 cue strings

## Where the brief and the code disagree

| Brief says | Code does |
|---|---|
| "30 duplicate pairs" | 30 **labelled pairs**: 15 true duplicates, 10 same-ward different-department, 5 same-ward same-department. |
| Ward resolver "suffix-tolerant" | Devanagari aliases match as plain substrings (so any suffix is tolerated, and an alias inside a longer word also matches). Latin aliases match whole words. |
| Duplicate similarity "character 2–4 gram cosine" | TF-IDF (char_wb 2–4, sublinear) **fitted on the training corpus**, cosine, after removing gazetteer aliases. |
| C = 10 "chosen by cross-validation" | `char_word_lr` defaults to C = 10. The CV search (`E1_C_search`, macro-F1) ties C = 10 and C = 30 at 0.99800, so the first maximum is 10. |
| Duplicates: merge at ≥ 0.45, review 0.30–0.45, new below | `DuplicateDetector.decide` returns these decisions. In the original pipeline, a merge only joins the cluster (it raises the cluster size for R32), and routing is decided by the gate alone. |
| Gazetteer of 59 localities | 59 localities, 15 ward offices, and one ambiguous name with three spellings (वडगाव / wadgaon / vadgaon). |
| Library version unspecified | The shipped `model.pkl` was pickled with scikit-learn **1.8.0**. Results also reproduce under 1.9.1. 1.8.0 is pinned. |
| Speech: "no ASR model has been run" | True. `nagarvani/asr.py` has an openai-whisper backend that was never run, plus the noise simulator. This build adds faster-whisper in `nagarvani/speech.py`. |
