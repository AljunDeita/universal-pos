"""
admin_window.py
----------------
Admin dashboard: sidebar navigation between Dashboard, Products, Categories,
Users, Sales & Reports, and Settings. Admin can also jump straight into the
POS terminal to ring up sales.
"""

import os
import customtkinter as ctk
from tkinter import messagebox, filedialog
from datetime import datetime
from PIL import Image

import theme
import inventory
import sales
import auth
import printing
import barcode_tools
import reports_export
from recovery_dialogs import RecoverySetupDialog
from barcode_tools import BarcodeScannerDialog
from database import get_setting, set_setting, get_app_data_dir


class AdminWindow(ctk.CTk):
    NAV_ITEMS = ["Dashboard", "Products", "Categories", "Users", "Sales & Reports", "Z-Reports", "Settings"]

    def __init__(self, user):
        super().__init__()
        self.user = user
        self.title(f"Universal POS — Admin ({user['full_name']})")
        self.geometry("1400x860")
        self.minsize(1200, 720)
        self.configure(fg_color=theme.BG)

        self.nav_buttons = {}
        self._build_sidebar()
        self.content = ctk.CTkFrame(self, fg_color=theme.BG, corner_radius=0)
        self.content.pack(side="left", fill="both", expand=True)

        self._show_section("Dashboard")
        if not auth.has_recovery(self.user):
            self.after(600, self._prompt_recovery_setup)

    def _prompt_recovery_setup(self):
        """Admins who forget their password have nobody above them to reset it, so nudge them once."""
        if messagebox.askyesno(
            "Set Up Password Recovery",
            "You haven't set a recovery question for your account yet.\n\n"
            "Without one, a forgotten admin password can't be recovered.\n\n"
            "Set it up now?",
        ):
            RecoverySetupDialog(self, self.user, on_done=self._recovery_saved_for_self)

    def _recovery_saved_for_self(self):
        fresh = auth.get_user(self.user["id"])      # refresh so we don't nag again this session
        if fresh:
            self.user.update(fresh)
        if getattr(self, "users_scroll", None) is not None and self.users_scroll.winfo_exists():
            self._render_users()

    # ==================================================================
    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, fg_color=theme.SURFACE, width=220, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=20, pady=(24, 30))
        ctk.CTkLabel(brand, text="₱ Universal POS", font=theme.font(20, "bold")).pack(anchor="w")
        ctk.CTkLabel(brand, text="Admin Console", font=theme.font(11), text_color=theme.TEXT_MUTED).pack(anchor="w")

        for item in self.NAV_ITEMS:
            btn = ctk.CTkButton(
                sidebar, text=item, anchor="w", height=42, corner_radius=8,
                fg_color="transparent", hover_color=theme.CARD_HOVER, font=theme.font(13),
                command=lambda i=item: self._show_section(i),
            )
            btn.pack(fill="x", padx=14, pady=3)
            self.nav_buttons[item] = btn

        spacer = ctk.CTkFrame(sidebar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        ctk.CTkButton(sidebar, text="🖥  Open POS Terminal", height=42, corner_radius=8,
                      fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER, font=theme.font(12, "bold"),
                      command=self._open_pos).pack(fill="x", padx=14, pady=(4, 6))
        ctk.CTkButton(sidebar, text="Log Out", height=38, corner_radius=8,
                      fg_color=theme.CARD, hover_color=theme.CARD_HOVER, font=theme.font(12),
                      command=self._logout).pack(fill="x", padx=14, pady=(0, 20))

    def _highlight_nav(self, active):
        for name, btn in self.nav_buttons.items():
            btn.configure(fg_color=theme.ACCENT_SOFT if name == active else "transparent")

    def _show_section(self, name):
        self._highlight_nav(name)
        for w in self.content.winfo_children():
            w.destroy()

        if name == "Dashboard":
            self._section_dashboard()
        elif name == "Products":
            self._section_products()
        elif name == "Categories":
            self._section_categories()
        elif name == "Users":
            self._section_users()
        elif name == "Sales & Reports":
            self._section_reports()
        elif name == "Z-Reports":
            self._section_z_reports()
        elif name == "Settings":
            self._section_settings()

    def _page_header(self, title, subtitle=""):
        wrap = ctk.CTkFrame(self.content, fg_color="transparent")
        wrap.pack(fill="x", padx=30, pady=(26, 16))
        ctk.CTkLabel(wrap, text=title, font=theme.font(22, "bold")).pack(anchor="w")
        if subtitle:
            ctk.CTkLabel(wrap, text=subtitle, font=theme.font(12), text_color=theme.TEXT_MUTED).pack(anchor="w")
        return wrap

    # ==================================================================
    # DASHBOARD
    # ==================================================================
    def _section_dashboard(self):
        self._page_header("Dashboard", "Today's performance at a glance")

        start, end = sales.today_range()
        today_sales = sales.sales_between(start, end)
        completed = [s for s in today_sales if s["status"] == "COMPLETED"]
        gross = sum(s["total"] for s in completed)
        tx_count = len(completed)
        low_stock = inventory.low_stock_products()

        cards = ctk.CTkFrame(self.content, fg_color="transparent")
        cards.pack(fill="x", padx=30)
        stats = [
            ("Today's Sales", f"₱{gross:,.2f}", theme.SUCCESS),
            ("Transactions", str(tx_count), theme.ACCENT),
            ("Low Stock Items", str(len(low_stock)), theme.WARNING if low_stock else theme.SUCCESS),
            ("Active Products", str(len(inventory.list_products())), theme.ACCENT),
        ]
        for i, (label, value, color) in enumerate(stats):
            card = ctk.CTkFrame(cards, fg_color=theme.CARD, corner_radius=14, height=100)
            card.grid(row=0, column=i, sticky="nsew", padx=8, pady=4)
            cards.grid_columnconfigure(i, weight=1)
            card.grid_propagate(False)
            ctk.CTkLabel(card, text=label, font=theme.font(12), text_color=theme.TEXT_MUTED).pack(
                anchor="w", padx=18, pady=(16, 0))
            ctk.CTkLabel(card, text=value, font=theme.font(24, "bold"), text_color=color).pack(
                anchor="w", padx=18, pady=(2, 0))

        body = ctk.CTkFrame(self.content, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=30, pady=20)
        body.grid_columnconfigure(0, weight=6)
        body.grid_columnconfigure(1, weight=4)
        body.grid_rowconfigure(0, weight=1)

        recent_box = ctk.CTkFrame(body, fg_color=theme.CARD, corner_radius=14)
        recent_box.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        ctk.CTkLabel(recent_box, text="Recent Transactions", font=theme.font(14, "bold")).pack(
            anchor="w", padx=18, pady=(16, 8))
        recent_scroll = ctk.CTkScrollableFrame(recent_box, fg_color="transparent")
        recent_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        recent = sales.recent_sales(25)
        if not recent:
            ctk.CTkLabel(recent_scroll, text="No transactions yet.", text_color=theme.TEXT_MUTED).pack(pady=10)
        for s in recent:
            row = ctk.CTkFrame(recent_scroll, fg_color=theme.SURFACE, corner_radius=8)
            row.pack(fill="x", pady=3, padx=6)
            dt = datetime.fromisoformat(s["created_at"]).strftime("%m/%d %I:%M %p")
            status_color = theme.DANGER if s["status"] == "VOID" else theme.SUCCESS
            ctk.CTkLabel(row, text=f"{s['invoice_no']}  ·  {dt}  ·  {s['cashier_name']}",
                         font=theme.font(11), anchor="w").pack(side="left", padx=10, pady=8)
            ctk.CTkLabel(row, text=f"₱{s['total']:.2f}  [{s['status']}]", font=theme.font(11, "bold"),
                         text_color=status_color).pack(side="right", padx=10)

        low_box = ctk.CTkFrame(body, fg_color=theme.CARD, corner_radius=14)
        low_box.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        ctk.CTkLabel(low_box, text="⚠ Low Stock Alerts", font=theme.font(14, "bold")).pack(
            anchor="w", padx=18, pady=(16, 8))
        low_scroll = ctk.CTkScrollableFrame(low_box, fg_color="transparent")
        low_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        if not low_stock:
            ctk.CTkLabel(low_scroll, text="All stock levels healthy.", text_color=theme.SUCCESS).pack(pady=10)
        for p in low_stock:
            row = ctk.CTkFrame(low_scroll, fg_color=theme.SURFACE, corner_radius=8)
            row.pack(fill="x", pady=3, padx=6)
            ctk.CTkLabel(row, text=p["name"], font=theme.font(11), anchor="w").pack(side="left", padx=10, pady=8)
            ctk.CTkLabel(row, text=f"{p['stock_qty']:g} {p['unit']} left", font=theme.font(11, "bold"),
                         text_color=theme.DANGER).pack(side="right", padx=10)

    # ==================================================================
    # PRODUCTS
    # ==================================================================
    def _section_products(self):
        self._page_header("Products", "Manage your catalog, prices, and stock levels")

        toolbar = ctk.CTkFrame(self.content, fg_color="transparent")
        toolbar.pack(fill="x", padx=30)
        self.prod_search = ctk.CTkEntry(toolbar, width=280, height=36, corner_radius=8,
                                         placeholder_text="Search products...")
        self.prod_search.pack(side="left")
        self.prod_search.bind("<KeyRelease>", lambda e: self._render_products_table())
        ctk.CTkButton(toolbar, text="+ Add Product", height=36, corner_radius=8, fg_color=theme.ACCENT,
                      hover_color=theme.ACCENT_HOVER, command=self._open_product_dialog).pack(side="right")

        header_row = ctk.CTkFrame(self.content, fg_color="transparent")
        header_row.pack(fill="x", padx=30, pady=(14, 4))
        cols = [("Name", 3), ("Category", 2), ("Price", 1), ("Stock", 1), ("Status", 1), ("Actions", 2)]
        for text, weight in cols:
            header_row.grid_columnconfigure(cols.index((text, weight)), weight=weight)
            ctk.CTkLabel(header_row, text=text, font=theme.font(11, "bold"), text_color=theme.TEXT_MUTED).grid(
                row=0, column=cols.index((text, weight)), sticky="w", padx=6)

        self.products_scroll = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        self.products_scroll.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        self._render_products_table()

    def _render_products_table(self):
        for w in self.products_scroll.winfo_children():
            w.destroy()
        products = inventory.list_products(search=self.prod_search.get().strip(), active_only=False)
        if not products:
            ctk.CTkLabel(self.products_scroll, text="No products found.", text_color=theme.TEXT_MUTED).pack(pady=20)
            return

        for p in products:
            row = ctk.CTkFrame(self.products_scroll, fg_color=theme.CARD, corner_radius=10)
            row.pack(fill="x", pady=4)
            for i, weight in enumerate([3, 2, 1, 1, 1, 2]):
                row.grid_columnconfigure(i, weight=weight)

            ctk.CTkLabel(row, text=p["name"], font=theme.font(12), anchor="w").grid(
                row=0, column=0, sticky="w", padx=10, pady=12)
            ctk.CTkLabel(row, text=p["category_name"] or "—", font=theme.font(11), text_color=theme.TEXT_MUTED,
                         anchor="w").grid(row=0, column=1, sticky="w", padx=6)
            ctk.CTkLabel(row, text=f"₱{p['price']:.2f}", font=theme.font(11), anchor="w").grid(
                row=0, column=2, sticky="w", padx=6)
            stock_color = theme.DANGER if p["stock_qty"] <= p["reorder_level"] else theme.TEXT_PRIMARY
            ctk.CTkLabel(row, text=f"{p['stock_qty']:g} {p['unit']}", font=theme.font(11), text_color=stock_color,
                         anchor="w").grid(row=0, column=3, sticky="w", padx=6)
            status_text = "Active" if p["active"] else "Disabled"
            ctk.CTkLabel(row, text=status_text, font=theme.font(11),
                         text_color=theme.SUCCESS if p["active"] else theme.TEXT_MUTED).grid(
                row=0, column=4, sticky="w", padx=6)

            actions = ctk.CTkFrame(row, fg_color="transparent")
            actions.grid(row=0, column=5, sticky="e", padx=6)
            ctk.CTkButton(actions, text="Edit", width=56, height=28, corner_radius=6, font=theme.font(10),
                          fg_color=theme.CARD_HOVER,
                          command=lambda p=p: self._open_product_dialog(p)).pack(side="left", padx=3)
            ctk.CTkButton(actions, text="Restock", width=64, height=28, corner_radius=6, font=theme.font(10),
                          fg_color=theme.CARD_HOVER,
                          command=lambda p=p: self._open_restock_dialog(p)).pack(side="left", padx=3)
            toggle_text = "Disable" if p["active"] else "Enable"
            ctk.CTkButton(actions, text=toggle_text, width=64, height=28, corner_radius=6, font=theme.font(10),
                          fg_color=theme.DANGER if p["active"] else theme.SUCCESS,
                          hover_color=theme.DANGER_HOVER if p["active"] else theme.SUCCESS_HOVER,
                          command=lambda p=p: self._toggle_product(p)).pack(side="left", padx=3)

    def _toggle_product(self, product):
        inventory.set_product_active(product["id"], not product["active"])
        self._render_products_table()

    def _open_restock_dialog(self, product):
        dlg = ctk.CTkToplevel(self)
        dlg.title(f"Restock — {product['name']}")
        dlg.geometry("340x220")
        dlg.configure(fg_color=theme.BG)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text=f"Restock: {product['name']}", font=theme.font(14, "bold")).pack(pady=(20, 4))
        ctk.CTkLabel(dlg, text=f"Current stock: {product['stock_qty']:g} {product['unit']}",
                     font=theme.font(11), text_color=theme.TEXT_MUTED).pack(pady=(0, 12))

        entry = ctk.CTkEntry(dlg, width=200, height=36, corner_radius=8, placeholder_text="Qty to add")
        entry.pack()

        def confirm():
            try:
                qty = float(entry.get())
                if qty <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Invalid", "Enter a positive quantity.")
                return
            inventory.adjust_stock(product["id"], qty, reason="Manual restock")
            dlg.destroy()
            self._render_products_table()

        ctk.CTkButton(dlg, text="Add Stock", height=38, corner_radius=8, fg_color=theme.SUCCESS,
                      hover_color=theme.SUCCESS_HOVER, command=confirm).pack(pady=20, padx=30, fill="x")

    def _open_product_dialog(self, product=None):
        is_edit = product is not None
        dlg = ctk.CTkToplevel(self)
        dlg.title("Edit Product" if is_edit else "Add Product")
        dlg.geometry("460x760")
        dlg.configure(fg_color=theme.BG)
        dlg.grab_set()

        form = ctk.CTkScrollableFrame(dlg, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=24, pady=20)

        # ---- Photo section --------------------------------------------------
        state = {"image_path": product["image_path"] if is_edit and product.get("image_path") else None}

        photo_frame = ctk.CTkFrame(form, fg_color=theme.CARD, corner_radius=12, height=140)
        photo_frame.pack(fill="x", pady=(0, 16))
        photo_frame.pack_propagate(False)
        photo_preview = ctk.CTkLabel(photo_frame, text="No Photo", font=theme.font(11), text_color=theme.TEXT_MUTED)
        photo_preview.pack(side="left", padx=16, pady=16)

        def refresh_preview():
            path = state["image_path"]
            if path and os.path.exists(path):
                try:
                    img = Image.open(path).convert("RGB").resize((100, 100))
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(100, 100))
                    photo_preview.configure(image=ctk_img, text="")
                    photo_preview.image = ctk_img
                except Exception:
                    photo_preview.configure(image=None, text="No Photo")
            else:
                photo_preview.configure(image=None, text="No Photo")

        refresh_preview()

        def upload_photo():
            path = filedialog.askopenfilename(
                title="Select Product Photo",
                filetypes=[("Image files", "*.png *.jpg *.jpeg *.webp *.bmp")],
            )
            if not path:
                return
            state["image_path"] = inventory.save_product_image(path)
            refresh_preview()

        photo_btns = ctk.CTkFrame(photo_frame, fg_color="transparent")
        photo_btns.pack(side="left", padx=10)
        ctk.CTkButton(photo_btns, text="📁 Upload Photo", width=140, height=34, corner_radius=8,
                      fg_color=theme.CARD_HOVER, command=upload_photo).pack(pady=4)
        ctk.CTkButton(photo_btns, text="Remove Photo", width=140, height=30, corner_radius=8,
                      fg_color=theme.DANGER, hover_color=theme.DANGER_HOVER, font=theme.font(10),
                      command=lambda: (state.update(image_path=None), refresh_preview())).pack(pady=4)

        def field(label, default=""):
            ctk.CTkLabel(form, text=label, font=theme.font(11), text_color=theme.TEXT_MUTED).pack(anchor="w")
            e = ctk.CTkEntry(form, height=36, corner_radius=8)
            e.pack(fill="x", pady=(2, 12))
            if default:
                e.insert(0, str(default))
            return e

        name_e = field("Product Name", product["name"] if is_edit else "")

        # ---- Barcode section (entry + scan + generate label) -----------------
        ctk.CTkLabel(form, text="Barcode (optional)", font=theme.font(11), text_color=theme.TEXT_MUTED).pack(anchor="w")
        barcode_row = ctk.CTkFrame(form, fg_color="transparent")
        barcode_row.pack(fill="x", pady=(2, 12))
        barcode_e = ctk.CTkEntry(barcode_row, height=36, corner_radius=8)
        barcode_e.pack(side="left", fill="x", expand=True, padx=(0, 6))
        if is_edit and product["barcode"]:
            barcode_e.insert(0, product["barcode"])

        def scan_barcode():
            def on_scanned(code):
                barcode_e.delete(0, "end")
                barcode_e.insert(0, code)
            BarcodeScannerDialog(dlg, on_scanned)

        ctk.CTkButton(barcode_row, text="📷", width=40, height=36, corner_radius=8,
                      fg_color=theme.CARD_HOVER, command=scan_barcode).pack(side="left", padx=2)

        def generate_label():
            code = barcode_e.get().strip()
            if not code:
                messagebox.showwarning("No Barcode", "Enter or scan a barcode first.")
                return
            out_dir = os.path.join(get_app_data_dir(), "barcode_labels")
            os.makedirs(out_dir, exist_ok=True)
            path = barcode_tools.generate_barcode_image(code, os.path.join(out_dir, code))
            self._show_barcode_label_dialog(path)

        ctk.CTkButton(barcode_row, text="🏷", width=40, height=36, corner_radius=8,
                      fg_color=theme.CARD_HOVER, command=generate_label).pack(side="left", padx=2)

        ctk.CTkLabel(form, text="Category", font=theme.font(11), text_color=theme.TEXT_MUTED).pack(anchor="w")
        cats = inventory.list_categories()
        cat_names = [c["name"] for c in cats] or ["Uncategorized"]
        cat_var = ctk.StringVar(value=product["category_name"] if is_edit and product["category_name"] else cat_names[0])
        ctk.CTkOptionMenu(form, values=cat_names, variable=cat_var, height=36, corner_radius=8).pack(
            fill="x", pady=(2, 12))

        price_e = field("Selling Price (₱)", product["price"] if is_edit else "")
        cost_e = field("Cost Price (₱)", product["cost"] if is_edit else "0")
        stock_e = field("Stock Quantity", product["stock_qty"] if is_edit else "0")
        unit_e = field("Unit (pc, kg, pack, etc.)", product["unit"] if is_edit else "pc")
        reorder_e = field("Reorder Level (low-stock alert)", product["reorder_level"] if is_edit else "5")

        vat_var = ctk.BooleanVar(value=bool(product["vat_exempt"]) if is_edit else False)
        ctk.CTkCheckBox(form, text="VAT-Exempt Item", variable=vat_var).pack(anchor="w", pady=(0, 16))

        def save():
            try:
                name = name_e.get().strip()
                if not name:
                    raise ValueError("Name is required.")
                price = float(price_e.get())
                cost = float(cost_e.get() or 0)
                stock = float(stock_e.get() or 0)
                reorder = float(reorder_e.get() or 0)
                unit = unit_e.get().strip() or "pc"
                barcode = barcode_e.get().strip() or None
                category_id = None
                for c in cats:
                    if c["name"] == cat_var.get():
                        category_id = c["id"]
                        break
            except ValueError as e:
                messagebox.showerror("Invalid Input", str(e) if str(e) else "Please check your numeric fields.")
                return

            if is_edit:
                ok, msg = inventory.update_product(
                    product["id"], name=name, barcode=barcode, category_id=category_id, price=price,
                    cost=cost, unit=unit, reorder_level=reorder, vat_exempt=int(vat_var.get()),
                    image_path=state["image_path"],
                )
                if not ok:
                    messagebox.showerror("Error", msg)
                    return
            else:
                ok, msg = inventory.add_product(barcode, name, category_id, price, cost, stock, unit,
                                                 reorder, vat_var.get(), image_path=state["image_path"])
                if not ok:
                    messagebox.showerror("Error", msg)
                    return
            dlg.destroy()
            self._render_products_table()

        ctk.CTkButton(form, text="Save Product", height=42, corner_radius=8, fg_color=theme.ACCENT,
                      hover_color=theme.ACCENT_HOVER, font=theme.font(13, "bold"), command=save).pack(
            fill="x", pady=(6, 0))

    def _show_barcode_label_dialog(self, image_path):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Barcode Label")
        dlg.geometry("340x340")
        dlg.configure(fg_color=theme.BG)
        dlg.grab_set()

        img = Image.open(image_path)
        w, h = img.size
        scale = min(280 / w, 160 / h)
        preview = img.resize((int(w * scale), int(h * scale)))
        ctk_img = ctk.CTkImage(light_image=preview, dark_image=preview, size=preview.size)
        label = ctk.CTkLabel(dlg, image=ctk_img, text="")
        label.image = ctk_img
        label.pack(pady=(20, 10))

        ctk.CTkLabel(dlg, text=f"Saved to:\n{image_path}", font=theme.font(9), text_color=theme.TEXT_MUTED,
                     wraplength=300, justify="center").pack(pady=(0, 12))

        def do_print():
            ok, msg = printing.print_file(image_path)
            if not ok:
                messagebox.showinfo("Print", msg)

        btn_row = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 16))
        ctk.CTkButton(btn_row, text="🖨 Print Label", height=38, corner_radius=8, fg_color=theme.ACCENT,
                      hover_color=theme.ACCENT_HOVER, command=do_print).pack(side="left", expand=True, fill="x", padx=(0, 6))
        ctk.CTkButton(btn_row, text="Close", height=38, corner_radius=8, fg_color=theme.CARD,
                      hover_color=theme.CARD_HOVER, command=dlg.destroy).pack(side="left", expand=True, fill="x", padx=(6, 0))

    # ==================================================================
    # CATEGORIES
    # ==================================================================
    def _section_categories(self):
        self._page_header("Categories", "Group your products for faster browsing")

        add_frame = ctk.CTkFrame(self.content, fg_color=theme.CARD, corner_radius=12)
        add_frame.pack(fill="x", padx=30, pady=(0, 16))
        inner = ctk.CTkFrame(add_frame, fg_color="transparent")
        inner.pack(padx=16, pady=16, fill="x")
        self.new_cat_entry = ctk.CTkEntry(inner, height=36, corner_radius=8, placeholder_text="New category name")
        self.new_cat_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(inner, text="+ Add", width=100, height=36, corner_radius=8, fg_color=theme.ACCENT,
                      hover_color=theme.ACCENT_HOVER, command=self._add_category).pack(side="right")

        self.cat_scroll = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        self.cat_scroll.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        self._render_categories()

    def _render_categories(self):
        for w in self.cat_scroll.winfo_children():
            w.destroy()
        cats = inventory.list_categories()
        if not cats:
            ctk.CTkLabel(self.cat_scroll, text="No categories yet.", text_color=theme.TEXT_MUTED).pack(pady=20)
            return
        for c in cats:
            row = ctk.CTkFrame(self.cat_scroll, fg_color=theme.CARD, corner_radius=10)
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text=c["name"], font=theme.font(12)).pack(side="left", padx=16, pady=12)
            count = len(inventory.list_products(category_id=c["id"], active_only=False))
            ctk.CTkLabel(row, text=f"{count} product(s)", font=theme.font(11),
                         text_color=theme.TEXT_MUTED).pack(side="right", padx=16)

    def _add_category(self):
        name = self.new_cat_entry.get().strip()
        if not name:
            return
        ok, msg = inventory.add_category(name)
        if not ok:
            messagebox.showerror("Error", "Category already exists or is invalid.")
            return
        self.new_cat_entry.delete(0, "end")
        self._render_categories()

    # ==================================================================
    # USERS
    # ==================================================================
    def _section_users(self):
        self._page_header("Users", "Manage admin and cashier accounts")

        toolbar = ctk.CTkFrame(self.content, fg_color="transparent")
        toolbar.pack(fill="x", padx=30)
        ctk.CTkButton(toolbar, text="+ Add User", height=36, corner_radius=8, fg_color=theme.ACCENT,
                      hover_color=theme.ACCENT_HOVER, command=self._open_add_user_dialog).pack(side="right")

        self.users_scroll = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        self.users_scroll.pack(fill="both", expand=True, padx=30, pady=20)
        self._render_users()

    def _render_users(self):
        for w in self.users_scroll.winfo_children():
            w.destroy()
        for u in auth.list_users():
            row = ctk.CTkFrame(self.users_scroll, fg_color=theme.CARD, corner_radius=10)
            row.pack(fill="x", pady=4)
            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", padx=16, pady=12)
            ctk.CTkLabel(info, text=f"{u['full_name']}  (@{u['username']})", font=theme.font(12, "bold"),
                         anchor="w").pack(anchor="w")
            recovery_ok = auth.has_recovery(u)
            ctk.CTkLabel(info, text=f"{u['role'].title()}  ·  {'Active' if u['active'] else 'Disabled'}"
                                    f"  ·  {'Recovery set' if recovery_ok else 'No recovery question'}",
                         font=theme.font(10), text_color=theme.TEXT_MUTED).pack(anchor="w")

            actions = ctk.CTkFrame(row, fg_color="transparent")
            actions.pack(side="right", padx=16)
            ctk.CTkButton(actions, text="Recovery", width=90, height=28, corner_radius=6, font=theme.font(10),
                          fg_color=theme.CARD_HOVER,
                          command=lambda u=u: self._recovery_dialog(u)).pack(side="left", padx=3)
            ctk.CTkButton(actions, text="Reset Password", width=120, height=28, corner_radius=6, font=theme.font(10),
                          fg_color=theme.CARD_HOVER,
                          command=lambda u=u: self._reset_password_dialog(u)).pack(side="left", padx=3)
            if u["username"] != "admin":
                toggle_text = "Disable" if u["active"] else "Enable"
                ctk.CTkButton(actions, text=toggle_text, width=80, height=28, corner_radius=6, font=theme.font(10),
                              fg_color=theme.DANGER if u["active"] else theme.SUCCESS,
                              hover_color=theme.DANGER_HOVER if u["active"] else theme.SUCCESS_HOVER,
                              command=lambda u=u: self._toggle_user(u)).pack(side="left", padx=3)

    def _toggle_user(self, u):
        auth.set_user_active(u["id"], not u["active"])
        self._render_users()

    def _recovery_dialog(self, u):
        def done():
            if u["id"] == self.user.get("id"):
                self._recovery_saved_for_self()
            self._render_users()
        RecoverySetupDialog(self, u, on_done=done)

    def _reset_password_dialog(self, u):
        dlg = ctk.CTkToplevel(self)
        dlg.title(f"Reset Password — {u['username']}")
        dlg.geometry("340x220")
        dlg.configure(fg_color=theme.BG)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text=f"New password for @{u['username']}", font=theme.font(13, "bold")).pack(pady=(20, 10))
        entry = ctk.CTkEntry(dlg, width=220, height=36, corner_radius=8, show="•")
        entry.pack()

        def confirm():
            pw = entry.get()
            if len(pw) < auth.MIN_PASSWORD_LENGTH:
                messagebox.showerror("Too Short", f"Password should be at least {auth.MIN_PASSWORD_LENGTH} characters.")
                return
            auth.reset_password(u["id"], pw)
            dlg.destroy()
            messagebox.showinfo("Done", "Password updated.")

        ctk.CTkButton(dlg, text="Update Password", height=38, corner_radius=8, fg_color=theme.ACCENT,
                      hover_color=theme.ACCENT_HOVER, command=confirm).pack(pady=20, padx=30, fill="x")

    def _open_add_user_dialog(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Add User")
        dlg.geometry("380x420")
        dlg.configure(fg_color=theme.BG)
        dlg.grab_set()

        form = ctk.CTkFrame(dlg, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=24, pady=20)

        def field(label):
            ctk.CTkLabel(form, text=label, font=theme.font(11), text_color=theme.TEXT_MUTED).pack(anchor="w")
            e = ctk.CTkEntry(form, height=36, corner_radius=8)
            e.pack(fill="x", pady=(2, 12))
            return e

        full_name_e = field("Full Name")
        username_e = field("Username")
        password_e = field("Password")
        password_e.configure(show="•")

        ctk.CTkLabel(form, text="Role", font=theme.font(11), text_color=theme.TEXT_MUTED).pack(anchor="w")
        role_var = ctk.StringVar(value="cashier")
        ctk.CTkOptionMenu(form, values=["cashier", "admin"], variable=role_var, height=36, corner_radius=8).pack(
            fill="x", pady=(2, 16))

        def save():
            if not full_name_e.get().strip() or not username_e.get().strip() or not password_e.get():
                messagebox.showerror("Missing Info", "Please fill in all fields.")
                return
            ok, msg = auth.create_user(username_e.get(), password_e.get(), full_name_e.get(), role_var.get())
            if not ok:
                messagebox.showerror("Error", msg)
                return
            dlg.destroy()
            self._render_users()

        ctk.CTkButton(form, text="Create User", height=42, corner_radius=8, fg_color=theme.ACCENT,
                      hover_color=theme.ACCENT_HOVER, font=theme.font(13, "bold"), command=save).pack(fill="x")

    # ==================================================================
    # SALES & REPORTS
    # ==================================================================
    def _section_reports(self):
        self._page_header("Sales & Reports", "Review transactions, void sales, and see top sellers")

        toolbar = ctk.CTkFrame(self.content, fg_color="transparent")
        toolbar.pack(fill="x", padx=30)
        ctk.CTkLabel(toolbar, text="Showing:", font=theme.font(12)).pack(side="left")
        self.report_range_var = ctk.StringVar(value="Today")
        ctk.CTkOptionMenu(toolbar, values=["Today", "Last 7 Days", "Last 30 Days", "All Time"],
                          variable=self.report_range_var, height=34, corner_radius=8,
                          command=lambda v: self._render_reports()).pack(side="left", padx=10)

        ctk.CTkButton(toolbar, text="🖨 Print Report", width=130, height=34, corner_radius=8,
                      fg_color=theme.CARD_HOVER, hover_color=theme.BORDER,
                      command=self._print_sales_report).pack(side="right", padx=(6, 0))
        ctk.CTkOptionMenu(toolbar, values=["Export as PDF", "Export as Excel", "Export as Word"],
                          command=self._export_sales_report, width=160, height=34, corner_radius=8,
                          fg_color=theme.ACCENT, button_color=theme.ACCENT_HOVER,
                          dynamic_resizing=False).pack(side="right", padx=(6, 0))

        body = ctk.CTkFrame(self.content, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=30, pady=16)
        body.grid_columnconfigure(0, weight=7)
        body.grid_columnconfigure(1, weight=3)
        body.grid_rowconfigure(0, weight=1)

        self.tx_box = ctk.CTkFrame(body, fg_color=theme.CARD, corner_radius=14)
        self.tx_box.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        ctk.CTkLabel(self.tx_box, text="Transactions", font=theme.font(14, "bold")).pack(anchor="w", padx=18, pady=(16, 8))
        self.tx_scroll = ctk.CTkScrollableFrame(self.tx_box, fg_color="transparent")
        self.tx_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 12))

        self.top_box = ctk.CTkFrame(body, fg_color=theme.CARD, corner_radius=14)
        self.top_box.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        ctk.CTkLabel(self.top_box, text="Top Products", font=theme.font(14, "bold")).pack(anchor="w", padx=18, pady=(16, 8))
        self.top_scroll = ctk.CTkScrollableFrame(self.top_box, fg_color="transparent")
        self.top_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 12))

        self._render_reports()

    def _sales_report_data(self):
        """Builds (title, subtitle, headers, rows, summary_lines) for the currently filtered range."""
        start, end = self._get_range_bounds()
        rows_raw = sales.sales_between(start, end)
        rows_raw.reverse()

        headers = ["Invoice No", "Date/Time", "Cashier", "Payment", "Subtotal", "Discount", "VAT", "Total", "Status"]
        rows = []
        gross = 0.0
        net = 0.0
        completed = 0
        for s in rows_raw:
            dt = datetime.fromisoformat(s["created_at"]).strftime("%m/%d/%Y %I:%M %p")
            rows.append([
                s["invoice_no"], dt, s["cashier_name"], s["payment_method"],
                f"₱{s['subtotal']:.2f}", f"₱{s['discount_amount']:.2f}", f"₱{s['vat_amount']:.2f}",
                f"₱{s['total']:.2f}", s["status"],
            ])
            if s["status"] == "COMPLETED":
                gross += s["subtotal"]
                net += s["total"]
                completed += 1

        summary_lines = [
            ("Range:", self.report_range_var.get()),
            ("Total Transactions:", str(len(rows_raw))),
            ("Completed:", str(completed)),
            ("Gross Sales:", f"₱{gross:.2f}"),
            ("Net Sales:", f"₱{net:.2f}"),
        ]
        title = "Universal POS — Sales Report"
        subtitle = f"{self.report_range_var.get()}  ·  Generated {datetime.now().strftime('%m/%d/%Y %I:%M %p')}"
        return title, subtitle, headers, rows, summary_lines

    def _export_sales_report(self, choice):
        fmt_map = {"Export as PDF": ("pdf", ".pdf"), "Export as Excel": ("xlsx", ".xlsx"), "Export as Word": ("docx", ".docx")}
        fmt, ext = fmt_map[choice]
        title, subtitle, headers, rows, summary_lines = self._sales_report_data()
        if not rows:
            messagebox.showinfo("No Data", "There are no transactions in this range to export.")
            return
        path = filedialog.asksaveasfilename(
            title="Save Sales Report", defaultextension=ext,
            initialfile=f"Sales_Report_{datetime.now().strftime('%Y%m%d')}{ext}",
            filetypes=[(choice, f"*{ext}")],
        )
        if not path:
            return
        try:
            reports_export.export_report(fmt, path, title, subtitle, headers, rows, summary_lines)
            messagebox.showinfo("Exported", f"Report saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))

    def _print_sales_report(self):
        title, subtitle, headers, rows, summary_lines = self._sales_report_data()
        if not rows:
            messagebox.showinfo("No Data", "There are no transactions in this range to print.")
            return
        text_lines = [title, subtitle, "-" * 60]
        for row in rows:
            text_lines.append(" | ".join(str(c) for c in row))
        text_lines.append("-" * 60)
        for label, value in summary_lines:
            text_lines.append(f"{label} {value}")
        text = "\n".join(text_lines)

        if not printing.printing_supported():
            messagebox.showinfo(
                "Printing Not Available",
                "Direct printing needs the 'pywin32' package on Windows.\n\n"
                "Run: pip install pywin32",
            )
            return
        printer_name = get_setting("receipt_printer_name", "") or None
        ok, msg = printing.print_receipt_text(text, printer_name)
        if ok:
            messagebox.showinfo("Printing", msg)
        else:
            messagebox.showerror("Print Failed", msg)

    def _range_bounds(self, label):
        from datetime import date, timedelta
        end = datetime.now().isoformat()
        if label == "Today":
            start = date.today().isoformat() + "T00:00:00"
        elif label == "Last 7 Days":
            start = (date.today() - timedelta(days=7)).isoformat() + "T00:00:00"
        elif label == "Last 30 Days":
            start = (date.today() - timedelta(days=30)).isoformat() + "T00:00:00"
        else:
            start = "0000-01-01T00:00:00"
        return start, end

    def _get_range_bounds(self):
        return self._range_bounds(self.report_range_var.get())

    def _render_reports(self):
        start, end = self._get_range_bounds()
        for w in self.tx_scroll.winfo_children():
            w.destroy()
        for w in self.top_scroll.winfo_children():
            w.destroy()

        rows = sales.sales_between(start, end)
        rows.reverse()
        if not rows:
            ctk.CTkLabel(self.tx_scroll, text="No transactions in this range.", text_color=theme.TEXT_MUTED).pack(pady=20)
        for s in rows:
            row = ctk.CTkFrame(self.tx_scroll, fg_color=theme.SURFACE, corner_radius=8)
            row.pack(fill="x", pady=3)
            dt = datetime.fromisoformat(s["created_at"]).strftime("%m/%d/%Y %I:%M %p")
            left = ctk.CTkFrame(row, fg_color="transparent")
            left.pack(side="left", padx=12, pady=8)
            ctk.CTkLabel(left, text=f"{s['invoice_no']}", font=theme.font(12, "bold"), anchor="w").pack(anchor="w")
            ctk.CTkLabel(left, text=f"{dt}  ·  {s['cashier_name']}  ·  {s['payment_method']}",
                         font=theme.font(10), text_color=theme.TEXT_MUTED, anchor="w").pack(anchor="w")

            right = ctk.CTkFrame(row, fg_color="transparent")
            right.pack(side="right", padx=12)
            status_color = theme.DANGER if s["status"] == "VOID" else theme.SUCCESS
            ctk.CTkLabel(right, text=f"₱{s['total']:.2f}", font=theme.font(12, "bold")).pack(side="left", padx=8)
            ctk.CTkLabel(right, text=s["status"], font=theme.font(10), text_color=status_color).pack(side="left", padx=4)
            if s["status"] == "COMPLETED":
                ctk.CTkButton(right, text="Void", width=54, height=26, corner_radius=6, font=theme.font(10),
                              fg_color=theme.DANGER, hover_color=theme.DANGER_HOVER,
                              command=lambda s=s: self._void_sale(s)).pack(side="left", padx=4)

        top = sales.top_products(start, end, limit=15)
        if not top:
            ctk.CTkLabel(self.top_scroll, text="No sales data yet.", text_color=theme.TEXT_MUTED).pack(pady=20)
        for t in top:
            row = ctk.CTkFrame(self.top_scroll, fg_color=theme.SURFACE, corner_radius=8)
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(row, text=t["product_name"], font=theme.font(11), anchor="w").pack(
                side="left", padx=10, pady=8)
            ctk.CTkLabel(row, text=f"{t['total_qty']:g} sold · ₱{t['total_sales']:.2f}",
                         font=theme.font(10), text_color=theme.TEXT_MUTED).pack(side="right", padx=10)

    def _void_sale(self, s):
        if not messagebox.askyesno("Void Sale", f"Void invoice {s['invoice_no']}? Stock will be restored."):
            return
        ok, msg = sales.void_sale(s["id"])
        if not ok:
            messagebox.showerror("Error", msg)
        self._render_reports()

    # ==================================================================
    # Z-REPORTS (per-shift end-of-day closeout history)
    # ==================================================================
    def _section_z_reports(self):
        self._page_header("Z-Reports", "End-of-shift closeout history, grouped by day")

        toolbar = ctk.CTkFrame(self.content, fg_color="transparent")
        toolbar.pack(fill="x", padx=30)
        ctk.CTkLabel(toolbar, text="Showing:", font=theme.font(12)).pack(side="left")
        self.zreport_range_var = ctk.StringVar(value="Last 7 Days")
        ctk.CTkOptionMenu(toolbar, values=["Today", "Last 7 Days", "Last 30 Days", "All Time"],
                          variable=self.zreport_range_var, height=34, corner_radius=8,
                          command=lambda v: self._render_z_reports()).pack(side="left", padx=10)

        ctk.CTkOptionMenu(toolbar, values=["Export List as PDF", "Export List as Excel", "Export List as Word"],
                          command=self._export_z_report_list, width=190, height=34, corner_radius=8,
                          fg_color=theme.ACCENT, button_color=theme.ACCENT_HOVER,
                          dynamic_resizing=False).pack(side="right")

        self.zreports_scroll = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        self.zreports_scroll.pack(fill="both", expand=True, padx=30, pady=(16, 20))
        self._render_z_reports()

    def _export_z_report_list(self, choice):
        fmt_map = {"Export List as PDF": ("pdf", ".pdf"), "Export List as Excel": ("xlsx", ".xlsx"),
                   "Export List as Word": ("docx", ".docx")}
        fmt, ext = fmt_map[choice]
        start, end = self._range_bounds(self.zreport_range_var.get())
        shifts = sales.list_shifts(start_iso=start, end_iso=end, closed_only=True)
        if not shifts:
            messagebox.showinfo("No Data", "There are no closed shifts (Z-Readings) in this range.")
            return

        headers = ["Date", "Cashier", "Reading No.", "Opened", "Closed", "Starting Cash", "Ending Cash"]
        rows = []
        for sh in shifts:
            opened_dt = datetime.fromisoformat(sh["opened_at"])
            closed_dt = datetime.fromisoformat(sh["closed_at"])
            rows.append([
                opened_dt.strftime("%m/%d/%Y"), sh["cashier_name"], f"{sh['last_reading_no']:04d}",
                opened_dt.strftime("%I:%M %p"), closed_dt.strftime("%I:%M %p"),
                f"₱{sh['starting_cash']:.2f}", f"₱{sh['ending_cash']:.2f}",
            ])

        path = filedialog.asksaveasfilename(
            title="Save Z-Report List", defaultextension=ext,
            initialfile=f"Z_Reports_{datetime.now().strftime('%Y%m%d')}{ext}",
            filetypes=[(choice, f"*{ext}")],
        )
        if not path:
            return
        try:
            reports_export.export_report(
                fmt, path, "Universal POS — Z-Reading History", self.zreport_range_var.get(),
                headers, rows,
            )
            messagebox.showinfo("Exported", f"Report saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))

    def _render_z_reports(self):
        for w in self.zreports_scroll.winfo_children():
            w.destroy()

        start, end = self._range_bounds(self.zreport_range_var.get())
        shifts = sales.list_shifts(start_iso=start, end_iso=end, closed_only=True)

        if not shifts:
            ctk.CTkLabel(self.zreports_scroll, text="No closed shifts (Z-Readings) in this range.",
                         text_color=theme.TEXT_MUTED).pack(pady=20)
            return

        # Group by the calendar date the shift was opened on
        groups = {}
        for sh in shifts:
            day = datetime.fromisoformat(sh["opened_at"]).strftime("%A, %B %d, %Y")
            groups.setdefault(day, []).append(sh)

        for day, day_shifts in groups.items():
            day_header = ctk.CTkFrame(self.zreports_scroll, fg_color="transparent")
            day_header.pack(fill="x", pady=(14, 4))
            ctk.CTkLabel(day_header, text=day, font=theme.font(13, "bold"),
                         text_color=theme.ACCENT).pack(anchor="w")

            for sh in day_shifts:
                row = ctk.CTkFrame(self.zreports_scroll, fg_color=theme.CARD, corner_radius=10)
                row.pack(fill="x", pady=4)

                opened = datetime.fromisoformat(sh["opened_at"]).strftime("%I:%M %p")
                closed = datetime.fromisoformat(sh["closed_at"]).strftime("%I:%M %p")

                left = ctk.CTkFrame(row, fg_color="transparent")
                left.pack(side="left", padx=16, pady=12)
                ctk.CTkLabel(left, text=f"{sh['cashier_name']}  ·  Reading No. {sh['last_reading_no']:04d}",
                             font=theme.font(12, "bold"), anchor="w").pack(anchor="w")
                ctk.CTkLabel(left, text=f"Shift: {opened} – {closed}", font=theme.font(10),
                             text_color=theme.TEXT_MUTED, anchor="w").pack(anchor="w")

                right = ctk.CTkFrame(row, fg_color="transparent")
                right.pack(side="right", padx=16)
                ctk.CTkLabel(right, text=f"Ending Cash: ₱{sh['ending_cash']:.2f}", font=theme.font(11),
                             text_color=theme.SUCCESS).pack(side="left", padx=10)
                ctk.CTkButton(right, text="View Full Report", width=130, height=30, corner_radius=6,
                              font=theme.font(11), fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
                              command=lambda sh=sh: self._open_z_report_dialog(sh)).pack(side="left", padx=4)

    def _open_z_report_dialog(self, shift):
        summary = sales.shift_summary(shift, end_iso=shift["closed_at"])

        dlg = ctk.CTkToplevel(self)
        dlg.title(f"Z-Reading — {shift['cashier_name']}")
        dlg.geometry("400x560")
        dlg.configure(fg_color=theme.BG)
        dlg.grab_set()

        opened_dt = datetime.fromisoformat(shift["opened_at"])
        closed_dt = datetime.fromisoformat(shift["closed_at"])

        ctk.CTkLabel(dlg, text="Z-READING (End of Shift)", font=theme.font(16, "bold")).pack(pady=(20, 2))
        ctk.CTkLabel(dlg, text=f"Reading No. {shift['last_reading_no']:04d}   |   {shift['cashier_name']}",
                     font=theme.font(11), text_color=theme.TEXT_MUTED).pack(pady=(0, 2))
        ctk.CTkLabel(dlg, text=f"{opened_dt.strftime('%b %d, %Y %I:%M %p')} – {closed_dt.strftime('%I:%M %p')}",
                     font=theme.font(10), text_color=theme.TEXT_MUTED).pack(pady=(0, 14))

        box = ctk.CTkFrame(dlg, fg_color=theme.CARD, corner_radius=12)
        box.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        def row(label, value, bold=False):
            r = ctk.CTkFrame(box, fg_color="transparent")
            r.pack(fill="x", padx=16, pady=4)
            ctk.CTkLabel(r, text=label, font=theme.font(12, "bold" if bold else "normal")).pack(side="left")
            ctk.CTkLabel(r, text=value, font=theme.font(12, "bold" if bold else "normal"),
                         text_color=theme.ACCENT if bold else theme.TEXT_PRIMARY).pack(side="right")

        row("Starting Cash:", f"₱{shift['starting_cash']:.2f}")
        row("Transactions:", str(summary["transaction_count"]))
        row("Gross Sales:", f"₱{summary['gross_sales']:.2f}")
        row("Discounts:", f"₱{summary['total_discounts']:.2f}")
        row("VAT Collected:", f"₱{summary['total_vat']:.2f}")
        row("Net Sales:", f"₱{summary['net_sales']:.2f}", bold=True)
        ctk.CTkLabel(box, text="").pack(pady=2)
        row("Cash Sales:", f"₱{summary['cash_sales']:.2f}")
        row("Non-Cash Sales:", f"₱{summary['non_cash_sales']:.2f}")
        row("Expected Cash:", f"₱{summary['expected_cash']:.2f}", bold=True)
        row("Actual Ending Cash:", f"₱{shift['ending_cash']:.2f}", bold=True)
        variance = round(shift["ending_cash"] - summary["expected_cash"], 2)
        row("Cash Variance:", f"{'+' if variance >= 0 else ''}₱{variance:.2f}")

        def build_report_data():
            headers = ["Metric", "Value"]
            rows_data = [
                ["Starting Cash", f"₱{shift['starting_cash']:.2f}"],
                ["Transactions", str(summary["transaction_count"])],
                ["Gross Sales", f"₱{summary['gross_sales']:.2f}"],
                ["Discounts", f"₱{summary['total_discounts']:.2f}"],
                ["VAT Collected", f"₱{summary['total_vat']:.2f}"],
                ["Net Sales", f"₱{summary['net_sales']:.2f}"],
                ["Cash Sales", f"₱{summary['cash_sales']:.2f}"],
                ["Non-Cash Sales", f"₱{summary['non_cash_sales']:.2f}"],
                ["Expected Cash", f"₱{summary['expected_cash']:.2f}"],
                ["Actual Ending Cash", f"₱{shift['ending_cash']:.2f}"],
                ["Cash Variance", f"{'+' if variance >= 0 else ''}₱{variance:.2f}"],
            ]
            title = f"Z-Reading No. {shift['last_reading_no']:04d} — {shift['cashier_name']}"
            subtitle = f"{opened_dt.strftime('%b %d, %Y %I:%M %p')} – {closed_dt.strftime('%I:%M %p')}"
            return title, subtitle, headers, rows_data

        def do_export(choice):
            fmt_map = {"Export as PDF": ("pdf", ".pdf"), "Export as Excel": ("xlsx", ".xlsx"),
                       "Export as Word": ("docx", ".docx")}
            fmt, ext = fmt_map[choice]
            title, subtitle, headers, rows_data = build_report_data()
            path = filedialog.asksaveasfilename(
                title="Save Z-Reading Report", defaultextension=ext,
                initialfile=f"ZReading_{shift['last_reading_no']:04d}{ext}",
                filetypes=[(choice, f"*{ext}")],
            )
            if not path:
                return
            try:
                reports_export.export_report(fmt, path, title, subtitle, headers, rows_data)
                messagebox.showinfo("Exported", f"Report saved to:\n{path}")
            except Exception as e:
                messagebox.showerror("Export Failed", str(e))

        def do_print():
            title, subtitle, headers, rows_data = build_report_data()
            text = f"{title}\n{subtitle}\n" + ("-" * 40) + "\n"
            for label, value in rows_data:
                text += f"{label:<22} {value}\n"
            if not printing.printing_supported():
                messagebox.showinfo("Printing Not Available",
                                     "Direct printing needs the 'pywin32' package on Windows.")
                return
            printer_name = get_setting("receipt_printer_name", "") or None
            ok, msg = printing.print_receipt_text(text, printer_name)
            (messagebox.showinfo if ok else messagebox.showerror)("Printing", msg)

        btn_row = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 8))
        ctk.CTkButton(btn_row, text="🖨 Print", height=36, corner_radius=8, fg_color=theme.CARD_HOVER,
                      hover_color=theme.BORDER, command=do_print).pack(side="left", expand=True, fill="x", padx=(0, 6))
        ctk.CTkOptionMenu(btn_row, values=["Export as PDF", "Export as Excel", "Export as Word"],
                          command=do_export, height=36, corner_radius=8, fg_color=theme.ACCENT,
                          button_color=theme.ACCENT_HOVER, dynamic_resizing=False).pack(
            side="left", expand=True, fill="x", padx=(6, 0))

        ctk.CTkButton(dlg, text="Close", height=38, corner_radius=8, fg_color=theme.CARD,
                      hover_color=theme.CARD_HOVER, command=dlg.destroy).pack(fill="x", padx=20, pady=(0, 20))

    # ==================================================================
    # SETTINGS
    # ==================================================================
    def _section_settings(self):
        self._page_header("Settings", "Store information and receipt printer setup")

        scroll = ctk.CTkScrollableFrame(self.content, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        # ---- Store info card -----------------------------------------------
        box = ctk.CTkFrame(scroll, fg_color=theme.CARD, corner_radius=14)
        box.pack(fill="x", pady=(0, 16))
        form = ctk.CTkFrame(box, fg_color="transparent")
        form.pack(fill="x", padx=24, pady=24)

        ctk.CTkLabel(form, text="Store Information", font=theme.font(14, "bold")).pack(anchor="w", pady=(0, 12))

        def field(label, key, container=None):
            container = container or form
            ctk.CTkLabel(container, text=label, font=theme.font(11), text_color=theme.TEXT_MUTED).pack(anchor="w")
            e = ctk.CTkEntry(container, height=36, corner_radius=8)
            e.insert(0, get_setting(key, ""))
            e.pack(fill="x", pady=(2, 14))
            return e

        name_e = field("Store Name", "store_name")
        address_e = field("Store Address", "store_address")
        tin_e = field("TIN (Tax Identification Number)", "store_tin")
        footer_e = field("Receipt Footer Message", "receipt_footer")

        def save_store():
            set_setting("store_name", name_e.get().strip())
            set_setting("store_address", address_e.get().strip())
            set_setting("store_tin", tin_e.get().strip())
            set_setting("receipt_footer", footer_e.get().strip())
            messagebox.showinfo("Saved", "Store settings updated.")

        ctk.CTkButton(form, text="Save Store Settings", height=42, corner_radius=8, fg_color=theme.ACCENT,
                      hover_color=theme.ACCENT_HOVER, font=theme.font(13, "bold"), command=save_store).pack(fill="x")

        # ---- Receipt printer card -------------------------------------------
        pbox = ctk.CTkFrame(scroll, fg_color=theme.CARD, corner_radius=14)
        pbox.pack(fill="x", pady=(0, 16))
        pform = ctk.CTkFrame(pbox, fg_color="transparent")
        pform.pack(fill="x", padx=24, pady=24)

        ctk.CTkLabel(pform, text="🖨 Receipt Printer", font=theme.font(14, "bold")).pack(anchor="w", pady=(0, 4))

        support_ok = printing.printing_supported()
        status_text = "Printer support detected." if support_ok else \
            "Printing needs the 'pywin32' package (Windows only). Run: pip install pywin32"
        ctk.CTkLabel(pform, text=status_text, font=theme.font(11),
                     text_color=theme.SUCCESS if support_ok else theme.WARNING, wraplength=500,
                     justify="left").pack(anchor="w", pady=(0, 14))

        ctk.CTkLabel(pform, text="Printer", font=theme.font(11), text_color=theme.TEXT_MUTED).pack(anchor="w")
        printers = printing.list_printers()
        printer_options = ["System Default"] + printers
        current_printer = get_setting("receipt_printer_name", "")
        default_value = current_printer if current_printer in printers else "System Default"
        self.printer_var = ctk.StringVar(value=default_value)
        ctk.CTkOptionMenu(pform, values=printer_options if printer_options != ["System Default"] else
                          ["System Default (no other printers detected)"],
                          variable=self.printer_var, height=36, corner_radius=8).pack(fill="x", pady=(2, 14))

        self.auto_print_var = ctk.BooleanVar(value=get_setting("auto_print_receipt", "0") == "1")
        ctk.CTkCheckBox(pform, text="Automatically print the receipt after every completed sale",
                         variable=self.auto_print_var).pack(anchor="w", pady=(0, 16))

        btn_row = ctk.CTkFrame(pform, fg_color="transparent")
        btn_row.pack(fill="x")

        def save_printer():
            chosen = self.printer_var.get()
            set_setting("receipt_printer_name", "" if chosen.startswith("System Default") else chosen)
            set_setting("auto_print_receipt", "1" if self.auto_print_var.get() else "0")
            messagebox.showinfo("Saved", "Printer settings updated.")

        def test_print():
            printer_name = None if self.printer_var.get().startswith("System Default") else self.printer_var.get()
            ok, msg = printing.test_print(printer_name)
            if ok:
                messagebox.showinfo("Test Print", msg)
            else:
                messagebox.showerror("Test Print Failed", msg)

        ctk.CTkButton(btn_row, text="Save Printer Settings", height=40, corner_radius=8, fg_color=theme.ACCENT,
                      hover_color=theme.ACCENT_HOVER, font=theme.font(12, "bold"), command=save_printer).pack(
            side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(btn_row, text="Test Print", height=40, corner_radius=8, fg_color=theme.CARD_HOVER,
                      hover_color=theme.BORDER, font=theme.font(12), command=test_print).pack(
            side="left", fill="x", expand=True, padx=(6, 0))

        # ---- Help / setup instructions ---------------------------------------
        help_box = ctk.CTkFrame(scroll, fg_color=theme.CARD, corner_radius=14)
        help_box.pack(fill="x")
        help_inner = ctk.CTkFrame(help_box, fg_color="transparent")
        help_inner.pack(fill="x", padx=24, pady=20)
        ctk.CTkLabel(help_inner, text="How to set up your receipt printer", font=theme.font(13, "bold")).pack(
            anchor="w", pady=(0, 8))
        help_text = (
            "1.  Connect your receipt printer (USB or network) to this computer and install its Windows driver "
            "— most thermal receipt printers (58mm/80mm) install as a 'Generic / Text Only' or vendor-specific printer.\n\n"
            "2.  Open Windows Settings → Bluetooth & devices → Printers & scanners, and confirm the printer shows "
            "up and says 'Ready'.\n\n"
            "3.  Optional: click the printer → Set as default, if this is the only printer you'll use for receipts. "
            "Leaving the dropdown above on 'System Default' will always use whichever printer is set as default in Windows.\n\n"
            "4.  To use a specific printer regardless of the Windows default (useful if this PC also has a regular "
            "document printer), pick it from the dropdown above and click 'Save Printer Settings'.\n\n"
            "5.  Click 'Test Print' to confirm everything is wired up correctly before relying on it during checkout.\n\n"
            "6.  Turn on 'Automatically print the receipt after every completed sale' if you want receipts to print "
            "immediately on checkout without a cashier having to click Print manually. You can also always print any "
            "receipt manually afterward from the receipt popup."
        )
        ctk.CTkLabel(help_inner, text=help_text, font=theme.font(11), text_color=theme.TEXT_MUTED,
                     justify="left", wraplength=760).pack(anchor="w")

    # ==================================================================
    def _open_pos(self):
        self.destroy()
        from pos_window import POSWindow
        POSWindow(self.user).mainloop()

    def _logout(self):
        if not messagebox.askyesno("Log Out", "Are you sure you want to log out?"):
            return
        self.destroy()
        from login_window import LoginWindow
        LoginWindow().mainloop()


if __name__ == "__main__":
    AdminWindow({"id": 1, "username": "admin", "full_name": "Administrator", "role": "admin"}).mainloop()
