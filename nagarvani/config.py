"""Paths, frozen thresholds and environment-driven settings.

The thresholds in this file are pre-specified (taken from the project brief, not tuned on
any test data). Changing them changes every reported number; see CLAUDE.md.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"
ARTEFACTS = ROOT / "artefacts"
MODELS = ROOT / "models"            # Whisper weights (git-ignored, fetched by scripts/fetch_models.py)
INSTANCE = ROOT / "instance"        # SQLite database and stored uploads (git-ignored)

TRAIN_CSV = DATA / "train.csv"
TEST_CSV = DATA / "test_handwritten.csv"
PAIRS_CSV = DATA / "test_duplicate_pairs.csv"
EXTERNAL_CSV = DATA / "external" / "midsem_seed_AB.csv"
CLASSIFIER_PATH = ARTEFACTS / "classifier.joblib"

# ---- frozen decision thresholds -------------------------------------------------------
GATE_MIN_CONFIDENCE = 0.50      # auto-route only if top class probability >= this ...
                                # ... and the ward office was resolved
FUZZY_MIN_RATIO = 0.80          # difflib ratio for the fuzzy locality fallback
DUP_MERGE = 0.45                # cosine >= this: merge into the open ticket
DUP_REVIEW = 0.30               # DUP_REVIEW <= cosine < DUP_MERGE: officer decides
DUP_ESCALATE_REPORTS = 3        # R32 in data/severity_rules.json (kept there; mirrored here for docs)
C_GRID = (0.1, 1.0, 10.0, 100.0)   # logistic-regression C candidates, chosen by CV on train only
CV_FOLDS = 5
RANDOM_STATE = 42

# ---- ASR (Phase 2) -----------------------------------------------------------------------
ASR_MODEL = os.environ.get("NAGARVANI_ASR_MODEL", "small")
ASR_DEVICE = os.environ.get("NAGARVANI_ASR_DEVICE", "auto")      # auto | cpu | cuda
ASR_VOCAB_PROMPT = os.environ.get("NAGARVANI_ASR_PROMPT", "0") == "1"
ASR_MIN_SECONDS = 1.0
ASR_MAX_SECONDS = 60.0
ASR_UNCERTAIN_LOGPROB = -1.0    # heuristic: below this average log-prob the ticket is flagged


def asr_model_dir(name: str | None = None) -> Path:
    return MODELS / f"faster-whisper-{name or ASR_MODEL}"
