# CLAUDE.md

NagarVani: Marathi/Hindi civic-complaint triage for PMC. It is a course prototype in
Python 3.11 with scikit-learn 1.8.0, Flask, SQLite and faster-whisper. Templates are
server-rendered, with plain CSS and a little vanilla JS. There is no build step and no ORM,
and nothing runs on the network at runtime.

## Layout

* `nagarvani/{normalise,classifier,location,severity,dedup,store,pipeline,asr}.py` are the
  **original prototype logic, byte-identical and checksummed**. Never edit them.
* `nagarvani/triage.py` holds `triage()`, the single entry point. It wraps the original
  components. The evaluation and the web app both call it.
* `corpus/` and `data/gazetteer.json` are frozen data. All checksums are in `data/FROZEN.sha256`.
* `experiments/run_eval.py` produces every reported number (`results/results.json`).
* `docs/HANDOVER.md` gives current status. `docs/DECISIONS.md` records choices and
  "Found but not changed".
* `archive/` holds superseded work: the midsem notebook and the 2026-10-02 rebuild. Never use it.

## Commands

```
python -m pytest -q              # all tests; tests/test_frozen_metrics.py guards the numbers (~2 min)
python scripts/reproduce.py      # verify every reported number
python experiments/run_eval.py   # regenerate results/results.json and figures
python run.py                    # start the app on 127.0.0.1:5000
python scripts/reset_demo.py --yes
```

## The frozen-numbers rule

The numbers in `results/results.json` are in the submitted report and the paper. Do not edit,
regenerate, re-split or re-tune any of the following:

* the corpus and the gazetteer;
* the original modules;
* the classifier configuration;
* any threshold.

Never tune anything against `corpus/test_handwritten.tsv`.

When you find a bug in frozen logic:

* If the fix leaves `tests/test_frozen_metrics.py` passing, apply it outside the frozen files.
* If the fix would change any number, do not apply it. Log it in `docs/DECISIONS.md` under
  "Found but not changed", with a reproducing input.

A deliberate re-freeze is the team's decision. It means updating `data/FROZEN.sha256`, the
expected values in the test, and the report, all together.

## Conventions

* Open every file with `encoding="utf-8"`. Scripts call `nagarvani.console.safe_console()`
  so printing Devanagari cannot crash a Windows console.
* Use Python scripts, not shell scripts or Makefiles, so everything works on Windows and Linux.
* Every number shown in the UI or docs must be read from a file that a script wrote.
* No LLM calls anywhere in the pipeline.
