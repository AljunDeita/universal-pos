"""
printing.py
-----------
Handles sending a receipt to a physical (or virtual/PDF) printer.

Windows has no built-in Python API for "just print this text file", so this
module uses `pywin32` (the `win32print` / `win32api` packages) when it's
available for proper printer selection and raw/text printing — most thermal
receipt printers register themselves as a normal Windows printer (often as
a "Generic / Text Only" driver), so this works with real receipt printers,
not just regular page printers.

If pywin32 isn't installed (e.g. testing on macOS/Linux, or a fresh venv
before running `pip install -r requirements.txt`), everything here degrades
gracefully instead of crashing the app — printing-related buttons will show
a clear message instead of raising an exception.
"""

import os
import sys
import tempfile
from datetime import datetime

_WIN32_AVAILABLE = False
if sys.platform == "win32":
    try:
        import win32print
        import win32api
        _WIN32_AVAILABLE = True
    except ImportError:
        _WIN32_AVAILABLE = False


def printing_supported():
    """True only on Windows with pywin32 installed — i.e. real printing is possible."""
    return _WIN32_AVAILABLE


def list_printers():
    """Returns a list of installed Windows printer names. Empty list if unsupported."""
    if not _WIN32_AVAILABLE:
        return []
    try:
        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        printers = win32print.EnumPrinters(flags)
        return sorted([p[2] for p in printers])
    except Exception:
        return []


def get_default_printer():
    if not _WIN32_AVAILABLE:
        return None
    try:
        return win32print.GetDefaultPrinter()
    except Exception:
        return None


def print_receipt_text(text, printer_name=None):
    """
    Sends the given receipt text to a printer.
    printer_name: a specific Windows printer name, or None/"" to use the
    system default printer.

    Returns (success: bool, message: str) — never raises, so callers can
    show the message directly to the user without wrapping in try/except.
    """
    if sys.platform != "win32":
        return False, "Direct printing is only supported on Windows."

    if not _WIN32_AVAILABLE:
        return False, (
            "Printing requires the 'pywin32' package, which isn't installed.\n"
            "Run: pip install pywin32"
        )

    # Write to a temp .txt file, then send it to the printer via the
    # Windows "printto" (specific printer) or "print" (default printer)
    # shell verb — the same mechanism Notepad's own Print uses, so it
    # works reliably across different printer drivers without needing to
    # hand-write raw ESC/POS commands for every printer model.
    try:
        fd, path = tempfile.mkstemp(suffix=".txt", prefix="receipt_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)

        if printer_name:
            win32api.ShellExecute(0, "printto", path, f'"{printer_name}"', ".", 0)
            return True, f"Sent to printer: {printer_name}"
        else:
            win32api.ShellExecute(0, "print", path, None, ".", 0)
            default = get_default_printer() or "default printer"
            return True, f"Sent to {default}"
    except Exception as e:
        return False, f"Could not print: {e}"


def test_print(printer_name=None):
    """Prints a short test slip — used by the 'Test Print' button in Settings."""
    now = datetime.now().strftime("%m/%d/%Y %I:%M %p")
    text = (
        "=" * 32 + "\n"
        + "   UNIVERSAL POS TEST PRINT\n"
        + "=" * 32 + "\n"
        + f"Date: {now}\n"
        + "-" * 32 + "\n"
        + "If you can read this, your\n"
        + "printer is set up correctly!\n"
        + "=" * 32 + "\n"
    )
    return print_receipt_text(text, printer_name)


def print_file(path, printer_name=None):
    """
    Prints an existing file (any type Windows knows how to open — used here
    for barcode label images) via the same "print"/"printto" shell verb
    mechanism as print_receipt_text, just without writing a new temp file
    first since the file already exists on disk.
    """
    if sys.platform != "win32":
        return False, "Direct printing is only supported on Windows."
    if not _WIN32_AVAILABLE:
        return False, (
            "Printing requires the 'pywin32' package, which isn't installed.\n"
            "Run: pip install pywin32"
        )
    if not os.path.exists(path):
        return False, f"File not found: {path}"
    try:
        if printer_name:
            win32api.ShellExecute(0, "printto", path, f'"{printer_name}"', ".", 0)
            return True, f"Sent to printer: {printer_name}"
        else:
            win32api.ShellExecute(0, "print", path, None, ".", 0)
            default = get_default_printer() or "default printer"
            return True, f"Sent to {default}"
    except Exception as e:
        return False, f"Could not print: {e}"
