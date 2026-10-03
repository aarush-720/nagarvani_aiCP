"""M3 - Text normalisation for Marathi / Hindi / romanised / code-mixed complaints."""
import re
import unicodedata

_ZW = dict.fromkeys(map(ord, "​‌‍﻿"), None)
_DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_REPEAT = re.compile(r"(.)\1{2,}")          # "pleaseeee" -> "pleasee"
_PUNCT = re.compile(r"[\"'“”‘’`~!?।॥;:()\[\]{}<>|/\\]+")
_SPACE = re.compile(r"\s+")


def normalise(text: str) -> str:
    """Return a canonical form used by every downstream module.

    1. Unicode NFC composition (merges nukta / decomposed vowel-sign variants)
    2. remove zero-width joiners and BOMs that WhatsApp keyboards insert
    3. Devanagari digits -> ASCII digits
    4. lower-case Latin script (romanised Marathi, English words)
    5. collapse character runs of 3+ to 2
    6. strip punctuation except commas, hyphens and full stops; squeeze spaces
    """
    t = unicodedata.normalize("NFC", text or "")
    t = t.translate(_ZW).translate(_DEV_DIGITS).lower()
    t = _REPEAT.sub(r"\1\1", t)
    t = _PUNCT.sub(" ", t)
    t = _SPACE.sub(" ", t).strip()
    return t


def script_profile(text: str) -> str:
    """Rough input-variety tag: 'deva', 'latin' or 'mixed'."""
    deva = sum(1 for c in text if "ऀ" <= c <= "ॿ")
    latin = sum(1 for c in text if c.isascii() and c.isalpha())
    if deva and latin:
        return "mixed" if min(deva, latin) / max(deva, latin) > 0.1 else ("deva" if deva > latin else "latin")
    return "deva" if deva else "latin"
