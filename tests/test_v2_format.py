"""Format checks for the test_v2 template and the writers' files (corpus/test_v2_<XX>.tsv).

test_v2 is held out, so failures name only the file, row id and column, never the text.
"""
from pathlib import Path

import pytest

from nagarvani import config, data

HEADER = ["id", "lang", "dept", "loc", "sev", "text"]
WRITERS = ("ABH", "VIR", "ADI")


def _rows(path):
    return data.read_csv(path, delimiter="\t")


def _problems(path, prefixes):
    with open(path, encoding="utf-8") as f:
        header = f.readline().rstrip("\r\n").split("\t")
    if header != HEADER:
        return [f"{path.name}: header {header}"]
    locs = set(data.gazetteer()["localities"]) | {"NONE"}
    allowed = {"lang": {"mr", "hi", "mr-rom", "mix"}, "dept": set(data.dept_codes()), "loc": locs,
               "sev": {"P1", "P2", "P3", "P4"}}
    known = {r["text"].strip() for r in data.load_train() + data.load_test()}
    out, ids = [], set()
    for r in _rows(path):
        rid = r.get("id") or "?"
        if not rid.startswith(prefixes) or rid in ids:
            out.append(f"{path.name}:{rid}: bad or repeated id")
        ids.add(rid)
        out += [f"{path.name}:{rid}: {col}" for col, ok in allowed.items() if r.get(col) not in ok]
        if not (r.get("text") or "").strip():
            out.append(f"{path.name}:{rid}: empty text")
        elif r["text"].strip() in known:
            out.append(f"{path.name}:{rid}: text copied from train or test_v1")
    return out


def test_template():
    path = config.CORPUS / "test_v2_TEMPLATE.tsv"
    assert _problems(path, ("EX",)) == []
    assert len(_rows(path)) == 3


@pytest.mark.parametrize("writer", WRITERS)
def test_writer_file(writer):
    path = config.CORPUS / f"test_v2_{writer}.tsv"
    if not path.exists():
        pytest.skip(f"{path.name} not handed in yet")
    assert _problems(path, (writer,)) == []
