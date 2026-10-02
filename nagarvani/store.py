"""SQLite persistence for tickets and officer corrections. Timestamps are stored in UTC (ISO 8601)."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_utc TEXT NOT NULL,
    updated_utc TEXT NOT NULL,
    channel TEXT NOT NULL,              -- typed | upload | microphone | seed
    language TEXT,                      -- mr | hi (ASR language toggle)
    audio_path TEXT,
    raw_transcript TEXT,                -- what ASR produced (NULL for typed)
    text TEXT NOT NULL,                 -- what the citizen finally submitted
    asr_json TEXT,
    ward_hint TEXT,
    status TEXT NOT NULL,               -- received | auto_routed | review | merged | resolved
    department TEXT,
    confidence REAL,
    ward TEXT,
    priority TEXT,
    deadline_utc TEXT,
    parent_id INTEGER REFERENCES tickets(id),
    report_count INTEGER NOT NULL DEFAULT 1,
    dup_candidate_id INTEGER,
    dup_score REAL,
    dup_pending INTEGER NOT NULL DEFAULT 0,
    transcript_uncertain INTEGER NOT NULL DEFAULT 0,
    review_reason TEXT,
    failure TEXT,
    masked_text TEXT,
    trace_json TEXT,
    submission_key TEXT UNIQUE,
    confirmed INTEGER NOT NULL DEFAULT 0,
    resolved_utc TEXT
);
CREATE INDEX IF NOT EXISTS ix_block ON tickets(ward, department, status);
CREATE TABLE IF NOT EXISTS corrections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id),
    created_utc TEXT NOT NULL,
    field TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    text TEXT,
    note TEXT
);
"""

OPEN_STATUSES = ("auto_routed", "review")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None) -> str | None:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds") if dt else None


def parse(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s) if s else None


class Store:
    def __init__(self, path: Path | str | None = None):
        self.path = str(path or (config.INSTANCE / "nagarvani.sqlite3"))
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # ---- writes ------------------------------------------------------------------------
    def create(self, **fields) -> int:
        now = iso(fields.pop("now", None) or utcnow())
        fields.setdefault("created_utc", now)
        fields.setdefault("updated_utc", now)
        fields.setdefault("status", "received")
        cols = ", ".join(fields)
        q = ", ".join("?" for _ in fields)
        cur = self.conn.execute(f"INSERT INTO tickets ({cols}) VALUES ({q})", list(fields.values()))
        self.conn.commit()
        return cur.lastrowid

    def update(self, ticket_id: int, **fields):
        fields["updated_utc"] = iso(utcnow())
        sets = ", ".join(f"{k} = ?" for k in fields)
        self.conn.execute(f"UPDATE tickets SET {sets} WHERE id = ?", [*fields.values(), ticket_id])
        self.conn.commit()

    def add_correction(self, ticket_id, field, old, new, text, note=""):
        self.conn.execute("INSERT INTO corrections (ticket_id, created_utc, field, old_value, new_value, text, note)"
                          " VALUES (?, ?, ?, ?, ?, ?, ?)", (ticket_id, iso(utcnow()), field, old, new, text, note))
        self.conn.commit()

    # ---- reads -------------------------------------------------------------------------
    def get(self, ticket_id: int):
        return self.conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()

    def by_submission_key(self, key: str):
        return self.conn.execute("SELECT * FROM tickets WHERE submission_key = ?", (key,)).fetchone()

    def open_in_block(self, ward: str, department: str, exclude_id: int | None = None):
        rows = self.conn.execute(
            f"SELECT id, masked_text, report_count FROM tickets WHERE ward = ? AND department = ? AND parent_id IS NULL"
            f" AND status IN ({','.join('?' * len(OPEN_STATUSES))}) AND id != ? AND masked_text IS NOT NULL",
            (ward, department, *OPEN_STATUSES, exclude_id or -1)).fetchall()
        return [(r["id"], r["masked_text"], r["report_count"]) for r in rows]

    def children(self, ticket_id: int):
        return self.conn.execute("SELECT * FROM tickets WHERE parent_id = ? ORDER BY id", (ticket_id,)).fetchall()

    def tickets(self, where: str = "1=1", params=()):
        return self.conn.execute(f"SELECT * FROM tickets WHERE {where}", params).fetchall()

    def corrections(self):
        return self.conn.execute("SELECT * FROM corrections ORDER BY id").fetchall()

    def ok(self) -> bool:
        try:
            self.conn.execute("SELECT 1").fetchone()
            return True
        except sqlite3.Error:
            return False


def trace_dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)
