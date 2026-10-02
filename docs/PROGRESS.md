# Progress

Build restarted from scratch on 2026-10-02 (see docs/DECISIONS.md D1).

| Phase | Status |
|---|---|
| 0. Inventory, data authoring and freeze | **Done.** |
| 1. Pipeline, classifier, evaluation, frozen-metrics test | **Done.** |
| 2. ASR (faster-whisper) | **Done in code, with mocked tests.** Real model never run: huggingface.co is blocked in the build sandbox. |
| 3. Flask app | **Done.** |
| 4. Demo tooling | **Done.** |
| 5. Verification and handover | **Done.** Logs in docs/verification/; see docs/HANDOVER.md. |

Remaining work is listed in docs/HANDOVER.md section 7. It is all for the team, by hand.
