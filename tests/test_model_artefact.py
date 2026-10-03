"""A classifier rebuilt with `python -m nagarvani.train` predicts exactly like the saved
results/model.pkl and like the prototype's shipped model."""
import pickle

import numpy as np
import pytest

from nagarvani import config, data, train


@pytest.fixture(scope="module")
def X():
    return [r["text"] for r in data.load_test()]


@pytest.fixture(scope="module")
def rebuilt():
    return train.fit()


@pytest.mark.parametrize("path", [config.MODEL_PATH, config.RESULTS / "model_shipped.pkl"], ids=["saved", "shipped"])
def test_rebuilt_matches(rebuilt, X, path):
    with open(path, "rb") as f:
        saved = pickle.load(f)
    assert list(saved.predict(X)) == list(rebuilt.predict(X))
    np.testing.assert_allclose(saved.predict_proba(X), rebuilt.predict_proba(X), rtol=0, atol=1e-9)
