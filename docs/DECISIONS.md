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

With these changes the full `results.json` equals the shipped one at v1.0. Since v2.0 it
differs in exactly the values listed in `tests/test_frozen_metrics.py` (`V2_CHANGES`).
The F4 fix makes the hash-seed pin unnecessary; it is kept so that the script still runs the
same way. v2.0 adds a fourth change: `--test v2` and `--test-file` choose another test set,
written to `results/test_v2/` (R10).

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

## R9. Speech clips are recorded from test_v1 sentences

Phase 1 needs to compare each spoken complaint with the same complaint typed, so the 48
clips use `test_v1` rows (`eval/recording_assignments.csv`, picked by `eval/recordings.py`
with seed 2026). That reverses rule 3 of the earlier recording protocol in
`data/audio/README.md` ("do not reuse the test set").

The cost: on these sentences the classifier has already been evaluated, and the team wrote
both the sentences and the rules. Spoken-input results therefore measure **how much ASR
degrades** a known input, not how well the system generalises. Report the spoken and typed
results side by side and say so. Generalisation is what `test_v2` measures.

## R10. The v2.0 re-freeze (Phase 2): F1–F6 fixed

The team decided to fix the six logged defects in the original modules (docs/FINAL_PLAN.md,
Phase 2). Each fix has its own commit with a test that reproduces the reported input
(`tests/test_v2_fixes.py`), a regenerated `data/FROZEN.sha256`, and the changed values in
`tests/test_frozen_metrics.py`. Tag `v1.0` keeps the code behind the submitted numbers, and
`results/results_shipped.json` stays as the v1.0 record. `RESULTS.md` (written by
`scripts/write_results_md.py`) puts v1.0 and v2.0 side by side. No threshold or classifier
setting changed, and the classifier was not retrained.

`test_v2` is evaluated with `python experiments/run_eval.py --test v2`, once, after these
commits. None of its rows was opened while the fixes were designed.

## R11. F6: "no issue stated" is decided on what is left after place names and generic words

The plan's rule was: defer when no severity cue and no department keyword fires. With the
keyword-baseline lexicon that flagged 193 of the 2,000 training complaints (all of which state
a problem, e.g. "bewaras gadya padun aahet", "पथदिवे बंद आहेत"), 7 of the 160 test_v1 complaints
and the app's own misspelt-locality example ("कचऱ्याचा" does not contain "कचर"). So a third
condition was added: nothing may be left once gazetteer aliases and a fixed list of generic
words are removed (`nagarvani/issue.py`). The list is the training generator's greeting,
location and urgency frames plus common words for "trouble", "please look", pronouns and
auxiliaries. It was written before any test-set measurement and checked only on the training
data, where it flags none. It flags no test_v1 complaint either, so F6 changes no reported number.

# Fixed in v2.0 (formerly "Found but not changed")

Defects F1–F6 were found on v1.0 and fixed in the v2.0 re-freeze (R10). The table keeps the
original description; the fix and its effect on the reported numbers follow it.

| # | Fix in v2.0 | Effect on reported numbers |
|---|---|---|
| F1 | `location.FUZZY_STOPWORDS` (बाहेर, baher, kara, bandh, undir, banner, banners) never match fuzzily. All but बाहेर are the training-corpus words that fuzzy-match an alias they are not a form of. | test_v1 ward: correctly unresolved 23/24 → 24/24, no false resolution. Simulated 10% CER ward accuracy 92.6% → 92.9%. |
| F2 | OPEN gains गायब, gayab, हरवल, चोरी, missing, खुल, टूट, toot, broken, फुटल. | None. |
| F3 | "नाही"/"nahi" (and Hindi "नहीं") count as "no cover" only within two words after the cover or DP-box cue; an OPEN word followed by a negator within two words is negated (`severity.open_evidence`). | Simulated 20% CER severity accuracy 61.1% → 61.0%. |
| F4 | Aliases sorted by `(-len, alias, key)`. | Simulated 20% CER ward accuracy 78.5% → 78.7% (Table 5.4). |
| F5 | OUTAGE gains पाणी आलेले नाही, आले नाही, आलं नाही, पाणी नाही, pani aala nahi, पानी नहीं and similar. | None. |
| F6 | The gate defers a complaint that states no problem, with NO_ISSUE_STATED (R11). | None. |

Original descriptions:

| # | Where | Reproducing input | What happens |
|---|---|---|---|
| F1 | Fuzzy ward fallback (`location.py`), no stopwords | Test T080: `डीपी बॉक्सचं दार उघडं आहे आणि वायर बाहेर आलेत, मुलं जवळ खेळतात` | बाहेर ("outside") ≈ बाणेर, so the ward is wrongly resolved to Aundh-Baner. The paper reports this. It's the one false resolution, so correctly-unresolved is 23/24. |
| F2 | `severity.py` cue OPEN | `मॅनहोलचे झाकण गायब आहे` (DRAIN) | "गायब" (missing) isn't in OPEN, so R02 (open manhole, P1) does not fire and the result is P3. |
| F3 | `severity.py` cue OPEN | `मॅनहोलचे झाकण नवीन बसवले, आता काही समस्या नाही` (DRAIN) | "नाही" ("not") is in OPEN, so a resolved cover still fires R02 and gives P1. |
| F4 | `location.py`: `sorted(set(pairs), key=lambda p: -len(p[0]))` | `PYTHONHASHSEED=0` vs `2` on the E7 noise loop | Aliases of equal length are ordered by per-process string hashing, so fuzzy tie-breaks can differ between runs. Only one stored value moves: simulated-noise ward accuracy at 20% CER (0.7853 vs 0.7868). **The PBL-4 report prints it** (Table 5.4: 78.5%, and "79% at 20%" in Section 5.7), so the seed pin in `run_eval.py` is what keeps that figure reproducible. Do not apply the sort fix without updating the report. The fix would be `key=lambda p: (-len(p[0]), p)`. |
| F5 | `severity.py` cue OUTAGE | `चार दिवसांपासून नळाला पाणी आलेले नाही` (WATER) | The cue lists the colloquial "आलेलं नाही" but not the standard spelling "आलेले नाही", so R12 (outage ≥ 2 days → P2) does not fire. |
| F6 | Classifier calibration (behaviour, not a bug) | `कोथरूडमध्ये खूप त्रास होतोय, कोणीतरी लक्ष द्या` | A vague complaint gets HEALTH at 0.61 and is auto-routed. |

# Found but not changed

Each item is a defect in frozen data or logic found after the v2.0 re-freeze. Fixing it would
change reported numbers, or could, so it's left for the team to decide.

(None yet.)
