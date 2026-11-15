# Report and paper edit checklist (v2.0, Phase 6c)

One list of every edit needed in the submitted documents, grouped by document. The full old and new
text for each item is in `docs/REPORT_CHANGES.md` (section named in brackets). Every number comes
from `RESULTS.md`, which `python scripts/write_results_md.py` writes from the result files.

Checked on 15 Nov 2026: `python -m pytest -q` (343 passed, 4 skipped: real-audio tests, no clips) and
`python scripts/reproduce.py` (all steps passed; `RESULTS.md` matches `results/results.json`).

## By hand, before anything else

- [ ] PBL-4 title page: replace the placeholder names, PRNs and emails.
- [ ] PBL-5 paper author block: same.
- [ ] Ask the IPR cell whether the public GitHub repo (public since early October) already counts as
      disclosure for the provisional patent (PBL-6, O4) before submitting the paper.

## PBL-4 project report

- [ ] §5.4 Ward resolution: the बाहेर → बाणेर false resolution is v1.0 only; v2.0 has none (24/24). [Phase 2]
- [ ] Table 5.4: 10% CER ward (exact + fuzzy) 92.6% → 92.9%; 20% CER ward 78.5% → 78.7%; 20% CER severity 61.1% → 61.0%. [Phase 2]
- [ ] Fig. 5.6: replace with the regenerated `results/figures/fig_asr_noise.png`. [Phase 2]
- [ ] New subsection "Defects found and fixed in v2.0" (F1–F6) after §5.8; renumber if needed. [Phase 2]
- [ ] §5.9 Threats to validity, author overlap: mention the held-out test_v2, **only once it has been run**. [Phase 2]
- [ ] Table 5.5, objective 3: "No false resolution on clean text since v2.0." [Phase 2]
- [ ] Ch. 4 gate condition: add "AND a problem is stated". [Phase 2]
- [ ] Table 3.1, M9 Closure verification: "Partial: citizen confirmation …". [Phase 3]
- [ ] Ch. 4, new section "Closure verification" + screenshot of `/status/<id>`. [Phase 3]
- [ ] Optional: per-ward table in Ch. 5 from `RESULTS.md`. [Phase 3]
- [ ] §6.2 Limitations: photo not verified automatically. [Phase 3]
- [ ] §6.3 Future scope, closure bullet: remaining M9 conditions only. [Phase 3]
- [ ] Table 3.1, ward dashboard module: "Implemented …". [Phase 4]
- [ ] Ch. 4, new section "Ward dashboard" + screenshot of `/dashboard` after `reset_demo`. Do not quote the seeded counts as results. [Phase 4]
- [ ] §6.3 Future scope, pilot bullet: the dashboard reports the override rate a pilot would measure. [Phase 4]
- [ ] Demo / screenshot appendix, if it lists example complaints: add the three new ones. [Phase 6b]

## PBL-5 IEEE paper

- [ ] Results, wards: the false resolution was v1.0 only. [Phase 2]
- [ ] Fig. 3: regenerated `fig_asr_noise.png`. [Phase 2]
- [ ] Limitations: one sentence on F1–F6, both versions tagged. [Phase 2]
- [ ] System description: one sentence on citizen-confirmed closure. [Phase 3]
- [ ] Optional: one sentence on the ward dashboard. [Phase 4]

## PBL-6 course outcomes

- [ ] §4.2 (O2) description: "…per-ward CSV export, citizen-confirmed closure with a status history, and a ward dashboard." [Phases 3–4]
- [ ] Optional, Table 2.1 CO5: "the closure rule never closes without confirmation". [Phase 3]
- [ ] Code size (count of non-blank lines in tracked `.py` files, excluding `archive/` and `docs/`, at tag v2.0):
      **4,865 lines in 58 files; 3,645 without tests (38 files), 1,220 in tests (20 files).**

## Still open (not code: needs the team)

- [ ] **test_v2** (held-out set): the writers' files are not in `corpus/` yet. When they are, run
      `python experiments/run_eval.py --test v2` then `python scripts/write_results_md.py`, and
      only then fill in the §5.9 sentence above. Report the number as it comes out.
- [ ] **Real speech (Phase 1)**: no recordings in `data/audio/` yet, and no Whisper model on the
      build machine. Follow `docs/RECORDING_GUIDE.md`, then `python eval/asr_eval.py`. Until then
      the report's statement that voice input was not evaluated stays true.
- [ ] **Windows check (Phase 6a)**: follow the README on a Windows laptop and note every failure.
- [ ] Phase 5 (MahaBERT/MuRIL baseline) is optional; drop it if there is no time.
