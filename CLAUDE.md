# CLAUDE.md

NagarVani: Marathi/Hindi civic-complaint triage for PMC. It is a course prototype in
Python 3.11 with scikit-learn, Flask, SQLite and faster-whisper. Templates are
server-rendered, with plain CSS and a little vanilla JS. There is no build step and no ORM,
and nothing runs on the network at runtime.

## Layout

* `nagarvani/pipeline.py`: `triage()`, the single entry point. The evaluation and the web app both call it.
* `nagarvani/`: classifier, location, severity (expert system), dedup, asr, store, service, app.
* `data/`: frozen inputs. Checksums are in `data/FROZEN.sha256`.
* `eval/evaluate.py` writes `results/eval.json` and `results/eval.md`. `eval/asr_eval.py` evaluates real audio.
* `docs/HANDOVER.md` gives current status; `docs/DECISIONS.md` records choices and "Found but not changed".

## Commands

```
python -m pytest -q              # all tests; tests/test_frozen_metrics.py guards the numbers
python scripts/reproduce.py      # verify every reported number
python run.py                    # start the app on 127.0.0.1:5000
python scripts/reset_demo.py --yes
```

## The frozen-numbers rule

The numbers in `results/eval.json` may be in the team's report. Do not edit, regenerate or
re-tune any of the following:

* data files: test set, training templates/CSV, gazetteer, rules, keywords
* the classifier configuration
* the thresholds in `nagarvani/config.py`

Never tune anything against `data/test_handwritten.csv`.

When you find a bug in frozen logic:

* If the fix leaves `tests/test_frozen_metrics.py` passing, apply it.
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
