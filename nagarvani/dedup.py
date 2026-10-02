"""Duplicate detection: block on (ward office, department), mask location words, compare
character 2-4 gram count vectors by cosine similarity.

    score >= DUP_MERGE              -> merge into the open ticket
    DUP_REVIEW <= score < DUP_MERGE -> an officer decides
    score < DUP_REVIEW              -> new ticket
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

from . import config
from .location import mask_locations
from .normalise import normalise


def masked(text: str) -> str:
    return mask_locations(normalise(text))


def char_ngrams(s: str, lo: int = 2, hi: int = 4) -> Counter:
    s = f" {s} "
    return Counter(s[i:i + n] for n in range(lo, hi + 1) for i in range(len(s) - n + 1))


def cosine(a: str, b: str) -> float:
    va, vb = char_ngrams(a), char_ngrams(b)
    dot = sum(c * vb[g] for g, c in va.items() if g in vb)
    na = math.sqrt(sum(c * c for c in va.values()))
    nb = math.sqrt(sum(c * c for c in vb.values()))
    return dot / (na * nb) if na and nb else 0.0


def decide(score: float) -> str:
    if score >= config.DUP_MERGE:
        return "merge"
    if score >= config.DUP_REVIEW:
        return "review"
    return "new"


@dataclass
class DuplicateResult:
    decision: str                 # merge | review | new | skipped
    ticket_id: int | None = None  # best-matching open ticket
    score: float | None = None
    report_count: int = 1         # reports of this issue including the new one (if merged)
    compared: int = 0             # open tickets in the same (ward, department) block
    reason: str = ""


def find(text: str, candidates) -> DuplicateResult:
    """candidates: iterable of (ticket_id, masked_text, report_count) in the same block."""
    m = masked(text)
    best = None
    n = 0
    for tid, other, reports in candidates:
        n += 1
        s = cosine(m, other)
        if best is None or s > best[1]:
            best = (tid, s, reports)
    if best is None:
        return DuplicateResult("new", compared=0, reason="no open ticket in the same ward office and department")
    tid, s, reports = best
    d = decide(s)
    count = reports + 1 if d == "merge" else 1
    words = {"merge": f"similarity {s:.2f} ≥ {config.DUP_MERGE}: same issue as ticket #{tid}",
             "review": f"similarity {s:.2f} is between {config.DUP_REVIEW} and {config.DUP_MERGE}: an officer decides",
             "new": f"best similarity {s:.2f} < {config.DUP_REVIEW}: a new issue"}
    return DuplicateResult(d, tid, round(s, 4), count, n, words[d])
