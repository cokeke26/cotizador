from __future__ import annotations

from datetime import date
from decimal import Decimal

import streamlit as st

from pdf_generator import build_quote_pdf_bytes
from utils import QuoteItem, to_decimal

st.set_page_config(page_title="Cotizador PDF", page_icon="🧾", layout="centered")


# -----------------------------
# CONTROL DE ACCESO (SIN CAMBIAR TU LÓGICA)
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

# Usamos una key que NO choque con métodos del dict (items, keys, values, etc.)
KEY_ITEMS = "quote_items"

with st.sidebar:
    st.subheader("Marca")
    brand_name = st.text_input("Nombre", value="HIDRACODE SOLUTIONS")
    brand_email = st.text_input("Email", value="contacto.hidracode@gmail.com")
    brand_phone = st.text_input("Teléfono", value="+56 9 4075 2095")
    logo_path = st.text_input("Ruta logo (opcional)", value="assets/logo.jpg")

st.subheader("Datos de la cotización")
col1, col2 = st.columns(2)
with col1:
    quote_number = st.text_input("N° Cotización", value="0001")
with col2:
    issue_date = st.date_input("Fecha", value=date.today())

st.subheader("Cliente")
col3, col4 = st.columns(2)
with col3:
    client_name = st.text_input("Nombre cliente", value="")
    client_email = st.text_input("Email cliente", value="")
with col4:
    client_company = st.text_input("Empresa", value="")

st.subheader("Ítems")

# Inicializar lista de ítems en session_state (usar corchetes, no punto)
if KEY_ITEMS not in st.session_state:
    st.session_state[KEY_ITEMS] = [
        {"description": "Diseño de logo", "Cantidad": 1, "unit_price": 50000},
        {"description": "Landing page (1 sección)", "Cantidad": 1, "unit_price": 120000},
    ]

# Render de ítems
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

# Build items (para el PDF)
items: list[QuoteItem] = []
for row in st.session_state[KEY_ITEMS]:
    desc = (row.get("description") or "").strip()
    if not desc:
        continue

    items.append(
        QuoteItem(
            description=desc,
            qty=to_decimal(row.get("Cantidad", 1)),
            unit_price=to_decimal(row.get("unit_price", 0)),
        )
    )

st.divider()

can_generate = bool(client_name.strip()) and len(items) > 0

if not can_generate:
    st.info("Completa al menos el nombre del cliente y agrega 1 ítem con descripción para generar el PDF.")

if st.button("Generar PDF", disabled=not can_generate):
    pdf_bytes = build_quote_pdf_bytes(
        quote_number=quote_number.strip() or "0001",
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

    filename = f"cotizacion_{quote_number.strip() or '0001'}.pdf"
    st.success("PDF generado.")
    st.download_button(
        label="Descargar PDF",
        data=pdf_bytes,
        file_name=filename,
        mime="application/pdf",
    )


