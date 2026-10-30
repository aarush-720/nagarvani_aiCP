"""eval/recordings.py: the committed assignments and the manifest builder."""
from collections import Counter

from eval import recordings
from nagarvani import data


def test_assignments_are_balanced_test_v1_rows():
    rows = data.read_csv(recordings.ASSIGNMENTS)
    test = {r["id"]: r for r in data.load_test()}
    assert len(rows) == 48 and len({r["test_id"] for r in rows}) == 48
    assert all(test[r["test_id"]]["text"] == r["reference_text"] for r in rows)
    assert {r["language"] for r in rows} == {"mr", "hi"}
    assert Counter(r["speaker_id"] for r in rows) == {s: 12 for s in recordings.SPEAKERS}
    assert set(Counter(r["department"] for r in rows).values()) <= {4, 5}


def test_assignments_regenerate_identically(tmp_path, monkeypatch):
    committed = recordings.ASSIGNMENTS.read_bytes()
    monkeypatch.setattr(recordings, "ASSIGNMENTS", tmp_path / "a.csv")
    recordings.assign()
    assert (tmp_path / "a.csv").read_bytes() == committed


def test_manifest_from_clip_names(tmp_path, monkeypatch):
    a = data.read_csv(recordings.ASSIGNMENTS)[0]
    monkeypatch.setattr(recordings, "AUDIO_DIR", tmp_path)
    monkeypatch.setattr(recordings, "MANIFEST", tmp_path / "manifest.csv")
    for name in (f"{a['speaker_id']}_{a['test_id']}_street_iphone.m4a", "S09_T001_quiet.ogg",
                 "recording 12.m4a", "notes.txt"):
        (tmp_path / name).write_bytes(b"")
    assert recordings.manifest() == 1                      # two clips skipped
    rows = data.read_csv(tmp_path / "manifest.csv")
    assert len(rows) == 1
    assert rows[0]["condition"] == "street" and rows[0]["device"] == "iphone"
    assert rows[0]["reference_text"] == a["reference_text"] and rows[0]["language"] == a["language"]
