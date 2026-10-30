# NagarVani v2.0 — final version plan (30 Oct → demo 2 Nov 2026)

Aarush drives Claude Code. Teammates do the human-only work (writing complaints, recording audio,
Colab, Windows check) in parallel. Each phase = one Claude Code session, started in plan mode.

> **Errata (checked against the repo in Phase 0, 30 Oct).** The phase prompts below are kept as written. Read them with these corrections:
> * Recordings go in `data/audio/` with `data/audio/manifest.csv`, not `eval/audio/`. Noisy versus quiet is the manifest's `condition` column.
> * `test_v1` is `corpus/test_handwritten.tsv` (tab-separated: `id, lang, dept, loc, sev, text`). The `test_v2` template is therefore `corpus/test_v2_TEMPLATE.tsv`, not `.csv`.
> * Templates and static files are under `nagarvani/`. The app starts with `python run.py`.
> * Training data is `corpus/train_template.tsv` (Phase 5), not `corpus/train.csv`.
> * Whisper cannot be downloaded in a Claude Code cloud session (Hugging Face is blocked there). Run `scripts/fetch_models.py` and the benchmark on a team laptop.
> * Claude Code pushes to its own session branch; Aarush merges it into `final`.

## Schedule

| When | Aarush + Claude Code | Teammates (parallel) |
|---|---|---|
| **Fri 30 Oct, evening** | Phase 0: tag, branch, verify CLAUDE.md, generate templates for teammates, download Whisper | Read templates; start writing `test_v2` complaints |
| **Sat 31 Oct, morning** | Phase 1: speech eval (as soon as clips arrive) | Record audio clips (by 11:00); finish `test_v2` (by 13:00) |
| **Sat 31 Oct, afternoon** | Phase 2: fix F1–F6, then evaluate on test_v1 + test_v2 | Viraj: start Phase 5 in Colab |
| **Sat 31 Oct, evening** | Phase 3: closure verification | — |
| **Sun 1 Nov, morning** | Phase 4: ward dashboard | Adithya: Windows setup check (Phase 6a) |
| **Sun 1 Nov, afternoon** | Phase 6b: demo script, README, RESULTS.md | Viraj: hand over Phase 5 numbers by 17:00 or drop |
| **Sun 1 Nov, evening** | Phase 6c: report/paper change list; merge; tag v2.0 at 22:00 | Full team dry run of demo |
| **Mon 2 Nov** | No code changes. Demo from tag v2.0. | — |

**If behind, cut in this order:** Phase 5 → Phase 4 → Phase 3. Never cut Phases 1, 2 or 6.

## Who does what
- **Aarush** — Claude Code sessions, commits, merges.
- **Abhinandan** — writes ~30 `test_v2` complaints; records ~12 clips.
- **Viraj** — writes ~30 `test_v2` complaints; records ~12 clips; Phase 5 (Colab).
- **Adithya** — writes ~30 `test_v2` complaints; records ~12 clips; Phase 6a (Windows check).
- Aarush also records ~12 clips (but does NOT write `test_v2` — he wrote the rules).

---

## Phase 0 — Setup (Fri evening, ~1.5 h)

Manual steps first:
```
git checkout main && git pull
git tag v1.0 && git push origin v1.0
git checkout -b final
# copy CLAUDE.md to repo root and docs/FINAL_PLAN.md into docs/
git add CLAUDE.md docs/FINAL_PLAN.md && git commit -m "P0: add project rules and final plan"
```

Prompt for Claude Code:
> Read CLAUDE.md and docs/FINAL_PLAN.md. Then:
> 1. Check the Layout and Commands sections of CLAUDE.md against the actual repo and fix anything wrong.
> 2. Run `pytest -q` and `python experiments/run_eval.py`, and confirm the headline numbers match RESULTS.md / the report (dept acc 86.9%, macro-F1 0.870, 70% auto-routed, 97.3% correct). Report any mismatch.
> 3. Read `corpus/` and create `corpus/test_v2_TEMPLATE.csv` with the exact same columns as the v1 test set, plus 3 example rows and a `docs/TEST_V2_GUIDE.md` explaining each column, the severity guideline (PBL-4 §3.3.4), the allowed department codes and locality keys, and the rule that each writer covers all 10 departments and mixes Marathi/Hindi/romanised/code-mixed.
> 4. Read `eval/asr_eval.py` and create `docs/RECORDING_GUIDE.md`: the exact file naming, format, and manifest CSV it expects. Pick 48 complaints from test_v1 (balanced across departments and languages, Marathi and Hindi only) and assign 12 to each team member in `eval/recording_assignments.csv`.
> 5. Run `scripts/fetch_models.py` to download Whisper and benchmark model sizes on this laptop. Tell me which size it recommends and the per-clip latency.
> Plan first; wait for my approval before editing.

