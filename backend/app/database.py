import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "sops_landing.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL DEFAULT '',
                nombre TEXT NOT NULL,
                telefono TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL,
                instagram TEXT NOT NULL DEFAULT '',
                ganando_dinero TEXT NOT NULL DEFAULT '',
                empresa_coaching TEXT NOT NULL DEFAULT '',
                efectivo_mensual TEXT NOT NULL DEFAULT '',
                codigo_usado TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                active INTEGER NOT NULL DEFAULT 1,
                times_used INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        existing = conn.execute("SELECT COUNT(*) FROM codes").fetchone()[0]
        if existing == 0:
            conn.execute(
                "INSERT INTO codes (code, active) VALUES (?, 1)", ("ATV-5051",)
            )
        conn.commit()


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
