# NagarVani — नगरवाणी

A triage layer for civic complaints to the Pune Municipal Corporation (PMC). A citizen speaks
or types a complaint in Marathi or Hindi (Devanagari, romanised, or mixed with English). The
system then:

1. assigns a **department** (one of 10),
2. resolves the place to one of **15 ward offices**,
3. sets a **severity band** with a rule-based expert system,
4. checks open tickets for **duplicates**,
5. **auto-routes** the ticket or sends it to a **human review queue**.

Every decision is shown step by step on a trace page.

It is a course prototype for IT3232 Artificial Intelligence (VIT Pune). It is a proposal, not a
production system, and it does not connect to PMC's real platform (PMC CARE has no public API).

> **Status and known gaps:** see [`docs/HANDOVER.md`](docs/HANDOVER.md), which starts with what
> does not work yet. Measured results: [`results/eval.md`](results/eval.md). Every figure there
> comes from `python eval/evaluate.py`. None is typed by hand.

## Requirements

* Python **3.11** (64-bit), on Windows 10/11, macOS or Linux.
* About 1 GB of disk for the Whisper `small` model (more for larger models).
* Internet **once**, for `pip install` and the model download. After that everything runs offline.
* No system ffmpeg: audio decoding uses the FFmpeg libraries bundled with the `av` package.

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

### Choosing the Whisper model (do this once on the demo laptop)

Record a ~15-second Marathi complaint (any format), then run:

```bash
python scripts/fetch_models.py --benchmark path/to/clip.ogg
```

