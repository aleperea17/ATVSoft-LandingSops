import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "sops_landing.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Las únicas claves que acepta la landing. Se escriben en mayúsculas porque
# la validación normaliza a mayúsculas antes de comparar (el visitante puede
# escribirlas como quiera). Esta lista manda: en cada arranque se dan de alta
# las que estén acá y se desactiva cualquier otra que haya quedado en la base.
ACCESS_CODES = ("VIRAL", "HAMBURGUESA", "SPOTIFY", "ONBOARDING")


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
        add_missing_columns(conn)
        sync_codes(conn)
        conn.commit()


def add_missing_columns(conn) -> None:
    """Agrega columnas nuevas sin tocar los leads viejos.

    Las preguntas del formulario cambiaron: 'empresa_coaching' y
    'efectivo_mensual' ya no se preguntan, pero se dejan en la tabla para no
    perder lo que respondieron los leads anteriores.
    """
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(leads)")}
    for column in ("atrae_clientes", "perfil", "cuello_botella", "estado"):
        if column not in existing:
            conn.execute(
                f"ALTER TABLE leads ADD COLUMN {column} TEXT NOT NULL DEFAULT ''"
            )


def sync_codes(conn) -> None:
    """Deja activas exactamente las claves de ACCESS_CODES y ninguna más.

    No borra nada: las claves viejas quedan en la tabla con active = 0, así se
    conserva su times_used y el historial de qué lead usó cuál.
    """
    for code in ACCESS_CODES:
        conn.execute("INSERT OR IGNORE INTO codes (code, active) VALUES (?, 1)", (code,))
        conn.execute("UPDATE codes SET active = 1 WHERE code = ?", (code,))

    placeholders = ",".join("?" for _ in ACCESS_CODES)
    conn.execute(
        f"UPDATE codes SET active = 0 WHERE code NOT IN ({placeholders})", ACCESS_CODES
    )


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
