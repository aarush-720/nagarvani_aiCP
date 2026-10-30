"""experiments/per_ward.py: the committed per-ward table is current and adds up to results.json."""
import importlib.util
import json

from tests.conftest import ROOT

spec = importlib.util.spec_from_file_location("per_ward", ROOT / "experiments" / "per_ward.py")
pw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pw)


def test_per_ward_is_current_and_adds_up():
    wards = pw.per_ward(pw.test_rows("v1"))
    committed = json.loads((ROOT / "results" / "per_ward.json").read_text(encoding="utf-8"))
    assert committed == {"test_set": "v1", "wards": wards}
    R = json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))
    c8 = R["E8_end_to_end"]["counts"]
    total = lambda k: sum(w[k] for w in wards.values())
    assert total("n") == R["data"]["n_test"]
    assert total("auto") == sum(v for k, v in c8.items() if k.startswith("auto"))
    assert total("auto_correct") == c8["auto_correct"]
    n = R["data"]["n_test"]
    assert total("dept_correct") == round(R["E1_dept"]["Char + word TF-IDF + LogReg (proposed)"]["acc"] * n)
