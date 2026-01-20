from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Sequence

import psycopg2
import psycopg2.extras
import streamlit as st

from utils import QuoteItem


def _get_database_url() -> str:
    url = st.secrets.get("DATABASE_URL")
    if not url:
        raise RuntimeError("Falta DATABASE_URL en st.secrets")
    return url


def get_conn():
    # Supabase normalmente requiere SSL
    return psycopg2.connect(_get_database_url())


def next_quote_number(year: int) -> tuple[int, str]:
    """
    Obtiene el siguiente correlativo del año de forma atómica (sin duplicados).
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
            seq = int(cur.fetchone()[0])
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
    with get_conn() as conn:
        with conn.cursor() as cur:
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
                    year, seq, quote_number, issue_date,
                    brand_name, brand_email, brand_phone,
                    client_name, client_email, client_company,
                    discount_pct, notes, validity_days
                ),
            )
            quote_id = int(cur.fetchone()[0])

            psycopg2.extras.execute_values(
                cur,
                """
                insert into quote_items(quote_id, description, qty, unit_price)
                values %s
                """,
                [(quote_id, it.description, it.qty, it.unit_price) for it in items],
            )

        conn.commit()

    return quote_id
