"""SQLite persistence: assessments, change history, AI analysis."""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from controls import CONTROLS
from risk import risk_score, risk_level

DB_PATH = os.getenv("GRC_DB", str(Path(__file__).parent / "grc.db"))


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _now():
    return datetime.now().isoformat(timespec="seconds")


def init_db():
    with _conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS assessments (
            control_id TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'NOT ASSESSED',
            evidence TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT 'manual',
            updated_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            control_id TEXT, status TEXT, evidence TEXT, source TEXT, timestamp TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS ai_findings (
            control_id TEXT PRIMARY KEY, finding TEXT, recommendation TEXT)""")
        c.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
        _migrate_au11(c)
        for ctl in CONTROLS:
            c.execute("INSERT OR IGNORE INTO assessments (control_id) VALUES (?)", (ctl["id"],))


def _migrate_au11(c):
    """AU-11 was relabelled AU-4 (Audit Log Storage Capacity). Carry saved results over."""
    if not c.execute("SELECT 1 FROM assessments WHERE control_id='AU-11'").fetchone():
        return
    new = c.execute("SELECT status FROM assessments WHERE control_id='AU-4'").fetchone()
    if new is None or new["status"] == "NOT ASSESSED":
        c.execute("DELETE FROM assessments WHERE control_id='AU-4'")
        c.execute("UPDATE assessments SET control_id='AU-4' WHERE control_id='AU-11'")
    else:
        c.execute("DELETE FROM assessments WHERE control_id='AU-11'")
    c.execute("UPDATE history SET control_id='AU-4' WHERE control_id='AU-11'")
    c.execute("DELETE FROM ai_findings WHERE control_id='AU-11'")


def save_assessment(control_id, status, evidence, source="manual"):
    ts = _now()
    with _conn() as c:
        c.execute("UPDATE assessments SET status=?, evidence=?, source=?, updated_at=? WHERE control_id=?",
                  (status, evidence, source, ts, control_id))
        c.execute("INSERT INTO history (control_id, status, evidence, source, timestamp) VALUES (?,?,?,?,?)",
                  (control_id, status, evidence, source, ts))


def get_assessments():
    """Catalog data merged with saved results and computed risk."""
    with _conn() as c:
        saved = {r["control_id"]: dict(r) for r in c.execute("SELECT * FROM assessments")}
    rows = []
    for ctl in CONTROLS:
        s = saved[ctl["id"]]
        score = risk_score(s["status"], ctl["likelihood"], ctl["impact"])
        rows.append({**ctl, "status": s["status"], "evidence": s["evidence"], "source": s["source"],
                     "updated_at": s["updated_at"], "risk_score": score, "risk_level": risk_level(score)})
    return rows


def get_history(limit=300):
    with _conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT timestamp, control_id, status, source, evidence FROM history ORDER BY id DESC LIMIT ?", (limit,))]


def save_ai_analysis(analysis):
    """analysis = {summary, model, findings: {control_id: {finding, recommendation}}}"""
    with _conn() as c:
        c.execute("DELETE FROM ai_findings")
        for cid, f in analysis["findings"].items():
            c.execute("INSERT INTO ai_findings VALUES (?,?,?)", (cid, f["finding"], f["recommendation"]))
        for k, v in (("ai_summary", analysis["summary"]), ("ai_model", analysis["model"]), ("ai_time", _now())):
            c.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (k, v))


def get_ai_analysis():
    with _conn() as c:
        meta = {r["key"]: r["value"] for r in c.execute("SELECT * FROM meta")}
        findings = {r["control_id"]: {"finding": r["finding"], "recommendation": r["recommendation"]}
                    for r in c.execute("SELECT * FROM ai_findings")}
    if "ai_summary" not in meta:
        return None
    return {"summary": meta["ai_summary"], "model": meta.get("ai_model", ""),
            "generated_at": meta.get("ai_time", ""), "findings": findings}


def reset_all():
    with _conn() as c:
        c.execute("UPDATE assessments SET status='NOT ASSESSED', evidence='', source='manual', updated_at=NULL")
        c.execute("DELETE FROM ai_findings")
        c.execute("DELETE FROM meta")
