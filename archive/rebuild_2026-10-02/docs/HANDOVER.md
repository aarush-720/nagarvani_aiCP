# Handover

Written for the developer. Read the first section before anything else.

## 1. What does not work, or was not verified

### Definition of done (from the brief)

| Item | Met? |
|---|---|
| `tests/test_frozen_metrics.py` passes and data checksums unchanged since Phase 0 | **Yes** (for this build's numbers; the brief's numbers could not be reproduced: item 2 below) |
| A typed complaint and an uploaded audio file each go from intake to a ticket with a complete trace | **Partly.** Typed: yes. Uploaded audio: yes with a **mocked** ASR backend only; never with real Whisper (item 1) |
| The app starts and the audio path works with the network disabled | **Partly.** The app starts and works offline; the real audio path was not tested (no model) |
| Officer queue filters, sorts, corrects, logs corrections, exports a ward CSV that opens in Excel | **Yes**, except that opening in Excel was not checked by eye (the BOM is tested) |
| Triple-duplicate escalation works in the live app | **Yes** (tests and demo script) |
| Every input in `docs/DEMO_SCRIPT.md` was run and its real output recorded | **Yes** (typed inputs; spoken versions not run) |
| No number in any template, README or doc is hard-coded or invented | **Yes** to the best of my checking: the UI reads `results/*.json` and `data/taxonomy.json`; the docs quote figures from `results/eval.json` or point to it; the brief's figures appear only in the comparison table, labelled as such |
| The fresh-clone test passed | **Yes**, except for the model download, which this sandbox blocks |
| `docs/HANDOVER.md` exists and opens with what is not working | Yes |

### Problems

1. **No speech recognition model has been run.** The build sandbox's network policy blocks
   `huggingface.co`, where faster-whisper models are hosted, so no Whisper weights could be
   downloaded. As a result:
   * the ASR code (`nagarvani/asr.py`) is tested only with a mocked backend, generated tones and
     silence. Audio decoding of WAV, MP3, M4A, MP4, WebM/Opus and OGG/Opus is verified for
     real through PyAV;
   * the model was **not chosen by measurement**. The default `small` is a placeholder
     (DECISIONS D13). Run `python scripts/fetch_models.py --benchmark <clip>` on the demo laptop;
   * the **offline real-audio test was not done**. The offline test that was done shows the
     app starts and works with the network disabled: typed path, all routes, and audio saved
     as a review ticket when no model is present (`docs/verification/offline_app.txt`).
     Real Whisper transcription with the network off is untested;
   * `eval/asr_eval.py` has never run on real audio. There are no clips and no
     `results/asr_eval.json`.
2. **The numbers in your submitted report are not reproduced, and cannot be.** The repository
   held only the midsem notebook. No code or data existed that produced the brief's section 2
   figures. This build wrote new data and produced new numbers (table in section 4). **Update
   the report.** The new test accuracy is higher than the reported one. Do not present that as
   an improvement: the test set was written by the same author as the training templates
   (next item), which very likely inflates it.
3. **The evaluation data was written by Claude, not by the team.** That covers the 160 test
   complaints, the 60 duplicate pairs, the training templates, the gazetteer assignments and
   the severity rules and labels (DECISIONS D3). Test and training text share an author, and so
   do the severity labels and rules. The external check on your own midsem set is lower on
   departments, and much lower on severity. Before the viva, the team should review
   `data/test_handwritten.csv`, ideally replace it with complaints the team writes itself,
   and then re-freeze.
