"""Reproduce every reported number with one command:  python scripts/reproduce.py

1. frozen data, original logic and shipped outputs match data/FROZEN.sha256, and the training
   corpus regenerates byte for byte from corpus/generate_train.py
2. a rebuilt classifier predicts exactly like results/model.pkl and the shipped model
3. the wrapper triage() decides exactly like the original Triage on all 160 test complaints
4. experiments/run_eval.py reproduces every reported number, and its full results.json equals
   the committed and the shipped results (tests/test_frozen_metrics.py)
5. the real-audio ASR evaluation (only if data/audio has clips and the Whisper model is present)
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
STEPS = [
    ("frozen files and training-corpus generator", [PY, "-m", "pytest", "-q", "tests/test_data_frozen.py"]),
    ("rebuilt classifier == saved artefact", [PY, "-m", "pytest", "-q", "tests/test_model_artefact.py"]),
    ("wrapper == original pipeline on the test set", [PY, "-m", "pytest", "-q", "tests/test_triage_equivalence.py"]),
    ("evaluation reproduces the reported numbers", [PY, "-m", "pytest", "-q", "tests/test_frozen_metrics.py"]),
    ("real-audio ASR evaluation", [PY, "eval/asr_eval.py"]),
]


def main():
    failed = []
    for name, cmd in STEPS:
        print(f"\n=== {name} ===", flush=True)
        if subprocess.run(cmd, cwd=ROOT).returncode != 0:
            failed.append(name)
    print("\n" + ("ALL STEPS PASSED" if not failed else "FAILED: " + "; ".join(failed)))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
