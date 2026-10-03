"""Wipe the demo database and seed 25 tickets for a realistic officer queue.

    python scripts/reset_demo.py            # asks for confirmation
    python scripts/reset_demo.py --yes

Seed complaints are drawn from the training corpus (corpus/train_template.tsv), never from the
test set, and run through the real pipeline with back-dated timestamps (spread over the
last 10 days), so some are genuinely overdue. Seeds avoid the (ward, department) blocks
used by docs/DEMO_SCRIPT.md, so they cannot interfere with the live duplicate demo.
"""
import random
import shutil
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nagarvani import config, data, service  # noqa: E402
from nagarvani.console import safe_console  # noqa: E402
from nagarvani.examples import EXAMPLES  # noqa: E402
from nagarvani.triage import triage  # noqa: E402
from nagarvani.tickets import Store, iso, utcnow  # noqa: E402

N_SEED = 21          # with a known place
N_NO_PLACE = 4       # no place named: these land in the review queue
SEED = 11


def demo_blocks():
    blocks = set()
    for e in EXAMPLES:
        r = triage(e["text"])
        if r.ward.ward:
            blocks.add((r.ward.ward, r.department))
    return blocks


def seed(store):
    avoid = demo_blocks()
    rng = random.Random(SEED)
    loc2ward = {k: v["ward"] for k, v in data.gazetteer()["localities"].items()}
    train = data.load_train()
    rows = [dict(r, ward=loc2ward[r["loc"]]) for r in train
            if r["loc"] != "NONE" and (loc2ward[r["loc"]], r["dept"]) not in avoid]
    rng.shuffle(rows)
    chosen, used_blocks, used_wards = [], set(), {}
    for r in rows:                       # spread over wards and departments, one per block
        if (r["ward"], r["dept"]) in used_blocks or used_wards.get(r["ward"], 0) >= 2:
            continue
        chosen.append(r)
        used_blocks.add((r["ward"], r["dept"]))
        used_wards[r["ward"]] = used_wards.get(r["ward"], 0) + 1
        if len(chosen) == N_SEED:
            break
    chosen += rng.sample([r for r in train if r["loc"] == "NONE"], N_NO_PLACE)
    rng.shuffle(chosen)
    now = utcnow()
    for i, r in enumerate(chosen):
        when = now - timedelta(hours=rng.uniform(1, 240))
        tid, _ = service.submit(store, text=r["text"], channel="seed", now=when)
        if i % 9 == 8:
            store.update(tid, status="resolved", resolved_utc=iso(when + timedelta(hours=12)))   # not an officer correction
    return chosen


def main():
    safe_console()
    db = config.INSTANCE / "nagarvani.sqlite3"
    if "--yes" not in sys.argv:
        if input(f"This deletes {db} and all uploaded audio. Type yes to continue: ").strip().lower() != "yes":
            print("cancelled")
            return
    if db.exists():
        db.unlink()
    shutil.rmtree(config.INSTANCE / "uploads", ignore_errors=True)
    store = Store(db)
    chosen = seed(store)
    counts = {}
    for t in store.tickets():
        counts[t["status"]] = counts.get(t["status"], 0) + 1
    overdue = sum(r["overdue"] for r in service.queue(store))
    print(f"seeded {len(chosen)} tickets into {db}: {counts}; {overdue} open tickets overdue")


if __name__ == "__main__":
    main()
