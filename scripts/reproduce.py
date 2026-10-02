"""Reproduce every reported number with one command:  python scripts/reproduce.py

1. verify the frozen data checksums
2. check that data/train.csv is exactly what the template generator produces
3. rebuild the classifier and check it predicts exactly like the saved artefact
4. re-run the evaluation and check results/eval.json is reproduced byte for byte
5. run the real-audio ASR evaluation (only if data/audio has clips and the model is present)
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
STEPS = [
    ("frozen data checksums", [PY, "scripts/checksums.py", "--verify"]),
    ("train.csv regenerates from templates", [PY, "scripts/generate_train.py", "--check"]),
    ("rebuilt classifier == saved artefact", [PY, "-m", "pytest", "-q", "tests/test_model_artefact.py"]),
    ("evaluation reproduces results/eval.json", [PY, "eval/evaluate.py", "--check"]),
    ("real-audio ASR evaluation", [PY, "eval/asr_eval.py"]),
]


def main():
    failed = []
    for name, cmd in STEPS:
        print(f"\n=== {name} ===", flush=True)
        r = subprocess.run(cmd, cwd=ROOT)
        if r.returncode != 0:
            failed.append(name)
    print("\n" + ("ALL STEPS PASSED" if not failed else "FAILED: " + "; ".join(failed)))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
