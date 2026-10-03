# Handover

Written for the developer. Read section 1 first.

## 1. What does not work, or was not verified

### Definition of done (from the brief)

| Item | Met? |
|---|---|
| `tests/test_frozen_metrics.py` passes and data checksums unchanged since Phase 0 | **Yes.** Every reported number reproduces from the original prototype. |
| A typed complaint and an uploaded audio file each go from intake to a ticket with a complete trace | **Partly.** Typed: yes. Uploaded audio: only with a **mocked** speech backend, never with real Whisper (problem 1). |
| The app starts and the audio path works with the network disabled | **Partly.** The app starts and works offline. The real audio path was not tested, because no model was available. |
| Officer queue filters, sorts, corrects, logs corrections, exports a ward CSV that opens in Excel | **Yes**, except that the CSV was not opened in Excel by eye. The byte-order mark is tested. |
| Triple-duplicate escalation works in the live app | **Yes** (tests and `docs/DEMO_SCRIPT.md` item 8). |
| Every input in `docs/DEMO_SCRIPT.md` was run and its real output recorded | **Yes** for the typed inputs. The spoken versions were not run. |
| No number in any template, README or doc is hard-coded or invented | **Yes**, as far as I checked. The UI derives every figure from `results/results.json`. The docs quote figures reproduced from it. |
| The fresh-clone test passed | **Yes**, apart from the model download, which this sandbox blocks. |
| `docs/HANDOVER.md` exists and opens with what is not working | Yes. |

### Problems

1. **No speech recognition model has been run.** The build sandbox blocks `huggingface.co`, so
   the faster-whisper code (`nagarvani/speech.py`) is tested only with a mocked backend,
   generated tones and silence. Audio decoding of WAV, MP3, M4A, MP4, WebM/Opus and OGG/Opus
   is verified for real. The model was not chosen by measurement: `small` is a placeholder.
   There are no real clips, so `results/asr_eval.json` does not exist. The report and paper
   already say voice input was not tested, and that is still true.
2. **Known defects in the frozen rules and gazetteer** are logged, not fixed (`docs/DECISIONS.md` F1–F6):
   * "मॅनहोलचे झाकण **गायब**" (cover missing) does not fire the open-manhole rule.
   * "…आता काही समस्या **नाही**" (no problem now) wrongly fires it.
   * The standard spelling "पाणी आलेले नाही" misses the outage rule.
   * The word बाहेर ("outside") resolves to Baner.
   * Vague complaints are auto-routed with confidence just over 0.5.
3. **Only verified on Linux.** The Windows and macOS instructions were not run on those
   systems. No microphone was used. The recording path (MediaRecorder) has no automated
   test, but the upload path was driven in headless Chromium.
4. **All data is team-constructed**, as the report already states. No real PMC complaints
   were used.

## 2. What happened in this build

* **2026-10-02.** The repository held only the midsem notebook, so a from-scratch rebuild was
  made. Its numbers differed from the report. It is now superseded and archived in
  `archive/rebuild_2026-10-02/`. None of its numbers belong in the report.
* **2026-10-03.** The original prototype (`NagarVani_prototype_code.zip`) was supplied. I ran
  it in a clean environment, and **every reported number reproduced**. The project was
  restructured as the brief intended:
  * **Frozen, byte-identical and checksummed:** the original eight logic modules, the
    corpus, the gazetteer, and the shipped results and model.
  * **New `triage()` entry point:** it wraps the original logic and adds explanations for the
    trace page. It is tested to make exactly the original decisions on all 160 test
    complaints.
  * **Kept from the rebuild and re-pointed at the original logic:** the web app, speech
    module, demo tooling and tests.
* **The PBL-5 paper draft was checked.** All of its figures match `results/results.json` (list
  in `docs/INVENTORY.md`).
* **The PBL-4 report was checked figure by figure.** One error was found: "both models reach
  99.8% under cross-validation". The char-only model reaches 99.65%. The sentence now reads
  "99.7–99.8%" in the report and in `docs/prototype/docs_build/report.js`. Details are in
  `docs/INVENTORY.md`, "PBL-4 report check".

## 3. What was verified, and how

