"""M7 output - SQLite ticket store and per-ward CSV queue export."""
import csv, os, sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at    TEXT NOT NULL,
    channel       TEXT,
    raw_text      TEXT NOT NULL,
    norm_text     TEXT NOT NULL,
    dept          TEXT, dept_conf REAL, top3 TEXT,
    locality      TEXT, ward TEXT, ward_status TEXT,
    priority      TEXT, sla_due TEXT, rules_fired TEXT,
    cluster_id    INTEGER, dup_decision TEXT, dup_score REAL,
    route_status  TEXT NOT NULL,            -- AUTO_ROUTED | NODAL_REVIEW
    status        TEXT NOT NULL DEFAULT 'OPEN'
);
CREATE INDEX IF NOT EXISTS ix_ward_dept ON tickets(ward, dept, status);
"""


class TicketStore:
    def __init__(self, path):
        self.path = path
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def insert(self, rec: dict) -> int:
        cols = ",".join(rec); q = ",".join("?" * len(rec))
        cur = self.db.execute(f"INSERT INTO tickets ({cols}) VALUES ({q})", list(rec.values()))
        tid = cur.lastrowid
        if rec.get("cluster_id") is None:
            self.db.execute("UPDATE tickets SET cluster_id=? WHERE id=?", (tid, tid))
        self.db.commit()
        return tid

    def open_tickets(self, ward=None, dept=None):
        q, a = "SELECT * FROM tickets WHERE status='OPEN'", []
        if ward: q += " AND ward=?"; a.append(ward)
        if dept: q += " AND dept=?"; a.append(dept)
        return [dict(r) for r in self.db.execute(q, a)]

    def cluster_size(self, cluster_id):
        return self.db.execute("SELECT COUNT(*) FROM tickets WHERE cluster_id=?", (cluster_id,)).fetchone()[0]

    def all(self):
        return [dict(r) for r in self.db.execute("SELECT * FROM tickets ORDER BY id")]

    def export_ward_queues(self, out_dir):
        """One CSV per ward office, ordered by priority then SLA deadline. NODAL_REVIEW rows go to
        nodal_review.csv. Returns list of files written."""
        os.makedirs(out_dir, exist_ok=True)
        rows = self.all()
        cols = ["id", "created_at", "priority", "sla_due", "dept", "dept_conf", "locality", "ward",
                "cluster_id", "dup_decision", "route_status", "raw_text"]
        groups = {}
        for r in rows:
            key = r["ward"] if r["route_status"] == "AUTO_ROUTED" else "nodal_review"
            groups.setdefault(key, []).append(r)
        files = []
        for key, rs in groups.items():
            rs.sort(key=lambda r: (r["priority"], r["sla_due"]))
            fn = os.path.join(out_dir, f"queue_{key}.csv")
            with open(fn, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
                w.writeheader(); w.writerows(rs)
            files.append(fn)
        return files
