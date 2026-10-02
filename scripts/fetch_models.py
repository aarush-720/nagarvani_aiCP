"""Download faster-whisper models into models/ (needs internet once; the app never does).

    python scripts/fetch_models.py                     # fetch the configured model (NAGARVANI_ASR_MODEL, default "small")
    python scripts/fetch_models.py --model medium      # fetch a specific model
    python scripts/fetch_models.py --benchmark CLIP    # fetch the candidates, time each on CLIP (~15 s of
                                                       # real Marathi speech), write results/asr_benchmark.json
                                                       # and recommend the largest model that takes <= 20 s

Model names are the faster-whisper names (tiny, base, small, medium, large-v3, turbo ...).
English-only (.en) and distil models are excluded because they do not transcribe Marathi.
"""
import argparse
import json
import os
import platform
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nagarvani import config  # noqa: E402
from nagarvani.console import safe_console  # noqa: E402

CANDIDATES = ["tiny", "base", "small", "medium", "large-v3-turbo", "large-v3"]   # smallest to largest
BUDGET_SECONDS = 20.0


def fetch(name):
    os.environ.pop("HF_HUB_OFFLINE", None)
    from faster_whisper.utils import download_model
    out = config.asr_model_dir(name)
    if (out / "model.bin").exists():
        print(f"already present: {out}")
        return out
    print(f"downloading {name} -> {out} ...")
    try:
        download_model(name, output_dir=str(out))
    except Exception as e:
        print(f"\nDOWNLOAD FAILED for '{name}': {type(e).__name__}: {e}")
        print("The model is hosted on huggingface.co. Check the internet connection (or proxy/firewall)"
              " and run this script again. The app still runs without it; only the audio path is disabled.")
        sys.exit(2)
    print("done")
    return out


def benchmark(clip, models):
    from faster_whisper import WhisperModel, decode_audio
    import ctranslate2
    device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
    compute = "float16" if device == "cuda" else "int8"
    audio = decode_audio(str(clip), sampling_rate=16000)
    rows = []
    for name in models:
        fetch(name)
        t0 = time.perf_counter()
        m = WhisperModel(str(config.asr_model_dir(name)), device=device, compute_type=compute, local_files_only=True)
        load = time.perf_counter() - t0
        t0 = time.perf_counter()
        segs, _ = m.transcribe(audio, language="mr", beam_size=5, vad_filter=False, condition_on_previous_text=False)
        text = " ".join(s.text.strip() for s in segs)
        secs = time.perf_counter() - t0
        rows.append({"model": name, "load_seconds": round(load, 2), "transcribe_seconds": round(secs, 2),
                     "text": text})
        print(f"{name:16s} load {load:6.1f} s   transcribe {secs:6.1f} s")
        del m
    ok = [r for r in rows if r["transcribe_seconds"] <= BUDGET_SECONDS]
    choice = ok[-1]["model"] if ok else rows[0]["model"]
    result = {"clip": str(clip), "clip_seconds": round(len(audio) / 16000, 2), "device": device,
              "compute_type": compute, "machine": platform.platform(), "processor": platform.processor(),
              "cpu_count": os.cpu_count(), "budget_seconds": BUDGET_SECONDS, "timings": rows,
              "recommended": choice}
    config.RESULTS.mkdir(exist_ok=True)
    (config.RESULTS / "asr_benchmark.json").write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                                       encoding="utf-8")
    print(f"\nrecommended: {choice}  (largest within {BUDGET_SECONDS:.0f} s)")
    print(f"set it with:  NAGARVANI_ASR_MODEL={choice}   (Windows: set NAGARVANI_ASR_MODEL={choice})")
    return result


def main():
    safe_console()
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=config.ASR_MODEL)
    ap.add_argument("--benchmark", metavar="CLIP")
    ap.add_argument("--candidates", default=",".join(CANDIDATES))
    a = ap.parse_args()
    if a.benchmark:
        benchmark(Path(a.benchmark), a.candidates.split(","))
    else:
        fetch(a.model)


if __name__ == "__main__":
    main()
