# NagarVani — नगरवाणी

A triage layer for civic complaints to the Pune Municipal Corporation (PMC). A citizen speaks
or types a complaint in Marathi or Hindi (Devanagari, romanised, or mixed with English). The
system then:

1. assigns one of **10 departments**,
2. resolves the place to one of **15 ward offices**,
3. sets a priority **P1–P4** with a deadline, using a **19-rule expert system**,
4. checks open tickets for **repeat reports**,
5. **auto-routes** the ticket or holds it for a **nodal officer**.

Every decision is shown step by step on a trace page.

It is a course prototype for IT3232 Artificial Intelligence (VIT Pune). It is a proposal, not a
production system, and it does not connect to PMC CARE (which has no public API).

> **Status and known gaps:** [`docs/HANDOVER.md`](docs/HANDOVER.md), which starts with what
> does not work yet. All reported numbers come from `python experiments/run_eval.py` and are
> stored in `results/results.json`.

## Requirements

* Python **3.11** (64-bit), on Windows 10/11, macOS or Linux.
* About 1 GB of disk for the Whisper `small` model (more for larger models).
* Internet **once**, for `pip install` and the model download. After that everything runs offline.
* No system ffmpeg: audio is decoded by the FFmpeg libraries bundled with the `av` package.

## Setup

### Windows (PowerShell or cmd)

```bat
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts\fetch_models.py
python scripts\reset_demo.py --yes
python run.py
```

### Linux / macOS

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/fetch_models.py
python scripts/reset_demo.py --yes
python run.py
```

`run.py` checks that the classifier artefact, database and Whisper model are present, then
prints the URL (http://127.0.0.1:5000/). The app binds to 127.0.0.1 only. If the Whisper model
is missing, the app still starts: typed complaints work, and the audio controls say why they
are disabled.

### Choosing the Whisper model (once, on the demo laptop)

Record a ~15-second Marathi complaint (any format), then run:

```bash
python scripts/fetch_models.py --benchmark path/to/clip.ogg
```

This times `tiny` → `large-v3` on this machine. It writes `results/asr_benchmark.json` and
recommends the largest model that transcribes the clip in about 20 s or less. Select it with
`NAGARVANI_ASR_MODEL=<name>` (Windows: `set NAGARVANI_ASR_MODEL=<name>`).
`NAGARVANI_ASR_PROMPT=1` turns on vocabulary biasing (default off). `NAGARVANI_PORT` changes
the port.

## Using it

| Page | What it is |
|---|---|
| `/` | Citizen intake: microphone, audio upload (WhatsApp `.ogg` works) or typing. Marathi/Hindi toggle (forced, not auto-detected). The transcript must be checked before submitting. Optional ward dropdown. One-click example complaints. No name or phone number is collected. |
| `/ticket/<id>` | The trace: what was heard, department top 3, location match, every severity rule that fired (with its cue words), the duplicate score against the thresholds, and the gate decision with its exact condition. |
| `/queue` | Officer view: review list and routed list. Filter by ward, department and status; sorted by priority then deadline; overdue flagged. Confirm, correct department/ward/priority, decide duplicates, resolve. |
| `/export/<ward>.csv` | One ward office's open queue (codes as in `data/gazetteer.json`, e.g. `/export/KOB.csv`). UTF-8 with BOM, so Excel shows Devanagari. |
| `/corrections.jsonl` | Every officer correction, logged as possible training data. Retraining is **not** implemented. |
| `/about` | Headline results read from `results/results.json`, plus the limitations. |
| `/health` | Whether the classifier, database and ASR model are loaded. |

The demo walkthrough, with the real output of every input, is in
[`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md).

## Reproducing every number

```bash
python scripts/reproduce.py
```

It checks, in order:
1. The frozen data, original logic and shipped outputs match their checksums, and the training
   corpus regenerates byte for byte.
2. A rebuilt classifier equals the saved one.
3. `triage()` decides exactly like the original pipeline on all 160 test complaints.
4. `experiments/run_eval.py` reproduces every reported number, and its whole `results.json`
   equals the shipped one.
5. The real-audio evaluation runs if clips exist.

You can also run each part on its own:

```bash
python experiments/run_eval.py     # all metrics and figures -> results/results.json, results/figures/
python -m nagarvani.train          # rebuild results/model.pkl (deterministic)
python eval/asr_eval.py            # WER/CER and end-to-end from audio (needs data/audio/manifest.csv)
python -m pytest -q                # full test suite, including tests/test_frozen_metrics.py
python scripts/run_demo_script.py  # regenerate docs/DEMO_SCRIPT.md from real outputs
```

## How it works

