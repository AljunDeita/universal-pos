"""
inventory.py
------------
Product & category CRUD, stock adjustments, low-stock lookups, and product
photo storage.
"""

import os
import shutil
import uuid

from datetime import datetime
from database import get_connection, get_app_data_dir


def get_product_images_dir():
    path = os.path.join(get_app_data_dir(), "product_images")
    os.makedirs(path, exist_ok=True)
    return path


def save_product_image(source_path):
    """
    Copies an image the user picked (via a file dialog) into the app's own
    data folder under a generated unique filename, so the product photo
    keeps working even if the original file is later moved, renamed, or
    deleted. Returns the new stored path.
    """
    ext = os.path.splitext(source_path)[1].lower() or ".png"
    dest_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(get_product_images_dir(), dest_name)
    shutil.copyfile(source_path, dest_path)
    return dest_path


def list_categories():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_category(name):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO categories (name) VALUES (?)", (name.strip(),))
        conn.commit()
        return True, "Category added."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def list_products(search="", category_id=None, active_only=True):
    conn = get_connection()
    query = """
        SELECT p.*, c.name AS category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE 1=1
    """
    params = []
    if active_only:
        query += " AND p.active = 1"
    if search:
        query += " AND (p.name LIKE ? OR p.barcode LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    if category_id:
        query += " AND p.category_id = ?"
        params.append(category_id)
    query += " ORDER BY p.name"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_product_by_barcode(barcode):
    conn = get_connection()
    row = conn.execute(
        "SELECT p.*, c.name AS category_name FROM products p "
        "LEFT JOIN categories c ON p.category_id = c.id "
        "WHERE p.barcode = ? AND p.active = 1",
        (barcode.strip(),),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_product_by_id(product_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_product(barcode, name, category_id, price, cost, stock_qty, unit, reorder_level, vat_exempt,
                 image_path=None):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO products (barcode, name, category_id, price, cost, stock_qty, unit, reorder_level, vat_exempt, active, image_path) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)",
            (barcode or None, name.strip(), category_id, price, cost, stock_qty, unit, reorder_level, int(vat_exempt), image_path),
        )
        conn.commit()
        return True, "Product added."
    except Exception as e:
        return False, f"Could not add product: {e}"
    finally:
        conn.close()


def update_product(product_id, **fields):
    if not fields:
        return False, "Nothing to update."
    conn = get_connection()
    try:
        cols = ", ".join(f"{k}=?" for k in fields)
        values = list(fields.values()) + [product_id]
        conn.execute(f"UPDATE products SET {cols} WHERE id=?", values)
        conn.commit()
        return True, "Product updated."
    except Exception as e:
        return False, f"Could not update product: {e}"
    finally:
        conn.close()


def set_product_active(product_id, active: bool):
    conn = get_connection()
    conn.execute("UPDATE products SET active=? WHERE id=?", (1 if active else 0, product_id))
    conn.commit()
    conn.close()


def adjust_stock(product_id, change_qty, reason="Manual adjustment"):
    """change_qty can be negative (sale/consumption) or positive (restock)."""
    conn = get_connection()
    conn.execute(
        "UPDATE products SET stock_qty = stock_qty + ? WHERE id=?", (change_qty, product_id)
    )
    conn.execute(
        "INSERT INTO stock_movements (product_id, change_qty, reason, created_at) VALUES (?, ?, ?, ?)",
        (product_id, change_qty, reason, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def low_stock_products():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM products WHERE active = 1 AND stock_qty <= reorder_level ORDER BY stock_qty ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
