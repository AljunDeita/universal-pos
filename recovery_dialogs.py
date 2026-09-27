"""
recovery_dialogs.py
-------------------
Pop-up dialogs for password recovery:

  * ForgotPasswordDialog  - opened from the login screen. Two steps:
        1) enter username  ->  2) answer the security question + choose a new password
  * RecoverySetupDialog   - used by an admin (Users tab) to set or change the security
        question for an account.
"""

import customtkinter as ctk
import theme
import auth


def _center_on(dlg, parent, width, height):
    """Positions the dialog in the middle of its parent window."""
    try:
        parent.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
        dlg.geometry(f"{width}x{height}+{max(x, 0)}+{max(y, 0)}")
    except Exception:
        dlg.geometry(f"{width}x{height}")


class _BaseDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, width, height):
        super().__init__(parent)
        self.parent_window = parent
        self.title(title)
        self.configure(fg_color=theme.BG)
        self.resizable(False, False)
        self.transient(parent)
        self._width, self._height = width, height
        _center_on(self, parent, width, height)
        self.bind("<Escape>", lambda e: self.destroy())
        # grab/focus must be deferred a moment or it can fail on Windows
        self.after(150, self._activate)

    def _activate(self):
        try:
            self.lift()
            self.focus_force()
            self.grab_set()
        except Exception:
            pass

    def _resize(self, height):
        self._height = height
        _center_on(self, self.parent_window, self._width, height)

    @staticmethod
    def _label(parent, text):
        ctk.CTkLabel(parent, text=text, font=theme.font(11), text_color=theme.TEXT_MUTED).pack(anchor="w")

    @staticmethod
    def _message(parent):
        lbl = ctk.CTkLabel(parent, text="", font=theme.font(11), text_color=theme.DANGER,
                           wraplength=340, justify="left", anchor="w")
        lbl.pack(anchor="w", fill="x", pady=(0, 6))
        return lbl


# ======================================================================
class ForgotPasswordDialog(_BaseDialog):
    def __init__(self, parent, prefill_username="", on_success=None):
        super().__init__(parent, "Forgot Password", 420, 300)
        self.on_success = on_success
        self.username = ""
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=30, pady=26)
        self._show_step_username(prefill_username)

    def _clear(self):
        for w in self.body.winfo_children():
            w.destroy()

    # ---- Step 1: who are you? ----------------------------------------
    def _show_step_username(self, prefill=""):
        self._clear()
        self._resize(300)
        ctk.CTkLabel(self.body, text="Forgot your password?", font=theme.font(20, "bold")).pack(anchor="w")
        ctk.CTkLabel(self.body, text="Enter your username and we'll ask your security question.",
                     font=theme.font(11), text_color=theme.TEXT_MUTED, wraplength=350, justify="left"
                     ).pack(anchor="w", pady=(2, 18))

        self._label(self.body, "Username")
        self.username_entry = ctk.CTkEntry(self.body, height=38, corner_radius=8, placeholder_text="e.g. cashier")
        self.username_entry.pack(fill="x", pady=(2, 8))
        if prefill:
            self.username_entry.insert(0, prefill)
        self.username_entry.bind("<Return>", lambda e: self._submit_username())
        self.msg = self._message(self.body)

        ctk.CTkButton(self.body, text="Continue", height=40, corner_radius=8, fg_color=theme.ACCENT,
                      hover_color=theme.ACCENT_HOVER, font=theme.font(13, "bold"),
                      command=self._submit_username).pack(fill="x")
        self.username_entry.focus()

    def _submit_username(self):
        username = self.username_entry.get().strip()
        if not username:
            self.msg.configure(text="Please enter your username.")
            return
        question, error = auth.get_recovery_question(username)
        if error:
            self.msg.configure(text=error)
            return
        self.username = username
        self._show_step_reset(question)

    # ---- Step 2: answer + new password -------------------------------
    def _show_step_reset(self, question):
        self._clear()
        self._resize(540)
        ctk.CTkLabel(self.body, text="Reset your password", font=theme.font(20, "bold")).pack(anchor="w")
        ctk.CTkLabel(self.body, text=f"Account: @{self.username}", font=theme.font(11),
                     text_color=theme.TEXT_MUTED).pack(anchor="w", pady=(2, 14))

        q_card = ctk.CTkFrame(self.body, fg_color=theme.CARD, corner_radius=8)
        q_card.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(q_card, text=question, font=theme.font(12, "bold"), wraplength=330, justify="left",
                     anchor="w").pack(anchor="w", padx=14, pady=10)

        self._label(self.body, "Your answer")
        self.answer_entry = ctk.CTkEntry(self.body, height=38, corner_radius=8)
        self.answer_entry.pack(fill="x", pady=(2, 12))

        self._label(self.body, "New password")
        self.new_pw_entry = ctk.CTkEntry(self.body, height=38, corner_radius=8, show="•")
        self.new_pw_entry.pack(fill="x", pady=(2, 12))

        self._label(self.body, "Confirm new password")
        self.confirm_pw_entry = ctk.CTkEntry(self.body, height=38, corner_radius=8, show="•")
        self.confirm_pw_entry.pack(fill="x", pady=(2, 8))
        self.confirm_pw_entry.bind("<Return>", lambda e: self._submit_reset())

        self.msg = self._message(self.body)

        ctk.CTkButton(self.body, text="Reset Password", height=40, corner_radius=8, fg_color=theme.ACCENT,
                      hover_color=theme.ACCENT_HOVER, font=theme.font(13, "bold"),
                      command=self._submit_reset).pack(fill="x")
        ctk.CTkButton(self.body, text="Back", height=30, corner_radius=8, fg_color="transparent",
                      hover_color=theme.CARD_HOVER, text_color=theme.TEXT_MUTED, font=theme.font(11),
                      command=lambda: self._show_step_username(self.username)).pack(pady=(6, 0))
        self.answer_entry.focus()

    def _submit_reset(self):
        answer = self.answer_entry.get()
        new_pw = self.new_pw_entry.get()
        confirm = self.confirm_pw_entry.get()

        if not answer.strip():
            self.msg.configure(text="Please answer the security question.")
            return
        if new_pw != confirm:
            self.msg.configure(text="The two passwords don't match.")
            return

        ok, message = auth.reset_password_with_answer(self.username, answer, new_pw)
        if not ok:
            self.msg.configure(text=message)
            # If that attempt triggered a lockout, there's no point staying on this step.
            if message.startswith("Too many"):
                self.answer_entry.configure(state="disabled")
            return

        username = self.username
        callback = self.on_success
        self.destroy()
        if callback:
            callback(username, message)


