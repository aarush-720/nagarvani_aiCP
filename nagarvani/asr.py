"""M2 - Speech front-end.

The prototype defines the ASR interface but does not ship a Marathi acoustic model:
pretrained checkpoints (Whisper, IndicWav2Vec) could not be downloaded in the build
environment. Voice input is therefore evaluated through `simulate_asr_noise`, which
injects character-level substitution / deletion / insertion errors at a controlled
character error rate (CER) so that the sensitivity of the downstream triage to
transcription quality can be measured.
"""
import random


class ASRBackend:
    """Interface every speech backend must satisfy."""
    def transcribe(self, wav_path: str) -> dict:          # -> {"text": str, "confidence": float}
        raise NotImplementedError


class WhisperBackend(ASRBackend):                          # pragma: no cover - needs model weights
    def __init__(self, size="small"):
        import whisper                                     # noqa: F401  (optional dependency)
        self.model = whisper.load_model(size)

    def transcribe(self, wav_path):
        r = self.model.transcribe(wav_path, language="mr")
        segs = r.get("segments") or []
        conf = sum(s.get("avg_logprob", -1.0) for s in segs) / max(1, len(segs))
        return {"text": r["text"], "confidence": float(conf)}


_DEVA = [chr(c) for c in range(0x0915, 0x0939 + 1)] + list("ािीुूेैोौंँ्")
_LAT = list("abcdefghijklmnopqrstuvwxyz")


def simulate_asr_noise(text: str, cer: float, rng: random.Random) -> str:
    """Corrupt `text` so that roughly `cer` of its characters are edited."""
    out = []
    for ch in text:
        if ch == " " or rng.random() >= cer:
            out.append(ch); continue
        pool = _DEVA if "ऀ" <= ch <= "ॿ" else _LAT
        op = rng.random()
        if op < 0.5:
            out.append(rng.choice(pool))                   # substitution
        elif op < 0.8:
            pass                                           # deletion
        else:
            out.append(ch + rng.choice(pool))              # insertion
    return "".join(out)
