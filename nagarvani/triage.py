"""The single triage entry point used by the evaluation AND the web app.

    triage(text, *, ward_hint=None, now=None, store=None) -> TriageResult

It wraps the original, frozen prototype components without changing them and calls them in
the same order as the original `pipeline.Triage.triage`:

    model.predict_proba  ->  WardResolver.resolve  ->  DuplicateDetector.decide (only if a
    ward is known and a store is given)  ->  severity.infer(cluster_size)  ->  gate
    (confidence >= tau AND ward resolved).

What it adds is read-only explanation for the trace page (which alias matched, the fuzzy
score, which cue term triggered each rule, which rules were overridden), the optional
dropdown ward hint, and timestamps in UTC. tests/test_triage_equivalence.py checks that it
gives the same department, confidence, ward, priority, rules and route as the original
Triage.triage on every test complaint.
"""
from __future__ import annotations

import pickle
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from functools import lru_cache

from . import config, data
from .dedup import DuplicateDetector
from .location import WardResolver
from .normalise import normalise
from .severity import CUES, RULES, SLA_HOURS, extract_facts, infer

TAU = 0.50   # the original Triage default; kept identical (see config.py)

# Which cue groups each rule tests (read off the rule conditions in severity.py).
RULE_CUES = {
    "R01": ["INJURY"], "R02": ["COVER", "OPEN"], "R03": ["CURRENT", "WIRE", "DANGLING", "DP_OPEN", "OPEN"],
    "R04": ["IMMINENT", "COLLAPSED"], "R05": ["TREE_FALL", "BLOCKING", "DANGLING"], "R06": ["OUTBREAK"],
    "R07": ["HOME", "SEWAGE"], "R08": ["RABID"], "R10": ["RISK"], "R11": ["NUISANCE"],
    "R12": ["OUTAGE", "DAYS"], "R13": ["DAYS"], "R15": ["DRAIN_BLOCK"], "R16": ["DAMAGE"], "R14": ["WASTAGE"],
    "R20": ["REQUEST"], "R30": ["VULNERABLE"], "R31": ["DAYS"], "R32": ["CLUSTER"],
}


# ---- components, loaded once ------------------------------------------------------------
@lru_cache(maxsize=1)
def model():
    with open(config.MODEL_PATH, "rb") as f:
        return pickle.load(f)


@lru_cache(maxsize=1)
def resolver():
    return WardResolver(str(config.GAZETTEER))


@lru_cache(maxsize=1)
def detector():
    return DuplicateDetector(resolver()).fit([r["text"] for r in data.load_train()])


def load_all():
    model(), resolver(), detector()


# ---- result types --------------------------------------------------------------------------
@dataclass
class WardResult:
    ward: str | None
    method: str                  # exact | fuzzy | hint | unresolved
    status: str                  # resolver status: resolved | ambiguous | unresolved
    locality: str | None
    matched_alias: str | None
    score: float | None
    candidates: list
    reason: str
    hint_used: bool = False
    hint: str | None = None


@dataclass
class GateResult:
    decision: str        # AUTO_ROUTED | SENT_TO_REVIEW | MERGED
    gate_passed: bool    # confidence >= tau AND ward known
    reason: str


@dataclass
class TriageResult:
    text: str
    normalised: str
    top3: list
    confidence: float
    department: str
    ward: WardResult
    severity: dict
    sla_hours: int
    deadline_utc: str
    duplicate: dict
    gate: GateResult
    created_utc: str
    route_original: str          # what the original Triage would record: AUTO_ROUTED | NODAL_REVIEW
    extras: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


