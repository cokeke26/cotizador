from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Sequence
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

import psycopg
import streamlit as st

from utils import QuoteItem


def _get_database_url() -> str:
    """
    Lee DATABASE_URL desde st.secrets.
    Debe ser una URL tipo:
    postgresql://postgres:<PASSWORD>@...:5432/postgres
    """
    url = st.secrets.get("DATABASE_URL")
    if not url:
        raise RuntimeError("Falta DATABASE_URL en st.secrets")
    return str(url).strip()


def _with_sslmode_require(url: str) -> str:
    """
    Supabase requiere SSL. Si la URL no trae sslmode, se lo agregamos.
    """
    parsed = urlparse(url)
    q = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if "sslmode" not in q:
        q["sslmode"] = "require"
    new_query = urlencode(q)
    return urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment)
    )


def get_conn() -> psycopg.Connection:
    """
    Abre conexión a PostgreSQL (Supabase) con SSL.
    """
    dsn = _with_sslmode_require(_get_database_url())
    return psycopg.connect(dsn)


def next_quote_number(year: int) -> tuple[int, str]:
    """
    Obtiene el siguiente correlativo del año de forma atómica (sin duplicados).
    Retorna (seq, "YYYY-0001").
    """
    sql = """
    insert into quote_counters(year, last_seq)
    values (%s, 1)
    on conflict (year)
    do update set last_seq = quote_counters.last_seq + 1
    returning last_seq;
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (year,))
            row = cur.fetchone()
            if not row:
                raise RuntimeError("No se pudo obtener el correlativo (fetchone vacío).")
            seq = int(row[0])

        # psycopg v3: si no hay error, al salir del with se confirma automáticamente.
        # Igual lo dejamos explícito para que sea claro:
        conn.commit()

    quote_number = f"{year}-{seq:04d}"
    return seq, quote_number


def insert_quote(
    *,
    year: int,
    seq: int,
    quote_number: str,
    issue_date: date,
    brand_name: str,
    brand_email: str,
    brand_phone: str,
    client_name: str,
    client_email: str,
    client_company: str,
    discount_pct: Decimal,
    notes: str,
    validity_days: int,
    items: Sequence[QuoteItem],
) -> int:
    """
    Inserta cotización + items en una transacción.
    Retorna quote_id.
    """
    if not items:
        raise ValueError("No puedes guardar una cotización sin ítems.")

    with get_conn() as conn:
        with conn.cursor() as cur:
            # 1) Insert cabecera
            cur.execute(
                """
                insert into quotes(
                  year, seq, quote_number, issue_date,
                  brand_name, brand_email, brand_phone,
                  client_name, client_email, client_company,
                  discount_pct, notes, validity_days
                )
                values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                returning id;
                """,
                (
                    year,
                    seq,
                    quote_number,
                    issue_date,
                    brand_name,
                    brand_email,
                    brand_phone,
                    client_name,
                    client_email,
                    client_company,
                    discount_pct,
                    notes,
                    validity_days,
                ),
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError("No se pudo insertar la cotización (fetchone vacío).")
            quote_id = int(row[0])

            # 2) Insert items (executemany)
            rows = [(quote_id, it.description, it.qty, it.unit_price) for it in items]
            cur.executemany(
                """
                insert into quote_items(quote_id, description, qty, unit_price)
                values (%s, %s, %s, %s)
                """,
                rows,
            )

        conn.commit()

    return quote_id

