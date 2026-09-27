"""
receipt.py
----------
Builds a plain-text, thermal-printer-style receipt (58/80mm look) as a string,
and can save it to /receipts as a .txt file that can be printed from Notepad
or any text editor. This avoids depending on an actual physical printer driver
so the project runs out-of-the-box on any PC.
"""

import os
from datetime import datetime
from database import get_setting, get_app_data_dir

RECEIPT_WIDTH = 42
RECEIPTS_DIR = os.path.join(get_app_data_dir(), "receipts")


def _center(text):
    return text.center(RECEIPT_WIDTH)


def _line(char="-"):
    return char * RECEIPT_WIDTH


def _row(left, right):
    space = RECEIPT_WIDTH - len(left) - len(right)
    if space < 1:
        space = 1
    return f"{left}{' ' * space}{right}"


def build_receipt_text(sale, items, cashier_name):
    store_name = get_setting("store_name", "MY STORE")
    store_address = get_setting("store_address", "")
    store_tin = get_setting("store_tin", "")
    footer = get_setting("receipt_footer", "Thank you!")

    dt = datetime.fromisoformat(sale["created_at"]).strftime("%m/%d/%Y %I:%M %p")

    lines = []
    lines.append(_center(store_name))
    if store_address:
        lines.append(_center(store_address))
    if store_tin:
        lines.append(_center(f"TIN: {store_tin}"))
    lines.append(_line("="))
    lines.append(_row("Invoice No:", sale["invoice_no"]))
    lines.append(_row("Date:", dt))
    lines.append(_row("Cashier:", cashier_name))
    lines.append(_line("-"))

    for it in items:
        lines.append(it["product_name"][:RECEIPT_WIDTH])
        qty_price = f'{it["qty"]:g} x {it["unit_price"]:.2f}'
        lines.append(_row(f"  {qty_price}", f'{it["line_total"]:.2f}'))

    lines.append(_line("-"))
    lines.append(_row("Subtotal:", f'{sale["subtotal"]:.2f}'))

    if sale["discount_type"] in ("senior", "pwd"):
        label = "Senior Citizen Disc." if sale["discount_type"] == "senior" else "PWD Discount"
        lines.append(_row(f"{label} (20%):", f'-{sale["discount_amount"]:.2f}'))
        lines.append(_row("VAT-Exempt Sale:", f'{sale["vat_exempt_amount"]:.2f}'))
    else:
        lines.append(_row("VATable Sale:", f'{(sale["subtotal"] - sale["vat_exempt_amount"] - sale["vat_amount"]):.2f}'))
        lines.append(_row("VAT-Exempt Sale:", f'{sale["vat_exempt_amount"]:.2f}'))
        lines.append(_row("VAT (12%):", f'{sale["vat_amount"]:.2f}'))

    lines.append(_line("="))
    lines.append(_row("TOTAL:", f'PHP {sale["total"]:.2f}'))
    lines.append(_row("Payment Method:", sale["payment_method"]))
    lines.append(_row("Amount Tendered:", f'{sale["amount_tendered"]:.2f}'))
    lines.append(_row("Change:", f'{sale["change_due"]:.2f}'))
    lines.append(_line("="))
    lines.append(_center("VAT Reg. TIN: " + store_tin) if store_tin else "")
    lines.append("")
    lines.append(_center(footer))
    lines.append(_center("This serves as your Official Receipt"))
    lines.append(_line())

    return "\n".join([l for l in lines if l is not None])


def save_receipt(sale, items, cashier_name):
    os.makedirs(RECEIPTS_DIR, exist_ok=True)
    text = build_receipt_text(sale, items, cashier_name)
    path = os.path.join(RECEIPTS_DIR, f"{sale['invoice_no']}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path, text