| Check | Command | Result / log |
|---|---|---|
| Full test suite | `python -m pytest -v tests` | 246 passed, 1 skipped (the real-audio test: no clips). `docs/verification/pytest_full.txt` |
| Reported numbers | `tests/test_frozen_metrics.py`, which runs `experiments/run_eval.py` | All reported values match. The full `results.json` equals the committed one and the prototype's shipped one (timing excluded; floats to 1e-12). |
| Frozen files | `tests/test_data_frozen.py`, `python scripts/checksums.py --verify` | Checksums unchanged. The training corpus regenerates byte for byte. |
| Wrapper == original | `tests/test_triage_equivalence.py`, plus the per-item assertions inside `run_eval.py` | Identical on all 160 complaints. |
| Rebuilt model | `tests/test_model_artefact.py` | Identical predictions to the saved and shipped `model.pkl` (probabilities within 1e-9). |
| Fresh clone | Clone from GitHub, new venv from `requirements.txt`, checksums, tests | Pass. Model fetch fails with a clear message (Hugging Face blocked). `docs/verification/fresh_clone.txt` |
| Offline | Fresh clone under `unshare -n` | Every route works. A typed complaint becomes a ticket. Audio without a model becomes a review ticket. `docs/verification/offline_app.txt` |
| Browser JavaScript | Headless Chromium + Playwright, mocked speech backend | Upload → transcript → check box → ticket; examples; double-click gives one ticket; no JS errors. `docs/verification/browser_js.txt` |
| Demo | `python scripts/run_demo_script.py`; `tests/test_demo_script.py` | All 9 behaviours, also on top of the seed data. |

## 4. Reported versus reproduced

| Quantity | Reported | Reproduced |
|---|---|---|
| Department accuracy | 86.9% (139/160) | 139/160 |
| Department macro-F1 | 0.870 | 0.870 |
| Top-3 accuracy | 95.6% | 153/160 |
| Keyword baseline | 81.9% | 131/160 |
| Char-only logistic regression (not adopted) | 88.8% | 142/160 |
| CV accuracy inside the template data | 99.8% | 99.8% |
| Auto-routed | 70% | 112/160 |
| Auto-routed with correct department and ward | 97.3% | 109/112 |
| Department errors held for the nodal officer | 18 of 21 | 18 of 21 |
| Severity band accuracy (predicted department) | 95.6% | 153/160 |
| P1 recall | 94.4% | 34/36 |
| Learned severity baseline | 76.9% | 123/160 |
| Macro-F1 at simulated 10% character error | 0.811 | 0.811 |
| Ward accuracy at 10% noise, exact only / with fuzzy | 49% / 93% | 49.4% / 92.6% |

## 5. Deviations from the brief

* The brief's prototype was supplied a day late. A rebuild was made in between, then archived.
* `experiments/run_eval.py` has three marked edits: a hash-seed pin, an output folder, and the
  end-to-end stream run through `triage()` (DECISIONS R4).
* The wrapper modules are named `triage.py`, `tickets.py` and `speech.py`, so the original
  modules keep their names and paths (R2).
* Web-app policies:
  * a dropdown ward counts as resolved;
  * a merge only happens when the gate passes;
  * escalation applies to the open ticket (R6).
* The speech model was not chosen by measurement, and real audio was not tested offline (R7).

## 6. Found but not changed

See `docs/DECISIONS.md`. In brief, F1–F6:
* the बाहेर→बाणेर fuzzy match (already reported in the paper);
* "गायब" missing from the open-cover cue;
* "नाही" in the open-cover cue;
* hash-order nondeterminism in alias sorting;
* the "आलेले नाही" spelling missing from the outage cue;
* over-confident routing of vague complaints.

## 7. What the team still has to do by hand

1. **Speech.** On a machine with internet, run
   `python scripts/fetch_models.py --benchmark <15 s Marathi clip>` and set
   `NAGARVANI_ASR_MODEL`. Then disconnect and run a real clip end to end (`python run.py`,
   upload a WhatsApp `.ogg`).
2. **Real-audio evaluation.** Record clips following `data/audio/README.md` and run
   `python eval/asr_eval.py`. `/about` then shows WER/CER. The report can say voice was
   tested only once this is done.
3. **Decide on F1–F6.** Any fix is a deliberate re-freeze: update `data/FROZEN.sha256`, the
   expected values in `tests/test_frozen_metrics.py`, and the report, together.
4. **Finish the documents.** Fill in the author names, emails and PRNs in the PBL-5 paper and
   on the PBL-4 title page, then re-export both PDFs from Word.
5. **Rehearse on the demo laptop:** setup, microphone in the demo browser, and a ward CSV
   opened in Excel. Then run `python scripts/reset_demo.py --yes` and follow
   `docs/DEMO_SCRIPT.md`.
