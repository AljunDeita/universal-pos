"""
pos_window.py
-------------
The main cashier-facing Point-of-Sale screen: product browsing/search,
barcode entry, cart management, discounts (Senior/PWD), payment, checkout,
receipt generation, and shift/X-reading controls.
"""

import os
import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
from PIL import Image

import theme
import inventory
import sales
import receipt as receipt_module
import printing
from barcode_tools import BarcodeScannerDialog
from database import get_setting


class POSWindow(ctk.CTk):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.cart = []  # list of dicts: product_id, product_name, price, qty, vat_exempt, unit, max_stock
        self.discount_type = "none"

        self.title(f"Universal POS — {user['full_name']}")
        self.geometry("1360x820")
        self.minsize(1180, 720)
        self.configure(fg_color=theme.BG)

        self.shift = sales.get_open_shift(self.user["id"])

        self._build_layout()
        self._refresh_products()

        if not self.shift:
            self.after(200, self._prompt_open_shift)

    # ==================================================================
    # LAYOUT
    # ==================================================================
    def _build_layout(self):
        self.grid_columnconfigure(0, weight=7)
        self.grid_columnconfigure(1, weight=4)
        self.grid_rowconfigure(1, weight=1)

        self._build_topbar()
        self._build_product_panel()
        self._build_cart_panel()

    def _build_topbar(self):
        bar = ctk.CTkFrame(self, fg_color=theme.SURFACE, height=64, corner_radius=0)
        bar.grid(row=0, column=0, columnspan=2, sticky="nsew")
        bar.grid_propagate(False)

        left = ctk.CTkFrame(bar, fg_color="transparent")
        left.pack(side="left", padx=20)
        ctk.CTkLabel(left, text="₱ Universal POS", font=theme.font(18, "bold")).pack(side="left")

        right = ctk.CTkFrame(bar, fg_color="transparent")
        right.pack(side="right", padx=20)

        ctk.CTkButton(right, text="Log Out", width=90, height=34, corner_radius=8,
                      fg_color=theme.CARD, hover_color=theme.CARD_HOVER,
                      command=self._logout).pack(side="right", padx=(8, 0))
        if self.user["role"] == "admin":
            ctk.CTkButton(right, text="⬅ Admin Dashboard", width=150, height=34, corner_radius=8,
                          fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
                          command=self._back_to_admin).pack(side="right", padx=(8, 0))
        ctk.CTkButton(right, text="X-Reading", width=110, height=34, corner_radius=8,
                      fg_color=theme.CARD, hover_color=theme.CARD_HOVER,
                      command=self._show_x_reading).pack(side="right", padx=(8, 0))
        ctk.CTkButton(right, text="End Shift (Z)", width=120, height=34, corner_radius=8,
                      fg_color=theme.WARNING, hover_color="#d68910", text_color="#1a1a1a",
                      command=self._end_shift).pack(side="right", padx=(8, 0))

        self.shift_label = ctk.CTkLabel(right, text="", font=theme.font(12), text_color=theme.TEXT_MUTED)
        self.shift_label.pack(side="right", padx=(0, 16))

        self.user_label = ctk.CTkLabel(
            right, text=f"👤 {self.user['full_name']}  ({self.user['role'].title()})",
            font=theme.font(12), text_color=theme.TEXT_MUTED,
        )
        self.user_label.pack(side="right", padx=(0, 16))
        self._refresh_shift_label()

    def _refresh_shift_label(self):
        self.shift = sales.get_open_shift(self.user["id"])
        if self.shift:
            opened = datetime.fromisoformat(self.shift["opened_at"]).strftime("%I:%M %p")
            self.shift_label.configure(text=f"Shift open since {opened}", text_color=theme.SUCCESS)
        else:
            self.shift_label.configure(text="No open shift", text_color=theme.DANGER)

    # ---- Product browsing panel -----------------------------------------------
    def _build_product_panel(self):
        panel = ctk.CTkFrame(self, fg_color=theme.BG, corner_radius=0)
        panel.grid(row=1, column=0, sticky="nsew", padx=(16, 8), pady=16)
        panel.grid_rowconfigure(2, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        # Barcode / quick add bar
        scan_frame = ctk.CTkFrame(panel, fg_color=theme.CARD, corner_radius=12, height=56)
        scan_frame.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        scan_frame.grid_propagate(False)
        ctk.CTkLabel(scan_frame, text="🔍 Scan / Enter Barcode:", font=theme.font(13)).pack(side="left", padx=16)
        self.barcode_entry = ctk.CTkEntry(scan_frame, width=220, height=36, corner_radius=8,
                                           placeholder_text="Scan barcode then press Enter")
        self.barcode_entry.pack(side="left", padx=(0, 8), pady=10)
        self.barcode_entry.bind("<Return>", self._on_barcode_scan)
        ctk.CTkButton(scan_frame, text="📷 Camera Scan", width=130, height=36, corner_radius=8,
                      fg_color=theme.CARD_HOVER, hover_color=theme.BORDER,
                      command=self._open_camera_scan).pack(side="left", padx=(0, 16), pady=10)

        # Search + category filter
        search_frame = ctk.CTkFrame(panel, fg_color="transparent")
        search_frame.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        self.search_entry = ctk.CTkEntry(search_frame, height=38, corner_radius=8,
                                          placeholder_text="Search product by name...")
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", lambda e: self._refresh_products())

        cats = ["All Categories"] + [c["name"] for c in inventory.list_categories()]
        self.category_var = ctk.StringVar(value="All Categories")
        cat_menu = ctk.CTkOptionMenu(search_frame, values=cats, variable=self.category_var,
                                      width=180, height=38, corner_radius=8,
                                      command=lambda v: self._refresh_products(),
                                      fg_color=theme.CARD, button_color=theme.CARD_HOVER)
        cat_menu.pack(side="left")

        # Scrollable product grid
        self.product_scroll = ctk.CTkScrollableFrame(panel, fg_color="transparent")
        self.product_scroll.grid(row=2, column=0, sticky="nsew")
        for i in range(4):
            self.product_scroll.grid_columnconfigure(i, weight=1, uniform="col")

    def _refresh_products(self, *_):
        for w in self.product_scroll.winfo_children():
            w.destroy()

        search = self.search_entry.get().strip() if hasattr(self, "search_entry") else ""
        cat_name = self.category_var.get() if hasattr(self, "category_var") else "All Categories"
        category_id = None
        if cat_name != "All Categories":
            for c in inventory.list_categories():
                if c["name"] == cat_name:
                    category_id = c["id"]
                    break

        products = inventory.list_products(search=search, category_id=category_id)

        if not products:
            ctk.CTkLabel(self.product_scroll, text="No products found.", text_color=theme.TEXT_MUTED,
                         font=theme.font(13)).grid(row=0, column=0, padx=10, pady=20)
            return

        for idx, p in enumerate(products):
            row, col = divmod(idx, 4)
            self._build_product_card(self.product_scroll, p, row, col)

    def _build_product_card(self, parent, product, row, col):
        low_stock = product["stock_qty"] <= product["reorder_level"]
        out_of_stock = product["stock_qty"] <= 0

        card = ctk.CTkFrame(parent, fg_color=theme.CARD, corner_radius=14, width=190, height=210)
        card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
        card.grid_propagate(False)

        # ---- Photo thumbnail (or a colored placeholder if none set) ----------
        photo_area = ctk.CTkFrame(card, fg_color=theme.SURFACE, corner_radius=10, height=70)
        photo_area.pack(fill="x", padx=10, pady=(10, 0))
        photo_area.pack_propagate(False)
        image_path = product.get("image_path")
        if image_path and os.path.exists(image_path):
            try:
                img = Image.open(image_path).convert("RGB").resize((70, 70))
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(70, 70))
                photo_label = ctk.CTkLabel(photo_area, image=ctk_img, text="")
                photo_label.image = ctk_img
                photo_label.pack(expand=True)
            except Exception:
                ctk.CTkLabel(photo_area, text="🛒", font=theme.font(24), text_color=theme.TEXT_MUTED).pack(expand=True)
        else:
            ctk.CTkLabel(photo_area, text="🛒", font=theme.font(24), text_color=theme.TEXT_MUTED).pack(expand=True)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(8, 0))
        badge_color = theme.DANGER if out_of_stock else (theme.WARNING if low_stock else theme.SUCCESS)
        ctk.CTkLabel(top, text=f"● {product['category_name'] or 'Uncategorized'}", font=theme.font(10),
                     text_color=theme.TEXT_MUTED).pack(side="left")

        ctk.CTkLabel(card, text=product["name"], font=theme.font(13, "bold"), wraplength=160,
                     justify="left", anchor="w").pack(fill="x", padx=12, pady=(4, 0))

        ctk.CTkLabel(card, text=f"₱{product['price']:.2f} / {product['unit']}", font=theme.font(13),
                     text_color=theme.ACCENT).pack(anchor="w", padx=12, pady=(2, 0))

        ctk.CTkLabel(card, text=f"Stock: {product['stock_qty']:g}", font=theme.font(10),
                     text_color=badge_color).pack(anchor="w", padx=12, pady=(2, 6))

        btn_text = "Out of Stock" if out_of_stock else "Add to Cart"
        btn = ctk.CTkButton(card, text=btn_text, height=28, corner_radius=8, font=theme.font(11),
                             fg_color=theme.ACCENT if not out_of_stock else theme.BORDER,
                             hover_color=theme.ACCENT_HOVER,
                             state="normal" if not out_of_stock else "disabled",
                             command=lambda p=product: self._add_to_cart(p))
        btn.pack(fill="x", padx=12, pady=(0, 12))

    # ---- Cart panel -------------------------------------------------------
    def _build_cart_panel(self):
        panel = ctk.CTkFrame(self, fg_color=theme.SURFACE, corner_radius=16)
        panel.grid(row=1, column=1, sticky="nsew", padx=(8, 16), pady=16)
        panel.grid_rowconfigure(1, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(panel, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        ctk.CTkLabel(header, text="🛒 Current Order", font=theme.font(16, "bold")).pack(side="left")
        ctk.CTkButton(header, text="Clear", width=70, height=28, corner_radius=8, font=theme.font(11),
                      fg_color=theme.DANGER, hover_color=theme.DANGER_HOVER,
                      command=self._clear_cart).pack(side="right")

        self.cart_scroll = ctk.CTkScrollableFrame(panel, fg_color="transparent")
        self.cart_scroll.grid(row=1, column=0, sticky="nsew", padx=16)

        # Totals + checkout section
        bottom = ctk.CTkFrame(panel, fg_color=theme.CARD, corner_radius=14)
        bottom.grid(row=2, column=0, sticky="ew", padx=16, pady=16)
        inner = ctk.CTkFrame(bottom, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=16)

        # Discount selector
        disc_frame = ctk.CTkFrame(inner, fg_color="transparent")
        disc_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(disc_frame, text="Discount:", font=theme.font(12)).pack(side="left")
        self.discount_var = ctk.StringVar(value="None")
        ctk.CTkOptionMenu(disc_frame, values=["None", "Senior Citizen (20%)", "PWD (20%)"],
                          variable=self.discount_var, width=180, height=30, corner_radius=8,
                          fg_color=theme.CARD_HOVER, button_color=theme.BORDER,
                          command=lambda v: self._update_totals()).pack(side="right")

        self.subtotal_label = self._totals_row(inner, "Subtotal")
        self.discount_label = self._totals_row(inner, "Discount")
        self.vat_label = self._totals_row(inner, "VAT (12%)")
        self.total_label = self._totals_row(inner, "TOTAL", big=True)

        # Payment method
        pay_frame = ctk.CTkFrame(inner, fg_color="transparent")
        pay_frame.pack(fill="x", pady=(10, 6))
        ctk.CTkLabel(pay_frame, text="Payment:", font=theme.font(12)).pack(side="left")
        self.payment_var = ctk.StringVar(value="CASH")
        ctk.CTkOptionMenu(pay_frame, values=["CASH", "GCASH", "CARD", "MAYA"],
                          variable=self.payment_var, width=180, height=30, corner_radius=8,
                          fg_color=theme.CARD_HOVER, button_color=theme.BORDER).pack(side="right")

        tender_frame = ctk.CTkFrame(inner, fg_color="transparent")
        tender_frame.pack(fill="x", pady=(6, 6))
        ctk.CTkLabel(tender_frame, text="Amount Tendered:", font=theme.font(12)).pack(side="left")
        self.tender_entry = ctk.CTkEntry(tender_frame, width=140, height=32, corner_radius=8,
                                          placeholder_text="0.00")
        self.tender_entry.pack(side="right")
        self.tender_entry.bind("<KeyRelease>", lambda e: self._update_change())

        self.change_label = self._totals_row(inner, "Change")

        self.checkout_btn = ctk.CTkButton(
            inner, text="CHECKOUT", height=48, corner_radius=10, font=theme.font(16, "bold"),
            fg_color=theme.SUCCESS, hover_color=theme.SUCCESS_HOVER, command=self._checkout,
        )
        self.checkout_btn.pack(fill="x", pady=(14, 0))

        self._update_totals()

    def _totals_row(self, parent, label, big=False):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=label, font=theme.font(15 if big else 12, "bold" if big else "normal"),
                     text_color=theme.TEXT_PRIMARY if big else theme.TEXT_MUTED).pack(side="left")
        value_label = ctk.CTkLabel(row, text="₱0.00", font=theme.font(16 if big else 12, "bold" if big else "normal"),
                                    text_color=theme.ACCENT if big else theme.TEXT_PRIMARY)
        value_label.pack(side="right")
        return value_label

    # ==================================================================
    # CART LOGIC
    # ==================================================================
    def _on_barcode_scan(self, event):
        code = self.barcode_entry.get().strip()
        self.barcode_entry.delete(0, "end")
        self._lookup_and_add_barcode(code)

    def _open_camera_scan(self):
        def on_scanned(code):
            self._lookup_and_add_barcode(code)
        BarcodeScannerDialog(self, on_scanned)

    def _lookup_and_add_barcode(self, code):
        if not code:
            return
        product = inventory.get_product_by_barcode(code)
        if not product:
            messagebox.showwarning("Not Found", f"No product with barcode '{code}'.")
            return
        self._add_to_cart(product)

    def _add_to_cart(self, product):
        if product["stock_qty"] <= 0:
            messagebox.showwarning("Out of Stock", f"{product['name']} is out of stock.")
            return
        for item in self.cart:
            if item["product_id"] == product["id"]:
                if item["qty"] + 1 > product["stock_qty"]:
                    messagebox.showwarning("Stock Limit", f"Only {product['stock_qty']:g} {product['unit']} left.")
                    return
                item["qty"] += 1
                self._render_cart()
                return
        self.cart.append({
            "product_id": product["id"],
            "product_name": product["name"],
            "price": product["price"],
            "qty": 1,
            "vat_exempt": product["vat_exempt"],
            "unit": product["unit"],
            "max_stock": product["stock_qty"],
        })
        self._render_cart()

    def _render_cart(self):
        for w in self.cart_scroll.winfo_children():
            w.destroy()

        if not self.cart:
            ctk.CTkLabel(self.cart_scroll, text="Cart is empty.\nAdd products from the left panel.",
                         text_color=theme.TEXT_MUTED, font=theme.font(12), justify="center").pack(pady=30)
        else:
            for idx, item in enumerate(self.cart):
                self._build_cart_row(idx, item)

        self._update_totals()

    def _build_cart_row(self, idx, item):
        row = ctk.CTkFrame(self.cart_scroll, fg_color=theme.CARD, corner_radius=10)
        row.pack(fill="x", pady=4)

        top = ctk.CTkFrame(row, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(10, 0))
        ctk.CTkLabel(top, text=item["product_name"], font=theme.font(12, "bold"), anchor="w").pack(side="left")
        ctk.CTkButton(top, text="✕", width=24, height=24, corner_radius=6, fg_color=theme.DANGER,
                      hover_color=theme.DANGER_HOVER, font=theme.font(11),
                      command=lambda i=idx: self._remove_item(i)).pack(side="right")

        bottom = ctk.CTkFrame(row, fg_color="transparent")
        bottom.pack(fill="x", padx=12, pady=(4, 10))
        ctk.CTkLabel(bottom, text=f"₱{item['price']:.2f}", font=theme.font(11),
                     text_color=theme.TEXT_MUTED).pack(side="left")

        qty_frame = ctk.CTkFrame(bottom, fg_color="transparent")
        qty_frame.pack(side="right")
        ctk.CTkButton(qty_frame, text="-", width=26, height=26, corner_radius=6, fg_color=theme.BORDER,
                      command=lambda i=idx: self._change_qty(i, -1)).pack(side="left")
        ctk.CTkLabel(qty_frame, text=f"{item['qty']:g}", width=36, font=theme.font(12)).pack(side="left")
        ctk.CTkButton(qty_frame, text="+", width=26, height=26, corner_radius=6, fg_color=theme.BORDER,
                      command=lambda i=idx: self._change_qty(i, 1)).pack(side="left")

        ctk.CTkLabel(bottom, text=f"= ₱{item['price'] * item['qty']:.2f}", font=theme.font(12, "bold")).pack(
            side="right", padx=10)

    def _change_qty(self, idx, delta):
        item = self.cart[idx]
        new_qty = item["qty"] + delta
        if new_qty <= 0:
            self._remove_item(idx)
            return
        if new_qty > item["max_stock"]:
            messagebox.showwarning("Stock Limit", f"Only {item['max_stock']:g} {item['unit']} available.")
            return
        item["qty"] = new_qty
        self._render_cart()

    def _remove_item(self, idx):
        del self.cart[idx]
        self._render_cart()

    def _clear_cart(self):
        if self.cart and not messagebox.askyesno("Clear Order", "Remove all items from the current order?"):
            return
        self.cart = []
        self.tender_entry.delete(0, "end")
        self._render_cart()

    def _current_discount_type(self):
        label = self.discount_var.get()
        if label.startswith("Senior"):
            return "senior"
        if label.startswith("PWD"):
            return "pwd"
        return "none"

    def _update_totals(self):
        totals = sales.compute_totals(self.cart, self._current_discount_type())
        self.subtotal_label.configure(text=f"₱{totals['subtotal']:.2f}")
        self.discount_label.configure(text=f"-₱{totals['discount_amount']:.2f}")
        self.vat_label.configure(text=f"₱{totals['vat_amount']:.2f}")
        self.total_label.configure(text=f"₱{totals['total']:.2f}")
        self._current_totals = totals
        self._update_change()

    def _update_change(self):
        try:
            tendered = float(self.tender_entry.get() or 0)
        except ValueError:
            tendered = 0
        change = tendered - self._current_totals["total"]
        self.change_label.configure(
            text=f"₱{change:.2f}", text_color=theme.SUCCESS if change >= 0 else theme.DANGER
        )

    # ==================================================================
    # CHECKOUT
    # ==================================================================
    def _checkout(self):
        if not self.cart:
            messagebox.showwarning("Empty Cart", "Add at least one item before checking out.")
            return
        if not self.shift:
            messagebox.showwarning("No Shift", "Please start your shift (enter starting cash) first.")
            self._prompt_open_shift()
            return
        try:
            tendered = float(self.tender_entry.get() or 0)
        except ValueError:
            messagebox.showerror("Invalid Amount", "Please enter a valid tendered amount.")
            return

        totals = self._current_totals
        if self.payment_var.get() == "CASH" and tendered < totals["total"]:
            messagebox.showerror("Insufficient Payment", "Amount tendered is less than the total due.")
            return

        invoice_no, sale_id = sales.record_sale(
            cashier_id=self.user["id"],
            cart=self.cart,
            totals=totals,
            amount_tendered=tendered,
            payment_method=self.payment_var.get(),
            discount_type=self._current_discount_type(),
        )

        sale, items = sales.get_sale_with_items(sale_id)
        path, text = receipt_module.save_receipt(sale, items, self.user["full_name"])

        auto_print_status = None
        if get_setting("auto_print_receipt", "0") == "1":
            printer_name = get_setting("receipt_printer_name", "") or None
            ok, msg = printing.print_receipt_text(text, printer_name)
            auto_print_status = (ok, msg)

        self._show_receipt_dialog(text, path, auto_print_status)

        self.cart = []
        self.tender_entry.delete(0, "end")
        self.discount_var.set("None")
        self._render_cart()
        self._refresh_products()

    def _show_receipt_dialog(self, text, path, auto_print_status=None):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Receipt")
        dlg.geometry("420x660")
        dlg.configure(fg_color=theme.BG)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="✅ Transaction Complete", font=theme.font(16, "bold"),
                     text_color=theme.SUCCESS).pack(pady=(16, 4))

        if auto_print_status is not None:
            ok, msg = auto_print_status
            ctk.CTkLabel(dlg, text=("🖨 " + msg) if ok else ("⚠ Auto-print failed: " + msg),
                         font=theme.font(10), text_color=theme.SUCCESS if ok else theme.WARNING,
                         wraplength=380).pack(pady=(0, 4))

        box = ctk.CTkTextbox(dlg, font=("Consolas", 11), fg_color=theme.CARD, corner_radius=10)
        box.pack(fill="both", expand=True, padx=16, pady=8)
        box.insert("1.0", text)
        box.configure(state="disabled")

        ctk.CTkLabel(dlg, text=f"Saved to: {path}", font=theme.font(10), text_color=theme.TEXT_MUTED,
                     wraplength=380).pack(pady=(0, 8))

        btn_row = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 16))
        ctk.CTkButton(btn_row, text="🖨 Print Receipt", height=38, corner_radius=8, fg_color=theme.CARD_HOVER,
                      hover_color=theme.BORDER, command=lambda: self._manual_print(text)).pack(
            side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(btn_row, text="Close", height=38, corner_radius=8, fg_color=theme.ACCENT,
                      hover_color=theme.ACCENT_HOVER, command=dlg.destroy).pack(
            side="left", fill="x", expand=True, padx=(6, 0))

    def _manual_print(self, text):
        if not printing.printing_supported():
            messagebox.showinfo(
                "Printing Not Available",
                "Direct printing needs the 'pywin32' package on Windows.\n\n"
                "Run: pip install pywin32\n\n"
                "Until then, you can open the saved receipt .txt file and print it manually.",
            )
            return
        printer_name = get_setting("receipt_printer_name", "") or None
        ok, msg = printing.print_receipt_text(text, printer_name)
        if ok:
            messagebox.showinfo("Printing", msg)
        else:
            messagebox.showerror("Print Failed", msg)

    # ==================================================================
    # SHIFT MANAGEMENT
    # ==================================================================
    def _prompt_open_shift(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Start Shift")
        dlg.geometry("360x260")
        dlg.configure(fg_color=theme.BG)
        dlg.grab_set()
        dlg.protocol("WM_DELETE_WINDOW", lambda: None)  # must open a shift to proceed

        ctk.CTkLabel(dlg, text="🕒 Start Your Shift", font=theme.font(16, "bold")).pack(pady=(24, 4))
        ctk.CTkLabel(dlg, text="Enter your starting cash drawer amount", font=theme.font(11),
                     text_color=theme.TEXT_MUTED).pack(pady=(0, 16))

        entry = ctk.CTkEntry(dlg, width=200, height=38, corner_radius=8, placeholder_text="e.g. 2000.00")
        entry.pack()

        def start():
            try:
                cash = float(entry.get() or 0)
            except ValueError:
                messagebox.showerror("Invalid", "Please enter a valid amount.")
                return
            sales.open_shift(self.user["id"], cash)
            self._refresh_shift_label()
            dlg.destroy()

        ctk.CTkButton(dlg, text="Start Shift", height=40, corner_radius=8, fg_color=theme.SUCCESS,
                      hover_color=theme.SUCCESS_HOVER, command=start).pack(pady=20, padx=30, fill="x")

    def _show_x_reading(self):
        if not self.shift:
            messagebox.showinfo("No Shift", "No open shift to read.")
            return
        reading_no = sales.bump_reading_no(self.shift["id"])
        summary = sales.shift_summary(self.shift)
        self._show_reading_dialog("X-READING (Mid-Shift)", reading_no, summary, closing=False)

    def _end_shift(self):
        if not self.shift:
            messagebox.showinfo("No Shift", "No open shift to close.")
            return
        summary = sales.shift_summary(self.shift)
        self._prompt_actual_cash_and_close(summary)

    def _prompt_actual_cash_and_close(self, summary):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Count Cash Drawer")
        dlg.geometry("360x260")
        dlg.configure(fg_color=theme.BG)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="🧮 Count Your Cash Drawer", font=theme.font(15, "bold")).pack(pady=(20, 4))
        ctk.CTkLabel(dlg, text=f"System-expected cash: ₱{summary['expected_cash']:.2f}",
                     font=theme.font(11), text_color=theme.TEXT_MUTED).pack(pady=(0, 14))

        entry = ctk.CTkEntry(dlg, width=200, height=38, corner_radius=8, placeholder_text="Actual counted cash")
        entry.pack()

        def confirm():
            try:
                actual_cash = float(entry.get())
            except ValueError:
                messagebox.showerror("Invalid", "Please enter a valid amount.")
                return
            reading_no = sales.bump_reading_no(self.shift["id"])
            sales.close_shift(self.shift["id"], actual_cash)
            dlg.destroy()
            self._show_reading_dialog("Z-READING (End of Shift)", reading_no, summary, closing=True,
                                       actual_cash=actual_cash)
            self.shift = None
            self._refresh_shift_label()

        ctk.CTkButton(dlg, text="Confirm & Close Shift", height=40, corner_radius=8, fg_color=theme.WARNING,
                      hover_color="#d68910", text_color="#1a1a1a", command=confirm).pack(pady=20, padx=30, fill="x")

    def _show_reading_dialog(self, title, reading_no, summary, closing, actual_cash=None):
        dlg = ctk.CTkToplevel(self)
        dlg.title(title)
        dlg.geometry("380x560")
        dlg.configure(fg_color=theme.BG)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text=title, font=theme.font(16, "bold")).pack(pady=(20, 2))
        ctk.CTkLabel(dlg, text=f"Reading No. {reading_no:04d}   |   {self.user['full_name']}",
                     font=theme.font(11), text_color=theme.TEXT_MUTED).pack(pady=(0, 14))

        box = ctk.CTkFrame(dlg, fg_color=theme.CARD, corner_radius=12)
        box.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        def row(label, value, bold=False, color=None):
            r = ctk.CTkFrame(box, fg_color="transparent")
            r.pack(fill="x", padx=16, pady=4)
            ctk.CTkLabel(r, text=label, font=theme.font(12, "bold" if bold else "normal")).pack(side="left")
            ctk.CTkLabel(r, text=value, font=theme.font(12, "bold" if bold else "normal"),
                         text_color=color or (theme.ACCENT if bold else theme.TEXT_PRIMARY)).pack(side="right")

        row("Transactions:", str(summary["transaction_count"]))
        row("Gross Sales:", f"₱{summary['gross_sales']:.2f}")
        row("Discounts:", f"₱{summary['total_discounts']:.2f}")
        row("VAT Collected:", f"₱{summary['total_vat']:.2f}")
        row("Net Sales:", f"₱{summary['net_sales']:.2f}", bold=True)
        ctk.CTkLabel(box, text="").pack(pady=2)
        row("Cash Sales:", f"₱{summary['cash_sales']:.2f}")
        row("Non-Cash Sales:", f"₱{summary['non_cash_sales']:.2f}")
        row("Expected Cash in Drawer:", f"₱{summary['expected_cash']:.2f}", bold=True)

        if actual_cash is not None:
            variance = round(actual_cash - summary["expected_cash"], 2)
            var_color = theme.SUCCESS if variance == 0 else theme.DANGER
            row("Actual Counted Cash:", f"₱{actual_cash:.2f}", bold=True)
            row("Cash Variance:", f"{'+' if variance >= 0 else ''}₱{variance:.2f}", bold=True, color=var_color)

        if closing:
            ctk.CTkLabel(dlg, text="Shift closed. You may now log out.", font=theme.font(11),
                         text_color=theme.WARNING).pack(pady=(0, 6))

        ctk.CTkButton(dlg, text="Close", height=38, corner_radius=8, fg_color=theme.ACCENT,
                      hover_color=theme.ACCENT_HOVER, command=dlg.destroy).pack(fill="x", padx=20, pady=(0, 20))

    # ==================================================================
    def _back_to_admin(self):
        if self.cart and not messagebox.askyesno(
            "Leave Current Order", "You have items in the cart that haven't been checked out. "
            "Go to the Admin Dashboard anyway?"
        ):
            return
        self.destroy()
        from admin_window import AdminWindow
        AdminWindow(self.user).mainloop()

    def _logout(self):
        if not messagebox.askyesno("Log Out", "Are you sure you want to log out?"):
            return
        self.destroy()
        from login_window import LoginWindow
        LoginWindow().mainloop()


if __name__ == "__main__":
    # Quick manual test (requires a valid user dict normally provided by login)
    POSWindow({"id": 2, "username": "cashier", "full_name": "Juan Dela Cruz", "role": "cashier"}).mainloop()
