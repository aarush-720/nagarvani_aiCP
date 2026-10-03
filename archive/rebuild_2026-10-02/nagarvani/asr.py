"""Speech recognition with faster-whisper (zero-shot Whisper; no Marathi fine-tuning).

    transcribe(path, language="mr") -> AsrResult

* The language is forced (Marathi "mr" or Hindi "hi"), never auto-detected.
* The model is loaded only from models/faster-whisper-<name>/ (fetched once by
  scripts/fetch_models.py). The Hugging Face hub is put in offline mode, so this module
  never touches the network.
* Audio is decoded by PyAV (bundled FFmpeg libraries): WebM/Opus, MP4/AAC, M4A, WAV, MP3
  and OGG/Opus all work without a system ffmpeg.
* Guards reject clips that are too short or long, mostly silent, empty transcripts, and
  transcripts that are one phrase repeated. These are HEURISTICS with hand-set thresholds,
  not validated values.
* ASR confidence never enters the routing gate. A low average log-probability only flags
  the ticket as "transcript uncertain" for the officer.
"""
from __future__ import annotations

import os
import re
import time
from dataclasses import asdict, dataclass

import numpy as np

from . import config, data
from .normalise import normalise

os.environ.setdefault("HF_HUB_OFFLINE", "1")
SAMPLE_RATE = 16000
SILENCE_RMS = 0.01           # heuristic: a 30 ms frame below this RMS counts as silent
MIN_VOICED_FRACTION = 0.10   # heuristic: fewer voiced frames than this = "mostly silence"
NO_SPEECH_REJECT = 0.80      # heuristic: Whisper's own no-speech probability (averaged)
PROMPT_MAX_CHARS = 350


class AsrUnavailable(RuntimeError):
    """The Whisper model is not on disk (or faster-whisper cannot load it)."""


class AudioRejected(ValueError):
    def __init__(self, code: str, message_mr: str, message_en: str, result: "AsrResult | None" = None):
        super().__init__(message_en)
        self.code, self.message_mr, self.message_en, self.result = code, message_mr, message_en, result


@dataclass
class AsrResult:
    text: str
    language: str
    avg_logprob: float | None
    no_speech_prob: float | None
    duration: float
    model: str
    seconds: float
    vocab_prompt: bool = False
    uncertain: bool = False

    def to_dict(self):
        return asdict(self)


# ---- audio ------------------------------------------------------------------------------
def decode(path) -> np.ndarray:
    from faster_whisper import decode_audio
    try:
        return decode_audio(str(path), sampling_rate=SAMPLE_RATE)
    except Exception as e:  # PyAV raises several error types for unreadable files
        raise AudioRejected("undecodable", "ही ऑडिओ फाईल वाचता आली नाही.",
                            f"The audio file could not be decoded ({type(e).__name__}).") from e


def voiced_fraction(audio: np.ndarray, frame: int = 480) -> float:
    n = len(audio) // frame
    if n == 0:
        return 0.0
    frames = audio[: n * frame].reshape(n, frame)
    rms = np.sqrt((frames.astype(np.float64) ** 2).mean(axis=1))
    return float((rms >= SILENCE_RMS).mean())


def check_audio(audio: np.ndarray) -> float:
    duration = len(audio) / SAMPLE_RATE
    if duration < config.ASR_MIN_SECONDS:
        raise AudioRejected("too_short", "रेकॉर्डिंग खूप लहान आहे (१ सेकंदापेक्षा कमी).",
                            f"Recording is too short ({duration:.1f} s; minimum {config.ASR_MIN_SECONDS:.0f} s).")
    if duration > config.ASR_MAX_SECONDS:
        raise AudioRejected("too_long", "रेकॉर्डिंग ६० सेकंदांपेक्षा मोठे आहे.",
                            f"Recording is too long ({duration:.0f} s; maximum {config.ASR_MAX_SECONDS:.0f} s).")
    if voiced_fraction(audio) < MIN_VOICED_FRACTION:
        raise AudioRejected("silence", "रेकॉर्डिंगमध्ये आवाज ऐकू आला नाही.",
                            "The recording is mostly silence.")
    return duration


def repeated_phrase(text: str) -> bool:
    """Heuristic for Whisper's loop hallucination: one short phrase repeated."""
    toks = normalise(text).split()
    if len(toks) >= 6 and len(set(toks)) / len(toks) < 0.3:
        return True
    for n in (2, 3, 4):                       # a 2-4 word phrase three times in a row
        for i in range(len(toks) - 3 * n + 1):
            g = toks[i:i + n]
            if toks[i + n:i + 2 * n] == g and toks[i + 2 * n:i + 3 * n] == g:
                return True
    run = 1                                   # one word four or more times in a row
    for a, b in zip(toks, toks[1:]):
        run = run + 1 if a == b else 1
        if run >= 4:
            return True
    return False


