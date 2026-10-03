"""M4a - Department classifier + baselines."""
import numpy as np
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.base import BaseEstimator, ClassifierMixin
from .normalise import normalise

DEPARTMENTS = {
    "ROAD": "Road Department",
    "SWM": "Solid Waste Management",
    "WATER": "Water Supply",
    "DRAIN": "Drainage",
    "ELEC": "Electrical (Street Lighting)",
    "HEALTH": "Health (Vector Control & Sanitation)",
    "TREE": "Garden / Tree Authority",
    "ENCROACH": "Anti-Encroachment",
    "BUILD": "Building Permission & Construction",
    "VET": "Veterinary (Stray Animals)",
}


def char_word_lr(C=10.0):
    """Proposed model: char_wb 2-5 + word 1-2 TF-IDF, class-balanced logistic regression."""
    feats = FeatureUnion([
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True,
                                 min_df=2, preprocessor=normalise)),
        ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True,
                                 token_pattern=r"(?u)[^\s,.\-]+", preprocessor=normalise)),
    ])
    return Pipeline([("feats", feats),
                     ("clf", LogisticRegression(C=C, max_iter=4000, class_weight="balanced"))])


def char_lr(C=10.0):
    return Pipeline([("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True,
                                               min_df=2, preprocessor=normalise)),
                     ("clf", LogisticRegression(C=C, max_iter=4000, class_weight="balanced"))])


def word_lr(C=10.0):
    return Pipeline([("tfidf", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True,
                                               token_pattern=r"(?u)[^\s,.\-]+", preprocessor=normalise)),
                     ("clf", LogisticRegression(C=C, max_iter=4000, class_weight="balanced"))])


def word_nb():
    return Pipeline([("tfidf", TfidfVectorizer(analyzer="word", ngram_range=(1, 1),
                                               token_pattern=r"(?u)[^\s,.\-]+", preprocessor=normalise)),
                     ("clf", MultinomialNB(alpha=0.1))])


class KeywordBaseline(BaseEstimator, ClassifierMixin):
    """Hand-built keyword lexicon; the 'no machine learning' reference point."""
    KW = {
        "ROAD": ["खड्ड", "गड्ढ", "khadd", "pothole", "रस्ता", "सड़क", "rasta", "road", "डांबर", "स्पीड ब्रेकर",
                 "फूटपाथ", "footpath", "पेव्हर"],
        "SWM": ["कचर", "कूड़", "kachr", "garbage", "घंटागाडी", "dustbin", "waste", "शौचालय", "toilet", "निर्माल्य"],
        "WATER": ["पाणी", "पानी", "pani", "नळ", "नल", "nal", "पाइपलाइन", "pipeline", "water", "टँकर", "tanker"],
        "DRAIN": ["ड्रेनेज", "drainage", "गटार", "gatar", "चेंबर", "chamber", "manhole", "मॅनहोल", "सांडपाणी",
                  "sandpani", "नाल", "सीवर", "sewage"],
        "ELEC": ["दिवा", "दिवे", "पथदिव", "light", "लाइट", "लाईट", "विज", "बिजली", "खांब", "खंभ", "khamb",
                 "wire", "तार", "करंट", "current", "डीपी"],
        "HEALTH": ["डास", "मच्छर", "das", "mosquito", "फवारणी", "fogging", "फॉगिंग", "डेंग्यू", "डेंगू",
                   "dengue", "मलेरिया", "malaria", "मेलेल", "मरा", "dead", "उंदीर", "चूह"],
        "TREE": ["झाड", "पेड़", "zad", "tree", "फांदी", "डाल", "fandi", "branch", "छाटणी", "वृक्ष"],
        "ENCROACH": ["फेरीवाल", "feriwal", "hawker", "अतिक्रमण", "atikraman", "टपरी", "टपऱ्या", "tapri",
                     "फलक", "बॅनर", "banner", "flex", "ठेले", "होर्डिंग", "hoarding"],
        "BUILD": ["बांधकाम", "bandhkam", "construction", "निर्माण", "मजला", "मंजिल", "majla", "इमारत",
                  "imarat", "building", "भिंत", "दीवार", "स्लॅब"],
        "VET": ["कुत्र", "कुत्त", "kutr", "dog", "जनावर", "मवेशी", "गाय", "गायी", "gai", "cattle", "डुकर",
                "माकड", "पिसाळ"],
    }

    def fit(self, X, y):
        self.classes_ = np.array(sorted(self.KW)); return self

    def predict_proba(self, X):
        out = []
        for x in X:
            t = normalise(x)
            s = np.array([sum(t.count(k.lower()) for k in self.KW[c]) for c in self.classes_], float) + 1e-3
            out.append(s / s.sum())
        return np.array(out)

    def predict(self, X):
        return self.classes_[self.predict_proba(X).argmax(1)]