# ======================================================================
class RecoverySetupDialog(_BaseDialog):
    """Lets an admin set/replace the security question and answer for a user."""

    def __init__(self, parent, user, on_done=None):
        super().__init__(parent, f"Recovery Question — {user['username']}", 440, 440)
        self.user = user
        self.on_done = on_done

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=30, pady=24)

        ctk.CTkLabel(body, text="Password recovery", font=theme.font(18, "bold")).pack(anchor="w")
        ctk.CTkLabel(
            body,
            text=(f"Set a question only @{user['username']} can answer. It lets them reset their own "
                  "password from the login screen via “Forgot password?”."),
            font=theme.font(11), text_color=theme.TEXT_MUTED, wraplength=370, justify="left",
        ).pack(anchor="w", pady=(2, 16))

        self._label(body, "Security question (pick one or type your own)")
        self.question_box = ctk.CTkComboBox(body, values=auth.SECURITY_QUESTIONS, height=38, corner_radius=8)
        self.question_box.pack(fill="x", pady=(2, 12))
        current = user.get("security_question")
        self.question_box.set(current if current else auth.SECURITY_QUESTIONS[0])

        self._label(body, "Answer")
        self.answer_entry = ctk.CTkEntry(body, height=38, corner_radius=8,
                                         placeholder_text="Not case-sensitive")
        self.answer_entry.pack(fill="x", pady=(2, 6))
        self.answer_entry.bind("<Return>", lambda e: self._save())

        ctk.CTkLabel(body, text="Tip: choose an answer that’s easy to remember but hard to guess.",
                     font=theme.font(10), text_color=theme.TEXT_MUTED).pack(anchor="w", pady=(0, 6))
        self.msg = self._message(body)

        ctk.CTkButton(body, text="Save Recovery Question", height=40, corner_radius=8, fg_color=theme.ACCENT,
                      hover_color=theme.ACCENT_HOVER, font=theme.font(13, "bold"),
                      command=self._save).pack(fill="x")
        self.answer_entry.focus()

    def _save(self):
        ok, message = auth.set_recovery(self.user["id"], self.question_box.get(), self.answer_entry.get())
        if not ok:
            self.msg.configure(text=message)
            return
        callback = self.on_done
        self.destroy()
        if callback:
            callback()
