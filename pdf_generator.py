from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Sequence

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle

from utils import QuoteItem, money_clp


def build_quote_pdf_bytes(
    *,
    quote_number: str,
    issue_date: date,
    brand_name: str,
    brand_email: str,
    brand_phone: str,
    client_name: str,
    client_email: str,
    client_company: str,
    items: Sequence[QuoteItem],
    discount_pct: Decimal,
    notes: str,
    validity_days: int = 10,
    logo_path: Optional[str] = None,
) -> bytes:
    """
    Genera un PDF de cotización en bytes.
    - Incluye IVA 19% (Chile).
    - Redondeo consistente con ROUND_HALF_UP a pesos (sin decimales).
    - Incluye saltos de página básicos para evitar cortes en tabla/notas.
    """
    from io import BytesIO

    # -----------------------------
    # Constantes de formato/cálculo
    # -----------------------------
    IVA_RATE = Decimal("0.19")  # 19%
    ONE = Decimal("1")
    HUNDRED = Decimal("100")
    ROUNDING = ROUND_HALF_UP

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    margin_x = 18 * mm
    top_margin = 18 * mm
    bottom_margin = 18 * mm

    def new_page() -> float:
        """Cierra página actual y prepara una nueva, devolviendo el nuevo y inicial."""
        c.showPage()
        return height - top_margin

    def draw_header(y: float) -> float:
        """Dibuja el encabezado y retorna y actualizado."""
        # Logo (opcional)
        has_logo = False
        if logo_path:
            try:
                c.drawImage(
                    logo_path,
                    margin_x,
                    y - 18 * mm,
                    width=28 * mm,
                    height=18 * mm,
                    mask="auto",
                )
                has_logo = True
            except Exception:
                # Mantener tu lógica: si falla, no revienta.
                has_logo = False

        x_title = margin_x + (34 * mm if has_logo else 0)

        c.setFont("Helvetica-Bold", 16)
        c.drawString(x_title, y, brand_name)

        c.setFont("Helvetica", 10)
        c.drawString(x_title, y - 5 * mm, f"{brand_email} | {brand_phone}")

        c.setFont("Helvetica-Bold", 12)
        c.drawRightString(width - margin_x, y, f"COTIZACIÓN #{quote_number}")
        c.setFont("Helvetica", 10)
        c.drawRightString(width - margin_x, y - 5 * mm, f"Fecha: {issue_date.strftime('%d-%m-%Y')}")

        y -= 18 * mm
        c.setStrokeColor(colors.lightgrey)
        c.line(margin_x, y, width - margin_x, y)
        y -= 10 * mm
        return y

    def draw_client_block(y: float) -> float:
        """Dibuja bloque de cliente y retorna y actualizado."""
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margin_x, y, "Cliente")
        y -= 6 * mm
        c.setFont("Helvetica", 10)
        c.drawString(margin_x, y, f"Nombre: {client_name}")
        y -= 5 * mm
        c.drawString(margin_x, y, f"Empresa: {client_company}")
        y -= 5 * mm
        c.drawString(margin_x, y, f"Email: {client_email}")
        y -= 10 * mm
        return y

    # -----------------------------
    # Inicio documento
    # -----------------------------
    y = height - top_margin
    y = draw_header(y)
    y = draw_client_block(y)

    # -----------------------------
    # Tabla de ítems
    # -----------------------------
    data = [["Descripción", "Cant.", "Precio unit.", "Total"]]
    subtotal = Decimal("0")

    for it in items:
        line_total = it.line_total  # ya viene redondeado por línea (ROUND_HALF_UP en utils.py)
        subtotal += line_total
        data.append(
            [
                it.description,
                f"{it.qty.normalize()}",
                money_clp(it.unit_price),
                money_clp(line_total),
            ]
        )

    table = Table(data, colWidths=[92 * mm, 18 * mm, 30 * mm, 30 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                ("ALIGN", (2, 1), (3, -1), "RIGHT"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.98, 0.98, 0.98)]),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
            ]
        )
    )

    # Medir tabla para saber si cabe en la página
    available_width = width - 2 * margin_x
    tw, th = table.wrapOn(c, available_width, y)

    # Si no cabe, nueva página con header (sin repetir cliente por simplicidad, manteniendo tu lógica)
    if (y - th) < bottom_margin:
        y = new_page()
        y = draw_header(y)
        # Opcional: si quieres repetir cliente en cada página, descomenta:
        # y = draw_client_block(y)
        tw, th = table.wrapOn(c, available_width, y)

    table.drawOn(c, margin_x, y - th)
    y -= (th + 10 * mm)

    # -----------------------------
    # Totales con IVA
    # -----------------------------
    # Asegurar subtotal redondeado a pesos (por consistencia)
    subtotal = subtotal.quantize(ONE, rounding=ROUNDING)

    discount_amount = (subtotal * (discount_pct / HUNDRED)).quantize(ONE, rounding=ROUNDING)
    neto = (subtotal - discount_amount).quantize(ONE, rounding=ROUNDING)
    iva_amount = (neto * IVA_RATE).quantize(ONE, rounding=ROUNDING)
    total = (neto + iva_amount).quantize(ONE, rounding=ROUNDING)

    # Si no hay espacio para totales + notas, salto de página
    min_space_for_totals_and_notes = 55 * mm
    if y < (bottom_margin + min_space_for_totals_and_notes):
        y = new_page()
        y = draw_header(y)

    c.setFont("Helvetica", 10)
    c.drawRightString(width - margin_x, y, f"Subtotal (Neto): {money_clp(subtotal)}")
    y -= 5 * mm
    # Mostrar % sin ruido (ej. 10 en vez de 10.0)
    pct_str = f"{discount_pct.normalize()}"
    c.drawRightString(width - margin_x, y, f"Descuento ({pct_str}%): - {money_clp(discount_amount)}")
    y -= 5 * mm
    c.drawRightString(width - margin_x, y, f"Neto: {money_clp(neto)}")
    y -= 5 * mm
    c.drawRightString(width - margin_x, y, f"IVA (19%): {money_clp(iva_amount)}")
    y -= 6 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(width - margin_x, y, f"TOTAL: {money_clp(total)}")
    y -= 10 * mm

    # -----------------------------
    # Notas / validez (con wrapping + salto de página)
    # -----------------------------
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin_x, y, "Notas y condiciones")
    y -= 5 * mm

    c.setFont("Helvetica", 9)
    validity_text = f"Validez: {validity_days} días."
    c.drawString(margin_x, y, validity_text)
    y -= 6 * mm

    max_width = width - 2 * margin_x
    font_name = "Helvetica"
    font_size = 9
    line_height = 11  # aprox.

    def wrap_lines(text: str) -> list[str]:
        lines: list[str] = []
        for paragraph in (text or "").split("\n"):
            line = ""
            for word in paragraph.split():
                test = (line + " " + word).strip()
                if c.stringWidth(test, font_name, font_size) <= max_width:
                    line = test
                else:
                    if line:
                        lines.append(line)
                    line = word
            if line:
                lines.append(line)
            lines.append("")  # línea en blanco entre párrafos
        return lines

    lines = wrap_lines(notes or "")

    # Dibujar línea por línea, con salto de página si falta espacio
    c.setFont(font_name, font_size)
    for ln in lines:
        if y < bottom_margin + (line_height * 2):
            y = new_page()
            y = draw_header(y)
            # Repetir título de notas en nueva página para contexto
            c.setFont("Helvetica-Bold", 10)
            c.drawString(margin_x, y, "Notas y condiciones (continuación)")
            y -= 6 * mm
            c.setFont(font_name, font_size)

        c.drawString(margin_x, y, ln)
        y -= (line_height * 0.9)

    c.save()
    return buffer.getvalue()

