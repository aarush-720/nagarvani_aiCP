"""M5 - Rule-based expert system for severity / priority assignment.

Architecture (classic production system):
  * Knowledge base   - CUES (fact-extraction lexicon) + RULES (condition -> action)
  * Working memory   - a set of facts derived from the complaint text,
                       the predicted department, parsed duration and duplicate-cluster size
  * Inference engine - forward chaining in salience order; each fired rule
                       tightens or escalates the priority band
  * Explanation      - the list of fired rules is returned with every decision

Bands: P1 (24 h), P2 (72 h), P3 (7 days), P4 (15 days).
"""
import re
from dataclasses import dataclass, field
from typing import Callable, List
from .normalise import normalise

SLA_HOURS = {"P1": 24, "P2": 72, "P3": 168, "P4": 360}

# ------------------------------------------------------------------ fact lexicon
CUES = {
    "INJURY": ["जखमी", "घायल", "चावा", "चावला", "चावत", "काट लिया", "काटा", "हमला", "bite",
               "injur", "jakhmi", "chavla", "chavto", "chavat", "घसरून", "घसरतात", "slip होऊन",
               "अपघात झाला", "accident झाला", "हादसा हुआ"],
    "COVER": ["झाकण", "jhakan", "zakan", "ढक्कन", "slab नाही", "cover नाही", "manhole open", "चेंबर उघड"],
    "OPEN": ["उघड", "ughad", "खुला", "open", "नाही", "nahi", "तुटल", "tutl"],
    "CURRENT": ["करंट", "current", "shock", "शॉक"],
    "WIRE": ["तार", "वायर", "wire", "taar"],
    "DANGLING": ["लोंबक", "लटक", "lombkal", "latak", "तुटून", "tutun", "बाहेर", "खाली पडल"],
    "DP_OPEN": ["डीपी", "dp box", "डीपी बॉक्स"],
    "IMMINENT": ["कधीही पड", "kadhihi pad", "पडू शकत", "padu shak", "गिरने वाला", "गिर सकत", "कोसळ",
                 "koslnar", "पडेल", "padel", "पडण्याची भीती", "मुळासकट", "wall पडेल"],
    "COLLAPSED": ["भिंत पडली", "bhint padli", "दीवार गिर", "तुकडे पडत", "भिंत कोसळ"],
    "BLOCKING": ["वाहतूक बंद", "रास्ता बंद", "jau shakat nahi", "रस्त्यावर पडल", "सड़क पर गिर",
                 "rastyavar padle", "road वर", "rastyavar"],
    "TREE_FALL": ["पडल", "padle", "गिर गया", "fall"],
    "RABID": ["पिसाळ", "pisal", "पागल कुत्ता"],
    "OUTBREAK": ["डेंग्यू", "डेंगू", "dengue", "मलेरिया", "malaria", "आजारी पड", "aajari", "बीमार",
                 "sick", "rugn", "रुग्ण", "मरीज"],
    "HOME": ["घरात", "घर में", "gharat", "घरों में"],
    "SEWAGE": ["सांडपाणी", "sandpani", "सीवर", "sewage", "toilet", "गटार", "ड्रेनेज", "drainage", "पाणी"],
    "RISK": ["अपघात होऊ", "accident hou", "accident होऊ", "हादसा हो सकता", "हादसे का डर", "धोका", "dhoka",
             "खतरा", "खतरनाक", "धंस", "खचला", "barricad"],
    "DAMAGE": ["नुकसान", "damage"],
    "DRAIN_BLOCK": ["overflow", "तुंब", "tumbl", "जाम", "block", "chock"],
    "NUISANCE": ["वास ये", "दुर्गंधी", "बदबू", "vaas", "smell", "माश्या", "जाळ", "जलाया", "धुरा", "धूर हो", "धूर ये", "dhur",
                 "smoke", "सडलेल", "गढूळ", "gadhul", "गंदा पानी", "dirty water", "माती", "दूषित",
                 "पिण्यायोग्य नाही", "सांडपाणी रस्त्यावर", "sandpani rastyavar", "ghan pani", "घाण पाणी",
                 "गंदा पानी सड़क", "मेलेल", "मरा हुआ",
                 "मरी हुई", "dead", "melela", "शौच", "shauch"],
    "OUTAGE": ["पाणी येत नाही", "पाणीच आलेलं नाही", "पाणी आलेलं नाही", "pani yet nahi", "पानी नहीं आ",
               "supply बंद", "पुरवठा बंद", "purvatha band", "पाणी नव्हतं", "सप्लाई बंद"],
    "WASTAGE": ["फुटली", "futli", "burst", "फट गई", "वाया जा", "vaya ja", "बर्बाद"],
    "REQUEST": ["मागणी", "request", "छाटणी", "chhatni", "trimming", "निर्बीजीकरण", "नसबंदी", "nasbandi",
                "sterili", "बिल चुक", "बिल जास्त", "मीटरचं बिल", "bill", "segregation", "wet आणि dry", "वेगळा घेत", "झाडलोट", "फलक",
                "बॅनर", "banner", "flex", "भुंकतात", "लुकलुक", "दिवसाही चालू", "on असतात", "बसवण्याची",
                "बसवावेत", "लगवाइए", "navin street", "अर्ज", "रोपं", "रोपे", "निगा", "येण्याची वेळ",
                "पाण्याची वेळ"],
    "VULNERABLE": ["शाळ", "school", "स्कूल", "shal", "हॉस्पिटल", "hospital", "अस्पताल", "दवाखान"],
}

