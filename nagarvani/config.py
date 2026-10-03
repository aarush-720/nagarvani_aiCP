"""Paths and settings for the wrapper layer (web app, ASR, evaluation).

The decision thresholds themselves live in the original, frozen prototype code and are used
from there unchanged:
    gate tau = 0.50                 nagarvani/pipeline.py   Triage(tau=0.50)
    fuzzy ratio = 0.80              nagarvani/location.py   WardResolver(fuzzy_threshold=0.80)
    duplicate merge / review        nagarvani/dedup.py      DuplicateDetector(theta_high=0.45, theta_low=0.30)
    classifier C = 10               nagarvani/classifier.py char_word_lr(C=10.0)
The constants below mirror them for display only; tests/test_units.py checks they agree.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus"
DATA = ROOT / "data"
RESULTS = ROOT / "results"
MODELS = ROOT / "models"            # Whisper weights (git-ignored, fetched by scripts/fetch_models.py)
INSTANCE = ROOT / "instance"        # SQLite database and stored uploads (git-ignored)

TRAIN_TSV = CORPUS / "train_template.tsv"
TEST_TSV = CORPUS / "test_handwritten.tsv"
PAIRS_TSV = CORPUS / "dup_pairs.tsv"
GAZETTEER = DATA / "gazetteer.json"
MODEL_PATH = RESULTS / "model.pkl"          # the path the original pipeline.py loads from
RESULTS_JSON = RESULTS / "results.json"     # written by experiments/run_eval.py

# Mirrors of the frozen thresholds (display only).
GATE_MIN_CONFIDENCE = 0.50
FUZZY_MIN_RATIO = 0.80
DUP_MERGE = 0.45
DUP_REVIEW = 0.30
CLASSIFIER_C = 10.0

# PYTHONHASHSEED under which experiments/run_eval.py reproduces the shipped results exactly.
# Only one value depends on it (simulated-noise ward accuracy at 20% CER); see docs/DECISIONS.md F4.
EVAL_HASH_SEED = "3"

# ---- ASR ---------------------------------------------------------------------------------
ASR_MODEL = os.environ.get("NAGARVANI_ASR_MODEL", "small")
ASR_DEVICE = os.environ.get("NAGARVANI_ASR_DEVICE", "auto")      # auto | cpu | cuda
ASR_VOCAB_PROMPT = os.environ.get("NAGARVANI_ASR_PROMPT", "0") == "1"
ASR_MIN_SECONDS = 1.0
ASR_MAX_SECONDS = 60.0
ASR_UNCERTAIN_LOGPROB = -1.0    # heuristic: below this average log-prob the ticket is flagged


def asr_model_dir(name: str | None = None) -> Path:
    return MODELS / f"faster-whisper-{name or ASR_MODEL}"
