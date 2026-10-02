# Decisions

Each entry records a choice the brief left open, or a deviation from it, and the reason.

## D1. Rebuild from scratch; the brief's numbers are not targets

The repository held only the midsem notebook, and the developer confirmed it is the final
prototype. The brief's "frozen numbers" rule assumed that code existed. It did not, so the
rule now protects **the numbers this build produces**. They are frozen at the first
evaluation run (Phase 1) and guarded by `tests/test_frozen_metrics.py`. I tuned nothing
toward the brief's values (86.9%, 139/160, ...). The team's submitted report has to be
updated to the numbers in `results/`.

## D2. Order of authoring, to avoid test-set leakage

1. Taxonomy, gazetteer, test set, duplicate pairs, severity rules and keyword lexicon were
   written first, before any model existed.
2. Training templates were written next.
3. A hygiene check compared every test sentence with its nearest training sentence
   (char 2-4 gram TF-IDF cosine). Six template phrases were near-paraphrases of test
   sentences (max cosine 0.82). I rewrote those **template** phrases, not the test
   sentences. After the rewrite the maximum was 0.74. `tests/test_data_hygiene.py` keeps
   it below 0.75.
4. All data files were checksummed (`data/FROZEN.sha256`) before the classifier was trained
   or any rule was run on the test set.

## D3. Who wrote the evaluation data (a limitation to state at the viva)

The brief describes a "hand-written" test set written by the team. Here, the 160 test
complaints, the 60 duplicate pairs, the training templates and the severity rules were all
drafted by Claude (an AI assistant) during this build. Two consequences:

* Test and training text share an author, so the test set is less independent than a
  team-written one. The team should review every test row and, ideally, replace it with
  complaints written by people who have not seen the templates.
* The severity labels and the severity rules share an author, so severity agreement is
  in-sample.

To partly offset this, the evaluation also reports results on the team's own midsem seed
set (`data/external/midsem_seed_AB.csv`, 460 rows, AI-drafted and human-checked by the team,
different style). See D6.

## D4. Thresholds are taken from the brief, not tuned

Gate confidence 0.50, fuzzy ratio 0.80, duplicate merge 0.45, duplicate review 0.30, and R32
at 3 reports are copied from the brief. They are pre-specified values, not fitted to data.
The logistic-regression C is chosen by 5-fold CV on the training set only, from
{0.1, 1, 10, 100}.

## D5. Severity design

* Bands P1-P4. The SLA hours (24/72/168/360) are the team's midsem proposal, labelled as
  proposed values everywhere.
* Forward chaining with salience. The most urgent proposal wins (safety first). The
  department default (R00) applies only when nothing else fires. P3/P4 complaints are raised
  one band when vulnerable people or places are mentioned (R30). R32 escalates one band at
  3 or more reports of the same issue.
* Rule IDs are grouped (R0x life safety, R2x urgency, R30/R32 modifiers, R40 low priority).
  They do not run consecutively, and the rule count (23) is whatever the knowledge base
  needed. It was not made to match the brief's "19 rules over 23 cue groups".

## D6. External set: label mapping

The midsem set has 8 departments + `other`. For external department accuracy, `other` rows
are dropped, and a prediction counts as correct when it falls in the mapped set:
roads→ROAD, solid_waste→SWM, water_supply→WATER, drainage→DRAIN, street_lights→ELEC,
trees_garden→TREE, encroachment→{ENCROACH, BUILD} (midsem merged the two),
health_mosquito→{HEALTH, VET} (midsem put stray dogs there). This is a coarse check of
transfer to differently-written text, not a like-for-like accuracy.

## D7. Dead animals belong to VET

Midsem put dead-animal removal under solid waste. Here it is VET, so that all animal
complaints go to one department. The team can change this in a re-freeze.

## D8. ASR model cannot be downloaded in the build environment

The build sandbox's network policy blocks `huggingface.co`, where faster-whisper models are
hosted. I did not try to route around the block through mirrors. Consequences, recorded
again in the handover:
* Model timing and selection by measurement (Phase 2) could not be done here.
  `scripts/fetch_models.py --benchmark` does it on the team's laptop and writes
  `results/asr_benchmark.json`.
* The offline real-audio test could not be run here.

## D9. How C was chosen (a change made before any test-set run)

The first criterion was mean 5-fold CV accuracy on the training set, with ties going to the
smaller C. C = 1, 10 and 100 all tie at 0.999, so it picked C = 1. On a hand-made example
(not a test item), C = 1 gave a plain pothole complaint only 0.35 top probability. The gate
thresholds that probability at 0.50, so C = 1 would send almost everything to review.

