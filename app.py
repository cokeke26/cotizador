from __future__ import annotations

from datetime import date
from decimal import Decimal

import streamlit as st

from pdf_generator import build_quote_pdf_bytes
from utils import QuoteItem, to_decimal

# DB (Supabase/Postgres)
from db import next_quote_number, insert_quote

st.set_page_config(page_title="Cotizador PDF", page_icon="🧾", layout="centered")


# -----------------------------
# CONTROL DE ACCESO (MISMA LÓGICA)
# -----------------------------
def require_login() -> None:
    """
    Requiere contraseña para acceder a la app.
    La contraseña se obtiene desde st.secrets["APP_PASSWORD"].

    En local: crea .streamlit/secrets.toml con:
    APP_PASSWORD = "tu_clave"

    En Streamlit Cloud: Settings -> Secrets y pega lo mismo.
    """
    if "auth_ok" not in st.session_state:
        st.session_state["auth_ok"] = False

    if st.session_state["auth_ok"]:
        return

    st.title("Acceso privado")
    st.caption("Esta herramienta es solo para uso interno.")

    pwd = st.text_input("Contraseña", type="password")

    col_a, col_b = st.columns([1, 3])
    if col_a.button("Ingresar"):
        try:
            expected = st.secrets["APP_PASSWORD"]
        except Exception:
            st.error("Falta configurar APP_PASSWORD en Secrets.")
            st.stop()

        if pwd == expected:
            st.session_state["auth_ok"] = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")

    st.stop()


require_login()
# -----------------------------
# FIN CONTROL DE ACCESO
# -----------------------------

st.title("Generador de cotizaciones en PDF")

# Keys seguras (no chocan con dict methods)
KEY_ITEMS = "quote_items"
KEY_QUOTE_NUMBER = "quote_number"
KEY_QUOTE_SEQ = "quote_seq"

with st.sidebar:
    st.subheader("Marca")
    brand_name = st.text_input("Nombre", value="HIDRACODE SOLUTIONS")
    brand_email = st.text_input("Email", value="contacto.hidracode@gmail.com")
    brand_phone = st.text_input("Teléfono", value="+56 9 4075 2095")
    logo_path = st.text_input("Ruta logo (opcional)", value="assets/logo.jpg")

    st.divider()
    st.subheader("Base de datos (Supabase)")
    # Validación suave para guiar si falta el secreto
    if not st.secrets.get("DATABASE_URL"):
        st.warning("Falta DATABASE_URL en Secrets. No se guardará historial ni se asignará N° automático.")


# -----------------------------
# Datos de la cotización (con autoincremento)
# -----------------------------
st.subheader("Datos de la cotización")
col1, col2, col3 = st.columns([1.2, 1.2, 2.2])

with col1:
    issue_date = st.date_input("Fecha", value=date.today())

with col2:
    st.text_input("Año", value=str(issue_date.year), disabled=True)

with col3:
    # Botón para pedir correlativo
    can_assign = bool(st.secrets.get("DATABASE_URL"))
    if st.button("Asignar N° (autoincremental)", disabled=not can_assign):
        try:
            seq, qn = next_quote_number(issue_date.year)
            st.session_state[KEY_QUOTE_SEQ] = seq
            st.session_state[KEY_QUOTE_NUMBER] = qn
            st.success(f"N° asignado: {qn}")
        except Exception as e:
            st.error("No se pudo asignar el número desde la base de datos.")
            st.exception(e)

quote_number = st.session_state.get(KEY_QUOTE_NUMBER, "")
st.text_input("N° Cotización", value=quote_number, disabled=True)

# Si cambian la fecha/año después de asignar número, advertir (para no mezclar)
if quote_number and str(issue_date.year) != quote_number.split("-")[0]:
    st.warning("Cambiaste el año de la fecha. Vuelve a asignar el N° para mantener el correlativo por año.")


# -----------------------------
# Cliente
# -----------------------------
st.subheader("Cliente")
col3, col4 = st.columns(2)
with col3:
    client_name = st.text_input("Nombre cliente", value="")
    client_email = st.text_input("Email cliente", value="")
with col4:
    client_company = st.text_input("Empresa", value="")

# -----------------------------
# Ítems
# -----------------------------
st.subheader("Ítems")

if KEY_ITEMS not in st.session_state:
    st.session_state[KEY_ITEMS] = [
        {"description": "Diseño de logo", "Cantidad": 1, "unit_price": 50000},
        {"description": "Landing page (1 sección)", "Cantidad": 1, "unit_price": 120000},
    ]

