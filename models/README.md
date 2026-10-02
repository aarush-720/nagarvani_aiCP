# models/

Whisper weights live here (git-ignored). Fetch them once, with internet:

    python scripts/fetch_models.py                    # the configured model (default: small)
    python scripts/fetch_models.py --benchmark CLIP   # time the candidates on a ~15 s clip and recommend one

After that the app loads `models/faster-whisper-<name>/` with the Hugging Face hub in
offline mode and never uses the network.