| Step | Method | Code |
|---|---|---|
| Normalisation | NFC, zero-width removal, Devanagari digits → ASCII, lower-case, repeated characters squeezed, punctuation (except , . -) removed | `nagarvani/normalise.py` |
| Department | TF-IDF (char_wb 2–5 + word 1–2 grams) → class-balanced logistic regression, C = 10 (chosen by 5-fold CV on the training data) | `nagarvani/classifier.py` |
| Ward office | Gazetteer aliases, longest first (Devanagari as substrings, Latin as whole words); ambiguous names deferred; fuzzy fallback with difflib ≥ 0.80 | `nagarvani/location.py`, `data/gazetteer.json` |
| Severity | Forward-chaining production system: 23 cue groups, 19 rules in salience order, default P3; R32 escalates at ≥ 3 reports | `nagarvani/severity.py` |
| Duplicates | Block on (ward, department), remove place names, char 2–4-gram TF-IDF cosine: ≥ 0.45 merge, 0.30–0.45 officer decides | `nagarvani/dedup.py` |
| Gate | Auto-route only if top probability ≥ 0.50 **and** the ward office is resolved | `nagarvani/pipeline.py` |
| Entry point | `triage()`: calls the components above in the original order; adds explanations for the trace page | `nagarvani/triage.py` |
| ASR | faster-whisper, zero-shot, language forced, int8 on CPU; guards for length, silence, empty and repeated output | `nagarvani/speech.py` |

The first six rows are the **original prototype's code, kept byte-identical** and checksummed.

## Repository layout

```
run.py                       start the app
requirements.txt             pinned dependencies (scikit-learn 1.8.0, as the shipped model)
nagarvani/                   the package
  normalise classifier location severity dedup store pipeline asr   ORIGINAL prototype logic (frozen)
  triage.py                  triage(): the entry point used by evaluation and app
  train.py                   python -m nagarvani.train
  speech.py                  faster-whisper backend and guards
  tickets.py service.py      web-app ticket store; submission and officer-action logic
  app.py templates/ static/  Flask app (server-rendered, plain CSS, small vanilla JS)
  results_view.py            headline figures derived from results/results.json
  examples.py                demo inputs (also the one-click examples)
corpus/                      FROZEN: training corpus + generator, 160 test complaints, 30 duplicate pairs
data/gazetteer.json          FROZEN: 59 localities -> 15 ward offices
data/FROZEN.sha256           checksums of everything frozen
data/taxonomy.json           Marathi display names only (not frozen logic)
data/audio/                  real clips for ASR evaluation (git-ignored; see README there)
experiments/run_eval.py      the evaluation behind every reported number
results/                     results.json, figures, queues, model.pkl; *_shipped = as delivered by the prototype
eval/asr_eval.py             real-audio evaluation (once clips exist)
scripts/                     fetch_models, reset_demo, run_demo_script, reproduce, checksums
tests/                       pytest suite
docs/                        HANDOVER, DECISIONS, INVENTORY, DEMO_SCRIPT, PROGRESS, annotation_guideline, prototype/
archive/                     earlier, superseded work (midsem notebook; 2026-10-02 rebuild)
models/  instance/           Whisper weights; SQLite database and uploads (both git-ignored)
```

## Proposed versus built

The original methodology proposed twelve modules.

| Module | Status |
|---|---|
| Ingestion | **Built, web form only** (microphone, file upload, typing). No WhatsApp, IVR or telephony. |
| ASR | **Built, zero-shot Whisper** (faster-whisper), not fine-tuned. Code and guards are tested with a mocked backend. **Real audio has not been evaluated yet.** |
| Normalisation | **Built** (NFC, zero-width, digits, case, repeated characters, punctuation). No transliteration. |
| Department classifier | **Built**: TF-IDF + logistic regression, 10 departments, no sub-categories. |
| Location | **Built**: gazetteer alias matching + fuzzy fallback. No entity model, GPS or ward polygons. |
| Severity | **Built**: rules only (19-rule forward chaining). A learned model exists only as an evaluation baseline. |
| Duplicates | **Built**: character n-gram cosine with ward/department blocking. No embeddings or geo-distance. |
| Routing and gate | **Built.** |
| Dashboard | **Built, officer queue only** (filters, sorting, overdue flags, corrections, CSV export). |
| Feedback | **Corrections logged only** (JSONL export). No retraining. |
| Clarification dialogue | Not built. |
| Closure verification | Not built. |
| PMC CARE adapter | Not built. Output is SQLite plus per-ward CSV. |

## Limitations

* All training and test data was written by the team. No real PMC complaints were used.
* Accuracy inside the template data is about 13 points higher than on the hand-written test
  complaints (exact values on `/about`). So the hand-written figure is the one that means
  anything, and real complaints would likely be harder still.
* The severity rules and the severity labels were written by the same team, so the severity
  agreement figure is in-sample.
* ASR is zero-shot Whisper with no Marathi fine-tuning. Real-audio evaluation has **not been
  run** (`results/asr_eval.json` does not exist yet). The character-noise results are a
  **simulation**.
* No integration with PMC CARE. Output is a local SQLite database and per-ward CSV files.
* SLA hours are proposed values, not official PMC figures.
* No authentication: single user, single machine.

## Rules for changing things

The data, the original logic and the thresholds are frozen, and the reported numbers depend
on them. See [`CLAUDE.md`](CLAUDE.md) and [`docs/DECISIONS.md`](docs/DECISIONS.md)
("Found but not changed").
