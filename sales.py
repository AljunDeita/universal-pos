"""
sales.py
--------
Core POS transaction logic:
  - PH-style VAT computation (12% VAT-inclusive pricing)
  - Senior Citizen / PWD 20% discount (VAT-exempt, per RA 9994 / RA 10754 style computation)
  - Checkout / invoice recording
  - Shift management (opening cash, X-reading, Z-reading)
  - Sales reports
"""

from datetime import datetime, date
from database import get_connection

VAT_RATE = 0.12


def compute_totals(cart, discount_type="none"):
    """
    cart: list of dicts with keys: price, qty, vat_exempt (0/1)
    discount_type: 'none' | 'senior' | 'pwd'

    Returns a dict with subtotal, vat_amount, vat_exempt_amount, discount_amount, total.
    All product prices are treated as VAT-INCLUSIVE (standard PH retail practice).
    """
    gross_total = sum(item["price"] * item["qty"] for item in cart)

    if discount_type in ("senior", "pwd"):
        # BIR-style: remove VAT first, then apply 20% discount on the net amount.
        # The whole transaction becomes VAT-exempt for the qualified beneficiary.
        net_of_vat = gross_total / (1 + VAT_RATE)
        discount_amount = round(net_of_vat * 0.20, 2)
        total = round(net_of_vat - discount_amount, 2)
        return {
            "subtotal": round(gross_total, 2),
            "vat_amount": 0.0,
            "vat_exempt_amount": total,
            "discount_amount": discount_amount,
            "total": total,
        }

    vatable_gross = sum(item["price"] * item["qty"] for item in cart if not item.get("vat_exempt"))
    exempt_gross = sum(item["price"] * item["qty"] for item in cart if item.get("vat_exempt"))
    vat_amount = round(vatable_gross - (vatable_gross / (1 + VAT_RATE)), 2)
    total = round(gross_total, 2)
    return {
        "subtotal": round(gross_total, 2),
        "vat_amount": vat_amount,
        "vat_exempt_amount": round(exempt_gross, 2),
        "discount_amount": 0.0,
        "total": total,
    }


def generate_invoice_no():
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) AS c FROM sales").fetchone()
    conn.close()
    n = row["c"] + 1
    return f"INV-{datetime.now().strftime('%Y%m%d')}-{n:05d}"


