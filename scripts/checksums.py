"""Write or verify SHA-256 checksums of the frozen data files (data/FROZEN.sha256).

    python scripts/checksums.py --verify   # exit 1 if any frozen file changed
    python scripts/checksums.py --write    # only when the team deliberately re-freezes
"""
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nagarvani.console import safe_console  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FROZEN = [
    "data/taxonomy.json",
    "data/gazetteer.json",
    "data/severity_rules.json",
    "data/keywords.json",
    "data/templates.json",
    "data/train.csv",
    "data/test_handwritten.csv",
    "data/test_duplicate_pairs.csv",
    "data/external/midsem_seed_AB.csv",
]
LIST = ROOT / "data" / "FROZEN.sha256"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current():
    return {rel: sha256(ROOT / rel) for rel in FROZEN}


def recorded():
    out = {}
    for line in LIST.read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, rel = line.split(maxsplit=1)
            out[rel] = digest
    return out


def main():
    safe_console()
    if "--write" in sys.argv:
        LIST.write_text("".join(f"{d}  {r}\n" for r, d in current().items()), encoding="utf-8")
        print(f"wrote {LIST}")
        return
    rec, cur = recorded(), current()
    bad = [r for r in FROZEN if rec.get(r) != cur[r]]
    for r in FROZEN:
        print(("CHANGED " if r in bad else "ok      ") + r)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
