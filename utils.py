from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

def money_clp(value: Decimal) -> str:
    # Formato CLP simple: 1234567 -> 1.234.567
    v = int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    s = f"{v:,}".replace(",", ".")
    return f"$ {s}"

def to_decimal(x) -> Decimal:
    try:
        return Decimal(str(x))
    except Exception:
        return Decimal("0")

@dataclass
class QuoteItem:
    description: str
    qty: Decimal
    unit_price: Decimal

    @property
    def line_total(self) -> Decimal:
        return (self.qty * self.unit_price).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
