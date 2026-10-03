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

1. **Consent.** Every speaker agrees to the clip being stored in the team's private repo and
   used for evaluation. Record no names, phone numbers or addresses of real people.
2. **Script.** Each speaker reads 10 complaints and speaks 5 more in their own words. Write
   the reference text down **before** recording (read items) or transcribe it by hand
   **after** (free items). Never copy Whisper's output as the reference.
3. **Do not reuse the test set.** Read complaints should be new sentences, not rows from
   `data/test_handwritten.csv` or the training templates. Otherwise ASR errors and
   classifier memorisation get mixed up.
4. **Coverage.** At least 5 speakers, men and women, of different ages. Cover all 10
   departments. Include about 20% Hindi (set `language=hi`) and some code-mixed English.
   Mention a locality in about 80% of clips.
5. **Conditions.** Record each speaker in at least two conditions: `quiet` indoors and one
   noisy condition (`street`, `fan`). Record some clips as WhatsApp voice notes (OGG/Opus),
   since that is a demo moment.
6. **Length.** 4 to 20 seconds. The app rejects clips under 1 s or over 60 s.
7. **Files.** Keep the original file the device produced. Do not convert or trim it.