4. **Vague complaints are auto-routed with false confidence.** For example,
   "कोथरूडमध्ये खूप त्रास होतोय, कोणीतरी लक्ष द्या" ("there's a lot of trouble in Kothrud,
   someone please look") gets HEALTH at just over 0.50 and passes the gate. C = 100, chosen
   by CV log-loss on near-separable template data, makes the model over-confident.
   Calibration was not attempted, because it would need data that is not the test set.
   (Live values are in `docs/DEMO_SCRIPT.md`, "Inputs that were tried and rejected".)
5. **Only verified on Linux.** The Windows and macOS instructions were written, but not run on
   those systems. The font stack covers Devanagari on all three, but it was only seen
   rendering on Linux (with Noto). The CSV has a BOM and was checked programmatically; it was
   not opened in Excel.
6. **The microphone was never used.** The browser recording path (MediaRecorder) has no
   automated test, because there is no microphone. The upload path, the transcript-check gate,
   the example buttons and the double-submit guard were driven in headless Chromium with a
   mocked ASR backend (`docs/verification/browser_js.txt`).
7. **Ward-office assignments for localities and the ward spellings are unverified** against
   PMC sources.

## 2. What was built

* **Data (frozen):** 10 departments, 15 ward offices, and 74 localities with
  Devanagari/romanised aliases plus ambiguous names. A 2,000-row template training set,
  deterministic from `data/templates.json`. A 160-row test set: 16 per department; 80
  Marathi, 20 Hindi, 30 romanised, 30 code-mixed; labelled with department, ward, location
  case and severity. 60 duplicate pairs. A severity knowledge base of 30 cue groups and 24
  rules. A keyword lexicon. Your midsem seed set is kept as an external check.
* **Pipeline:** `triage()` covers normalisation, the classifier (TF-IDF char + word → LR,
  C by CV log-loss on train), ward resolution (exact + fuzzy, never guessing), forward-chaining
  severity with a firing trace and overrides, the SLA deadline, duplicate detection against
  the live store, and the frozen gate. Result: a `TriageResult` dataclass.
* **ASR:** a faster-whisper wrapper with forced language, an offline-only model directory,
  PyAV decoding, heuristic guards, an "uncertain" flag that does not affect routing, and an
  optional vocabulary prompt. There is a fetch/benchmark script, an ASR evaluation script and
  a recording protocol.
* **Web app:** intake (mic, upload, typing, check-before-submit, examples, optional ward),
  the trace page, the officer queue (filters, sorting, overdue, confirm, correct, duplicate
  decision, resolve, corrections JSONL), the per-ward CSV, `/about` (rendered from results
  JSON) and `/health`. Every submission is persisted before processing. Failures become
  review tickets. No stack traces are shown. Times are stored in UTC and displayed in IST.
* **Demo tooling:** `run.py`, `reset_demo.py` (25 seeded tickets from training templates,
  some overdue, some in review), `run_demo_script.py` → `docs/DEMO_SCRIPT.md` (9 behaviours,
  real outputs), and `reproduce.py`.

## 3. What was verified, and how

| Check | Command | Result / log |
|---|---|---|
| Full test suite | `python -m pytest -v tests` | 118 passed, 1 skipped (the real-audio test: no clips). `docs/verification/pytest_full.txt` |
| Frozen metrics and data checksums | `tests/test_frozen_metrics.py`, `tests/test_data_frozen.py` | pass |
| Every number reproduces | `python scripts/reproduce.py` | ALL STEPS PASSED (`results/eval.json` byte-identical) |
| Rebuilt model == saved artefact | `tests/test_model_artefact.py` | identical predictions, probabilities within 1e-9 |
| Fresh clone | clone from GitHub, new venv from `requirements.txt`, checksums, fetch models, tests | tests pass; model fetch fails with a clear message (Hugging Face blocked). `docs/verification/fresh_clone.txt` |
| Offline run | fresh clone started under `unshare -n` (no network) | every route 200, typed complaint → ticket, audio without a model → review ticket. `docs/verification/offline_app.txt` |
| Browser JS | headless Chromium + Playwright, mocked ASR | upload → transcript → check box → ticket; examples; double-click → one ticket; no JS errors. `docs/verification/browser_js.txt` |
| Demo inputs | `python scripts/run_demo_script.py`; `tests/test_demo_script.py` | all 9 behaviours as described, also on top of the seed data |

## 4. Reported versus reproduced numbers

The brief's values are copied here **only for comparison**. No code that produced them
existed. The right-hand column is read from `results/eval.json`.

| Quantity | Value in the brief / submitted report | This build (`results/eval.json`) |
|---|---|---|
| Department accuracy | 86.9% (139/160) | 94.4% (151/160) |
| Department macro-F1 | 0.870 | 0.944 |
| Department top-3 accuracy | 95.6% (153/160) | 98.1% (157/160) |
| Keyword baseline accuracy | 81.9% | 71.9% (115/160) |
| Char-only logistic regression accuracy | 88.8% (not adopted) | 93.8% (150/160) (not adopted) |
| CV accuracy inside the template data | 99.8% | 99.9% |
| Auto-routed share | 70% | 76.2% (122/160) |
| Auto-routed with correct department and ward | 97.3% | 96.7% (118/122) |
| Department errors caught by the gate | 18 of 21 | 55.6% (5/9) |
| Severity band accuracy (predicted department) | 95.6% | 84.4% (135/160) |
| P1 recall | 94.4% | 96.7% (29/30) |
| Learned severity baseline | 76.9% | 73.8% (118/160) |
| Macro-F1 under simulated 10% character error | 0.811 | 0.787 |
| Ward accuracy under simulated noise, exact-only | 49% | 31.4% (43/137) |
| Ward accuracy under simulated noise, with fuzzy | 93% | 85.4% (117/137) |
| *New:* department accuracy on the team's midsem set (coarse mapping) | — | 85.1% (370/435) |
| *New:* severity agreement with the team's midsem labels | — | 58.1% (151/260) |
| *New:* P1 precision | — | 90.6% (29/32) |
| *New:* duplicate merge precision / recall (60 pairs) | — | 100.0% (18/18) / 60.0% (18/30) |

## 5. Deviations from the brief

* The project was restarted from scratch (D1). The "frozen numbers" are this build's, frozen at
  the first evaluation run.
* The test set, pairs, templates and rules were written by Claude, not the team (D3).
* C is chosen by CV log-loss, not accuracy. The criterion changed before any test-set run (D9).
* Rule count and IDs (24 rules, 30 cue groups) differ from the brief's 19 rules and 23 cue groups (D5).
* A duplicate is only merged automatically when the gate passes (D10). A ward from the
  dropdown counts as resolved (D11).
* An extra external evaluation on your midsem set was added (D6). Dead animals are classed
  as VET (D7).
* The ASR model was not chosen by measurement, and real audio was not tested offline (D8, D13).
* The Whisper VAD filter is off, and the guards run first (D15).

## 6. Found but not changed

These are listed in `docs/DECISIONS.md` with reproducing inputs. Fixing any of them changes
the frozen numbers.

* **F1:** the gazetteer alias `banner` (for Baner) matches the English word "banner".
* **F2:** the fuzzy matcher reads बाहेर ("outside") as बाणेर.
* **F3:** inflected stem changes such as हिंगणे → हिंगण्यात are not resolved.

## 7. What the team still has to do by hand

1. On a machine with internet: `python scripts/fetch_models.py --benchmark <15 s Marathi clip>`.
   Set `NAGARVANI_ASR_MODEL` to the recommendation. Then disconnect the network and run a
   real clip end to end (`python run.py`, upload a WhatsApp `.ogg`).
2. Record clips following `data/audio/README.md`, write `data/audio/manifest.csv`, and run
   `python eval/asr_eval.py`. `/about` will then show the measured WER/CER.
3. Review, and preferably replace, the test set and the severity labels. Decide F1–F3. Then
   re-freeze deliberately, all at once: checksums (`python scripts/checksums.py --write`),
   `python eval/evaluate.py`, the expected values in `tests/test_frozen_metrics.py`, and the report.
4. Update the submitted report and paper draft to the numbers in `results/eval.md`, with the
   authorship caveat.
5. Verify the ward-office names and locality-to-ward assignments against PMC sources.
6. Run the setup once on the actual demo laptop (Windows or macOS). Open a ward CSV in Excel.
   Test the microphone in the browser you will demo with (Chrome records WebM/Opus, Safari MP4).
7. Before the demo: `python scripts/reset_demo.py --yes`, then follow `docs/DEMO_SCRIPT.md`.
