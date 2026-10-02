# Progress

Build restarted from scratch on 2026-10-02 (see docs/DECISIONS.md D1).

| Phase | Status |
|---|---|
| 0. Inventory, data authoring and freeze | **Done.** |
| 1. Pipeline, classifier, evaluation, frozen-metrics test | **Done.** `triage()` in nagarvani/pipeline.py; `python -m nagarvani.train`; `python eval/evaluate.py`; tests/test_frozen_metrics.py guards the numbers. |
| 2. ASR (faster-whisper) | Next. |
| 3. Flask app | Not started. |
| 4. Demo tooling | Not started. |
| 5. Verification and handover | Not started. |

Resuming: read the brief, this file and docs/DECISIONS.md, then run `python -m pytest -q`.
