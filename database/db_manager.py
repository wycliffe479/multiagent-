"""
database/db_manager.py
SQLite helper for storing and retrieving past incidents.
Auto-creates the database and seeds sample data on first run.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "incidents.db")


# ---------------------------------------------------------------------------
# Schema setup
# ---------------------------------------------------------------------------

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables and seed sample data if the DB doesn't exist yet."""
    conn = _get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id TEXT    NOT NULL,
            server_name TEXT,
            error_type  TEXT,
            severity    TEXT,
            location    TEXT,
            fix_applied TEXT,
            resolved    INTEGER DEFAULT 1,
            created_at  TEXT    DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS solutions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            error_type   TEXT UNIQUE NOT NULL,
            fix          TEXT NOT NULL,
            success_rate REAL DEFAULT 0.9,
            notes        TEXT
        )
    """)

    # Seed only if tables are empty
    c.execute("SELECT COUNT(*) FROM incidents")
    if c.fetchone()[0] == 0:
        incidents = [
            ("INC-001", "server-7",  "connection_refused", "critical", "us-east-1",  "restart_server"),
            ("INC-002", "server-12", "high_cpu",           "warning",  "eu-west-1",  "scale_up"),
            ("INC-003", "server-3",  "memory_leak",        "critical", "us-west-2",  "restart_pods"),
            ("INC-004", "server-7",  "connection_refused", "critical", "us-east-1",  "restart_server"),
            ("INC-005", "server-9",  "disk_full",          "warning",  "ap-south-1", "clear_cache"),
            ("INC-006", "server-15", "deployment_failed",  "critical", "eu-central", "rollback"),
            ("INC-007", "server-2",  "high_cpu",           "warning",  "us-east-2",  "scale_up"),
            ("INC-008", "server-7",  "connection_refused", "critical", "us-east-1",  "restart_server"),
        ]
        c.executemany(
            "INSERT INTO incidents (incident_id, server_name, error_type, severity, location, fix_applied) VALUES (?,?,?,?,?,?)",
            incidents,
        )

    c.execute("SELECT COUNT(*) FROM solutions")
    if c.fetchone()[0] == 0:
        solutions = [
            ("connection_refused", "restart_server", 0.95, "Restart the service/server"),
            ("high_cpu",           "scale_up",        0.88, "Scale horizontally"),
            ("memory_leak",        "restart_pods",    0.90, "Restart affected pods"),
            ("disk_full",          "clear_cache",     0.85, "Clear cache and temp files"),
            ("deployment_failed",  "rollback",        0.92, "Rollback to last stable version"),
            ("down",               "restart_server",  0.87, "Restart the server"),
            ("oom",                "restart_pods",    0.89, "Restart pods to free memory"),
        ]
        c.executemany(
            "INSERT INTO solutions (error_type, fix, success_rate, notes) VALUES (?,?,?,?)",
            solutions,
        )

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def search_past_incidents(server_name: str, error_type: str) -> list[dict]:
    """Return incidents that match server_name OR error_type."""
    init_db()
    conn = _get_conn()
    c = conn.cursor()
    c.execute(
        """
        SELECT * FROM incidents
        WHERE server_name = ? OR error_type = ?
        ORDER BY created_at DESC
        LIMIT 5
        """,
        (server_name, error_type),
    )
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_solution_for_error(error_type: str) -> dict | None:
    """Return the known solution for an error type, or None."""
    init_db()
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM solutions WHERE error_type = ?", (error_type,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def add_incident(incident_id: str, server_name: str, error_type: str,
                 severity: str, location: str, fix_applied: str):
    """Persist a newly resolved incident so future agents can learn from it."""
    init_db()
    conn = _get_conn()
    conn.execute(
        """
        INSERT INTO incidents (incident_id, server_name, error_type, severity, location, fix_applied)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (incident_id, server_name, error_type, severity, location, fix_applied),
    )
    conn.commit()
    conn.close()
