"""
Almacenamiento local (SQLite) para el MVP.

Guarda: ajustes del usuario, reportes, eventos (notificaciones) y suscripciones
de notificaciones push. Es local y simple; para la nube se migrará a DynamoDB o
Postgres sin cambiar el resto del código (todo pasa por estas funciones).
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "octotraiding.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    symbol TEXT NOT NULL DEFAULT 'BTCUSDT',
    interval TEXT NOT NULL DEFAULT '1h',
    capital REAL NOT NULL DEFAULT 1000,
    risk_pct REAL NOT NULL DEFAULT 0.01,
    quiet_start INTEGER NOT NULL DEFAULT 23,
    quiet_end INTEGER NOT NULL DEFAULT 7,
    notify_strong_only INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    symbol TEXT NOT NULL,
    price REAL, signal TEXT, score REAL, regime TEXT, daily_trend TEXT,
    entry REAL, stop REAL, target REAL, rr REAL, position_pct REAL,
    narrative TEXT, created_at TEXT,
    UNIQUE(symbol, ts)
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    type TEXT NOT NULL,
    message TEXT,
    data TEXT,
    notified INTEGER DEFAULT 0,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint TEXT UNIQUE NOT NULL,
    p256dh TEXT NOT NULL,
    auth TEXT NOT NULL,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    position TEXT,
    last_processed TEXT
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(_SCHEMA)
        conn.execute(
            "INSERT OR IGNORE INTO settings (id, updated_at) VALUES (1, ?)", (_now(),)
        )
        conn.execute(
            "INSERT OR IGNORE INTO state (id, position, last_processed) VALUES (1, NULL, NULL)"
        )


# ---------------------------------------------------------------------------
# Ajustes
# ---------------------------------------------------------------------------
def get_settings() -> dict[str, Any]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM settings WHERE id = 1").fetchone()
    return dict(row) if row else {}


def update_settings(**fields: Any) -> dict[str, Any]:
    allowed = {
        "symbol", "interval", "capital", "risk_pct",
        "quiet_start", "quiet_end", "notify_strong_only",
    }
    fields = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if fields:
        cols = ", ".join(f"{k} = ?" for k in fields)
        with _connect() as conn:
            conn.execute(
                f"UPDATE settings SET {cols}, updated_at = ? WHERE id = 1",
                (*fields.values(), _now()),
            )
    return get_settings()


# ---------------------------------------------------------------------------
# Estado de la operación (posición abierta + última vela procesada)
# ---------------------------------------------------------------------------
def get_state() -> dict[str, Any]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM state WHERE id = 1").fetchone()
    if not row:
        return {"position": None, "last_processed": None}
    return {
        "position": json.loads(row["position"]) if row["position"] else None,
        "last_processed": row["last_processed"],
    }


def save_state(position: dict | None, last_processed: str | None) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE state SET position = ?, last_processed = ? WHERE id = 1",
            (json.dumps(position) if position else None, last_processed),
        )


# ---------------------------------------------------------------------------
# Reportes
# ---------------------------------------------------------------------------
def add_report(report: dict[str, Any]) -> None:
    with _connect() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO reports
               (ts, symbol, price, signal, score, regime, daily_trend,
                entry, stop, target, rr, position_pct, narrative, created_at)
               VALUES (:ts, :symbol, :price, :signal, :score, :regime, :daily_trend,
                       :entry, :stop, :target, :rr, :position_pct, :narrative, :created_at)""",
            {**report, "created_at": _now()},
        )


def recent_reports(limit: int = 48) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM reports ORDER BY ts DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def latest_report() -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM reports ORDER BY ts DESC LIMIT 1").fetchone()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Eventos (notificaciones)
# ---------------------------------------------------------------------------
def add_event(ts: str, type_: str, message: str, data: dict | None = None) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO events (ts, type, message, data, created_at) VALUES (?, ?, ?, ?, ?)",
            (ts, type_, message, json.dumps(data) if data else None, _now()),
        )
        return int(cur.lastrowid)


def recent_events(limit: int = 50) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Suscripciones de push
# ---------------------------------------------------------------------------
def add_subscription(endpoint: str, p256dh: str, auth: str) -> None:
    with _connect() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO subscriptions (endpoint, p256dh, auth, created_at)
               VALUES (?, ?, ?, ?)""",
            (endpoint, p256dh, auth, _now()),
        )


def list_subscriptions() -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM subscriptions").fetchall()
    return [dict(r) for r in rows]


def remove_subscription(endpoint: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM subscriptions WHERE endpoint = ?", (endpoint,))