def check_transcript(r: AsrResult):
    if not re.search(r"[A-Za-zऀ-ॿ]", r.text or ""):
        raise AudioRejected("empty", "काहीही ऐकू आले नाही.", "No words were recognised.", r)
    if repeated_phrase(r.text):
        raise AudioRejected("repetition", "ऐकलेला मजकूर एकच वाक्य पुन्हा पुन्हा आहे (बहुधा चूक).",
                            "The transcript is one phrase repeated, a known Whisper error on noise.", r)
    if r.no_speech_prob is not None and r.no_speech_prob >= NO_SPEECH_REJECT:
        raise AudioRejected("no_speech", "बोलणे ओळखता आले नाही.",
                            "Whisper judged that the clip probably contains no speech.", r)


# ---- vocabulary prompt (optional, default off) ------------------------------------------
CIVIC_TERMS = ["पुणे महानगरपालिका", "तक्रार", "रस्ता", "खड्डा", "कचरा", "घंटागाडी", "पाणीपुरवठा", "नळ",
               "ड्रेनेज", "गटार", "मॅनहोल", "पथदिवा", "डास", "फवारणी", "झाड", "फांदी", "अतिक्रमण",
               "फेरीवाले", "बांधकाम", "भटकी कुत्री"]


def vocab_prompt() -> str:
    by_ward: dict[str, list[str]] = {}
    for loc in data.gazetteer()["localities"]:
        dev = next((a for a in loc["aliases"] if re.search("[\u0900-\u097F]", a)), None)
        if dev:
            by_ward.setdefault(loc["ward"], []).append(dev)
    names = []                                  # round-robin so every ward office is represented
    for i in range(max(len(v) for v in by_ward.values())):
        names += [v[i] for v in by_ward.values() if i < len(v)]
    # Whisper keeps at most ~223 prompt tokens and Devanagari costs about one token per
    # 1-2 characters, so the prompt is capped; locality names are added until the cap.
    out = "तक्रार: " + ", ".join(CIVIC_TERMS) + ". ठिकाण: "
    for n in names:
        if len(out) + len(n) + 2 > PROMPT_MAX_CHARS:
            break
        out += n + ", "
    return out.rstrip(", ") + "."


# ---- backend ------------------------------------------------------------------------------
_backend = None
_backend_name = None


def set_backend(backend, name="mock"):
    """Tests inject a fake object with .transcribe(audio, language=..., initial_prompt=...)."""
    global _backend, _backend_name
    _backend, _backend_name = backend, name


def model_available(name: str | None = None) -> bool:
    d = config.asr_model_dir(name)
    return (d / "model.bin").exists()


def _device():
    if config.ASR_DEVICE != "auto":
        return config.ASR_DEVICE
    try:
        import ctranslate2
        return "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
    except Exception:
        return "cpu"


def load_backend(name: str | None = None):
    global _backend, _backend_name
    name = name or config.ASR_MODEL
    if _backend is not None and (_backend_name == name or _backend_name == "mock"):
        return _backend
    if not model_available(name):
        raise AsrUnavailable(f"Whisper model '{name}' not found in {config.asr_model_dir(name)}. "
                             "Run: python scripts/fetch_models.py")
    try:
        from faster_whisper import WhisperModel
        device = _device()
        _backend = WhisperModel(str(config.asr_model_dir(name)), device=device,
                                compute_type="float16" if device == "cuda" else "int8", local_files_only=True)
        _backend_name = name
    except Exception as e:
        raise AsrUnavailable(f"could not load Whisper model '{name}': {e}") from e
    return _backend


def transcribe(path, language: str = "mr", *, vocab: bool | None = None, model: str | None = None,
               run_guards: bool = True) -> AsrResult:
    if language not in ("mr", "hi"):
        raise ValueError("language must be 'mr' or 'hi'")
    vocab = config.ASR_VOCAB_PROMPT if vocab is None else vocab
    audio = decode(path)
    duration = check_audio(audio) if run_guards else len(audio) / SAMPLE_RATE
    backend = load_backend(model)
    t0 = time.perf_counter()
    segments, _info = backend.transcribe(audio, language=language, beam_size=5, vad_filter=False,
                                         condition_on_previous_text=False,
                                         initial_prompt=vocab_prompt() if vocab else None)
    segments = list(segments)          # faster-whisper decodes lazily
    seconds = time.perf_counter() - t0
    text = " ".join(s.text.strip() for s in segments).strip()
    lp = [s.avg_logprob for s in segments]
    ns = [s.no_speech_prob for s in segments]
    r = AsrResult(text=text, language=language,
                  avg_logprob=round(float(np.mean(lp)), 4) if lp else None,
                  no_speech_prob=round(float(np.mean(ns)), 4) if ns else None,
                  duration=round(duration, 2), model=_backend_name or "unknown", seconds=round(seconds, 2),
                  vocab_prompt=bool(vocab))
    r.uncertain = r.avg_logprob is not None and r.avg_logprob < config.ASR_UNCERTAIN_LOGPROB
    if run_guards:
        check_transcript(r)
    return r
