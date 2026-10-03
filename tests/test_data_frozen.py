"""Guard: frozen data, original logic and shipped outputs are byte-identical to the recorded
checksums, and the training corpus regenerates exactly from its generator."""
import subprocess
import sys

from scripts import checksums
from tests.conftest import ROOT


def test_checksums_unchanged():
    assert checksums.recorded() == checksums.current()


def test_train_corpus_regenerates(tmp_path):
    out = tmp_path / "train.tsv"
    code = ("import runpy, sys; sys.argv=['generate_train.py']; "
            "m = runpy.run_path(r'%s', run_name='nagarvani_gen'); m['main'](200, out=r'%s')"
            % (ROOT / "corpus" / "generate_train.py", out))
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    assert out.read_bytes() == (ROOT / "corpus" / "train_template.tsv").read_bytes()
