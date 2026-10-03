# Progress

| Phase | Status |
|---|---|
| 0. Inventory and baseline | **Done (2026-10-03).** Original prototype verified: every reported number reproduces (docs/INVENTORY.md). Frozen files checksummed in data/FROZEN.sha256; tests/test_frozen_metrics.py guards the numbers. |
| 1. One pipeline function | **Done.** `nagarvani.triage.triage()` wraps the original logic; equivalence tested on all 160 test complaints; the evaluation's end-to-end stream runs through it. `python -m nagarvani.train` rebuilds the artefact identically. |
| 2. Real speech recognition | **Done in code, with mocked tests.** `nagarvani/speech.py`, `scripts/fetch_models.py`, `eval/asr_eval.py`. No model run: huggingface.co is blocked in the build sandbox. |
| 3. Web application | **Done**, re-pointed at the original logic. |
| 4. Demo tooling | **Done.** run.py, reset_demo, run_demo_script → docs/DEMO_SCRIPT.md, reproduce. |
| 5. Verify and hand over | **Done.** Logs in docs/verification/; see docs/HANDOVER.md. |

History: a from-scratch rebuild was made on 2026-10-02, when the original prototype was not in
the repository. It is superseded and archived in archive/rebuild_2026-10-02/.
Remaining work for the team is in docs/HANDOVER.md, section 7.
