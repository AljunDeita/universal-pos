"""
login_window.py
----------------
Modern login screen. On success, launches either the Admin Dashboard
or the Cashier POS screen depending on the account's role.
"""

import customtkinter as ctk
from tkinter import messagebox
import theme
from auth import verify_login
from recovery_dialogs import ForgotPasswordDialog


class LoginWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Universal POS — Login")
        self.geometry("980x600")
        self.minsize(900, 560)
        self.configure(fg_color=theme.BG)
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        container = ctk.CTkFrame(self, fg_color=theme.BG)
        container.pack(fill="both", expand=True)
        container.grid_columnconfigure(0, weight=6)
        container.grid_columnconfigure(1, weight=5)
        container.grid_rowconfigure(0, weight=1)

        # ---- Left branding panel -------------------------------------------------
        left = ctk.CTkFrame(container, fg_color=theme.SURFACE, corner_radius=0)
        left.grid(row=0, column=0, sticky="nsew")

        brand_wrap = ctk.CTkFrame(left, fg_color="transparent")
        brand_wrap.place(relx=0.5, rely=0.5, anchor="center")

        badge = ctk.CTkFrame(brand_wrap, fg_color=theme.ACCENT, corner_radius=20, width=64, height=64)
        badge.pack(pady=(0, 24))
        badge.pack_propagate(False)
        ctk.CTkLabel(badge, text="₱", font=theme.font(30, "bold"), text_color="white").pack(expand=True)

        ctk.CTkLabel(
            brand_wrap, text="Universal POS", font=theme.font(34, "bold"), text_color=theme.TEXT_PRIMARY
        ).pack()
        ctk.CTkLabel(
            brand_wrap,
            text="Modern Point-of-Sale for Philippine Retail",
            font=theme.font(14),
            text_color=theme.TEXT_MUTED,
        ).pack(pady=(4, 30))

        for text in ["✓ BIR-style VAT & Senior/PWD discount", "✓ Real-time inventory tracking",
                     "✓ X-Reading & Z-Reading shift reports", "✓ Role-based access (Admin / Cashier)"]:
            ctk.CTkLabel(brand_wrap, text=text, font=theme.font(13), text_color=theme.TEXT_MUTED, anchor="w").pack(
                fill="x", pady=3
            )

        # ---- Right login form -------------------------------------------------
        right = ctk.CTkFrame(container, fg_color=theme.BG, corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")

        form = ctk.CTkFrame(right, fg_color=theme.CARD, corner_radius=18, width=360)
        form.place(relx=0.5, rely=0.5, anchor="center")
        form_inner = ctk.CTkFrame(form, fg_color="transparent")
        form_inner.pack(padx=40, pady=40)

        ctk.CTkLabel(form_inner, text="Welcome back", font=theme.font(24, "bold")).pack(anchor="w")
        ctk.CTkLabel(
            form_inner, text="Sign in to continue to your terminal", font=theme.font(12), text_color=theme.TEXT_MUTED
        ).pack(anchor="w", pady=(0, 24))

        ctk.CTkLabel(form_inner, text="Username", font=theme.font(12), text_color=theme.TEXT_MUTED).pack(anchor="w")
        self.username_entry = ctk.CTkEntry(form_inner, width=280, height=42, corner_radius=10,
                                            placeholder_text="e.g. admin")
        self.username_entry.pack(pady=(4, 16))

        ctk.CTkLabel(form_inner, text="Password", font=theme.font(12), text_color=theme.TEXT_MUTED).pack(anchor="w")
        self.password_entry = ctk.CTkEntry(form_inner, width=280, height=42, corner_radius=10, show="•",
                                            placeholder_text="••••••••")
        self.password_entry.pack(pady=(4, 6))
        self.password_entry.bind("<Return>", lambda e: self._attempt_login())

        forgot_link = ctk.CTkLabel(form_inner, text="Forgot password?", font=theme.font(11, "bold"),
                                   text_color=theme.ACCENT, cursor="hand2")
        forgot_link.pack(anchor="e")
        forgot_link.bind("<Button-1>", lambda e: self._open_forgot_password())
        forgot_link.bind("<Enter>", lambda e: forgot_link.configure(text_color=theme.ACCENT_HOVER))
        forgot_link.bind("<Leave>", lambda e: forgot_link.configure(text_color=theme.ACCENT))

        self.error_label = ctk.CTkLabel(form_inner, text="", font=theme.font(11), text_color=theme.DANGER,
                                        wraplength=280, justify="left")
        self.error_label.pack(anchor="w", pady=(4, 6))

        login_btn = ctk.CTkButton(
            form_inner, text="Sign In", width=280, height=42, corner_radius=10,
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER, font=theme.font(14, "bold"),
            command=self._attempt_login,
        )
        login_btn.pack(pady=(14, 4))

        ctk.CTkLabel(
            form_inner,
            text="Default admin: admin / admin123\nDefault cashier: cashier / cashier123",
            font=theme.font(10), text_color=theme.TEXT_MUTED, justify="left",
        ).pack(anchor="w", pady=(16, 0))

        self.username_entry.focus()

    # ------------------------------------------------------------------
    def _show_message(self, text, success=False):
        self.error_label.configure(text=text, text_color=theme.SUCCESS if success else theme.DANGER)

    def _open_forgot_password(self):
        ForgotPasswordDialog(
            self,
            prefill_username=self.username_entry.get().strip(),
            on_success=self._after_password_reset,
        )

    def _after_password_reset(self, username, message):
        self.username_entry.delete(0, "end")
        self.username_entry.insert(0, username)
        self.password_entry.delete(0, "end")
        self._show_message(message, success=True)
        self.password_entry.focus()

    # ------------------------------------------------------------------
    def _attempt_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        if not username or not password:
            self._show_message("Please enter both username and password.")
            return

        user = verify_login(username, password)
        if not user:
            self._show_message("Invalid username or password.")
            return

        self.destroy()
        if user["role"] == "admin":
            from admin_window import AdminWindow
            app = AdminWindow(user)
        else:
            from pos_window import POSWindow
            app = POSWindow(user)
        app.mainloop()


if __name__ == "__main__":
    LoginWindow().mainloop()