# ---- explanations (read-only re-derivations from the frozen components) --------------------
def _explain_location(text: str, loc: dict):
    r = resolver()
    t = normalise(text)
    if loc["status"] == "resolved" and not loc.get("fuzzy"):
        masked = t
        for alias, key in r.aliases:                       # same scan as WardResolver.resolve
            if r._find(alias, masked):
                if key == loc["locality"]:
                    return alias, 1.0, f"exact match on gazetteer alias '{alias}' (locality {key})"
                masked = masked.replace(alias, " ")
        return None, 1.0, f"exact match (locality {loc['locality']})"
    if loc.get("fuzzy"):
        toks = t.split()
        best, best_alias = 0.0, None
        for alias, key in r.aliases:                       # same scan as WardResolver._fuzzy
            if len(alias) < 4:
                continue
            n = len(alias.split())
            for i in range(len(toks) - n + 1):
                win = " ".join(toks[i:i + n])[:len(alias) + 1]
                s = SequenceMatcher(None, alias, win).ratio()
                if s > best:
                    best, best_alias = s, alias
        return best_alias, round(best, 3), (f"no exact alias; fuzzy match to '{best_alias}' with similarity "
                                            f"{best:.2f} ≥ {r.fuzzy_threshold}")
    if loc["status"] == "ambiguous":
        return None, None, "place name is ambiguous between: " + ", ".join(loc["candidates"])
    return None, None, "no gazetteer locality found in the text"


def _cue_terms(norm: str, groups) -> dict:
    out = {}
    for g in groups:
        if g in CUES:
            hit = next((c for c in CUES[g] if c.lower() in norm), None)
            if hit:
                out[g] = hit
    return out


def _explain_severity(text: str, dept: str, csize: int) -> dict:
    res = infer(text, dept, cluster_size=csize)
    facts = extract_facts(text, dept, csize)
    norm = normalise(text)
    base = infer(text, dept, cluster_size=csize, use_escalation=False)["band"]
    by_id = {r.rid: r for r in RULES}
    fired = []
    for rid in res["fired"]:
        r = by_id[rid]
        cues = _cue_terms(norm, RULE_CUES.get(rid, []))
        if "DAYS" in RULE_CUES.get(rid, []):
            cues["DAYS"] = f"{facts['DAYS']} days stated"
        if rid == "R32":
            cues["CLUSTER"] = f"{csize} reports"
        action = {"set": f"at least P{r.band}", "relax": "P4 (service request)", "escalate": "escalate one band"}[r.kind]
        fired.append({"rule": rid, "name": r.text, "cues": cues, "action": action, "salience": r.salience})
    overridden = []
    set_fired = [by_id[x] for x in res["fired"] if by_id[x].kind == "set"]
    if set_fired:
        top = min(set_fired, key=lambda r: r.band)
        for r in set_fired:
            if r.band > top.band:
                overridden.append({"rule": r.rid, "proposed": f"P{r.band}", "by": top.rid,
                                   "why": "a more urgent rule fired"})
    if "R20" not in res["fired"] and by_id["R20"].cond(facts):
        overridden.append({"rule": "R20", "proposed": "P4", "by": set_fired[0].rid if set_fired else None,
                           "why": "service-request relaxation suppressed because a hazard rule fired"})
    return {"band": res["band"], "base_band": base, "default_band": "P3", "fired": fired,
            "overridden": overridden, "facts": {k: v for k, v in facts.items() if v and k != "DEPT"}}


def _resolve_ward(text: str, ward_hint: str | None) -> tuple[dict, WardResult]:
    loc = resolver().resolve(text)
    alias, score, reason = _explain_location(text, loc)
    wards = data.gazetteer()["ward_offices"]
    if loc["status"] == "resolved":
        if ward_hint and ward_hint != loc["ward"]:
            reason += f" (dropdown choice {ward_hint} ignored: the text names a place)"
        return loc, WardResult(loc["ward"], "fuzzy" if loc.get("fuzzy") else "exact", "resolved", loc["locality"],
                               alias, score, loc["candidates"], reason, False, ward_hint)
    if ward_hint and ward_hint in wards:
        return loc, WardResult(ward_hint, "hint", loc["status"], None, alias, score, loc["candidates"],
                               reason + "; used the ward office the citizen chose in the dropdown", True, ward_hint)
    return loc, WardResult(None, "unresolved", loc["status"], None, alias, score, loc["candidates"], reason,
                           False, ward_hint)


