# Progress

Build restarted from scratch on 2026-10-02 (see docs/DECISIONS.md D1).

| Phase | Status |
|---|---|
| 0. Inventory, data authoring and freeze | **Done.** Midsem archived. Taxonomy, gazetteer, test set, duplicate pairs, rules, keywords and templates written; train.csv generated; checksums in data/FROZEN.sha256. |
| 1. Pipeline, classifier, evaluation, frozen-metrics test | Next. |
| 2. ASR (faster-whisper) | Not started. |
| 3. Flask app | Not started. |
| 4. Demo tooling | Not started. |
| 5. Verification and handover | Not started. |

Resuming: read the brief, this file and docs/DECISIONS.md, run `python scripts/checksums.py --verify`.
