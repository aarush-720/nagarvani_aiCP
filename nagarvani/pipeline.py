"""End-to-end triage pipeline (Algorithm 1 in the report)."""
import csv, json, os, pickle
from datetime import datetime, timedelta
from .normalise import normalise
from .location import WardResolver
from .classifier import char_word_lr, DEPARTMENTS
from .severity import infer
from .dedup import DuplicateDetector
from .store import TicketStore

ROOT = os.path.join(os.path.dirname(__file__), "..")
MODEL_PATH = os.path.join(ROOT, "results", "model.pkl")


def load_tsv(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8"), delimiter="\t"))
    for r in rows:
        if r["lang"] == "rom": r["lang"] = "mr-rom"
    return rows


class Triage:
    def __init__(self, db_path=":memory:", tau=0.50, model=None):
        self.tau = tau
        self.resolver = WardResolver()
        train = load_tsv(os.path.join(ROOT, "corpus", "train_template.tsv"))
        if model is None:
            if os.path.exists(MODEL_PATH):
                model = pickle.load(open(MODEL_PATH, "rb"))
            else:
                model = char_word_lr().fit([r["text"] for r in train], [r["dept"] for r in train])
        self.model = model
        self.dedup = DuplicateDetector(self.resolver).fit([r["text"] for r in train])
        self.store = TicketStore(db_path)

    def triage(self, text, channel="text", now=None, persist=True):
        now = now or datetime.now()
        norm = normalise(text)
        proba = self.model.predict_proba([text])[0]
        classes = list(self.model.classes_)
        order = proba.argsort()[::-1]
        dept, conf = classes[order[0]], float(proba[order[0]])
        top3 = [(classes[i], round(float(proba[i]), 3)) for i in order[:3]]
        loc = self.resolver.resolve(text)

        decision, dup_id, dup_score = "new", None, 0.0
        cluster_id, csize = None, 1
        if loc["ward"]:
            decision, dup_id, dup_score = self.dedup.decide(
                text, dept, loc["ward"], self.store.open_tickets(loc["ward"], dept))
            if decision == "merge":
                parent = next(t for t in self.store.open_tickets(loc["ward"], dept) if t["id"] == dup_id)
                cluster_id = parent["cluster_id"]
                csize = self.store.cluster_size(cluster_id) + 1

        sev = infer(text, dept, cluster_size=csize)
        route = "AUTO_ROUTED" if (conf >= self.tau and loc["status"] == "resolved") else "NODAL_REVIEW"
        reasons = []
        if conf < self.tau: reasons.append(f"department confidence {conf:.2f} < τ={self.tau}")
        if loc["status"] != "resolved": reasons.append(f"location {loc['status']}")
        rec = dict(created_at=now.isoformat(timespec="seconds"), channel=channel, raw_text=text,
                   norm_text=norm, dept=dept, dept_conf=round(conf, 4), top3=json.dumps(top3),
                   locality=loc["locality"], ward=loc["ward"], ward_status=loc["status"],
                   priority=sev["band"],
                   sla_due=(now + timedelta(hours=sev["sla_hours"])).isoformat(timespec="minutes"),
                   rules_fired=",".join(sev["fired"]), cluster_id=cluster_id,
                   dup_decision=decision, dup_score=round(dup_score, 3), route_status=route)
        tid = self.store.insert(rec) if persist else None
        return dict(rec, id=tid, dept_name=DEPARTMENTS[dept], ward_name=loc["ward_name"],
                    explanation=sev["explanation"], review_reasons=reasons, cluster_size=csize,
                    top3=top3)
