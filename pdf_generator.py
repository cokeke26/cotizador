from __future__ import annotations

from datetime import date
from decimal import Decimal
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
    from io import BytesIO

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    margin_x = 18 * mm
    y = height - 18 * mm

    # Header
    if logo_path:
        try:
            c.drawImage(logo_path, margin_x, y - 18*mm, width=28*mm, height=18*mm, mask='auto')
        except Exception:
            pass

    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin_x + (34*mm if logo_path else 0), y, brand_name)

    c.setFont("Helvetica", 10)
    c.drawString(margin_x + (34*mm if logo_path else 0), y - 5*mm, f"{brand_email} | {brand_phone}")

    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(width - margin_x, y, f"COTIZACIÓN #{quote_number}")
    c.setFont("Helvetica", 10)
    c.drawRightString(width - margin_x, y - 5*mm, f"Fecha: {issue_date.strftime('%d-%m-%Y')}")

    y -= 18 * mm
    c.setStrokeColor(colors.lightgrey)
    c.line(margin_x, y, width - margin_x, y)
    y -= 10 * mm

    # Client block
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

    # Items table
    data = [["Descripción", "Cant.", "Precio unit.", "Total"]]
    subtotal = Decimal("0")

    for it in items:
        line_total = it.line_total
        subtotal += line_total
        data.append([
            it.description,
            f"{it.qty.normalize()}",
            money_clp(it.unit_price),
            money_clp(line_total),
        ])

    table = Table(data, colWidths=[92*mm, 18*mm, 30*mm, 30*mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
        ("TEXTCOLOR", (0,0), (-1,0), colors.black),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 10),
        ("FONTSIZE", (0,1), (-1,-1), 9),
        ("GRID", (0,0), (-1,-1), 0.5, colors.lightgrey),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (1,1), (1,-1), "RIGHT"),
        ("ALIGN", (2,1), (3,-1), "RIGHT"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.Color(0.98,0.98,0.98)]),
        ("BOTTOMPADDING", (0,0), (-1,0), 8),
        ("TOPPADDING", (0,0), (-1,0), 8),
    ]))

    # Render table
    tw, th = table.wrapOn(c, width - 2*margin_x, y)
    table.drawOn(c, margin_x, y - th)
    y -= (th + 10*mm)

    # Totals
    discount_amount = (subtotal * (discount_pct / Decimal("100"))).quantize(Decimal("1"))
    total = (subtotal - discount_amount).quantize(Decimal("1"))

    c.setFont("Helvetica", 10)
    c.drawRightString(width - margin_x, y, f"Subtotal: {money_clp(subtotal)}")
    y -= 5*mm
    c.drawRightString(width - margin_x, y, f"Descuento ({discount_pct}%): - {money_clp(discount_amount)}")
    y -= 6*mm
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(width - margin_x, y, f"TOTAL: {money_clp(total)}")
    y -= 10*mm

    # Notes / validity
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin_x, y, "Notas y condiciones")
    y -= 5*mm
    c.setFont("Helvetica", 9)
    validity_text = f"Validez: {validity_days} días."
    c.drawString(margin_x, y, validity_text)
    y -= 5*mm

    # Simple wrapping
    max_width = width - 2*margin_x
    text_obj = c.beginText(margin_x, y)
    text_obj.setFont("Helvetica", 9)

    for paragraph in (notes or "").split("\n"):
        line = ""
        for word in paragraph.split():
            test = (line + " " + word).strip()
            if c.stringWidth(test, "Helvetica", 9) <= max_width:
                line = test
            else:
                text_obj.textLine(line)
                line = word
        if line:
            text_obj.textLine(line)
        text_obj.textLine("")  # blank line between paragraphs

    c.drawText(text_obj)

    c.showPage()
    c.save()

    return buffer.getvalue()
