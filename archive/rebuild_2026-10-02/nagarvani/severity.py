"""Forward-chaining expert system for severity bands (knowledge base: data/severity_rules.json).

Working memory holds: the cue groups found in the text (with the matching term), the
department, the number of reports of the same issue, and the current band. On each cycle
the eligible unfired rule with the highest salience fires (each rule fires at most once)
until no rule is eligible. Every firing is recorded so the trace page can show it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from . import data
from .normalise import normalise

BANDS = ["P1", "P2", "P3", "P4"]


def more_urgent(a: str, b: str) -> str:
    return a if BANDS.index(a) <= BANDS.index(b) else b


def _norm_term(term: str) -> str:
    # Keep deliberate leading/trailing spaces in a term (word-boundary hints such as "तार ").
    core = normalise(term)
    return (" " if term.startswith(" ") else "") + core + (" " if term.endswith(" ") else "")


@lru_cache(maxsize=1)
def knowledge_base():
    kb = data.severity_kb()
    cues = {g: [_norm_term(t) for t in terms] for g, terms in kb["cue_groups"].items()}
    rules = sorted(kb["rules"], key=lambda r: -r["salience"])   # stable: file order within a salience
    return cues, rules


def find_cues(norm_text: str) -> dict:
    """{cue group: first matching term} for every group present in the text."""
    cues, _ = knowledge_base()
    padded = f" {norm_text} "
    found = {}
    for group, terms in cues.items():
        for t in terms:
            if t and t in padded:
                found[group] = t.strip()
                break
    return found


@dataclass
class Firing:
    rule: str
    name: str
    cues: dict          # group -> matched term (only the groups this rule tested positively)
    action: str         # human-readable
    band: str | None    # band proposed or band after a raise


@dataclass
class SeverityResult:
    band: str
    base_band: str
    fired: list = field(default_factory=list)        # Firing, in firing order
    overridden: list = field(default_factory=list)   # [{"rule", "proposed", "by"}]
    cues: dict = field(default_factory=dict)

    @property
    def rule_ids(self):
        return [f.rule for f in self.fired]


def assess(text: str, department: str, report_count: int = 1) -> SeverityResult:
    norm = normalise(text)
    _, rules = knowledge_base()
    wm_cues = find_cues(norm)
    fired: list[Firing] = []
    done: set[str] = set()
    proposals: list[tuple[str, str]] = []      # (rule id, band) from non-default rules
    default: tuple[str, str] | None = None
    raises: list[tuple[str, str, str]] = []

    def base_band():
        if proposals:
            best = proposals[0]
            for p in proposals[1:]:
                if BANDS.index(p[1]) < BANDS.index(best[1]):
                    best = p
            return best
        return default

    def current_band():
        b = base_band()
        band = b[1] if b else None
        for _, _, after in raises:
            band = after
        return band

    def eligible(rule):
        cond = rule["if"]
        if any(g not in wm_cues for g in cond.get("all", [])):
            return False
        if cond.get("any") and not any(g in wm_cues for g in cond["any"]):
            return False
        if any(g in wm_cues for g in cond.get("none", [])):
            return False
        if "band_in" in cond and current_band() not in cond["band_in"]:
            return False
        if "min_reports" in cond and report_count < cond["min_reports"]:
            return False
        return True

    while True:
        rule = next((r for r in rules if r["id"] not in done and eligible(r)), None)
        if rule is None:
            break
        done.add(rule["id"])
        cond, then = rule["if"], rule["then"]
        used = {g: wm_cues[g] for g in cond.get("all", []) + cond.get("any", []) if g in wm_cues}
        if "band" in then:
            proposals.append((rule["id"], then["band"]))
            fired.append(Firing(rule["id"], rule["name"], used, f"propose {then['band']}", then["band"]))
        elif "default_band" in then:
            band = then["default_band"].get(department, "P3")
            default = (rule["id"], band)
            note = f"department default for {department}: {band}"
            if proposals:
                note += " (not used: another rule proposed a band)"
            fired.append(Firing(rule["id"], rule["name"], used, note, band))
        elif "raise" in then:
            before = current_band()
            after = BANDS[max(0, BANDS.index(before) - then["raise"])]
            raises.append((rule["id"], before, after))
            if "min_reports" in cond:
                used = {"reports": str(report_count)}
            note = f"raise {before} → {after}" if after != before else f"already {before}, cannot raise further"
            fired.append(Firing(rule["id"], rule["name"], used, note, after))

    base = base_band()
    overridden = []
    for rid, band in proposals:
        if band != base[1]:
            overridden.append({"rule": rid, "proposed": band, "by": base[0]})
    if proposals and default:
        overridden.append({"rule": default[0], "proposed": default[1], "by": base[0]})
    return SeverityResult(current_band(), base[1], fired, overridden, wm_cues)