This times `tiny` → `large-v3` on this machine. It writes `results/asr_benchmark.json` and
recommends the largest model that transcribes the clip in about 20 s or less. Select that model with
`NAGARVANI_ASR_MODEL=<name>` (Windows: `set NAGARVANI_ASR_MODEL=<name>`) before `python run.py`.
Optional: `NAGARVANI_ASR_PROMPT=1` turns on vocabulary biasing (civic terms and locality names
as Whisper's `initial_prompt`; default off). `NAGARVANI_PORT` changes the port.

## Using it

| Page | What it is |
|---|---|
| `/` | Citizen intake: microphone, audio upload (WhatsApp `.ogg` works) or typing. Marathi/Hindi toggle (forced, not auto-detected). The transcript must be checked (tick box) before submitting. Optional ward dropdown. One-click example complaints. No name or phone number is collected. |
| `/ticket/<id>` | The trace: what was heard, department top 3, location match, every severity rule fired, duplicate score against the thresholds, and the gate decision with the exact condition. |
| `/queue` | Officer view: review list and routed list. Filter by ward, department and status; sorted by priority then deadline; overdue flagged. Confirm, correct department/ward/priority, decide duplicates, resolve. |
| `/export/<ward>.csv` | One ward's open queue (e.g. `/export/W08.csv`). UTF-8 with BOM so Excel shows Devanagari. |
| `/corrections.jsonl` | Every officer correction. Logged as possible training data; retraining is **not** implemented. |
| `/about` | Headline results read from `results/*.json`, plus the limitations. |
| `/health` | Whether the classifier, database and ASR model are loaded. |

The demo walkthrough, with the real output of every input, is in
[`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md).

## Reproducing every number

```bash
python scripts/reproduce.py
```

It runs these steps:
1. Verify the frozen data checksums (`data/FROZEN.sha256`).
2. Check that `data/train.csv` regenerates exactly from the templates.
3. Rebuild the classifier and check it predicts exactly like `artefacts/classifier.joblib`.
4. Re-run the evaluation and check `results/eval.json` is reproduced byte for byte.
5. Run the real-audio ASR evaluation if clips exist in `data/audio/`.

You can also run each part on its own:

```bash
python -m nagarvani.train          # rebuild the classifier artefact (deterministic)
python eval/evaluate.py            # department, ward, gate, severity, duplicates, simulated noise, external set
python eval/asr_eval.py            # WER/CER and end-to-end from audio (needs data/audio/manifest.csv; see data/audio/README.md)
python -m pytest -q                # full test suite, including tests/test_frozen_metrics.py
python scripts/run_demo_script.py  # regenerate docs/DEMO_SCRIPT.md from real outputs
```

## How it works

| Step | Method | Code |
|---|---|---|
| Normalisation | Unicode NFC, zero-width removal, Devanagari digits → ASCII, punctuation → space, Latin lower-case | `nagarvani/normalise.py` |
| Department | TF-IDF (char_wb 2–5 grams + word 1–2 grams) → class-balanced logistic regression; C chosen by 5-fold CV log-loss on the training set only | `nagarvani/classifier.py` |
| Ward office | Gazetteer alias match, longest first, Marathi/Hindi/romanised suffixes allowed; fuzzy fallback with difflib ≥ 0.80; ambiguous or unknown places are never guessed | `nagarvani/location.py`, `data/gazetteer.json` |
| Severity | Forward-chaining expert system with salience; cue groups → rules → band P1–P4; R32 escalates at ≥ 3 reports | `nagarvani/severity.py`, `data/severity_rules.json` |
| Duplicates | Block on (ward, department), mask place names, character 2–4-gram cosine: ≥ 0.45 merge, 0.30–0.45 officer decides, < 0.30 new | `nagarvani/dedup.py` |
| Gate | Auto-route only if top probability ≥ 0.50 **and** the ward office is known; otherwise review | `nagarvani/pipeline.py` |
| ASR | faster-whisper, zero-shot, language forced, int8 on CPU; guards for length, silence, empty and repeated output | `nagarvani/asr.py` |

`nagarvani.pipeline.triage()` is the single entry point used by both the evaluation and the
web app, so the demo runs the same code that produced the numbers.

## Repository layout

```
run.py                     start the app
requirements.txt           pinned dependencies
nagarvani/                 the package
  pipeline.py              triage(): the one entry point
  classifier.py train.py   department model; python -m nagarvani.train
  location.py severity.py dedup.py normalise.py
  asr.py                   faster-whisper wrapper and guards
  store.py service.py      SQLite persistence; submission and officer-action logic
  app.py templates/ static/   Flask app (server-rendered, plain CSS, small vanilla JS)
  examples.py              demo inputs (also the one-click examples)
data/                      FROZEN data (checksums in data/FROZEN.sha256)
  taxonomy.json            10 departments, 15 ward offices, severity bands + proposed SLA hours
  gazetteer.json           localities → ward offices, ambiguous names, fuzzy stopwords
  severity_rules.json      cue groups and rules of the expert system
  templates.json → train.csv   synthetic training data (scripts/generate_train.py)
  test_handwritten.csv     160 test complaints;  test_duplicate_pairs.csv  60 pairs
  keywords.json            keyword baseline lexicon
  external/midsem_seed_AB.csv  the team's midsem seed set (external check only)
  audio/                   real clips for ASR evaluation (git-ignored; see README there)
artefacts/classifier.joblib   trained classifier (+ .json with C and CV scores)
eval/evaluate.py asr_eval.py  evaluation scripts → results/
results/                   eval.json / eval.md (and asr_eval.*, asr_benchmark.json once run)
scripts/                   fetch_models, reset_demo, run_demo_script, reproduce, checksums, generate_train
tests/                     pytest suite
docs/                      HANDOVER, DECISIONS, DEMO_SCRIPT, INVENTORY, PROGRESS, verification logs
archive/midsem/            the earlier Colab/Gradio prototype (not reference behaviour)
models/                    Whisper weights (git-ignored)
instance/                  SQLite database and uploaded audio (git-ignored)
```

## Proposed versus built

The original methodology proposed twelve modules.

| Module | Status |
|---|---|
| Ingestion | **Built, web form only** (microphone, file upload, typing). No WhatsApp, IVR or telephony. |
| ASR | **Built, zero-shot Whisper** (faster-whisper), not fine-tuned. Code and guards are tested with a mocked backend; **real audio has not been evaluated yet**. |
| Normalisation | **Built, light** (NFC, zero-width, digits, punctuation, case). No transliteration. |
| Department classifier | **Built**: TF-IDF + logistic regression, 10 departments, no sub-categories. |
| Location | **Built**: gazetteer alias matching + fuzzy fallback. No entity model, GPS or ward polygons. |
| Severity | **Built**: rules only (forward chaining). A learned regressor exists only as an evaluation baseline. |
| Duplicates | **Built**: character n-gram cosine with ward/department blocking. No embeddings or geo-distance. |
| Routing and gate | **Built.** |
| Dashboard | **Built, officer queue only** (filters, sorting, overdue flags, corrections, CSV export). |
| Feedback | **Corrections logged only** (JSONL export). No retraining. |
| Clarification dialogue | Not built. |
| Closure verification | Not built. |
| PMC CARE adapter | Not built. Output is SQLite plus per-ward CSV. |

## Limitations

* All training and test data was written for this project. No real PMC complaints were used.
  The 160 test complaints, the duplicate pairs, the training templates and the severity rules
  were drafted during this build, not by the team, and share an author (see `docs/DECISIONS.md` D3).
* Accuracy inside the template data is much higher than on separately written text (exact gap
  in `results/eval.md`). The separately written figure is the one that means anything, and
  real complaints would likely be harder still.
* The severity rules and the test severity labels share an author, so severity agreement is
  in-sample. Agreement with the team's independently written midsem labels is reported
  alongside it and is lower.
* ASR is zero-shot Whisper with no Marathi fine-tuning. Real-audio evaluation has **not been
  run** (no clips yet; `results/asr_eval.json` does not exist). The character-noise results in
  `results/eval.md` are a **simulation**, not ASR.
* ASR guard thresholds and the "transcript uncertain" flag are heuristics. ASR confidence does
  not enter the routing gate.
* No integration with PMC CARE. Output is a local SQLite database and per-ward CSV files.
* SLA hours are the team's proposed values, not official PMC figures.
* No authentication: single user, single machine.

## Rules for changing things

The data files and thresholds are frozen, and the numbers in `results/` depend on them. See
[`CLAUDE.md`](CLAUDE.md) and [`docs/DECISIONS.md`](docs/DECISIONS.md) ("Found but not changed").
