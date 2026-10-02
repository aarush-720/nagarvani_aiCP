"""Text normalisation shared by every component.

Deliberately light: Unicode NFC, drop zero-width joiners, map Devanagari digits to ASCII,
lower-case Latin letters, turn punctuation into spaces, collapse whitespace. Spelling
variation (paani/pani, कोथरूड/कोथरुड) is left to character n-grams and the gazetteer.
"""
import re
import unicodedata

_ZW = dict.fromkeys(map(ord, "​‌‍﻿"), None)
_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
# Danda, double danda and ASCII/Unicode punctuation become spaces; keep letters, marks, digits.
_PUNCT = re.compile(r"[^\wऀ-ॿ\s]|_")
_SPACE = re.compile(r"\s+")


def normalise(text: str) -> str:
    s = unicodedata.normalize("NFC", text or "")
    s = s.translate(_ZW).translate(_DIGITS)
    s = s.replace("।", " ").replace("॥", " ")
    s = _PUNCT.sub(" ", s)
    s = _SPACE.sub(" ", s).strip()
    return s.lower()


def script_of(text: str) -> str:
    """'devanagari', 'romanised' or 'code-mixed' (used for reporting only)."""
    has_dev = bool(re.search("[ऀ-ॿ]", text or ""))
    has_lat = bool(re.search("[A-Za-z]", text or ""))
    if has_dev and has_lat:
        return "code-mixed"
    return "devanagari" if has_dev else "romanised"
