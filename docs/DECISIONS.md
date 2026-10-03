# Decisions

Choices the brief left open, deviations from it, and the reasons. Decisions from the
superseded 2026-10-02 rebuild are in `archive/rebuild_2026-10-02/docs/DECISIONS.md`. Only those
still in force are restated here.

## R1. Wrap the original prototype; supersede the from-scratch rebuild

The original prototype reproduces every reported number (`docs/INVENTORY.md`). So the brief
applies as written: its data and logic are frozen, and the new code wraps them. The rebuild's
data, results and logic went to `archive/rebuild_2026-10-02/`. Its web app, ASR module, ticket
store, tests and demo tooling were re-pointed at the original logic.

## R2. Original files stay at their original paths, byte-identical

The prototype's modules use paths relative to their own location (`../data/gazetteer.json`,
`../corpus/`, `../results/model.pkl`). Keeping its layout means they run with **zero edits**,
and they are checksummed alongside the data (`data/FROZEN.sha256`). The wrapper modules that
would have clashed got new names:
* `triage.py`: the `triage()` entry point;
* `tickets.py`: the web app's ticket store;
* `speech.py`: the faster-whisper backend.

## R3. `triage()` reproduces `Triage.triage` and only adds explanation

`nagarvani/triage.py` calls the original classifier, resolver, duplicate detector and
`severity.infer`, in the original order with the original thresholds. It adds read-only
explanation for the trace page:
* the alias that matched, and the fuzzy score (re-derived by the same scan);
* the cue term behind each fired rule;
* rules that were superseded, or the service-request rule suppressed by a hazard;
* the dropdown ward hint, and UTC timestamps.

`tests/test_triage_equivalence.py` checks that department, confidence, top 3, ward,
band, fired rules, route and deadline equal the original on all 160 test complaints.
`experiments/run_eval.py` asserts the same on every complaint of the E8 stream.

## R4. Three marked changes to `experiments/run_eval.py`

1. **Hash-seed pin.** The script re-runs itself under `PYTHONHASHSEED=3` (see F4).
2. **Output folder.** `NAGARVANI_RESULTS_DIR` lets the tests write to a temporary folder.
3. **E8 through `triage()`.** The end-to-end stream goes through `triage()` with a live ticket
   store, and the original `Triage` runs alongside with every decision asserted equal.

With these changes the full `results.json` still equals the shipped one.

## R5. scikit-learn pinned to 1.8.0

The shipped `model.pkl` was pickled with 1.8.0, so that's the version the code was written
against. Results reproduce under both 1.8.0 and 1.9.1, with float differences of 1e-16 or
smaller. The rebuilt model predicts identically to the shipped one, with probabilities within
1e-15.

## R6. Web-app policy layered on the original decisions

These apply only in the live app. The offline evaluation never uses them.
* **A dropdown ward counts as "ward known" for the gate.** It is used only when the text
  resolver fails, and the trace marks it.
* **A merge links the report to the open ticket only when the gate passes.** A report that
  fails the gate goes to review with the duplicate shown as a pending decision. Similarity
  0.30–0.45 sends the report to review ("officer decides").
* **Escalation applies to the open ticket.** When R32 fires on a merged report, the open
  ticket's priority becomes the more urgent of the two.
* **What the original does.** It records the merge as a cluster link and routes by the gate
  alone. `triage()` reports that original decision as `route_original`.

## R7. Speech (carried over from the rebuild)

* **The model could not be downloaded here**, because the sandbox network blocks
  huggingface.co. So no ASR model has been run, and model timing and selection by
  measurement were not done. `scripts/fetch_models.py --benchmark` does both on the demo
  laptop. The default `small` is a placeholder.
* **The guard thresholds are heuristics:**
  * length 1–60 s;
  * fewer than 10% voiced frames counts as silence;
  * repetition rules;
  * no-speech probability ≥ 0.80;
  * a "transcript uncertain" flag when average log-probability is below -1.0.

  None of them enters the routing gate.
* **Decoding settings:** the language is forced, beam size 5,
  `condition_on_previous_text=False`, and the VAD filter is off because the guards run first.
* **Separate scoring normalisation.** WER/CER use `speech.plain_text`, which is NFC with all
  punctuation stripped. The original `normalise` keeps commas, full stops and hyphens, which
  would count as errors.

## R8. Display metadata is not frozen

`data/taxonomy.json` holds only Marathi display names and band labels. SLA hours come from
`severity.SLA_HOURS`.

# Found but not changed

Each item is a defect in frozen data or logic. Fixing it would change reported numbers, or
could, so it's left for the team to decide in a deliberate re-freeze.

| # | Where | Reproducing input | What happens |
|---|---|---|---|
| F1 | Fuzzy ward fallback (`location.py`), no stopwords | Test T080: `डीपी बॉक्सचं दार उघडं आहे आणि वायर बाहेर आलेत, मुलं जवळ खेळतात` | बाहेर ("outside") ≈ बाणेर, so the ward is wrongly resolved to Aundh-Baner. The paper reports this. It's the one false resolution, so correctly-unresolved is 23/24. |
| F2 | `severity.py` cue OPEN | `मॅनहोलचे झाकण गायब आहे` (DRAIN) | "गायब" (missing) isn't in OPEN, so R02 (open manhole, P1) does not fire and the result is P3. |
| F3 | `severity.py` cue OPEN | `मॅनहोलचे झाकण नवीन बसवले, आता काही समस्या नाही` (DRAIN) | "नाही" ("not") is in OPEN, so a resolved cover still fires R02 and gives P1. |
| F4 | `location.py`: `sorted(set(pairs), key=lambda p: -len(p[0]))` | `PYTHONHASHSEED=0` vs `2` on the E7 noise loop | Aliases of equal length are ordered by per-process string hashing, so fuzzy tie-breaks can differ between runs. Only one stored value moves: simulated-noise ward accuracy at 20% CER (0.7853 vs 0.7868). **The PBL-4 report prints it** (Table 5.4: 78.5%, and "79% at 20%" in Section 5.7), so the seed pin in `run_eval.py` is what keeps that figure reproducible. Do not apply the sort fix without updating the report. The fix would be `key=lambda p: (-len(p[0]), p)`. |
| F5 | `severity.py` cue OUTAGE | `चार दिवसांपासून नळाला पाणी आलेले नाही` (WATER) | The cue lists the colloquial "आलेलं नाही" but not the standard spelling "आलेले नाही", so R12 (outage ≥ 2 days → P2) does not fire. |
| F6 | Classifier calibration (behaviour, not a bug) | `कोथरूडमध्ये खूप त्रास होतोय, कोणीतरी लक्ष द्या` | A vague complaint gets HEALTH at 0.61 and is auto-routed. |
