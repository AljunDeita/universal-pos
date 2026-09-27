"""
database.py
-----------
All SQLite database setup and data-access logic for the POS system lives here.
Keeping it in one module makes it easy to swap SQLite for something else later
(e.g. MySQL/PostgreSQL) without touching the UI code.
"""

import sqlite3
import hashlib
import os
from datetime import datetime

import sys


def get_app_data_dir():
    """
    Returns a writable, per-user folder to store the database and receipts in —
    independent of where the program itself is installed. This matters once the
    app is installed via a Windows installer into Program Files, which is
    read-only for normal user accounts: writing pos_system.db next to the .exe
    there would fail (or silently write to a virtualized copy) unless we use a
    proper user-data location instead.
    """
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    else:
        base = os.path.expanduser("~")
    app_dir = os.path.join(base, "UniversalPOS")
    os.makedirs(app_dir, exist_ok=True)
    return app_dir


DB_NAME = os.path.join(get_app_data_dir(), "pos_system.db")


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str) -> str:
    """Simple salted SHA-256 hash. Good enough for a local POS terminal."""
    salt = "pos_ph_salt_v1"
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def init_db():
    """Creates all tables if they don't exist yet, and seeds default data."""
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'cashier')),
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT UNIQUE,
            name TEXT NOT NULL,
            category_id INTEGER,
            price REAL NOT NULL,
            cost REAL NOT NULL DEFAULT 0,
            stock_qty REAL NOT NULL DEFAULT 0,
            unit TEXT NOT NULL DEFAULT 'pc',
            reorder_level REAL NOT NULL DEFAULT 5,
            vat_exempt INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );

        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            tin TEXT,
            address TEXT,
            is_senior_pwd INTEGER NOT NULL DEFAULT 0,
            id_number TEXT
        );

        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT UNIQUE NOT NULL,
            cashier_id INTEGER NOT NULL,
            customer_id INTEGER,
            subtotal REAL NOT NULL,
            discount_type TEXT NOT NULL DEFAULT 'none',
            discount_amount REAL NOT NULL DEFAULT 0,
            vat_amount REAL NOT NULL DEFAULT 0,
            vat_exempt_amount REAL NOT NULL DEFAULT 0,
            total REAL NOT NULL,
            amount_tendered REAL NOT NULL,
            change_due REAL NOT NULL,
            payment_method TEXT NOT NULL DEFAULT 'CASH',
            status TEXT NOT NULL DEFAULT 'COMPLETED',
            created_at TEXT NOT NULL,
            FOREIGN KEY (cashier_id) REFERENCES users(id),
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );

        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            qty REAL NOT NULL,
            unit_price REAL NOT NULL,
            line_total REAL NOT NULL,
            FOREIGN KEY (sale_id) REFERENCES sales(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS stock_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            change_qty REAL NOT NULL,
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cashier_id INTEGER NOT NULL,
            starting_cash REAL NOT NULL,
            opened_at TEXT NOT NULL,
            closed_at TEXT,
            ending_cash REAL,
            last_reading_no INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (cashier_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """
    )
    conn.commit()

    # --- Lightweight migrations for databases created by older versions of
    # --- this app (so upgrading the installed app never loses existing data)
    existing_cols = {row["name"] for row in cur.execute("PRAGMA table_info(products)").fetchall()}
    if "image_path" not in existing_cols:
        cur.execute("ALTER TABLE products ADD COLUMN image_path TEXT")
        conn.commit()

    # Password-recovery ("Forgot password?") columns on users
    user_cols = {row["name"] for row in cur.execute("PRAGMA table_info(users)").fetchall()}
    for col, ddl in [
        ("security_question", "TEXT"),
        ("security_answer_hash", "TEXT"),
        ("recovery_failed_attempts", "INTEGER NOT NULL DEFAULT 0"),
        ("recovery_locked_until", "TEXT"),
    ]:
        if col not in user_cols:
            cur.execute(f"ALTER TABLE users ADD COLUMN {col} {ddl}")
    conn.commit()

    # Seed default admin account if no users exist yet
    cur.execute("SELECT COUNT(*) AS c FROM users")
    if cur.fetchone()["c"] == 0:
        now = datetime.now().isoformat()
        cur.execute(
            "INSERT INTO users (username, password_hash, full_name, role, active, created_at) "
            "VALUES (?, ?, ?, ?, 1, ?)",
            ("admin", hash_password("admin123"), "Administrator", "admin", now),
        )
        cur.execute(
            "INSERT INTO users (username, password_hash, full_name, role, active, created_at) "
            "VALUES (?, ?, ?, ?, 1, ?)",
            ("cashier", hash_password("cashier123"), "Juan Dela Cruz", "cashier", now),
        )
        conn.commit()

    # Seed default settings (store info used on the receipt)
    default_settings = {
        "store_name": "MY SARI-SARI STORE POS",
        "store_address": "Purok 1, Brgy. Sample, Maramag, Bukidnon",
        "store_tin": "000-000-000-000",
        "vat_rate": "0.12",
        "receipt_footer": "Thank you for your purchase! Please come again.",
        "receipt_printer_name": "",      # empty = use system default printer
        "auto_print_receipt": "0",       # "1" = print automatically after checkout
    }
    for k, v in default_settings.items():
        cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
    conn.commit()

    # Seed a couple of sample categories/products so the app isn't empty on first run
    cur.execute("SELECT COUNT(*) AS c FROM categories")
    if cur.fetchone()["c"] == 0:
        for name in ["Beverages", "Snacks", "Grocery", "Personal Care", "Others"]:
            cur.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        conn.commit()

        cur.execute("SELECT id, name FROM categories")
        cats = {r["name"]: r["id"] for r in cur.fetchall()}
        sample_products = [
            ("4800016641503", "Coca-Cola 1.5L", "Beverages", 75.00, 60.00, 50, "bottle"),
            ("4800016461101", "Lucky Me Pancit Canton", "Snacks", 15.00, 11.00, 100, "pack"),
            ("4902430735735", "Kopiko Brown Coffee 3in1", "Beverages", 8.00, 6.00, 200, "sachet"),
            ("8850006964916", "Rice (Well-Milled) 1kg", "Grocery", 55.00, 48.00, 80, "kg"),
            ("4809008180010", "Safeguard Soap 90g", "Personal Care", 35.00, 27.00, 60, "pc"),
        ]
        now = datetime.now().isoformat()
        for barcode, name, cat, price, cost, stock, unit in sample_products:
            cur.execute(
                "INSERT INTO products (barcode, name, category_id, price, cost, stock_qty, unit, reorder_level, vat_exempt, active) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 1)",
                (barcode, name, cats[cat], price, cost, stock, unit, 10),
            )
        conn.commit()

    conn.close()


def get_setting(key, default=None):
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key, value):
    conn = get_connection()
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    conn.commit()
    conn.close()
