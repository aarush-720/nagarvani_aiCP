# Report and paper changes for v2.0

Every edit needed in the PBL-4 report and the PBL-5 paper, appended phase by phase.
Each entry gives the section or table, the old text or value, and the new one. Every
value is read from a file that a script wrote (`results/*.json`, `RESULTS.md`).

## Phase 0

No report or paper changes. Every headline number reproduced on 30 Oct 2026
(`python -m pytest -q`, `python experiments/run_eval.py`): department accuracy 139/160,
macro-F1 0.870, 112/160 auto-routed, 109/112 correct when routed.

## Phase 2 (defects F1–F6 fixed; v2.0 re-freeze)

Values come from `RESULTS.md` (v1.0 = `results/results_shipped.json`, v2.0 = `results/results.json`).
The report and paper builders (`docs/prototype/docs_build/report.js`, `paper.js`) read
`results.json`, so every templated number updates on rebuild. The prose below is not
templated and has to be edited by hand.

| Where | Old | New |
|---|---|---|
| PBL-4 §5.4 Ward resolution, last sentences of the first paragraph | "With the fuzzy fallback switched on, one of those 24 is falsely resolved: *बाहेर* ("outside") matches the alias *बाणेर* at a ratio of 0.80. On clean text, then, the fallback costs one false resolution in 160." | "In v1.0 the fuzzy fallback falsely resolved one of those 24: *बाहेर* ("outside") matched the alias *बाणेर* at a ratio of 0.80. v2.0 excludes a short list of common words from fuzzy matching (Section 5.9), so all 24 stay unresolved and the fallback costs nothing on clean text." |
| PBL-4 Table 5.4, 10% CER row, "Ward (exact + fuzzy)" | 92.6% | 92.9% |
| PBL-4 Table 5.4, 20% CER row, "Ward (exact + fuzzy)" | 78.5% | 78.7% |
| PBL-4 Table 5.4, 20% CER row, "Severity band acc." | 61.1% | 61.0% |
| PBL-4 §5.7 prose ("93% at 10% and 79% at 20%", "61% at 20%") | — | Unchanged after rounding. |
| PBL-4 Fig. 5.6 | v1.0 figure | Regenerated `results/figures/fig_asr_noise.png` (the two ward points move by 0.3 and 0.15 points). |
| PBL-4 Chapter 5, new subsection after §5.8 (the plan calls it §5.9; the report's §5.9 is "Threats to validity", so either insert "5.9 Defects found and fixed in v2.0" and renumber 5.9→5.10, 5.10→5.11, or add it as §5.8.1) | — | "Six defects found on v1.0 were fixed in v2.0, each with a test that reproduces it: (F1) common words such as *बाहेर* fuzzy-matched a locality; (F2) *गायब* ('missing') did not fire the open-manhole rule; (F3) a *नाही* anywhere in a drainage complaint made the cover 'open'; (F4) equal-length aliases were ordered by string hashing; (F5) the standard spelling *पाणी आलेले नाही* missed the outage rule; (F6) content-free complaints such as *कोथरूडमध्ये खूप त्रास होतोय, कोणीतरी लक्ष द्या* were auto-routed. The gate now defers a complaint that names only a place and general words (NO_ISSUE_STATED). On test_v1 the fixes change one ward count (23/24 → 24/24 correctly unresolved) and three simulated-noise values (Table 5.4); every other number in this chapter is unchanged." |
| PBL-4 §5.9 Threats to validity, "Author overlap" bullet | ends "…the classifier learned only from template text." | Add: "Version 2.0 adds a held-out test set written by team members who did not write the rules (Section 5.x, `RESULTS.md`)." Fill in when test_v2 has run. |
| PBL-4 Table 5.5, objective 3 | "…the fuzzy fallback limits the damage from transcription errors." | Add: "No false resolution on clean text since v2.0." |
| PBL-4 §4.x (algorithm / gate description, wherever the gate condition "confidence ≥ τ and ward resolved" is stated) | "confidence ≥ τ AND ward resolved" | "confidence ≥ τ AND ward resolved AND a problem is stated" |
| PBL-5 paper, results paragraph on wards | "The fuzzy fallback adds one false resolution (*बाहेर* ≈ *बाणेर*)." | "In v1.0 the fuzzy fallback added one false resolution (*बाहेर* ≈ *बाणेर*); v2.0 removes it with a short stop-word list." |
| PBL-5 paper, Fig. 3 | v1.0 figure | Regenerated `fig_asr_noise.png`. |
| PBL-5 paper, limitations | — | Add one sentence: "Six rule and lexicon defects found on the test set were fixed in v2.0 (F1–F6); both versions are tagged." |

## Phase 3 (closure verification, M9 light; per-ward audit)

| Where | Old | New |
|---|---|---|
| PBL-4 Table 3.1, row "M9 Closure verification", prototype status | "Not implemented" | "Partial: citizen confirmation required before closure; a 'not fixed' answer reopens the ticket one priority band higher with a new deadline; officer's photo stored, not analysed (no geotag or visual check)" |
| PBL-4 Chapter 4, new section after the officer console (§4.x "Closure verification") | — | "The PMC Standing Committee directed that no complaint be closed without the complainant's feedback. In NagarVani an officer's 'Mark resolved' requires a note, accepts an optional photo, and moves the ticket to *awaiting citizen confirmation*; it does not close it. The citizen sees the note and photo on the ticket's status page and answers *हे काम झाले का? / Was this fixed?* Yes closes the ticket; No reopens it, raises its priority by one band and restarts its deadline. A ticket left without an answer for 72 hours is flagged in the officer queue but never closed automatically. Every status change is recorded with its time and actor (system, officer or citizen), and tests check that no path other than the citizen's Yes reaches *closed*. The photo is not yet checked for location, time or content." Add a screenshot of the citizen page (`/status/<id>`). |
| PBL-4 §5.10 Table 5.5 or Chapter 5 (optional) | — | Per-ward table from `RESULTS.md` ("Per ward office, v2.0 on test_v1"), with the note that each ward has 5–15 complaints. On test_v1, department accuracy ranges from 60% (BIB, 3/5) to 100% (AUB, WKN, DSN, KYW). |
| PBL-4 §6.2 Limitations | "PMC CARE was not integrated with, by design." | Add: "Closure is confirmed by the citizen but the resolution photo is not verified automatically." |
| PBL-4 §6.3 Future scope, "Clarification and closure" bullet | "…and the evidence-bound closure predicate (M9) that responds to the Standing Committee's directive [18]." | "…and the remaining conditions of the closure predicate (M9): geotag and timestamp checks and visual comparison of before and after photographs. Citizen confirmation is implemented in v2.0." |
| PBL-5 paper, system description (after the routing gate) | — | One sentence: "A resolved ticket closes only when the complainant confirms the fix; a rejection reopens it at a higher priority." |
| PBL-6 Table 2.1, CO5 row | — | Optionally add: "the closure rule never closes without confirmation; silence is not consent". |
| PBL-6 §4.2 (O2), "Description" | "…Includes an officer console (Flask) and per-ward CSV export." | "…Includes an officer console (Flask), per-ward CSV export, and citizen-confirmed closure with a status history." |
