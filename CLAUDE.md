# CLAUDE.md

NagarVani: Marathi/Hindi voice-first triage of Pune Municipal Corporation (PMC) civic
complaints. A complaint (typed or spoken; Marathi, Hindi, romanised Marathi or code-mixed) is
normalised, classified to one of 10 departments, resolved to one of 15 ward offices, given a
severity band P1–P4 by a rule-based expert system, checked for duplicates, and then either
auto-routed to a ward queue or deferred to a nodal officer.

IT3232 Artificial Intelligence course project, VIT Pune, TY IT, 2026–27. Team: Aarush Sengupta,
Abhinandan Goswami, Viraj Adake, Adithya Sagri. Guide: Prof. (Dr.) Pravin R. Futane.

It is a course prototype in Python 3.11 with scikit-learn 1.8.0, Flask, SQLite and
faster-whisper. Templates are server-rendered, with plain CSS and a little vanilla JS. There is
no build step and no ORM, and nothing runs on the network at runtime.

**Final demo: Monday 2 November 2026. Code freeze: Sunday 1 November, 22:00.**
The schedule and the prompt for each phase are in `docs/FINAL_PLAN.md`.

## Scope boundary (never violate)

PMC CARE has no public API. NagarVani does NOT file complaints into PMC CARE. It writes to local
SQLite and exports per-ward CSV queues. Its output is a pre-triaged recommendation that awaits
confirmation by a nodal officer: a proposal, not an integration. No WhatsApp, IVR or telephony
work in this release.

## Layout

* `nagarvani/{normalise,classifier,location,severity,dedup,store,pipeline,asr}.py` are the
  **original prototype logic, checksummed** (triage core, M3–M7). See the frozen-numbers rule.
* `nagarvani/triage.py` holds `triage(text, ward_hint=None, store=None)`, the single entry
  point. It wraps the original components. The evaluation and the web app both call it.
* `nagarvani/speech.py` is the faster-whisper backend (M2), with input guards.
* `nagarvani/tickets.py` and `service.py` hold the web-app ticket store and officer actions.
* `nagarvani/app.py`, `nagarvani/templates/` and `nagarvani/static/` are the Flask app. `run.py` starts it.
* `nagarvani/{config,data,console,examples,results_view}.py` are helpers: paths and settings,
  data loading, the Windows console fix, demo examples, and reading `results/` for the UI.
* `nagarvani/train.py` rebuilds `results/model.pkl`.
* `corpus/` holds the template generator, 2,000 training rows (`train_template.tsv`), the
  160-row `test_v1` set (`test_handwritten.tsv`) and 30 duplicate pairs (`dup_pairs.tsv`).
  `corpus/test_v2*` is the held-out set written by teammates (see the evaluation rules).
* `data/gazetteer.json` is frozen. `data/taxonomy.json` is display metadata only. Checksums are in `data/FROZEN.sha256`.
* `data/audio/` holds the real recordings and `manifest.csv` (git-ignored except the README and example).
* `experiments/run_eval.py` produces every reported number (`results/results.json`).
* `eval/asr_eval.py` produces WER/CER and the end-to-end results from real audio (`results/asr_eval.json`).
  `eval/recording_assignments.csv` lists who records which test complaint.
* `scripts/` holds `fetch_models`, `reset_demo`, `run_demo_script`, `reproduce` and `checksums`.
* `tests/` is the pytest suite.
* `docs/HANDOVER.md` gives current status. `docs/DECISIONS.md` records choices and
  "Found but not changed". `docs/REPORT_CHANGES.md` lists every report and paper edit.
* `archive/` holds superseded work: the midsem notebook and the 2026-10-02 rebuild. Never use it.

## Commands

```
python -m pytest -q                       # all tests; tests/test_frozen_metrics.py guards the numbers (~2 min)
python scripts/reproduce.py               # verify every reported number
python experiments/run_eval.py            # regenerate results/results.json and figures
python -m nagarvani.train                 # rebuild results/model.pkl
python scripts/checksums.py --verify      # check data/FROZEN.sha256
python eval/asr_eval.py [--model NAME]    # real-audio evaluation (needs data/audio/manifest.csv)
python scripts/fetch_models.py [--benchmark CLIP]   # download Whisper once; time the model sizes
python run.py                             # start the app on 127.0.0.1:5000
python scripts/reset_demo.py --yes
```

## Versioning

* Tag `v1.0` is the code that produced every number in PBL-4 and PBL-5. **Never move or rewrite it.**
* All final-version work goes to branch `final`. Claude Code sessions push to their own branch,
  and Aarush merges it into `final`. `final` is merged into `main` and tagged `v2.0` at code freeze.

## The frozen-numbers rule

The numbers in `results/results.json` are in the submitted report and the paper. Outside
Phase 2 of `docs/FINAL_PLAN.md`, do not edit, regenerate, re-split or re-tune any of the following:

* the corpus and the gazetteer;
* the original modules;
* the classifier configuration;
* any threshold (τ=0.50, θ_high=0.45, θ_low=0.30, fuzzy 0.80).

Never tune anything against a test set (`corpus/test_handwritten.tsv` or `corpus/test_v2*`).
If a threshold changes, justify it from the training data or cross-validation only.

When you find a bug in frozen logic outside Phase 2:

* If the fix leaves `tests/test_frozen_metrics.py` passing, apply it outside the frozen files.
* If the fix would change any number, do not apply it. Log it in `docs/DECISIONS.md` under
  "Found but not changed", with a reproducing input.

**Phase 2 is the team's deliberate re-freeze** (defects F1–F6 only). Any edit to a core file or
frozen data file must, in the same commit:

* regenerate `data/FROZEN.sha256`;
* update `tests/test_frozen_metrics.py` to the new values, keeping the old values in a comment;
* add every changed number to `RESULTS.md` (metric, v1.0 value, v2.0 value, test set, command).

## Evaluation honesty rules

* `test_v1` (160 rows, written by the rule authors) is where F1–F6 were found.
* `test_v2` was written by teammates who did not write the rules. It is held out:
  * do not open, print or inspect its rows while designing fixes;
  * run the evaluation on it only after the fixes are committed.
* Report bad numbers as they are. Zero-shot Whisper on Marathi may score poorly; that is a
  finding, not a failure.

## Working rules

* Start every phase in plan mode. Do not edit until the plan is approved.
* `python -m pytest -q` must pass before every commit. Add tests for every fix and feature.
* Make one commit per logical change. Start the message with the phase, e.g.
  `P2: add stop-words to fuzzy ward matcher (F1)`.
* After each phase, append to `docs/REPORT_CHANGES.md` which report or paper section or table
  changes, and its new text or values.

## Conventions

* Open every file with `encoding="utf-8"`. Scripts call `nagarvani.console.safe_console()`
  so printing Devanagari cannot crash a Windows console.
* Use Python scripts, not shell scripts or Makefiles, so everything works on Windows and Linux.
* Every number shown in the UI or docs must be read from a file that a script wrote.
* No LLM calls anywhere in the pipeline.
* The app must keep running fully offline after setup. Do not use CDN links: vendor any JS or
  CSS into `nagarvani/static/`.
* Do not break typed-only operation when the Whisper model is absent.
* Keep UI text bilingual (Marathi + English) where the existing templates do.
