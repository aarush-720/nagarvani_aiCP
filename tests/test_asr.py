"""ASR wrapper tests. No speech audio exists in the repo, so the backend is mocked; guards
are tested with generated silence and tones; real clips run only if data/audio has them."""
from types import SimpleNamespace

import pytest

from nagarvani import asr, config
from tests import audio_fixtures as af


class FakeBackend:
    def __init__(self, text="कोथरूडमध्ये रस्त्यावर मोठा खड्डा आहे", logprob=-0.3, no_speech=0.05):
        self.text, self.logprob, self.no_speech, self.calls = text, logprob, no_speech, []

    def transcribe(self, audio, **kw):
        self.calls.append(kw)
        seg = SimpleNamespace(text=self.text, avg_logprob=self.logprob, no_speech_prob=self.no_speech)
        return iter([seg] if self.text is not None else []), SimpleNamespace(language=kw.get("language"))


@pytest.fixture
def fake():
    b = FakeBackend()
    asr.set_backend(b, "mock")
    yield b
    asr.set_backend(None, None)


@pytest.mark.parametrize("ext", sorted(af.FORMATS))
def test_every_format_decodes_and_transcribes(tmp_path, fake, ext):
    p = af.write(tmp_path / f"clip.{ext}", af.tone(3.0))
    r = asr.transcribe(p, "mr")
    assert r.text.startswith("कोथरूड") and r.language == "mr" and 2.9 < r.duration < 3.2
    assert fake.calls[-1]["language"] == "mr"


def test_language_is_forced(tmp_path, fake):
    asr.transcribe(af.write(tmp_path / "a.wav", af.tone(2)), "hi")
    assert fake.calls[-1]["language"] == "hi"
    with pytest.raises(ValueError):
        asr.transcribe(tmp_path / "a.wav", "en")


def test_vocab_prompt_switch(tmp_path, fake):
    p = af.write(tmp_path / "a.wav", af.tone(2))
    asr.transcribe(p, vocab=False)
    assert fake.calls[-1]["initial_prompt"] is None
    asr.transcribe(p, vocab=True)
    assert "कोथरूड" in fake.calls[-1]["initial_prompt"]


@pytest.mark.parametrize("samples,code", [
    (af.tone(0.5), "too_short"),
    (af.tone(61), "too_long"),
    (af.silence(3), "silence"),
])
def test_audio_guards(tmp_path, fake, samples, code):
    p = af.write(tmp_path / "g.wav", samples)
    with pytest.raises(asr.AudioRejected) as e:
        asr.transcribe(p)
    assert e.value.code == code and e.value.message_mr


@pytest.mark.parametrize("text,code", [
    ("", "empty"), ("...", "empty"),
    ("धन्यवाद धन्यवाद धन्यवाद धन्यवाद धन्यवाद", "repetition"),
    ("पाणी नाही पाणी नाही पाणी नाही", "repetition"),
])
def test_transcript_guards(tmp_path, text, code):
    asr.set_backend(FakeBackend(text), "mock")
    try:
        with pytest.raises(asr.AudioRejected) as e:
            asr.transcribe(af.write(tmp_path / "t.wav", af.tone(3)))   # a tone is not silence
        assert e.value.code == code
    finally:
        asr.set_backend(None, None)


def test_no_speech_and_uncertain_flags(tmp_path):
    p = af.write(tmp_path / "t.wav", af.tone(3))
    asr.set_backend(FakeBackend(no_speech=0.95), "mock")
    try:
        with pytest.raises(asr.AudioRejected):
            asr.transcribe(p)
        asr.set_backend(FakeBackend(logprob=-1.4), "mock")
        assert asr.transcribe(p).uncertain is True
        asr.set_backend(FakeBackend(logprob=-0.2), "mock")
        assert asr.transcribe(p).uncertain is False
    finally:
        asr.set_backend(None, None)


def test_undecodable_file(tmp_path, fake):
    p = tmp_path / "bad.ogg"
    p.write_bytes(b"not audio at all")
    with pytest.raises(asr.AudioRejected) as e:
        asr.transcribe(p)
    assert e.value.code == "undecodable"


def test_missing_model_is_reported(monkeypatch, tmp_path):
    asr.set_backend(None, None)
    monkeypatch.setattr(config, "MODELS", tmp_path)
    with pytest.raises(asr.AsrUnavailable):
        asr.load_backend("small")


AUDIO = config.DATA / "audio"
CLIPS = [p for p in AUDIO.glob("*") if p.suffix.lower() in {".wav", ".mp3", ".m4a", ".ogg", ".webm", ".mp4"}]


@pytest.mark.skipif(not CLIPS, reason="no real clips in data/audio (the team supplies them)")
@pytest.mark.skipif(not asr.model_available(), reason="Whisper model not fetched")
@pytest.mark.parametrize("clip", CLIPS, ids=lambda p: p.name)
def test_real_clip_end_to_end(clip):
    from nagarvani.pipeline import triage
    asr.set_backend(None, None)
    try:
        r = asr.transcribe(clip, "mr")
    except asr.AudioRejected as e:
        pytest.skip(f"clip rejected by a guard: {e.code}")
    assert r.text and r.seconds >= 0
    assert triage(r.text).department
