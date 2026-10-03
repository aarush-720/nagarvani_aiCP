"""Generate data/train.csv from data/templates.json and data/gazetteer.json.

Deterministic: the same template file and seed always give the same CSV, byte for byte.
Run:  python scripts/generate_train.py          (writes data/train.csv)
      python scripts/generate_train.py --check  (regenerates in memory and compares)
"""
import csv
import io
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nagarvani import config, data  # noqa: E402
from nagarvani.console import safe_console  # noqa: E402

LATIN = re.compile(r"[A-Za-z]")


def _alias_pools():
    dev, lat = [], []
    for loc in data.gazetteer()["localities"]:
        for a in loc["aliases"]:
            (lat if LATIN.search(a) else dev).append((a, loc["id"], loc["ward"]))
    return dev, lat


def _allocate(total, parts):
    base = [total // parts] * parts
    for i in range(total - sum(base)):
        base[i] += 1
    return base


def generate():
    t = data.read_json(config.DATA / "templates.json")
    rng = random.Random(t["seed"])
    depts = data.dept_codes()
    dev, lat = _alias_pools()
    rows, seen = [], set()
    for lang, total in t["language_totals"].items():
        for dept, n in zip(depts, _allocate(total, len(depts))):
            issues = t["issues"][dept][lang]
            made, attempts = 0, 0
            while made < n:
                attempts += 1
                if attempts > 10000:
                    raise RuntimeError(f"cannot make {n} unique rows for {dept}/{lang}")
                frame = rng.choice(t["frames"][lang])
                issue, band = rng.choice(issues)
                tail = rng.choice(t["tails"][lang])
                if "{loc}" in frame and rng.random() < t["no_location_share"]:
                    frame = "{issue}" if "{tail}" not in frame else "{issue}, {tail}"
                if "{loc}" in frame:
                    pool = lat if lang == "rom" or (lang == "mix" and rng.random() < 0.7) else dev
                    alias, loc_id, ward = rng.choice(pool)
                    if lang == "rom" and rng.random() < 0.5:
                        alias = alias.title()
                else:
                    alias, loc_id, ward = "", "", ""
                text = frame.format(loc=alias, issue=issue, tail=tail)
                if text in seen:
                    continue
                seen.add(text)
                rows.append({"text": text, "language": lang, "department": dept,
                             "severity": band, "locality": loc_id, "ward": ward})
                made += 1
    rng.shuffle(rows)
    return rows


def to_csv(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["text", "language", "department", "severity", "locality", "ward"],
                       lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def main():
    safe_console()
    content = to_csv(generate())
    if "--check" in sys.argv:
        same = config.TRAIN_CSV.read_text(encoding="utf-8") == content
        print("train.csv matches the generator" if same else "train.csv DIFFERS from the generator")
        sys.exit(0 if same else 1)
    config.TRAIN_CSV.write_text(content, encoding="utf-8", newline="")
    print(f"wrote {config.TRAIN_CSV} ({content.count(chr(10)) - 1} rows)")


if __name__ == "__main__":
    main()
