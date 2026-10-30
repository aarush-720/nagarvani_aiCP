"""RESULTS.md is generated from the result files and is up to date."""
from scripts import write_results_md as w
from tests.conftest import ROOT


def test_results_md_is_current(tmp_path, monkeypatch):
    monkeypatch.setattr(w, "OUT", tmp_path / "RESULTS.md")
    w.main()
    assert (tmp_path / "RESULTS.md").read_text(encoding="utf-8") == (ROOT / "RESULTS.md").read_text(encoding="utf-8")