Send TEST_V2_GUIDE.md and RECORDING_GUIDE.md to the team tonight.

**Recording tips for the team:** phone voice recorder is fine; speak naturally, not reading-voice; record about a third of the clips with real background noise (traffic, fan, TV); keep each clip 5–30 s.

---

## Phase 1 — Real speech evaluation (Sat morning, ~2.5 h)

> Phase 1. Read CLAUDE.md. The recordings are in `eval/audio/` with the manifest. Plan:
> 1. Validate every clip against the guards in `nagarvani/speech.py`; list any rejected and why.
> 2. Run `eval/asr_eval.py` with the recommended Whisper size (and one size smaller if time allows). Report WER and CER overall and split by language, speaker, and noisy vs quiet.
> 3. Report end-to-end results on the transcripts: department accuracy, ward resolution, severity band, auto-route rate, and correct-when-routed — side by side with the same 48 complaints as typed text.
> 4. Show me the 10 worst transcripts next to the reference text and classify the error types (vowel signs, word boundaries, English words, place names).
> 5. Compare real CER with the simulated-noise results in the report (§5.7) and say whether the simulator was optimistic or pessimistic.
> Write results to RESULTS.md (new section "Real speech") and docs/REPORT_CHANGES.md (report §4.4, §4.9, §5.7, §5.10, §6.2; paper limitations). Do not change any core code in this phase.

Expect high WER for zero-shot Marathi. That is fine: the citizen confirms the transcript before submitting, and that is the point to make in the viva.

---

## Phase 2 — Fix known defects F1–F6 (Sat afternoon, ~3.5 h)

> Phase 2. Read CLAUDE.md and PBL-4 §5.9 defects (summarised below). Do NOT open corpus/test_v2*. Plan fixes for:
> - F1: fuzzy ward fallback matches बाहेर → बाणेर. Add a stop-word list (common Marathi/Hindi words) excluded from fuzzy matching.
> - F2: गायब ("missing") is not in the OPEN cue group, so R02 does not fire. Add it plus other spelling variants of missing/open/broken.
> - F3: negation — "झाकण नवीन बसवले, आता काही समस्या नाही" still fires R02. Make the cue extraction negation-aware within a small window, without breaking cases like "झाकण नाही" (no cover = hazard). Write tests for both directions.
> - F4: equal-length aliases ordered by string hashing. Make ordering deterministic (length desc, then alphabetical).
> - F5: OUTAGE cue lacks the standard spelling आलेले नाही. Add standard and colloquial variants.
> - F6: content-free complaints (e.g. "कोथरूडमध्ये खूप त्रास होतोय, कोणीतरी लक्ष द्या") get auto-routed. Add a "no problem cue" check in the gate: if no severity cue and no department keyword fires, defer with reason NO_ISSUE_STATED.
> For each defect: a failing test first, then the fix, then the passing test. One commit per defect.
> Then: retrain if needed, regenerate FROZEN.sha256, run run_eval.py on test_v1, and only then run it on test_v2 for the first time. Put v1.0 vs v2.0 on test_v1, and v2.0 on test_v2, into RESULTS.md. Update the frozen-metrics test. Log report changes (§5.9 becomes "Defects found and fixed in v2.0"; Tables in Ch. 5).

The `test_v2` numbers will probably be lower than `test_v1`. Report them anyway — that is the honest held-out result and it answers the "author overlap" objection.

---

## Phase 3 — Closure verification, M9 light (Sat evening, ~2.5 h)

> Phase 3. Read CLAUDE.md. Implement evidence-bound closure in the web-app layer only (no core changes), answering the PMC Standing Committee directive that no complaint be closed without complainant feedback:
> - New ticket states: OPEN → RESOLVED_PENDING_CONFIRMATION → CLOSED, or → REOPENED.
> - Officer "Mark resolved" requires a resolution note and optionally a photo (stored locally under `data/uploads/`, size/type checked). It does NOT close the ticket.
> - A citizen page by ticket ID (no login, single-machine demo) asks in Marathi + English: "Was this fixed?" Yes → CLOSED; No → REOPENED, SLA clock restarted, priority kept.
> - If no citizen response within a configurable window, the ticket shows "Awaiting confirmation" — never auto-closed.
> - The decision trace records every state change with timestamp and actor.
> - Tests for every transition, including that CLOSED is unreachable without citizen confirmation.
> Plan first. Log report changes (Table 3.1 M9 status; new §4.x; future scope).