_NUMW = {"एक": 1, "दोन": 2, "दो": 2, "तीन": 3, "चार": 4, "पाच": 5, "पांच": 5, "सहा": 6, "छह": 6,
         "सात": 7, "आठ": 8, "नऊ": 9, "दहा": 10, "दस": 10, "पंधरा": 15, "पंद्रह": 15, "वीस": 20,
         "बीस": 20, "ek": 1, "don": 2, "teen": 3, "char": 4, "pach": 5}
_UNIT = [(r"(दिवस|दिन|divas|day)", 1), (r"(आठवड|हफ्त|हफ़्त|aathvad|week)", 7),
         (r"(महिन|महीन|mahin|month)", 30)]
_NUM_RE = r"(\d+|" + "|".join(sorted(_NUMW, key=len, reverse=True)) + r")"


def parse_duration_days(t: str) -> int:
    """Longest stated duration in days (0 if none). Deliberately simple: no negation handling."""
    best = 0
    for unit_re, mult in _UNIT:
        for m in re.finditer(_NUM_RE + r"\s*" + unit_re, t):
            n = m.group(1)
            n = int(n) if n.isdigit() else _NUMW[n]
            best = max(best, n * mult)
    if re.search(r"आठवडाभर|हफ्ते भर", t): best = max(best, 7)
    if re.search(r"महिनाभर|महिनोन्|महीनों|mahina zala|month झाला|महिना झाला", t): best = max(best, 30 if "महिनोन्" not in t else 60)
    if re.search(r"कई दिनों|बरेच दिवस|kiti divas|many days", t): best = max(best, 3)
    return best


def extract_facts(text: str, dept: str, cluster_size: int = 1) -> dict:
    t = normalise(text)
    has = {k: any(c.lower() in t for c in v) for k, v in CUES.items()}
    has["DEPT"] = dept
    has["DAYS"] = parse_duration_days(t)
    has["CLUSTER"] = cluster_size
    return has


# ------------------------------------------------------------------ rule base
@dataclass
class Rule:
    rid: str
    text: str                                  # human-readable IF ... THEN ...
    cond: Callable[[dict], bool]
    kind: str                                  # 'set' (cap at band) | 'escalate' (one band up) | 'relax'
    band: int = 0
    salience: int = 0


