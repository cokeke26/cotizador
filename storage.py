from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

# Modo de almacenamiento:
# - LOCAL: SQLite (desarrollo)
# - CLOUD: PostgreSQL (producción)
STORAGE_MODE = os.getenv("STORAGE_MODE", "LOCAL")

# ---------- SQLITE (LOCAL) ----------
SQLITE_PATH = Path("outputs") / "quotes.db"

def _sqlite_connect() -> sqlite3.Connection:
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(SQLITE_PATH.as_posix(), timeout=10)
    con.execute("PRAGMA journal_mode=WAL;")
    return con

def sqlite_init() -> None:
    con = _sqlite_connect()
    try:
        con.execute("""
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL
        );
        """)
        con.commit()
    finally:
        con.close()

def sqlite_next_quote_number(width: int = 4) -> str:
    con = _sqlite_connect()
    try:
        cur = con.execute(
            "INSERT INTO quotes (created_at) VALUES (?)",
            (datetime.utcnow().isoformat(),)
        )
        con.commit()
        return str(cur.lastrowid).zfill(width)
    finally:
        con.close()

# ---------- POSTGRES (CLOUD – placeholder) ----------
def postgres_next_quote_number(width: int = 4) -> str:
    """
    Placeholder para cuando migres a PostgreSQL.
    """
    raise NotImplementedError("PostgreSQL no configurado aún")

# ---------- API UNIFICADA ----------
def init_storage() -> None:
    if STORAGE_MODE == "LOCAL":
        sqlite_init()
    else:
        pass  # Postgres init cuando corresponda

def get_next_quote_number(width: int = 4) -> str:
    if STORAGE_MODE == "LOCAL":
        return sqlite_next_quote_number(width)
    return postgres_next_quote_number(width)
