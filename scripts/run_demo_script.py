"""Run every demo input through the real pipeline (via the same service code as the web app,
on a fresh in-memory database) and write docs/DEMO_SCRIPT.md with the actual outputs.

    python scripts/run_demo_script.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nagarvani import config, data, service  # noqa: E402
from nagarvani.console import safe_console  # noqa: E402
from nagarvani.examples import EXAMPLES  # noqa: E402
from nagarvani.tickets import Store  # noqa: E402

SAY = {
    "clean_marathi": "A clear complaint, a known place, high confidence: it goes straight to the department. R12 (water outage of two days or more) raises it to P2.",
    "romanised": "Romanised Marathi works because the classifier uses character n-grams and the gazetteer has Latin aliases.",
    "code_mixed": "Marathi and English mixed in one sentence, as people actually speak. Two hazard rules fire (nuisance and blocked drain).",
    "life_safety": "The rule base, not the model, decides life safety. R02 (open manhole) fires on the cue words shown and sets P1; R30 (near a school) fires too, but P1 is already the top band.",
    "fuzzy": "हडप्सर is not a gazetteer alias, but it is within the similarity threshold of हडपसर, so the fuzzy fallback resolves it and the trace shows the score.",
    "unknown_place": "Pimple Saudagar is in Pimpri-Chinchwad, not PMC, and is not in the gazetteer. The system does not guess a ward, so the gate sends it to a nodal officer. The citizen could also pick a ward in the optional dropdown.",
    "low_confidence": "Debris at the roadside could be Roads or Solid Waste. The top probability is under 0.50, so it defers instead of guessing, with the top three departments filled in for the officer.",
    "failure": "An honest failure, from the model's real errors on the test set: a drain that smells and breeds mosquitoes is read as Solid Waste. Its confidence is above 0.50 and the place is known, so the gate does NOT catch it. The officer corrects it, and the correction is logged.",
}



REJECTED_LOW_CONFIDENCE = ["कोथरूडमध्ये खूप त्रास होतोय, कोणीतरी लक्ष द्या", "कर्वेनगरमध्ये बांधकामाचे साहित्य रस्त्यावर ठेवले आहे"]
REJECTED_UNKNOWN_PLACE = ["उंड्री येथे रस्त्यावर मोठे खड्डे पडले आहेत", "लोहगाव मध्ये कचरा उचलला जात नाही"]
REJECTED_LIFE_SAFETY = ["धनकवडीत मॅनहोलचे झाकण गायब आहे, शाळकरी मुले रोज इथून जातात"]


def row(store, tid):
    t = store.get(tid)
    tr = json.loads(t["trace_json"])
    rules = ", ".join(f"{f['rule']} ({f['action']})" for f in tr["severity"]["fired"]) or "none (default P3)"
    top3 = ", ".join(f"{d} {p:.2f}" for d, p in tr["top3"])
    w = tr["ward"]
    ward = f"{w['ward']} ({data.ward_names()[w['ward']]['en']}) via {w['method']}" if w["ward"] else f"not resolved ({w['reason']})"
    if w["method"] == "fuzzy":
        ward += f", nearest alias '{w['matched_alias']}', similarity {w['score']}"
    d = tr["duplicate"]
    dup = d["decision"] + (f", score {d['score']:.2f} vs #{d['ticket_id']}" if d["ticket_id"] else f" ({d['reason']})")
    return [f"* Ticket #{tid}: **{tr['gate']['decision']}**, status `{t['status']}`",
            f"* Department top 3: {top3}",
            f"* Ward: {ward}",
            f"* Severity: **{tr['severity']['band']}**; rules fired: {rules}",
            f"* Duplicate check: {dup}",
            f"* Gate reason: {tr['gate']['reason']}"]


def run_sheet(ex):
    """The 10-minute demo in FINAL_PLAN Phase 6b order, run on top of the reset_demo seed so the
    ticket numbers printed here are the ones the presenter will see after `reset_demo --yes`."""
    from nagarvani import closure, dashboard
    from scripts import reset_demo
    s = Store(":memory:")
    reset_demo.seed(s)

    def go(key):
        tid, _ = service.submit(s, text=ex[key]["text"], channel="typed")
        return tid, s.get(tid), json.loads(s.get(tid)["trace_json"])

    def line(t, tr):
        rules = ", ".join(f["rule"] for f in tr["severity"]["fired"]) or "none"
        return (f"**{tr['gate']['decision']}** → {t['department']} ({tr['top3'][0][1]:.2f}), ward {t['ward'] or '—'}, "
                f"{t['priority']}, rules {rules}")

    L = ["## 10-minute run sheet", "",
         "Before the demo: `python scripts/reset_demo.py --yes`, then `python run.py`, and open",
         "http://127.0.0.1:5000 in a browser. Keep `/queue` and `/dashboard` open in other tabs.",
         "Outputs below are real, produced on top of the seed, so the ticket numbers match the live app",
         "if the steps are done in this order and nothing else is submitted first.", ""]
    tid1, t, tr = go("clean_marathi")
    L += ["### Step 1 (1 min): typed Marathi complaint → auto-routed with its trace", "",
          f"Type or click example 1: `{ex['clean_marathi']['text']}`", "",
          f"* Ticket #{tid1}: {line(t, tr)}",
          "* Show on the trace page: top-3 departments with probabilities, ward via exact alias, the fired rule, the gate reason.",
          "* Fallback: none needed (typed).", ""]
    tid, t, tr = go("hindi")
    L += ["### Step 2 (1.5 min): spoken Hindi complaint → check transcript → routed", "",
          f"Switch the language toggle to Hindi, press record and say: `{ex['hindi']['text']}`", "",
          f"* The transcript appears in the text box. Correct it if needed, tick the confirmation box, submit.",
          f"* With this exact text: ticket #{tid}: {line(t, tr)}",
          "* Say: zero-shot Whisper makes mistakes in Marathi and Hindi; that is why the citizen confirms the transcript before anything is filed.",
          "* Fallback (no microphone, or the Whisper model is missing): click example 10 (same text, typed), or upload a pre-recorded",
          "  `.ogg`/`.wav` with the file button. If ASR is unavailable the audio is still saved as a review ticket — show that, it is a designed behaviour.", ""]
    tid, t, tr = go("cover_missing")
    L += ["### Step 3 (1 min): open manhole → P1 by a visible rule (F2 fix)", "",
          f"Click example 11: `{ex['cover_missing']['text']}`", "",
          f"* Ticket #{tid}: {line(t, tr)}",
          "* Say: 'गायब' (missing) was not a cue in v1.0, so R02 did not fire (defect F2). v2.0 adds it, with a test. The rule base, not the model, decides life safety.",
          "* Fallback: example 4 (`उघडे`, open) shows the same rule. Do not submit both: they are different wards, but keep the run predictable.", ""]
    ids = [go(k)[0] for k in ("dup1", "dup2", "dup3")]
    p = s.get(ids[0])
    L += ["### Step 4 (1.5 min): third duplicate report → R32 escalation", "",
          "Click examples 8a, 8b, 8c one after another (three wordings of the same pothole).", "",
          f"* Tickets #{ids[0]}, #{ids[1]}, #{ids[2]}: the second and third are `{s.get(ids[1])['status']}` / `{s.get(ids[2])['status']}` into #{ids[0]}.",
          f"* #{ids[0]} now shows {p['report_count']} reports, priority **{p['priority']}**, escalation: \"{p['escalation']}\".",
          "* Show #" + str(ids[0]) + " in the officer queue: marked '3 reports' and 'escalated'.",
          "* Fallback: none needed (typed).", ""]
    tid, t, tr = go("vague")
    L += ["### Step 5 (1 min): vague complaint → deferred, NO_ISSUE_STATED (F6 fix)", "",
          f"Click example 12: `{ex['vague']['text']}`", "",
          f"* Ticket #{tid}: {line(t, tr)}",
          f"* Gate reason: {tr['gate']['reason']}",
          "* Say: v1.0 auto-routed this to Health at 0.61 confidence although no problem is described (defect F6). v2.0 sends it to the nodal officer instead of guessing.", ""]
    closure.transition(s, tid1, "resolve", note="नळजोडणी दुरुस्त केली / pipeline repaired")
    closure.transition(s, tid1, "report_not_fixed", note="अजूनही पाणी येत नाही / still no water")
    t = s.get(tid1)
    L += ["### Step 6 (2 min): officer resolves → citizen says No → reopened", "",
          f"1. Open ticket #{tid1} (step 1). In 'Mark resolved' write a note, e.g. `नळजोडणी दुरुस्त केली / pipeline repaired`, optionally attach a photo, submit.",
          "   The status becomes *waiting for citizen confirmation*, not closed.",
          f"2. Go to 'My complaint', enter {tid1}. The citizen page asks *हे काम झाले का? / Was this fixed?* Press **No**.",
          f"3. Result: status `{t['status']}`, priority {t['priority']} (one band up), deadline restarted; the history on the ticket page lists every change with time and actor.",
          "* Say: this answers the Standing Committee directive — nothing closes without the complainant. Only the citizen's Yes reaches *closed*; tests check there is no other path.",
          "* Fallback: none needed.", ""]
    d = dashboard.build(s)
    T = d["totals"]
    L += ["### Step 7 (1.5 min): ward dashboard", "",
          "Open `/dashboard`. After steps 1–6 it shows (seed + demo):", "",
          f"* {T['open']} open, {T['p1_open']} P1 open, {T['breached']} past deadline, {T['pending']} waiting for the citizen "
          f"({T['awaiting']} past 72 h), {T['deferred']} deferred to the nodal officer, {T['reopened']} reopened.",
          f"* Duplicate clusters: " + "; ".join(f"#{c['id']} {c['size']} reports, {c['department']} {c['ward']}" for c in d["clusters"]) + ".",
          f"* Officer override rate: {d['override']['overridden']}/{d['override']['auto_routed']} auto-routed tickets corrected.",
          "* Filter by Kothrud-Bavdhan to show the escalated pothole. Say: the override rate is the metric we would measure in a pilot.",
          "* Say clearly: the seed tickets come from the training corpus with made-up times. These counts are a demo state, not results.", "",
          "Spare time: the honest failure (example 9) and the About page with the evaluation numbers and limitations.", ""]
    return L


def main():
    safe_console()
    store = Store(":memory:")
    ex = {e["key"]: e for e in EXAMPLES}
    L = ["# Demo script", "",
         "Generated by `python scripts/run_demo_script.py`. Each input below was run through the real",
         "pipeline (the same `service.submit` → `triage()` code the web app uses), and",
         "the output shown is what it produced. Run `python scripts/reset_demo.py` before the demo: the",
         "seeded tickets do not touch these inputs' duplicate blocks, but re-check item 8 after any seed change.",
         "Every input is also a one-click example on the intake page (the fallback if the microphone fails).", "",
         f"Classifier: the original char + word TF-IDF logistic regression (C = 10), loaded from results/model.pkl.", ""]
    L += run_sheet(ex)
    L += ["## Behaviour catalogue", "",
          "Each behaviour on its own, on a fresh empty database (so ticket numbers start at 1).", ""]
    n = 0
    for key in ["clean_marathi", "romanised", "code_mixed", "life_safety", "fuzzy", "unknown_place", "low_confidence"]:
        n += 1
        e = ex[key]
        tid, _ = service.submit(store, text=e["text"], channel="typed")
        L += [f"## {n}. {e['behaviour']}", "", f"Input: `{e['text']}`", ""] + row(store, tid) + ["", f"Say: {SAY[key]}", ""]
    n += 1
    L += [f"## {n}. Triple duplicate with escalation", "",
          "Submit the three reports one after another (three different wordings of the same pothole).", ""]
    ids = []
    for key in ["dup1", "dup2", "dup3"]:
        e = ex[key]
        tid, _ = service.submit(store, text=e["text"], channel="typed")
        ids.append(tid)
        L += [f"### {e['behaviour']}", "", f"Input: `{e['text']}`", ""] + row(store, tid) + [""]
    p = store.get(ids[0])
    L += [f"Result on the first ticket #{ids[0]}: {p['report_count']} reports, priority **{p['priority']}**, "
          f"escalation note: \"{p['escalation']}\".", "",
          "Say: the reports are merged, not duplicated in the queue. At the third report R32 fires and the open ticket "
          "moves up one band. Show the first report's ticket in the officer queue: it is marked '3 reports' and 'escalated'.", ""]
    n += 1
    e = ex["failure"]
    tid, _ = service.submit(store, text=e["text"], channel="typed")
    test = {r["id"]: r for r in data.load_test()}["T054"]
    L += [f"## {n}. {e['behaviour']}", "", f"Input: `{e['text']}` (test item T054; gold label {test['dept']})", ""]
    L += row(store, tid) + ["", f"Say: {SAY['failure']}", ""]
    L += ["## Spoken versions", "",
          "Read any of the inputs aloud with the Marathi toggle on. The transcript appears for checking before submission.",
          "Whisper's transcript will differ from the typed text, so the outcome may differ. That is real, and it is",
          "why the citizen checks the transcript. If the microphone fails, use the example buttons.",
          "A WhatsApp voice note (.ogg) can be uploaded with the file button.", ""]
    from nagarvani.triage import triage
    def tried(texts):
        out = []
        for t in texts:
            r = triage(t)
            out.append(f"  * `{t}` → {r.department} {r.confidence:.2f}, ward {r.ward.ward or 'none'}, "
                       f"{r.severity['band']}, {r.gate.decision}")
        return out
    L += ["## Inputs that were tried and rejected (re-run just now)", "",
          "* For item 7 (low confidence → review):", *tried(REJECTED_LOW_CONFIDENCE),
          "  The first is a vague complaint. v1.0 sent it to Health with confidence 0.61 and auto-routed it;",
          "  since v2.0 (F6) the gate defers it with NO_ISSUE_STATED (it is still not a low-confidence case).",
          "* For item 6 (unknown locality): these places turned out to be in the gazetteer:", *tried(REJECTED_UNKNOWN_PLACE),
          "* For item 4 (life safety): 'झाकण गायब' (cover missing). v1.0 missed it because 'गायब' was not in",
          "  the OPEN cue list; since v2.0 (F2) R02 fires:", *tried(REJECTED_LIFE_SAFETY),
          "* Exact-text repeats were not used for item 8: paraphrases show that matching is not literal."]
    out = config.ROOT / "docs" / "DEMO_SCRIPT.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
