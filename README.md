# Universal POS

A modern, offline Point-of-Sale desktop app built for Philippine retail
(sari-sari stores, small shops, restaurants) — written in pure Python with a
dark, card-based UI (via `customtkinter`) and a local SQLite database.

## Quick Start

```
git clone https://github.com/YOUR-USERNAME/universal-pos.git
cd universal-pos
pip install -r requirements.txt
python main.py
```

The app creates its database automatically on first run, with sample
products and two ready-made accounts (see **Default Login Accounts** below).
No manual database setup is needed.

## Features

- **Login system** with role-based access (Admin / Cashier), hashed passwords
- **Cashier POS screen**: barcode/manual product scan, product search & category
  filter, live cart, quantity +/- controls
- **Philippine tax rules**:
  - 12% VAT-inclusive pricing computed automatically (VATable / VAT-exempt breakdown)
  - Senior Citizen & PWD 20% discount, computed the BIR way (VAT removed, then 20% off)
- **Multiple payment methods**: Cash, GCash, Maya, Card — with change computation
- **Digital receipts**: auto-generated, saved as `.txt` files under `/receipts`
  (ready to print from any text editor), styled like a thermal-printer slip
- **Inventory management**: add/edit/disable products, categories, stock levels,
  restocking, low-stock alerts with reorder levels
- **Shift management**: cashiers open a shift with a starting cash amount;
  **X-Reading** (mid-shift snapshot) and **Z-Reading** (end-of-shift closeout)
  summarize gross sales, discounts, VAT, cash vs non-cash sales, and expected
  cash in the drawer — modeled after the BIR-required POS terminal readings
- **Admin dashboard**: today's sales overview, recent transactions, low-stock
  panel, full product/category/user management, sales history with date-range
  filters, top-selling products, void-sale (with automatic stock restore),
  and editable store info (name/address/TIN) used on receipts
- **Modern UI**: dark theme, rounded cards, sidebar navigation, responsive product grid

## Requirements

- Python 3.9+ (3.10–3.12 recommended)
- `customtkinter` (installed via requirements.txt)
- Tkinter — included with almost all standard Python installers on Windows/macOS.
  On Linux, if you get a `ModuleNotFoundError: No module named 'tkinter'`, install
  it with your package manager first, e.g. `sudo apt install python3-tk`.

## Setup in PyCharm

1. Clone or download the project, and open the `universal_pos` folder in PyCharm as a new project.
2. PyCharm will usually detect `requirements.txt` and offer to install it — accept,
   or open the terminal in PyCharm and run:
   ```
   pip install -r requirements.txt
   ```
3. Right-click `main.py` → **Run 'main'** (or open `main.py` and click the green ▶ button).
4. The app creates `pos.db` automatically on first run, with a couple of
   sample categories/products already loaded so you can try it right away.

## Default Login Accounts

| Role    | Username | Password    |
|---------|----------|-------------|
| Admin   | admin    | admin123    |
| Cashier | cashier  | cashier123  |

**Change these passwords** (Admin → Users → Reset Password) before using this
for anything beyond testing.

## Forgot Password

Because Universal POS runs fully offline (no email), password recovery uses a
**security question**:

1. **Set it up** — Admin → Users → **Recovery** button on any account. (The admin is
   also prompted once on first login if their own account has no question yet.)
2. **Use it** — on the login screen click **Forgot password?**, enter the username,
   answer the question, and choose a new password.

Notes:
- Answers aren't case-sensitive and extra spaces are ignored.
- After 5 wrong answers, recovery for that account locks for 5 minutes.
- Accounts with no recovery question can still be reset by an admin (Users → Reset Password),
  which also clears any lockout.
- **Admins:** set your own recovery question — an admin who forgets their password with
  no question set can't be recovered from inside the app.

## Project Structure

```
universal_pos/
├── main.py            # Entry point — run this
├── database.py         # SQLite schema, connection helper, seed data
├── auth.py              # Login, user accounts, password recovery
├── inventory.py         # Product & category CRUD, stock adjustments
├── sales.py             # VAT/discount math, checkout, shifts, X/Z-reading, reports
├── receipt.py           # Text-receipt generation, saved under /receipts
├── theme.py              # Shared color palette / fonts
├── login_window.py      # Login screen
├── recovery_dialogs.py  # Forgot-password + recovery-question dialogs
├── pos_window.py        # Cashier POS / checkout screen
├── admin_window.py      # Admin dashboard (products, users, reports, settings)
├── requirements.txt
└── README.md
```

## Notes on the Senior Citizen / PWD Discount

This implementation applies the **20% discount to the whole transaction** and
removes VAT entirely (the standard simplified approach for small POS systems).
In a real BIR-registered establishment, the discount legally applies only to
the qualified person's own consumption/purchase, and additional ID/OSCA
number capture may be required — you can extend the `customers` table
(already includes `is_senior_pwd` and `id_number` columns) and the checkout
flow in `pos_window.py` if you need that level of detail.

## Building a Distributable Installer

Want to install this on other computers without them needing Python or
PyCharm? See **`INSTALLER_GUIDE.md`** for a full step-by-step walkthrough
of packaging this project into a single `UniversalPOS_Setup.exe` using
PyInstaller + Inno Setup.

## Extending

- To connect an actual receipt/thermal printer, replace the file-writing in
  `receipt.py` with a driver call (e.g. `python-escpos` for ESC/POS printers).
- To add barcode scanner hardware, no extra code is needed — most USB/Bluetooth
  barcode scanners act as a keyboard and will type into the "Scan Barcode"
  field automatically, followed by Enter.
- The database layer (`database.py`) is isolated, so swapping SQLite for
  MySQL/PostgreSQL later only requires changing `get_connection()`.