Before running anything on the test set, I switched the criterion to mean 5-fold CV
log-loss on the training set. Log-loss is a proper scoring rule and judges the
probabilities the gate uses. It picks C = 100, the largest value in the pre-set grid.
Template data is close to separable, so CV log-loss keeps improving as C grows. I did not
extend the grid. The test set played no part in this choice.

## D10. What happens when the gate and duplicate detection disagree

* Gate fails → SENT_TO_REVIEW. Any duplicate candidate is shown to the officer as a pending
  decision, never merged automatically.
* Gate passes, similarity ≥ 0.45 → MERGED into the open ticket. Its report count goes up,
  and severity is re-assessed with that count, so R32 fires at 3 reports. The parent
  ticket's priority becomes the more urgent of its own and the new result.
* Gate passes, 0.30 ≤ similarity < 0.45 → SENT_TO_REVIEW with "possible duplicate, officer
  decides".
* Gate passes, similarity < 0.30 → AUTO_ROUTED.

Reason: the gate stays authoritative. An uncertain department never causes an automatic
merge, because the block depends on that department.

## D11. A dropdown ward counts as "ward resolved" for the gate

When the text names no place, or names an ambiguous one, and the citizen picked a ward
office in the dropdown, that ward is used (method "hint") and the gate treats the ward as
known. The citizen stated it explicitly, which a guess would not be. The trace marks it.
The offline evaluation never uses hints.

## D12. Results files contain no timestamps

`results/eval.json` is byte-for-byte reproducible (`python eval/evaluate.py --check`).

# Found but not changed

These are defects in frozen data or logic. Fixing any of them would change the frozen
numbers, so they are left for the team to decide on in a deliberate re-freeze.

| # | Where | Reproducing input | What happens | Effect on numbers |
|---|---|---|---|---|
| F1 | `data/gazetteer.json`: alias `banner` for Baner | `Paud road वर banner आणि flex लावून signal झाकला गेलाय` (T127) | The English word "banner" matches Baner (W01) as well as Paud Road (W08), so the place is ruled ambiguous and the ticket goes to review. | Removing the alias would resolve T127 (ward correct 135→136/137) and could change the gate figures. |
| F2 | Fuzzy fallback with no stopword for बाहेर | `सोसायटीच्या gate बाहेर dry waste चे bags पडून आहेत` (T031) | बाहेर ("outside") ≈ बाणेर at ratio 0.80, so the ward is wrongly resolved to W01. | Adding बाहेर to `fuzzy_stopwords` fixes it (correctly unresolved 22→23/23). |
| F3 | Suffix list cannot undo stem changes | `हिंगण्यात ...` (T145) | हिंगणे→हिंगण्यात changes the stem, so there is no exact or fuzzy match. (कोंढव्यात, मुंढव्यात, येरवड्यात do pass fuzzy.) | A stem rule (-े/-ा → -्यात) would change ward numbers. |

## D13. The default ASR model ("small") was not chosen by measurement

The brief asks to time candidate models on this machine and to pick the largest one that
transcribes a 15-second clip in about 20 s. That could not be done in the build sandbox:
the models could not be downloaded (D8), and no speech clip exists. The default `small` is
a placeholder. It is a multilingual model of moderate size, chosen without any timing.
The team should run `python scripts/fetch_models.py --benchmark <15 s Marathi clip>` on
the demo laptop. That writes `results/asr_benchmark.json` with the timings and a
recommendation. Then set `NAGARVANI_ASR_MODEL`.

## D14. ASR guard thresholds are heuristics

These thresholds were set by hand and have not been validated on real audio:
* Length: 1-60 s.
* "Mostly silence": fewer than 10% of 30 ms frames have RMS ≥ 0.01.
* Repetition: a 2-4 word phrase three times in a row, a single word four times in a row,
  or fewer than 30% distinct words in a transcript of 6 or more words.
* Whisper no-speech probability ≥ 0.80.
* "Transcript uncertain" flag: average log-probability < -1.0.

None of them affects the routing gate. They are described as heuristics in the code, the
UI and the README.

## D15. Whisper decoding options

Beam size 5. `condition_on_previous_text=False` to reduce repetition loops. The VAD filter
is off: clips are short and the silence guard runs first, and the VAD would hide the
duration and silence behaviour the guards report on. The language is always forced.
