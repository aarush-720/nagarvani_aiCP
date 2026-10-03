"""Rebuild the classifier artefact deterministically:  python -m nagarvani.train

Fits the original proposed model (classifier.char_word_lr, C=10) on corpus/train_template.tsv
and writes results/model.pkl, the file the original pipeline and nagarvani.triage load.
experiments/run_eval.py writes the same model to the same path.
"""
import pickle

from . import config, data
from .classifier import char_word_lr
from .console import safe_console


def fit():
    train = data.load_train()
    return char_word_lr().fit([r["text"] for r in train], [r["dept"] for r in train])


def main():
    safe_console()
    m = fit()
    config.RESULTS.mkdir(exist_ok=True)
    with open(config.MODEL_PATH, "wb") as f:
        pickle.dump(m, f)
    print(f"saved {config.MODEL_PATH}")


if __name__ == "__main__":
    main()
