"""Ward-office resolution from free text using the gazetteer.

1. Exact: every alias (longest first) is searched in the normalised text, allowing common
   Marathi/Hindi/romanised suffixes after it (कोथरूडमध्ये, पेठेत, kothrud-la ...).
2. Fuzzy fallback (only when nothing matched exactly): 1-3 word windows, with a known
   suffix stripped, are compared with every alias of the same script using difflib; the
   best ratio must be >= FUZZY_MIN_RATIO.
3. Unknown or ambiguous places are never guessed: the result says why and the gate sends
   the ticket to a human.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from functools import lru_cache

from . import config, data
from .normalise import normalise

LETTER = r"0-9a-zऀ-ॿ"
DEV_SUFFIXES = ["मध्ये", "मधे", "मधील", "मधला", "मधले", "मधल्या", "मधून", "च्या", "चा", "ची", "चे", "चं",
                "तील", "ातील", "ेतील", "ेत", "ेला", "ेच्या", "ेचा", "ेची", "ेचे", "ात", "त", "ला", "ना",
                "ाला", "ाच्या", "जवळ", "जवळील", "जवळचा", "जवळचे", "कडे", "वर", "वरील", "वरचा",
                "वरचे", "वरची", "वरच्या", "हून", "पासून", "ही", "च"]
LAT_SUFFIXES = ["madhye", "madhe", "mdhe", "made", "madhil", "madhla", "madhlya", "madhun", "chya", "cha",
                "chi", "che", "la", "var", "javal", "kade", "hun", "mein", "me", "at", "t"]
_SUFFIX_RE = "|".join(re.escape(s) for s in sorted(set(DEV_SUFFIXES + LAT_SUFFIXES), key=len, reverse=True))


def _is_latin(s: str) -> bool:
    return bool(re.search("[a-z]", s))


@dataclass
class AliasEntry:
    alias: str            # normalised alias as searched
    loc_id: str | None    # None for an ambiguous alias
    ward: str | None
    wards: tuple = ()     # candidate wards for an ambiguous alias
    why: str = ""


@dataclass
class LocationResult:
    status: str                    # resolved | ambiguous | unknown
    method: str                    # exact | fuzzy | none
    ward: str | None = None
    locality: str | None = None
    matched_alias: str | None = None
    matched_text: str | None = None
    score: float | None = None
    candidates: list = field(default_factory=list)   # wards in play when ambiguous
    reason: str = ""
    spans: list = field(default_factory=list)        # (start, end) in normalised text, for masking


@lru_cache(maxsize=1)
def alias_index() -> list[AliasEntry]:
    g = data.gazetteer()
    out, seen = [], set()
    for loc in g["localities"]:
        for a in loc["aliases"]:
            n = normalise(a)
            for form in {n, n.replace(" ", "")}:
                if form not in seen:
                    seen.add(form)
                    out.append(AliasEntry(form, loc["id"], loc["ward"]))
    for amb in g["ambiguous"]:
        n = normalise(amb["alias"])
        for form in {n, n.replace(" ", "")}:
            if form not in seen:
                seen.add(form)
                out.append(AliasEntry(form, None, None, tuple(amb["wards"]), amb["why"]))
    out.sort(key=lambda e: len(e.alias), reverse=True)
    return out


@lru_cache(maxsize=1)
def _compiled():
    return [(e, re.compile(rf"(?<![{LETTER}]){re.escape(e.alias)}(?:{_SUFFIX_RE})?(?![{LETTER}])"))
            for e in alias_index()]


@lru_cache(maxsize=1)
def _stopwords():
    return {normalise(w) for w in data.gazetteer()["fuzzy_stopwords"]}


def exact_matches(norm: str):
    """Non-overlapping alias matches, longest alias first: list of (entry, start, end)."""
    taken, found = [], []
    for entry, rx in _compiled():
        for m in rx.finditer(norm):
            s, e = m.span()
            if any(s < te and ts < e for ts, te in taken):
                continue
            taken.append((s, e))
            found.append((entry, s, e))
    return sorted(found, key=lambda t: t[1])


def _strip_suffix(word: str) -> str:
    m = re.match(rf"^(.{{3,}}?)(?:{_SUFFIX_RE})$", word)
    return m.group(1) if m else word


def fuzzy_best(norm: str):
    """Best (score, entry, window_text, span) per ward, sorted by score descending."""
    tokens = [(m.group(), m.start(), m.end()) for m in re.finditer(rf"[{LETTER}]+", norm)]
    stop = _stopwords()
    best = {}
    entries = [e for e in alias_index() if len(e.alias) >= 4]
    for n in (1, 2, 3):
        for i in range(len(tokens) - n + 1):
            window = tokens[i:i + n]
            text = " ".join(t[0] for t in window)
            span = (window[0][1], window[-1][2])
            for cand in {text, _strip_suffix(text)}:
                if len(cand) < 4 or cand in stop:
                    continue
                latin = _is_latin(cand)
                sm = difflib.SequenceMatcher(None, cand, "", autojunk=False)
                for e in entries:
                    if _is_latin(e.alias) != latin or abs(len(e.alias) - len(cand)) > 4:
                        continue
                    sm.set_seq2(e.alias)
                    if sm.real_quick_ratio() < config.FUZZY_MIN_RATIO or sm.quick_ratio() < config.FUZZY_MIN_RATIO:
                        continue
                    r = sm.ratio()
                    key = e.ward or ("AMB:" + e.alias)
                    if r > best.get(key, (0,))[0]:
                        best[key] = (r, e, text, span)
    return sorted(best.values(), key=lambda t: -t[0])


def resolve(text: str, allow_fuzzy: bool = True) -> LocationResult:
    norm = normalise(text)
    matches = exact_matches(norm)
    if matches:
        spans = [(s, e) for _, s, e in matches]
        amb = [m for m in matches if m[0].loc_id is None]
        firm = [m for m in matches if m[0].loc_id is not None]
        wards = sorted({m[0].ward for m in firm})
        if len(wards) == 1 and (not amb or all(wards[0] in m[0].wards for m in amb)):
            e, s, en = firm[0]
            return LocationResult("resolved", "exact", e.ward, e.loc_id, e.alias, norm[s:en], 1.0,
                                  wards, f"exact match on '{e.alias}'", spans)
        if not firm:
            e, s, en = amb[0]
            return LocationResult("ambiguous", "exact", None, None, e.alias, norm[s:en], None, list(e.wards),
                                  f"'{e.alias}' is ambiguous: {e.why}", spans)
        cands = sorted(set(wards) | {w for m in amb for w in m[0].wards})
        names = ", ".join(f"'{m[0].alias}'" for m in matches)
        return LocationResult("ambiguous", "exact", None, None, None, None, None, cands,
                              f"places in different ward offices mentioned: {names}", spans)

    ranked = [r for r in fuzzy_best(norm) if r[0] >= config.FUZZY_MIN_RATIO] if allow_fuzzy else []
    if not ranked:
        return LocationResult("unknown", "none", reason="no gazetteer locality found in the text")
    score, e, window, span = ranked[0]
    if e.loc_id is None:
        return LocationResult("ambiguous", "fuzzy", None, None, e.alias, window, round(score, 3), list(e.wards),
                              f"'{window}' is close to the ambiguous name '{e.alias}': {e.why}", [span])
    rivals = [r for r in ranked[1:] if r[0] >= score - 0.02]
    if rivals:
        cands = sorted({e.ward} | {w for r in rivals for w in ([r[1].ward] if r[1].ward else r[1].wards)})
        return LocationResult("ambiguous", "fuzzy", None, None, e.alias, window, round(score, 3), cands,
                              f"'{window}' is equally close to places in different ward offices", [span])
    return LocationResult("resolved", "fuzzy", e.ward, e.loc_id, e.alias, window, round(score, 3), [e.ward],
                          f"fuzzy match '{window}' ≈ '{e.alias}' (similarity {score:.2f} ≥ {config.FUZZY_MIN_RATIO})",
                          [span])


def mask_locations(norm: str) -> str:
    """Remove every exact alias match (used by duplicate detection)."""
    spans = [(s, e) for _, s, e in exact_matches(norm)]
    out, last = [], 0
    for s, e in spans:
        out.append(norm[last:s])
        last = e
    out.append(norm[last:])
    return re.sub(r"\s+", " ", " ".join(out)).strip()
