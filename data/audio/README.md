# Real audio for ASR evaluation

This folder is git-ignored except for this file and `manifest.example.csv`. Put recorded
clips here, plus a `manifest.csv`, and run:

    python eval/asr_eval.py

That writes `results/asr_eval.json` and `results/asr_eval.md`, which the `/about` page then
shows. With no clips it prints a message and writes nothing.

## manifest.csv

UTF-8, with a header row and these columns:

| Column | Meaning |
|---|---|
| `file` | File name inside `data/audio/` (WAV, MP3, M4A, OGG/Opus, WebM/Opus, MP4). |
| `reference_text` | Exactly what the speaker said, in the script they intended (Devanagari for Marathi or Hindi; Latin for English words if you want them scored that way). |
| `department` | Department code (ROAD, SWM, WATER, DRAIN, ELEC, HEALTH, TREE, ENCROACH, BUILD, VET). |
| `locality` | Gazetteer locality key from `data/gazetteer.json` (e.g. `kothrud`) or empty if no place is named. |
| `speaker_id` | Anonymous id (S01, S02 ...). Never a name. |
| `condition` | `quiet`, `street`, `fan`, `phone_speaker`, or another short label. |
| `device` | e.g. `laptop_mic`, `android_whatsapp`, `iphone`. |
| `language` (optional) | `mr` (default) or `hi`, passed to Whisper as the forced language. |

See `manifest.example.csv`.

## Recording protocol

For the v2.0 evaluation, follow `docs/RECORDING_GUIDE.md`. Each of four speakers records 12
assigned `test_v1` complaints, and `python eval/recordings.py manifest` builds `manifest.csv`
from the clip names. This replaces the earlier protocol, which asked for new sentences rather
than test-set rows (see `docs/DECISIONS.md` R9). Its other points still apply:

1. **Consent.** Every speaker agrees to the clip being stored in the team's private repo and
   used for evaluation. Record no names, phone numbers or addresses of real people.
2. **Conditions.** Record some clips in real background noise (`street`, `fan`, `tv`).
3. **Length.** The app rejects clips under 1 s or over 60 s.
4. **Files.** Keep the original file the device produced. Do not convert or trim it.
