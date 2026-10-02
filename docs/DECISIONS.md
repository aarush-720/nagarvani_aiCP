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
