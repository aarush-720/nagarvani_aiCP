"""Recording assignments and the audio manifest for the real-speech evaluation.

    python eval/recordings.py assign      # (re)write eval/recording_assignments.csv
    python eval/recordings.py manifest    # build data/audio/manifest.csv from the clips present

`assign` picks 48 Marathi and Hindi complaints from test_v1, balanced across departments
(seed 2026), and gives 12 to each of four speakers, a quarter of them Hindi and a third noisy.
`manifest` reads clip names of the form <speaker>_<test id>_<condition>[_<device>].<ext>
(e.g. S02_T034_street.m4a), checks each against the assignments, and writes the manifest
that eval/asr_eval.py reads. See docs/RECORDING_GUIDE.md.
"""
from __future__ import annotations

import argparse
import csv
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nagarvani import config, data  # noqa: E402
from nagarvani.console import safe_console  # noqa: E402

ASSIGNMENTS = Path(__file__).resolve().parent / "recording_assignments.csv"
AUDIO_DIR = config.DATA / "audio"
MANIFEST = AUDIO_DIR / "manifest.csv"
SEED = 2026
SPEAKERS = ["S01", "S02", "S03", "S04"]
PER_SPEAKER = 12
HINDI_PER_SPEAKER = 3
NOISY_PER_SPEAKER = 4
AUDIO_EXT = {".wav", ".mp3", ".m4a", ".ogg", ".opus", ".webm", ".mp4", ".aac"}
CLIP_NAME = re.compile(r"^(S\d\d)_(T\d{3})_([a-z]+)(?:_([a-z0-9]+))?$")
ASSIGN_COLS = ["speaker_id", "test_id", "language", "department", "locality", "planned_condition",
               "reference_text"]
MANIFEST_COLS = ["file", "reference_text", "department", "locality", "speaker_id", "condition", "device",
                 "language", "test_id"]


def _shown(path):
    return path.relative_to(config.ROOT) if path.is_relative_to(config.ROOT) else path


def pick(rows):
    """48 rows: per department one Hindi and three Marathi, plus 2 Hindi and 6 Marathi extras
    on distinct departments. Returns {lang: [rows]} ordered by department."""
    rng = random.Random(SEED)
    pools = defaultdict(list)
    for r in rows:
        if r["lang"] in ("mr", "hi"):
            pools[r["dept"], r["lang"]].append(r)
    depts = sorted({r["dept"] for r in rows})
    for p in pools.values():
        rng.shuffle(p)
    extra = rng.sample(depts, 8)
    take = {("hi", d): 1 + (d in extra[:2]) for d in depts} | {("mr", d): 3 + (d in extra[2:]) for d in depts}
    return {lang: [r for d in depts for r in pools[d, lang][:take[lang, d]]] for lang in ("hi", "mr")}


def assign():
    chosen = pick(data.load_test())
    rng = random.Random(SEED + 1)
    out = []
    for lang, n in (("hi", HINDI_PER_SPEAKER), ("mr", PER_SPEAKER - HINDI_PER_SPEAKER)):
        rows = chosen[lang]
        assert len(rows) == n * len(SPEAKERS), (lang, len(rows))
        for i, r in enumerate(rows):         # round-robin over department order spreads departments
            out.append({"speaker_id": SPEAKERS[i % len(SPEAKERS)], "test_id": r["id"], "language": lang,
                        "department": r["dept"], "locality": "" if r["loc"] == "NONE" else r["loc"],
                        "reference_text": r["text"]})
    for s in SPEAKERS:
        mine = [a for a in out if a["speaker_id"] == s]
        noisy = {id(a) for a in rng.sample(mine, NOISY_PER_SPEAKER)}
        for a in mine:
            a["planned_condition"] = "noisy" if id(a) in noisy else "quiet"
    out.sort(key=lambda a: (a["speaker_id"], a["test_id"]))
    with open(ASSIGNMENTS, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ASSIGN_COLS)
        w.writeheader()
        w.writerows(out)
    print(f"Wrote {_shown(ASSIGNMENTS)}: {len(out)} clips, {PER_SPEAKER} per speaker.")


def manifest():
    assigned = {(a["speaker_id"], a["test_id"]): a for a in data.read_csv(ASSIGNMENTS)}
    rows, problems, seen = [], [], set()
    for p in sorted(AUDIO_DIR.iterdir()):
        if p.suffix.lower() not in AUDIO_EXT:
            continue
        m = CLIP_NAME.match(p.stem)
        if not m:
            problems.append(f"{p.name}: name is not <speaker>_<test id>_<condition>[_<device>]")
            continue
        speaker, tid, condition, device = m.groups()
        a = assigned.get((speaker, tid))
        if a is None:
            problems.append(f"{p.name}: {tid} is not assigned to {speaker}")
            continue
        if (speaker, tid) in seen:
            problems.append(f"{p.name}: second clip for {speaker} {tid}")
            continue
        seen.add((speaker, tid))
        rows.append({"file": p.name, "reference_text": a["reference_text"], "department": a["department"],
                     "locality": a["locality"], "speaker_id": speaker, "condition": condition,
                     "device": device or "phone", "language": a["language"], "test_id": tid})
    missing = sorted(set(assigned) - seen)
    with open(MANIFEST, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_COLS)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {_shown(MANIFEST)}: {len(rows)} clips.")
    for s in SPEAKERS:
        todo = [t for sp, t in missing if sp == s]
        if todo:
            print(f"  {s} still to record ({len(todo)}): {', '.join(todo)}")
    for msg in problems:
        print(f"  SKIPPED {msg}")
    return 1 if problems else 0


def main():
    safe_console()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=["assign", "manifest"])
    a = ap.parse_args()
    return assign() if a.command == "assign" else manifest()


if __name__ == "__main__":
    sys.exit(main())
