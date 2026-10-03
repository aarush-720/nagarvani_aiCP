"""NagarVani nodal-officer console (Flask). Run:  python app/app.py  ->  http://127.0.0.1:5000"""
import json, os, sys
from flask import Flask, request, render_template, redirect, url_for, send_file
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from nagarvani.pipeline import Triage
from nagarvani.classifier import DEPARTMENTS

app = Flask(__name__)
T = Triage(db_path=os.environ.get("NAGARVANI_DB", os.path.join(ROOT, "results", "console.db")))
PRIO_COL = {"P1": "#b3261e", "P2": "#c86b00", "P3": "#2a6f97", "P4": "#5f6b73"}


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST" and request.form.get("text", "").strip():
        result = T.triage(request.form["text"].strip(), channel=request.form.get("channel", "web"))
    return render_template("index.html", r=result, depts=DEPARTMENTS, pc=PRIO_COL)


@app.route("/queues")
def queues():
    rows = T.store.all()
    wards = {}
    for r in rows:
        key = r["ward"] if r["route_status"] == "AUTO_ROUTED" else "NODAL"
        wards.setdefault(key, []).append(r)
    for v in wards.values():
        v.sort(key=lambda r: (r["priority"], r["sla_due"]))
    names = dict(T.resolver.wards, NODAL="Nodal officer review")
    return render_template("queues.html", wards=wards, names=names, depts=DEPARTMENTS, pc=PRIO_COL, n=len(rows))


@app.route("/export")
def export():
    files = T.store.export_ward_queues(os.path.join(ROOT, "results", "console_queues"))
    return {"written": [os.path.basename(f) for f in files]}


if __name__ == "__main__":
    app.run(debug=False, port=int(os.environ.get("PORT", 5000)))