def record_sale(cashier_id, cart, totals, amount_tendered, payment_method, discount_type,
                 customer_id=None):
    """
    Persists a completed sale: header row, line items, and stock decrements.
    cart items need: product_id, product_name, price, qty
    Returns (invoice_no, sale_id)
    """
    conn = get_connection()
    invoice_no = generate_invoice_no()
    now = datetime.now().isoformat()
    change_due = round(amount_tendered - totals["total"], 2)

    cur = conn.execute(
        """INSERT INTO sales
           (invoice_no, cashier_id, customer_id, subtotal, discount_type, discount_amount,
            vat_amount, vat_exempt_amount, total, amount_tendered, change_due, payment_method,
            status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'COMPLETED', ?)""",
        (
            invoice_no, cashier_id, customer_id, totals["subtotal"], discount_type,
            totals["discount_amount"], totals["vat_amount"], totals["vat_exempt_amount"],
            totals["total"], amount_tendered, change_due, payment_method, now,
        ),
    )
    sale_id = cur.lastrowid

    for item in cart:
        line_total = round(item["price"] * item["qty"], 2)
        conn.execute(
            """INSERT INTO sale_items (sale_id, product_id, product_name, qty, unit_price, line_total)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (sale_id, item["product_id"], item["product_name"], item["qty"], item["price"], line_total),
        )
        conn.execute("UPDATE products SET stock_qty = stock_qty - ? WHERE id=?", (item["qty"], item["product_id"]))
        conn.execute(
            "INSERT INTO stock_movements (product_id, change_qty, reason, created_at) VALUES (?, ?, ?, ?)",
            (item["product_id"], -item["qty"], f"Sale {invoice_no}", now),
        )

    conn.commit()
    conn.close()
    return invoice_no, sale_id


def void_sale(sale_id, restock=True):
    conn = get_connection()
    sale = conn.execute("SELECT * FROM sales WHERE id=?", (sale_id,)).fetchone()
    if not sale or sale["status"] == "VOID":
        conn.close()
        return False, "Sale not found or already voided."
    items = conn.execute("SELECT * FROM sale_items WHERE sale_id=?", (sale_id,)).fetchall()
    if restock:
        now = datetime.now().isoformat()
        for it in items:
            conn.execute("UPDATE products SET stock_qty = stock_qty + ? WHERE id=?", (it["qty"], it["product_id"]))
            conn.execute(
                "INSERT INTO stock_movements (product_id, change_qty, reason, created_at) VALUES (?, ?, ?, ?)",
                (it["product_id"], it["qty"], f"Void {sale['invoice_no']}", now),
            )
    conn.execute("UPDATE sales SET status='VOID' WHERE id=?", (sale_id,))
    conn.commit()
    conn.close()
    return True, "Sale voided and stock restored."


def get_sale_with_items(sale_id):
    conn = get_connection()
    sale = conn.execute("SELECT * FROM sales WHERE id=?", (sale_id,)).fetchone()
    items = conn.execute("SELECT * FROM sale_items WHERE sale_id=?", (sale_id,)).fetchall()
    conn.close()
    if not sale:
        return None, []
    return dict(sale), [dict(i) for i in items]


def recent_sales(limit=100):
    conn = get_connection()
    rows = conn.execute(
        """SELECT s.*, u.full_name AS cashier_name FROM sales s
           JOIN users u ON s.cashier_id = u.id
           ORDER BY s.id DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def sales_between(start_iso, end_iso):
    conn = get_connection()
    rows = conn.execute(
        """SELECT s.*, u.full_name AS cashier_name FROM sales s
           JOIN users u ON s.cashier_id = u.id
           WHERE s.created_at BETWEEN ? AND ? ORDER BY s.id""",
        (start_iso, end_iso),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def top_products(start_iso, end_iso, limit=10):
    conn = get_connection()
    rows = conn.execute(
        """SELECT si.product_name, SUM(si.qty) AS total_qty, SUM(si.line_total) AS total_sales
           FROM sale_items si
           JOIN sales s ON si.sale_id = s.id
           WHERE s.created_at BETWEEN ? AND ? AND s.status='COMPLETED'
           GROUP BY si.product_name ORDER BY total_sales DESC LIMIT ?""",
        (start_iso, end_iso, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Shift management + X-Reading / Z-Reading (BIR-inspired terminal readings)
# ---------------------------------------------------------------------------

def open_shift(cashier_id, starting_cash):
    conn = get_connection()
    conn.execute(
        "INSERT INTO shifts (cashier_id, starting_cash, opened_at) VALUES (?, ?, ?)",
        (cashier_id, starting_cash, datetime.now().isoformat()),
    )
    conn.commit()
    shift_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    conn.close()
    return shift_id


def get_open_shift(cashier_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM shifts WHERE cashier_id=? AND closed_at IS NULL ORDER BY id DESC LIMIT 1",
        (cashier_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def shift_summary(shift, end_iso=None):
    """
    Aggregates all COMPLETED sales made during the shift.
    If end_iso is omitted, sums everything from opened_at up to now (used for a
    live X-Reading on an open shift). Pass the shift's closed_at to get the
    exact snapshot for a historical Z-Reading instead.
    """
    conn = get_connection()
    if end_iso:
        rows = conn.execute(
            """SELECT * FROM sales WHERE cashier_id=? AND created_at >= ? AND created_at <= ?
               AND status='COMPLETED' ORDER BY id""",
            (shift["cashier_id"], shift["opened_at"], end_iso),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT * FROM sales WHERE cashier_id=? AND created_at >= ? AND status='COMPLETED'
               ORDER BY id""",
            (shift["cashier_id"], shift["opened_at"]),
        ).fetchall()
    conn.close()
    rows = [dict(r) for r in rows]

    gross_sales = sum(r["subtotal"] for r in rows)
    total_discounts = sum(r["discount_amount"] for r in rows)
    total_vat = sum(r["vat_amount"] for r in rows)
    net_sales = sum(r["total"] for r in rows)
    cash_sales = sum(r["total"] for r in rows if r["payment_method"] == "CASH")
    non_cash_sales = net_sales - cash_sales
    expected_cash = shift["starting_cash"] + cash_sales

    by_method = {}
    for r in rows:
        by_method[r["payment_method"]] = by_method.get(r["payment_method"], 0) + r["total"]

    return {
        "transaction_count": len(rows),
        "gross_sales": round(gross_sales, 2),
        "total_discounts": round(total_discounts, 2),
        "total_vat": round(total_vat, 2),
        "net_sales": round(net_sales, 2),
        "cash_sales": round(cash_sales, 2),
        "non_cash_sales": round(non_cash_sales, 2),
        "expected_cash": round(expected_cash, 2),
        "by_method": by_method,
    }


def close_shift(shift_id, ending_cash):
    conn = get_connection()
    conn.execute(
        "UPDATE shifts SET closed_at=?, ending_cash=?, last_reading_no = last_reading_no + 1 WHERE id=?",
        (datetime.now().isoformat(), ending_cash, shift_id),
    )
    conn.commit()
    conn.close()


def bump_reading_no(shift_id):
    conn = get_connection()
    conn.execute("UPDATE shifts SET last_reading_no = last_reading_no + 1 WHERE id=?", (shift_id,))
    conn.commit()
    row = conn.execute("SELECT last_reading_no FROM shifts WHERE id=?", (shift_id,)).fetchone()
    conn.close()
    return row["last_reading_no"]


def today_range():
    today = date.today().isoformat()
    return f"{today}T00:00:00", f"{today}T23:59:59"


def list_shifts(start_iso=None, end_iso=None, closed_only=True):
    """Returns shifts (with cashier name) for the admin Z-Reports screen, newest first."""
    conn = get_connection()
    query = """SELECT sh.*, u.full_name AS cashier_name FROM shifts sh
               JOIN users u ON sh.cashier_id = u.id WHERE 1=1"""
    params = []
    if closed_only:
        query += " AND sh.closed_at IS NOT NULL"
    if start_iso:
        query += " AND sh.opened_at >= ?"
        params.append(start_iso)
    if end_iso:
        query += " AND sh.opened_at <= ?"
        params.append(end_iso)
    query += " ORDER BY sh.opened_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]
