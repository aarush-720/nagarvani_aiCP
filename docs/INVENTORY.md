# Inventory

## History of this repository

| When | What was found |
|---|---|
| Start of build (2026-10-02) | Remote and local repo empty; no commits. |
| After GitHub access fixed | `main` held one upload: `nagarvani_midsem/` (Colab notebook, viva guide, 460-row seed CSV, two figures). |
| Clarified by the developer | That midsem notebook **is** the team's final prototype. The build restarts from scratch. |

## What the midsem prototype contained (now in `archive/midsem/`)

| File | Content |
|---|---|
| `NagarVani_final.ipynb` | 22 cells. Gradio UI, openai-whisper `large-v3` on a Colab GPU, TF-IDF char 2-5 + civic-lexicon features + logistic regression (C=10), 12 life-safety rules + department default bands, abstention threshold chosen from out-of-fold CV, in-memory ticket list. No Flask, no SQLite, no location resolution, no duplicate detection. |
| `nagarvani_seed_dataset_AB.csv` | 460 complaints: Set A 200 (8 departments x 25), Set B 260 (8 departments + `other`, with P1-P4 severity labels). AI-drafted, human-checked by the team. |
| `NagarVani_viva_guide.md` | Midsem demo script and numbers card. |
| `confusion_matrix.png`, `tau_curve.png` | Midsem figures. |

## Where the brief's section 2 differs from what existed

Every item in section 2 of the build brief was absent: there was no 10-department taxonomy,
no 2,000-row template training set, no 160-row hand-written test set, no gazetteer, no
19-rule expert system, no duplicate detector, no gate on ward resolution and no Flask app.
The midsem notebook used 8 departments + `other`, 460 seed rows and a different model.

**None of the numbers in the brief's section 2 table can be reproduced from anything that
existed.** No code or data in the repository produced them. This build produces its own
numbers (see `results/` and `docs/HANDOVER.md`); they are not expected to match.

## What was reused from the midsem prototype

* The 15 ward-office names (spellings as in the notebook; still to be verified against PMC).
* The proposed SLA hours: P1 24 h, P2 72 h, P3 168 h, P4 360 h.
* The idea of life-safety rules with exclusion words (e.g. झाडला "swept" must not trigger the tree rule).
* The 460-row seed CSV, copied unchanged to `data/external/midsem_seed_AB.csv` and used only as an
  **external evaluation set** (never for training or rule writing).

## Entry points of the rebuilt system

See `README.md` (layout and commands), `docs/HANDOVER.md` (status) and `docs/PROGRESS.md`.