RULES: List[Rule] = [
    # ---- life-safety overrides (salience 100) -> P1
    Rule("R01", "IF injury/bite/accident has occurred THEN P1", lambda f: f["INJURY"], "set", 1, 100),
    Rule("R02", "IF dept=DRAIN AND cover missing/broken/open THEN P1 (open manhole)",
         lambda f: f["DEPT"] == "DRAIN" and f["COVER"] and f["OPEN"], "set", 1, 100),
    Rule("R03", "IF dept=ELEC AND (live current OR dangling wire OR open DP box) THEN P1",
         lambda f: f["DEPT"] == "ELEC" and (f["CURRENT"] or (f["WIRE"] and f["DANGLING"]) or
                                            (f["DP_OPEN"] and f["OPEN"])), "set", 1, 100),
    Rule("R04", "IF dept in {ELEC,TREE,BUILD,ENCROACH} AND collapse imminent/occurred THEN P1",
         lambda f: f["DEPT"] in ("ELEC", "TREE", "BUILD", "ENCROACH") and (f["IMMINENT"] or f["COLLAPSED"]),
         "set", 1, 100),
    Rule("R05", "IF dept=TREE AND (tree fallen AND road blocked OR branch dangling) THEN P1",
         lambda f: f["DEPT"] == "TREE" and ((f["TREE_FALL"] and f["BLOCKING"]) or f["DANGLING"]), "set", 1, 100),
    Rule("R06", "IF disease outbreak / people fallen ill THEN P1", lambda f: f["OUTBREAK"], "set", 1, 100),
    Rule("R07", "IF dept=DRAIN AND sewage entering a dwelling THEN P1",
         lambda f: f["DEPT"] == "DRAIN" and f["HOME"] and f["SEWAGE"], "set", 1, 100),
    Rule("R08", "IF dept=VET AND rabid animal THEN P1", lambda f: f["DEPT"] == "VET" and f["RABID"], "set", 1, 100),
    # ---- public-health / hazard-risk rules (salience 50) -> at least P2
    Rule("R10", "IF explicit risk of accident/damage THEN at least P2", lambda f: f["RISK"], "set", 2, 50),
    Rule("R11", "IF public-health nuisance (smell, burning, sewage, carcass, contamination) THEN at least P2",
         lambda f: f["NUISANCE"], "set", 2, 50),
    Rule("R12", "IF dept=WATER AND supply outage >= 2 days THEN at least P2",
         lambda f: f["DEPT"] == "WATER" and f["OUTAGE"] and f["DAYS"] >= 2, "set", 2, 50),
    Rule("R13", "IF dept=SWM AND garbage uncollected >= 3 days THEN at least P2",
         lambda f: f["DEPT"] == "SWM" and f["DAYS"] >= 3, "set", 2, 50),
    Rule("R15", "IF dept=DRAIN AND drain blocked/overflowing THEN at least P2",
         lambda f: f["DEPT"] == "DRAIN" and f["DRAIN_BLOCK"], "set", 2, 50),
    Rule("R16", "IF dept=TREE AND property damaged by fallen tree THEN at least P2",
         lambda f: f["DEPT"] == "TREE" and f["DAMAGE"], "set", 2, 50),
    Rule("R14", "IF dept=WATER AND pipeline burst / major wastage THEN at least P2",
         lambda f: f["DEPT"] == "WATER" and f["WASTAGE"], "set", 2, 50),
    # ---- default and service requests (salience 10)
    Rule("R20", "IF complaint is a service request / cosmetic AND no hazard fired THEN P4",
         lambda f: f["REQUEST"], "relax", 4, 10),
    # ---- escalation modifiers (salience 0), applied after the band is fixed
    Rule("R30", "IF near school/hospital THEN escalate one band", lambda f: f["VULNERABLE"], "escalate", 0, 0),
    Rule("R31", "IF problem persists >= 14 days THEN escalate one band", lambda f: f["DAYS"] >= 14, "escalate", 0, 0),
    Rule("R32", "IF >= 3 citizens reported the same defect (duplicate cluster) THEN escalate one band",
         lambda f: f["CLUSTER"] >= 3, "escalate", 0, 0),
]


def infer(text: str, dept: str, cluster_size: int = 1, use_escalation=True, use_recurrence=True):
    """Forward-chain over RULES. Returns dict(band, sla_hours, fired, facts)."""
    f = extract_facts(text, dept, cluster_size)
    band, fired = 3, []                                   # default P3
    hazard_fired = False
    for r in sorted(RULES, key=lambda r: -r.salience):
        if r.kind == "escalate" and not use_escalation: continue
        if r.rid == "R32" and not use_recurrence: continue
        if not r.cond(f): continue
        if r.kind == "set":
            if r.band < band:
                band = r.band
            hazard_fired = True
            fired.append(r.rid)
        elif r.kind == "relax":
            if not hazard_fired:
                band = 4; fired.append(r.rid)
        elif r.kind == "escalate":
            if band > 1:
                band -= 1
            fired.append(r.rid)
    p = f"P{band}"
    return dict(band=p, sla_hours=SLA_HOURS[p], fired=fired,
                explanation=[next(r.text for r in RULES if r.rid == x) for x in fired],
                facts={k: v for k, v in f.items() if v})
