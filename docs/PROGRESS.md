# Progress

Build restarted from scratch on 2026-10-02 (see docs/DECISIONS.md D1).

| Phase | Status |
|---|---|
| 0. Inventory, data authoring and freeze | **Done.** |
| 1. Pipeline, classifier, evaluation, frozen-metrics test | **Done.** `triage()` in nagarvani/pipeline.py; `python -m nagarvani.train`; `python eval/evaluate.py`; tests/test_frozen_metrics.py guards the numbers. |
| 2. ASR (faster-whisper) | **Done (code + mocked tests).** nagarvani/asr.py, scripts/fetch_models.py, eval/asr_eval.py, data/audio/README.md. Model download blocked in the build sandbox (DECISIONS D8, D13). |
| 3. Flask app | **Done.** nagarvani/app.py, service.py, templates/, static/; tests/test_app.py. |
| 4. Demo tooling | **Done.** run.py, scripts/reset_demo.py, scripts/run_demo_script.py → docs/DEMO_SCRIPT.md, scripts/reproduce.py. |
| 5. Verification and handover | Next. |

Resuming: read the brief, this file and docs/DECISIONS.md, then run `python -m pytest -q`.
