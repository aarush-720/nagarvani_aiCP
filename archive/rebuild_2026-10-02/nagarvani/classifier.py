"""Department classifier: TF-IDF (char_wb 2-5 grams + word 1-2 grams) -> class-balanced
logistic regression. C is chosen by stratified 5-fold CV on the training set only.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache

import joblib
import numpy as np
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.pipeline import FeatureUnion, Pipeline

from . import config, data
from .normalise import normalise

WORD_TOKENS = r"[0-9a-zऀ-ॿ]+"   # \w alone splits Devanagari words at vowel signs


def build(C: float, char_only: bool = False) -> Pipeline:
    char = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True)
    if char_only:
        features = char
    else:
        word = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True,
                               token_pattern=WORD_TOKENS)
        features = FeatureUnion([("char", char), ("word", word)])
    clf = LogisticRegression(C=C, class_weight="balanced", max_iter=5000, random_state=config.RANDOM_STATE)
    return Pipeline([("features", features), ("clf", clf)])


def training_xy():
    rows = data.load_train()
    return [normalise(r["text"]) for r in rows], [r["department"] for r in rows]


def select_c(X, y, char_only=False):
    """Choose C by mean 5-fold CV log-loss on the training set (lower is better).

    Log-loss rather than accuracy because the gate thresholds the predicted probability,
    and because CV accuracy on template data saturates (several C values tie at 0.999).
    """
    cv = StratifiedKFold(n_splits=config.CV_FOLDS, shuffle=True, random_state=config.RANDOM_STATE)
    scores = {}
    for C in config.C_GRID:
        res = cross_validate(build(C, char_only), X, y, cv=cv, scoring=("accuracy", "neg_log_loss"))
        scores[C] = {"accuracy": float(np.mean(res["test_accuracy"])),
                     "log_loss": float(-np.mean(res["test_neg_log_loss"]))}
    best = min(config.C_GRID, key=lambda c: (round(scores[c]["log_loss"], 6), c))
    return best, scores


def fit(char_only=False):
    X, y = training_xy()
    C, scores = select_c(X, y, char_only)
    model = build(C, char_only).fit(X, y)
    meta = {"C": C, "selection": "min mean 5-fold CV log-loss on train",
            "cv_by_C": {str(k): v for k, v in scores.items()},
            "cv_accuracy": scores[C]["accuracy"], "cv_log_loss": scores[C]["log_loss"],
            "n_train": len(X), "sklearn": sklearn.__version__,
            "train_sha256": hashlib.sha256(config.TRAIN_CSV.read_bytes()).hexdigest(),
            "char_only": char_only}
    return model, meta


def save(model, meta, path=config.CLASSIFIER_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "meta": meta}, path)
    path.with_suffix(".json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


@lru_cache(maxsize=1)
def load(path=config.CLASSIFIER_PATH):
    obj = joblib.load(path)
    return obj["model"], obj["meta"]


@dataclass
class Prediction:
    top3: list          # [(dept, prob), ...] most probable first
    confidence: float   # probability of the top department


def predict(text: str, model=None) -> Prediction:
    model = model or load()[0]
    proba = model.predict_proba([normalise(text)])[0]
    order = np.argsort(-proba, kind="stable")
    top = [(str(model.classes_[i]), float(proba[i])) for i in order[:3]]
    return Prediction(top, top[0][1])
