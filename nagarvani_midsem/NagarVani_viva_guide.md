# NagarVani — Midsem Demo & Viva Guide

Everything here matches **`NagarVani_final.ipynb`**. Every number and demo result below was produced by running that notebook (all cells except Whisper, which needs Colab's GPU). Don't use `nagarvani_mvp.ipynb` or the old MVP guide.

---

## Tonight, in order

- [ ] Put every team member's name in the notebook's first cell.
- [ ] Colab → upload `NagarVani_final.ipynb` → `Runtime → Change runtime type → T4 GPU` → `Run all` (about 5 minutes).
- [ ] Scroll to **Step 7b** and confirm it ends with `ALL CHECKS PASSED` (31 checks).
- [ ] Open the `gradio.live` link. Type the five demo sentences below and check the results match.
- [ ] Record the same sentences as voice. **If most voice clips go to human review,** see "The one knob" below.
- [ ] Screen-record one full demo run (your backup if Colab or Wi-Fi fails).
- [ ] Check the ward-office names in the notebook against the PMC website (2 minutes).
- [ ] Say the 60-second pitch out loud three times.
- [ ] Sleep.

---

## The 60-second pitch

"PMC's complaint system has a large backlog, and many complaints sit before anyone even assigns a department. NagarVani is a triage layer in front of it. A citizen speaks a complaint in Marathi. Whisper, a pretrained speech model, turns it into text. A classifier predicts the department, using small chunks of characters because Marathi words change their endings, plus civic keywords. If it isn't confident enough, it doesn't guess: the complaint goes to a human. Separately, safety rules make anything dangerous, like an open manhole or a live wire, top priority regardless of the model. The result is a ticket in the ward's queue."

---

## Demo script (about 3 minutes)

Pick a ward each time. Point at the ticket table after each submission.

| # | Input | Verified result | What to say |
|---|---|---|---|
| 1 | `कोथरूड मध्ये रस्त्यावर मोठा खड्डा आहे गाड्यांना त्रास होतोय` | Routed · Roads · P3 | "A clear case routes automatically." |
| 2 | `गटार तुंबलंय पाणी रस्त्यावर वाहतंय दुर्गंधी` | Routed · Drainage · P2 | "Different department, correct priority." |
| 3 | `मॅनहोल उघडे आहे, रात्री कोणी पडू शकते` | Routed · Drainage · **P1** (rule: open manhole) | "Safety rules override the model." |
| 4 | `इथे खूप त्रास आहे, कोणीतरी बघा` | **Human review** (confidence 0.17) | "Too vague, so it defers instead of guessing." |
| 5 | `मॅनहोल उघडा आहे रस्त्यावर कोणी पडणार` | **Human review, but P1** | "Unsure of the department, still marked urgent, so it goes to the top of the review queue." |

**Optional romanised example** (not in the training data): `nalala don divsapasun pani aala nahi` → Routed · Water Supply · P2.
Don't use `nalala paani yet nahi`: it's almost identical to a training sentence.

**Voice versions:** the transcript will differ from what you type, so results may differ. That's fine, and it's real.

---

## Numbers card (memorise the bold ones)

All preliminary, on AI-drafted, human-checked seed data.

**Data:** 460 complaints. Set A = 200 (8 departments × 25). Set B = 260 (8 departments + *Other*, with severity labels). Drafted separately, in different styles.

**Honest held-out accuracy** (train on one set, test on the other):

| Model | A→B macro-F1 | B→A macro-F1 |
|---|---|---|
| TF-IDF char n-grams + LogReg | **0.75** | 0.67 |
| Hybrid (+ lexicon from Set A) | **0.72** | 0.90 (optimistic: lexicon came from A) |

**By script (A→B, hybrid):** Devanagari **0.89**, code-mixed 0.73, romanised **0.49**.

**Cross-validation on both sets combined (optimistic):** keyword rules 0.60, TF-IDF 0.74, hybrid 0.82 macro-F1.

**Abstention:** τ = **0.79**, chosen from data as the lowest review rate with at most 5% misrouting. At τ = 0.79: 46% sent to review, 4.8% misrouted. On held-out data: 48% review, **9.8% misrouted**, because probabilities aren't calibrated yet.

**Severity (Set B labels):** P1 recall **23 of 25** (optimistic: rules were revised after reading Set B), 5 false P1 out of 235, exact band match 0.54.

**Self-checks:** **31 of 31 pass** on every run (demo sentences, must-be-P1, must-not-be-P1, junk input).

**The honest one-liner:** "About 0.72 to 0.75 macro-F1 on independently written text. Strong on Devanagari, weak on romanised. The pipeline works end to end, and real accuracy will be measured on our held-out corpus."

---

## What each step does (one line each)

1. **Config and data.** Both seed sets, 9 classes, 15 ward offices.
2. **Normalisation.** Unicode NFC (identical-looking Marathi text can be stored as different byte sequences), strip invisible characters, lowercase Latin letters.
3. **Classifier.** Chop text into 2–5-character pieces and weight them with TF-IDF; logistic regression learns which pieces point to which department. The hybrid adds 8 keyword-count features.
3b. **Held-out check.** Train on one set, test on the other. This is the honest number.
4. **Threshold.** Try every τ from 0 to 0.99, and pick the lowest review rate with at most 5% misrouting.
5. **Severity.** Life-safety rules force P1. Otherwise a department default, raised one level by urgency words (school, hospital, danger). SLA hours are **our proposed values**, not official PMC figures.
6. **Whisper large-v3.** Zero-shot, `language="mr"`. Confidence = average word probability. Below 0.45, the complaint goes to review. Guards: silence is discarded (Whisper can invent text on silence), English-only or looping output gets low confidence, and any ASR error asks the citizen to re-record or type instead of crashing.
7. **Triage.** Chains the steps. Review is triggered by low speech confidence, low classifier confidence, top two departments too close, a prediction of *Other*, or no usable words. Times are Pune time (IST); P1 tickets sort to the top even when they're in review.
7b. **Self-checks.** 31 cases run automatically: demo sentences, life-safety sentences that must be P1, ordinary complaints that must not be, and junk input that must not crash.
8. **Gradio app.** Record/type, pick a ward, get a ticket; the queue is sorted by priority. The same complaint from the same ward within 2 minutes is recognised as a resubmission, not a new ticket. Any unexpected error shows a polite message instead of crashing the page.

---

## Likely questions

**"Your data is synthetic."**
"Yes, and we say so upfront. Both seed sets are AI-drafted and human-checked. To get an honest number, we trained on one set and tested on the other: about 0.72 to 0.75 macro-F1. Building a real corpus with real recordings is our next step."

**"Why is the cross-validation score higher than the held-out one?"**
"The keyword lexicon was written from Set A, which is inside the cross-validation data. On unseen text the lexicon doesn't help yet; plain TF-IDF does slightly better. That's a finding, and it's why learned models on real data come next."

**"Why not MahaBERT or MuRIL?"**
"They have over a hundred million parameters, and 460 synthetic rows would give an unreliable result. We'll fine-tune and compare them against this baseline on the real corpus."

**"Why not just use ChatGPT?"**
"Cost and data residency matter for a municipal system, we need calibrated confidence to decide when to defer, and the course is about building and evaluating models."

**"How did you pick the threshold?"**
"From data. We swept τ from 0 to 0.99 and took the lowest review rate with at most 5% misrouting. It's cautious: about half go to review. That's the honest cost of a small dataset."

**"How do you know it works?"**
"Step 7b runs 31 checks every time the notebook runs: the demo sentences, life-safety sentences that must be P1, ordinary ones that must not be, and junk input like empty text or emoji that must go to a human without crashing. All pass. One deliberate behaviour: 'the manhole cover has been fixed, thanks' is still flagged P1, because for safety we prefer a false alarm to a missed danger."

**"Why rules for severity?"**
"Where safety is at stake we want decisions that are predictable and auditable. A rule can be checked line by line; a probability can fail silently."

**"How does it handle romanised Marathi?"**
"Poorly so far: 0.49 on unseen romanised text. Character n-grams partly cover it. Transliteration to Devanagari is planned for M3." (Example: `zaad padla aahe rastyavar` is correctly marked P1 by the safety rules, but the classifier's department guess is wrong, so it goes to review.)

**"Did you use AI to build this?"**
"Yes, to help write code and draft seed sentences, which we checked. The design comes from our PBL documents, and we can explain any part." Then explain whichever cell he points at.

**If you don't know an answer:** "I'm not certain. My understanding is X, and I'll confirm it." Never bluff.

---

## Built vs planned (PBL-3 module IDs)

| Module | Status |
|---|---|
| M1 Ingestion (voice/text + ward) | **Built** (Gradio) |
| M2 ASR | **Built** (Whisper large-v3, zero-shot) |
| M3 Normalisation | **Partial** (Unicode only; transliteration planned) |
| M4a Department classifier | **Built** (TF-IDF + lexicon hybrid, with held-out check) |
| M4b Location | Ward dropdown only; landmark extraction planned |
| M5 Severity | **Built** (rules + department defaults) |
| M6 Duplicate detection | Planned |
| M7 Routing and abstention | **Built** (threshold from data) |
| M8 Clarifying question (voice) | Future work |
| M9 Closure verification | Future work |
| M10 PMC CARE integration | Future work (CSV export only for now) |
| M11 Officer dashboard | Planned (ticket table only for now) |
| M12 Learning from corrections | Future work |

**Nothing here is claimed as built unless it's in the notebook.** No source_id group split, no PMCCareSink, no override logging exist yet: they're planned.

---

## "What are you going to add?"

1. **Real data first.** A few hundred real complaints and recordings from at least ten speakers, double-labelled, with a held-out test set.
2. **Better models on that data.** Fine-tune MahaBERT and MuRIL against today's baseline; compare Whisper with AI4Bharat's Marathi speech model; calibrate probabilities.
3. **Missing modules.** Transliteration for romanised text, landmark-based location, duplicate detection, and an officer view with one-click correction.

Give dates you can actually meet. WhatsApp, IVR and PMC CARE integration are future work, not endsem promises.

---

## The one knob

If most **voice** clips go to review tonight, open the Step 4 cell and change `TARGET_MISROUTE = 0.05` to `0.10`, then re-run from Step 4 down. Verified effect: τ drops to 0.56 and review falls to about 23%, but held-out misrouting rises to about 18%. If you change it, say so: "We loosened the threshold to route more; here's the trade-off on the curve."

---

## If things go wrong

| Problem | What to do |
|---|---|
| Colab or Wi-Fi fails | Play the screen recording; keep the notebook outputs open in another tab. |
| Whisper mishears | "That's why speech confidence feeds routing: a bad transcript goes to review." |
| Something misroutes | Show the top-3 guesses: "This is why abstention exists; calibration is next." |
| GPU out of memory | Change `"large-v3"` to `"medium"` in Step 6. |
| Step 7b shows a FAIL | Read the line; it names the sentence and what came out. Don't demo that sentence. |
| Page says "Something went wrong" | Type the complaint instead of recording; the error is printed in the Colab cell output. |
| "You promised WhatsApp, IVR, photo verification…" | "PBL-3 is the full design. For the midsem we built the core slice; here's the module table." |
| Asked to rescope | Agree, and ask which part he wants prioritised. |
