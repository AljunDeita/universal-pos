"""
theme.py
--------
Central place for colors/fonts so every window looks consistent.
"""

import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BG = "#0f1115"
SURFACE = "#171a21"
CARD = "#1e222c"
CARD_HOVER = "#262b38"
BORDER = "#2a2f3a"

ACCENT = "#5b8def"
ACCENT_HOVER = "#4a78d6"
ACCENT_SOFT = "#22314f"

SUCCESS = "#2ecc71"
SUCCESS_HOVER = "#27ae60"
DANGER = "#e74c3c"
DANGER_HOVER = "#c0392b"
WARNING = "#f39c12"

TEXT_PRIMARY = "#f2f3f5"
TEXT_MUTED = "#9aa0ac"

FONT_FAMILY = "Segoe UI"


def font(size=13, weight="normal"):
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight)
