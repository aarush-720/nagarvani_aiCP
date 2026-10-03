"""Start NagarVani:  python run.py   (then open the printed URL)

Checks that the classifier artefact, the database and the Whisper model are present.
Binds to 127.0.0.1 only. Set NAGARVANI_PORT to change the port (default 5000).
"""
import logging
import os
import sys

from nagarvani import config
from nagarvani import speech as asr
from nagarvani.console import safe_console


def main():
    safe_console()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ok = True
    if config.MODEL_PATH.exists():
        print(f"[ok]   classifier artefact: {config.MODEL_PATH.relative_to(config.ROOT)}")
    else:
        ok = False
        print("[FAIL] classifier artefact missing. Run: python -m nagarvani.train  (or python experiments/run_eval.py)")
    if asr.model_available():
        print(f"[ok]   Whisper model '{config.ASR_MODEL}': {config.asr_model_dir().relative_to(config.ROOT)}")
    else:
        print(f"[warn] Whisper model '{config.ASR_MODEL}' not found in models/. Typed complaints work; audio is disabled.")
        print("       Fetch it once (internet needed): python scripts/fetch_models.py")
    if not ok:
        sys.exit(1)
    from nagarvani.app import create_app
    app = create_app()
    db = app.extensions["nagarvani"]["store"]
    print(f"[ok]   database: {os.path.relpath(db.path, config.ROOT)} ({len(db.tickets())} tickets)")
    port = int(os.environ.get("NAGARVANI_PORT", "5000"))
    print(f"\n  NagarVani is running:  http://127.0.0.1:{port}/\n  (Ctrl+C to stop)\n")
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