---

## Phase 4 — Ward dashboard, M11 (Sun morning, ~2.5 h)

> Phase 4. Read CLAUDE.md. Add `/dashboard` to the Flask app, fully offline (no CDN; plain CSS bars or vendored JS in static/):
> - Per ward office: open tickets, P1 open, SLA breached, awaiting confirmation, deferred-to-nodal.
> - Top duplicate clusters (size ≥ 3) with department and ward.
> - Department × ward heat table of open tickets.
> - Officer override rate (corrections ÷ auto-routed) — the metric proposed for a pilot.
> - Filters by ward and department; works on the demo data from `scripts/reset_demo`.
> Extend reset_demo so the dashboard looks realistic (a few breaches, one cluster of 4, some reopened tickets).
> Tests for the aggregation queries. Plan first.

---

## Phase 5 — Transformer baseline, optional (Viraj, Colab, Sat afternoon → Sun 17:00)

Not integrated into the app (keeps it CPU-only and offline). Report as an extra row in the classifier comparison table.

- Fine-tune `l3cube-pune/marathi-bert-v2` (MahaBERT) and/or `google/muril-base-cased` on the 2,000 training complaints, 10 departments, 3–4 epochs.
- Evaluate on test_v1 and test_v2: accuracy, macro-F1, top-3, split by language variety.
- Ask Claude Code (or Claude chat) to write the Colab notebook: "Write a Colab notebook that fine-tunes MahaBERT on corpus/train.csv for 10-class department classification and evaluates on test_v1 and test_v2 with the same metrics as experiments/run_eval.py."
- Hand over a CSV of metrics by 17:00 Sunday. If not done, drop it — the report already argues TF-IDF is the deliberate lighter choice.

---

## Phase 6 — Packaging, demo, documents (Sun, ~5 h total)

**6a — Windows check (Adithya, Sun morning):** clone the `final` branch on a Windows laptop, follow the README exactly, and write down every step that failed. Aarush feeds the list to Claude Code:
> Phase 6a. Here are the setup failures on Windows: [paste]. Fix the README and setup scripts. Do not change triage behaviour.

**6b — Demo script and README:**
> Phase 6b. Read CLAUDE.md. Write `docs/DEMO_SCRIPT.md` for a 10-minute demo that shows, in order:
> (1) typed Marathi pothole complaint → auto-routed with trace; (2) spoken Hindi complaint → transcript confirmation → routed;
> (3) open-manhole complaint → P1 with fired rules (the F2 fix); (4) third duplicate report → R32 escalation;
> (5) vague complaint → deferred NO_ISSUE_STATED (the F6 fix); (6) officer resolves → citizen says No → reopened;
> (7) dashboard. Make `scripts/reset_demo` load exactly the state the script needs.
> Also give a fallback for every step if the microphone or Whisper fails on the day. Update README for v2.0.

**6c — Documents and freeze (Sun evening):**
> Phase 6c. Read docs/REPORT_CHANGES.md and RESULTS.md. Produce one consolidated list of every edit needed in the PBL-4 report and PBL-5 paper (section, old text/value, new text/value), plus the updated code-size figure for PBL-6 (count lines of Python with and without tests). Run the full test suite and run_eval.py one last time and confirm RESULTS.md matches. Then merge `final` into `main` and tag `v2.0`.

Also fix by hand: the placeholder names and PRNs on the PBL-4 title page and the paper's author block.

---

## Viva points this release adds
- Voice-first claim now rests on real recordings with measured WER/CER, not simulated noise.
- A held-out test set written by non-rule-authors answers the author-overlap threat.
- Every known defect is fixed, with a test that reproduces it.
- Closure requires citizen confirmation — directly answers the Standing Committee directive.
- v1.0 and v2.0 are both tagged, so every number in both versions of the report is reproducible.

## Open risk (not code)
The GitHub repo has been public since early October. PBL-6 says the provisional patent (O4) must be filed before public disclosure. Ask the IPR cell whether the public repo already counts as disclosure before submitting the paper.
