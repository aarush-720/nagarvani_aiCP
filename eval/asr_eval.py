"""Real-audio evaluation of ASR and of the pipeline end to end.

    python eval/asr_eval.py [--model NAME]

Reads data/audio/manifest.csv (file, reference_text, department, locality, speaker_id,
condition, device). Writes results/asr_eval.json and results/asr_eval.md. With no clips it
prints a message and writes nothing.

Text normalisation before WER/CER: nagarvani.normalise.normalise (Unicode NFC, zero-width
characters removed, Devanagari digits to ASCII, punctuation and danda to spaces, Latin
lower-cased, whitespace collapsed).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nagarvani import asr, config, data  # noqa: E402
from nagarvani.console import safe_console  # noqa: E402
from nagarvani.normalise import normalise  # noqa: E402
from nagarvani.pipeline import triage  # noqa: E402

AUDIO_DIR = config.DATA / "audio"
MANIFEST = AUDIO_DIR / "manifest.csv"
NORMALISATION = ("nagarvani.normalise.normalise: Unicode NFC, zero-width characters removed, Devanagari digits "
                 "to ASCII, punctuation and danda replaced by spaces, Latin lower-cased, whitespace collapsed")


def edit_distance(a, b):
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def error_counts(ref, hyp):
    r, h = normalise(ref), normalise(hyp)
    return (edit_distance(r.split(), h.split()), len(r.split()),
            edit_distance(r.replace(" ", ""), h.replace(" ", "")), len(r.replace(" ", "")))


def load_manifest():
    if not MANIFEST.exists():
        return []
    rows = data.read_csv(MANIFEST)
    return [r for r in rows if (AUDIO_DIR / r["file"]).exists()]


def _triage_or_none(text):
    try:
        return triage(text) if text else None
    except ValueError:            # no words (e.g. ASR produced nothing usable)
        return None


def pipeline_stats(texts, rows, loc_ward):
    n = len(rows)
    res = [_triage_or_none(t) for t in texts]
    dept = sum(x is not None and x.department == r["department"] for x, r in zip(res, rows))
    resolved = sum(x is not None and x.ward.ward is not None for x in res)
    correct_ward = sum(x is not None and bool(r["locality"]) and x.ward.ward == loc_ward.get(r["locality"])
                       for x, r in zip(res, rows))
    with_loc = sum(bool(r["locality"]) for r in rows)
    auto = sum(x is not None and x.gate.decision == "AUTO_ROUTED" for x in res)

    def rate(k, t):
        return {"count": k, "total": t, "rate": round(k / t, 4) if t else None}
    return {"department_accuracy": rate(dept, n), "ward_resolution_rate": rate(resolved, n),
            "ward_correct": rate(correct_ward, with_loc), "auto_route_rate": rate(auto, n)}


def run_setting(rows, vocab, model):
    out, per = [], []
    for r in rows:
        try:
            a = asr.transcribe(AUDIO_DIR / r["file"], r.get("language") or "mr", vocab=vocab, model=model,
                               run_guards=False)
            out.append(a.text)
            per.append({"file": r["file"], "hypothesis": a.text, "avg_logprob": a.avg_logprob,
                        "seconds": a.seconds, "duration": a.duration})
        except asr.AudioRejected as e:
            out.append("")
            per.append({"file": r["file"], "hypothesis": "", "error": e.message_en})
    return out, per


def summarise(rows, hyps):
    tot = [0, 0, 0, 0]
    by = defaultdict(lambda: [0, 0, 0, 0])
    for r, h in zip(rows, hyps):
        c = error_counts(r["reference_text"], h)
        for i in range(4):
            tot[i] += c[i]
            by[r["condition"]][i] += c[i]
    f = lambda c: {"wer": round(c[0] / c[1], 4) if c[1] else None,  # noqa: E731
                   "cer": round(c[2] / c[3], 4) if c[3] else None, "ref_words": c[1], "ref_chars": c[3]}
    return f(tot), {k: f(v) for k, v in sorted(by.items())}


def main():
    safe_console()
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=config.ASR_MODEL)
    a = ap.parse_args()
    rows = load_manifest()
    if not rows:
        print(f"No audio clips found (expected {MANIFEST} listing files in {AUDIO_DIR}). "
              "Nothing evaluated, nothing written. See data/audio/README.md.")
        return 0
    if not asr.model_available(a.model):
        print(f"Whisper model '{a.model}' is not in models/. Run: python scripts/fetch_models.py --model {a.model}")
        return 1
    loc_ward = {loc["id"]: loc["ward"] for loc in data.gazetteer()["localities"]}
    refs = [r["reference_text"] for r in rows]
    result = {"model": a.model, "n_clips": len(rows), "normalisation": NORMALISATION,
              "speakers": len({r["speaker_id"] for r in rows}),
              "from_reference_text": pipeline_stats(refs, rows, loc_ward), "settings": {}}
    for name, vocab in (("no_vocab_prompt", False), ("vocab_prompt", True)):
        hyps, per = run_setting(rows, vocab, a.model)
        overall, by_cond = summarise(rows, hyps)
        result["settings"][name] = {"overall": overall, "by_condition": by_cond,
                                    "from_audio": pipeline_stats(hyps, rows, loc_ward), "clips": per}
    config.RESULTS.mkdir(exist_ok=True)
    (config.RESULTS / "asr_eval.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                                  encoding="utf-8")
    md = [f"# ASR evaluation ({result['n_clips']} clips, {result['speakers']} speakers, model {a.model})", "",
          f"Normalisation before scoring: {NORMALISATION}.", "",
          "| Setting | WER | CER | Dept acc (audio) | Ward resolved (audio) | Auto-routed (audio) |",
          "|---|---|---|---|---|---|"]
    for name, s in result["settings"].items():
        fa = s["from_audio"]
        md.append(f"| {name} | {s['overall']['wer']} | {s['overall']['cer']} | {fa['department_accuracy']['rate']} | "
                  f"{fa['ward_resolution_rate']['rate']} | {fa['auto_route_rate']['rate']} |")
    fr = result["from_reference_text"]
    md += ["", f"Same items from the reference text: department accuracy {fr['department_accuracy']['rate']}, "
           f"ward resolved {fr['ward_resolution_rate']['rate']}, auto-routed {fr['auto_route_rate']['rate']}.", "",
           "## By condition (no vocabulary prompt)", "", "| Condition | WER | CER |", "|---|---|---|"]
    for c, v in result["settings"]["no_vocab_prompt"]["by_condition"].items():
        md.append(f"| {c} | {v['wer']} | {v['cer']} |")
    (config.RESULTS / "asr_eval.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    sys.exit(main())