for i, row in enumerate(st.session_state[KEY_ITEMS]):
    c1, c2, c3, c4 = st.columns([5, 1.2, 2, 1])

    row["description"] = c1.text_input(
        f"Descripción {i+1}",
        value=row.get("description", ""),
        key=f"desc_{i}",
    )

    row["Cantidad"] = c2.number_input(
        f"Cantidad {i+1}",
        min_value=0.0,
        value=float(row.get("Cantidad", 1)),
        step=1.0,
        key=f"qty_{i}",
    )

    row["unit_price"] = c3.number_input(
        f"Precio {i+1}",
        min_value=0.0,
        value=float(row.get("unit_price", 0)),
        step=1000.0,
        key=f"price_{i}",
    )

    if c4.button("❌", key=f"del_{i}", help="Eliminar ítem"):
        st.session_state[KEY_ITEMS].pop(i)
        st.rerun()

col_add, col_space = st.columns([1, 5])
if col_add.button("Añadir ítem"):
    st.session_state[KEY_ITEMS].append({"description": "", "Cantidad": 1, "unit_price": 0})
    st.rerun()

# -----------------------------
# Totales y condiciones
# -----------------------------
st.subheader("Totales")
discount_pct = st.number_input(
    "Descuento (%)",
    min_value=0.0,
    max_value=90.0,
    value=0.0,
    step=1.0,
)

notes = st.text_area(
    "Notas / condiciones",
    value="• Entrega: 3-5 días hábiles.\n• Incluye 1 ronda de ajustes.\n• Forma de pago: 50% inicio, 50% contra entrega.",
    height=110,
)

validity_days = st.number_input(
    "Validez (días)",
    min_value=1,
    max_value=60,
    value=10,
    step=1,
)

# Build items para el PDF/DB
items: list[QuoteItem] = []
for row in st.session_state[KEY_ITEMS]:
    desc = (row.get("description") or "").strip()
    if not desc:
        continue

    qty = to_decimal(row.get("Cantidad", 1))
    unit_price = to_decimal(row.get("unit_price", 0))

    # filtro mínimo: si qty es 0, no lo agregues
    if qty <= 0:
        continue

    items.append(QuoteItem(description=desc, qty=qty, unit_price=unit_price))

st.divider()

can_generate = bool(client_name.strip()) and len(items) > 0

if not can_generate:
    st.info("Completa al menos el nombre del cliente y agrega 1 ítem con descripción (y cantidad > 0) para generar el PDF.")

# Requisito: para guardar + número autoincremental, debe existir quote_number asignado
needs_number = True
has_number = bool(st.session_state.get(KEY_QUOTE_NUMBER))

if needs_number and not has_number:
    st.warning("Antes de generar, presiona “Asignar N° (autoincremental)” para obtener el correlativo desde la base de datos.")

btn_disabled = (not can_generate) or (not has_number)

if st.button("Generar PDF", disabled=btn_disabled):
    qn = st.session_state.get(KEY_QUOTE_NUMBER, "").strip()
    seq = int(st.session_state.get(KEY_QUOTE_SEQ, 0))
    yr = int(issue_date.year)

    # 1) Guardar en DB (Supabase)
    try:
        if not st.secrets.get("DATABASE_URL"):
            st.error("Falta DATABASE_URL en Secrets. No puedo guardar ni asegurar correlativo.")
            st.stop()

        insert_quote(
            year=yr,
            seq=seq,
            quote_number=qn,
            issue_date=issue_date,
            brand_name=brand_name.strip() or "HIDRACODE SOLUTIONS",
            brand_email=brand_email.strip(),
            brand_phone=brand_phone.strip(),
            client_name=client_name.strip(),
            client_email=client_email.strip(),
            client_company=client_company.strip(),
            discount_pct=Decimal(str(discount_pct)),
            notes=notes,
            validity_days=int(validity_days),
            items=items,
        )
    except Exception as e:
        st.error("No se pudo guardar la cotización en la base de datos.")
        st.exception(e)
        st.stop()

    # 2) Generar PDF
    with st.spinner("Generando PDF..."):
        pdf_bytes = build_quote_pdf_bytes(
            quote_number=qn or "0001",
            issue_date=issue_date,
            brand_name=brand_name.strip() or "HIDRACODE SOLUTIONS",
            brand_email=brand_email.strip(),
            brand_phone=brand_phone.strip(),
            client_name=client_name.strip(),
            client_email=client_email.strip(),
            client_company=client_company.strip(),
            items=items,
            discount_pct=Decimal(str(discount_pct)),
            notes=notes,
            validity_days=int(validity_days),
            logo_path=logo_path.strip() if logo_path.strip() else None,
        )

    filename = f"cotizacion_{qn or '0001'}.pdf"
    st.success("PDF generado y guardado en la base de datos.")
    st.download_button(
        label="Descargar PDF",
        data=pdf_bytes,
        file_name=filename,
        mime="application/pdf",
    )

    # Opcional: limpiar número para que obligue a asignar uno nuevo en la próxima cotización
    st.session_state.pop(KEY_QUOTE_NUMBER, None)
    st.session_state.pop(KEY_QUOTE_SEQ, None)