# ---- the entry point ------------------------------------------------------------------------
def triage(text: str, *, ward_hint: str | None = None, now: datetime | None = None, store=None,
           exclude_ticket: int | None = None) -> TriageResult:
    norm = normalise(text)
    if not any(ch.isalpha() for ch in norm):
        raise ValueError("no words to classify")
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)

    # 1. department (original: model.predict_proba on the raw text; the pipeline normalises)
    m = model()
    proba = m.predict_proba([text])[0]
    classes = list(m.classes_)
    order = proba.argsort()[::-1]
    dept, conf = classes[order[0]], float(proba[order[0]])
    top3 = [(classes[i], float(proba[i])) for i in order[:3]]

    # 2. ward office (original resolver; the dropdown hint only fills a gap)
    loc, ward = _resolve_ward(text, ward_hint)

    # 3. duplicates (original detector; live path only)
    dup = {"decision": "skipped", "ticket_id": None, "score": None, "report_count": 1, "compared": 0,
           "reason": "offline run: no ticket store"}
    csize = 1
    if store is not None:
        if ward.ward is None:
            dup["reason"] = "ward office unknown, so there is no block to compare in"
        else:
            block = store.open_for_dedup(ward.ward, dept, exclude_ticket)
            decision, best_id, score = detector().decide(text, dept, ward.ward, block)
            parent = next((b for b in block if b["id"] == best_id), None)
            root = parent["cluster_root"] if parent else None
            if decision == "merge":
                csize = parent["cluster_size"] + 1
            words = {"merge": f"similarity {score:.2f} ≥ {detector().theta_high}: same issue as ticket #{root}",
                     "review": f"similarity {score:.2f} is between {detector().theta_low} and "
                               f"{detector().theta_high}: an officer decides",
                     "new": (f"best similarity {score:.2f} < {detector().theta_low}: a new issue" if block
                             else "no open ticket in the same ward office and department")}
            dup = {"decision": decision, "ticket_id": root, "score": round(float(score), 4), "report_count": csize,
                   "compared": len(block), "reason": words[decision]}

    # 4. severity (original expert system; R32 sees the cluster size)
    sev = _explain_severity(text, dept, csize)
    hours = SLA_HOURS[sev["band"]]

    # 5. gate: original rule (confidence >= tau AND ward resolved); a dropdown ward counts as known
    conf_ok = conf >= TAU
    gate_passed = conf_ok and ward.ward is not None
    route_original = "AUTO_ROUTED" if (conf_ok and loc["status"] == "resolved") else "NODAL_REVIEW"
    conds = (f"confidence {conf:.2f} {'≥' if conf_ok else '<'} {TAU}; "
             f"ward office {'known (' + ward.method + ')' if ward.ward else 'not resolved (' + loc['status'] + ')'}")
    if not gate_passed:
        decision, reason = "SENT_TO_REVIEW", f"Gate failed: {conds}."
        if dup["decision"] in ("merge", "review"):
            reason += f" Possible duplicate of #{dup['ticket_id']} (similarity {dup['score']:.2f}) left for the officer."
    elif dup["decision"] == "merge":
        decision, reason = "MERGED", f"Gate passed ({conds}); {dup['reason']}."
    elif dup["decision"] == "review":
        decision, reason = "SENT_TO_REVIEW", f"Gate passed ({conds}), but {dup['reason']}."
    else:
        decision, reason = "AUTO_ROUTED", f"Gate passed: {conds}."

    return TriageResult(
        text=text, normalised=norm, top3=top3, confidence=conf, department=dept, ward=ward, severity=sev,
        sla_hours=hours, deadline_utc=(now + timedelta(hours=hours)).isoformat(timespec="seconds"),
        duplicate=dup, gate=GateResult(decision, gate_passed, reason), created_utc=now.isoformat(timespec="seconds"),
        route_original=route_original, extras={"masked_text": detector()._strip_loc(text)})
