"""Guard: frozen data files are byte-identical to the Phase 0 checksums, and train.csv is
exactly what the generator produces from the frozen templates."""
import subprocess
import sys

from scripts import checksums
from tests.conftest import ROOT


def test_checksums_unchanged():
    rec, cur = checksums.recorded(), checksums.current()
    assert rec == cur


def test_train_csv_regenerates():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "generate_train.py"), "--check"],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stdout + r.stderr
