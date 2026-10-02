"""A classifier rebuilt with `python -m nagarvani.train` predicts exactly like the saved artefact."""
import numpy as np

from nagarvani import classifier, data
from nagarvani.normalise import normalise


def test_rebuilt_model_matches_saved():
    saved, meta = classifier.load()
    rebuilt, meta2 = classifier.fit()
    X = [normalise(r["text"]) for r in data.load_test()]
    assert meta["C"] == meta2["C"]
    assert list(saved.predict(X)) == list(rebuilt.predict(X))
    np.testing.assert_allclose(saved.predict_proba(X), rebuilt.predict_proba(X), rtol=0, atol=1e-9)
