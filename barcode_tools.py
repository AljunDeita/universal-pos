"""
barcode_tools.py
-----------------
- generate_barcode_image(): renders a scannable Code128 barcode label (PNG)
  for a product code, so you can print physical shelf labels.
- BarcodeScannerDialog: a reusable popup that opens the computer's webcam,
  looks for a barcode in the live video feed, and calls back with the
  decoded value the moment one is found (or reports that no camera is
  available). Used both when adding/editing a product and at POS checkout,
  as an alternative to a physical USB barcode scanner.
"""

import os

from barcode import Code128
from barcode.writer import ImageWriter

try:
    import cv2
    from pyzbar import pyzbar
    from PIL import Image
    CAMERA_SUPPORT = True
except Exception:
    CAMERA_SUPPORT = False

import customtkinter as ctk
import theme


def generate_barcode_image(code, out_path_no_ext):
    """
    Renders `code` as a Code128 barcode PNG. out_path_no_ext should NOT
    include the .png extension (the barcode library appends it). Returns the
    actual saved file path.
    """
    code_obj = Code128(str(code), writer=ImageWriter())
    saved_path = code_obj.save(out_path_no_ext, options={
        "write_text": True, "module_height": 10.0, "font_size": 9, "quiet_zone": 4,
    })
    return saved_path


class BarcodeScannerDialog(ctk.CTkToplevel):
    """
    Usage:
        BarcodeScannerDialog(self, on_scanned=lambda code: ...)
    on_scanned is called exactly once, with the decoded barcode string, the
    moment a barcode is successfully read. The dialog closes itself either
    way (success or Cancel).
    """

    def __init__(self, parent, on_scanned):
        super().__init__(parent)
        self.on_scanned = on_scanned
        self.title("Scan Barcode")
        self.geometry("500x460")
        self.configure(fg_color=theme.BG)
        self.grab_set()
        self.resizable(False, False)

        ctk.CTkLabel(self, text="📷 Scan Barcode", font=theme.font(15, "bold")).pack(pady=(16, 4))

        self.video_frame = ctk.CTkFrame(self, fg_color=theme.CARD, width=440, height=330, corner_radius=10)
        self.video_frame.pack(padx=20, pady=8)
        self.video_frame.pack_propagate(False)
        self.video_label = ctk.CTkLabel(self.video_frame, text="")
        self.video_label.pack(expand=True, fill="both")

        self.status_label = ctk.CTkLabel(self, text="Opening camera...", font=theme.font(11),
                                          text_color=theme.TEXT_MUTED)
        self.status_label.pack(pady=(4, 8))

        ctk.CTkButton(self, text="Cancel", height=36, corner_radius=8, fg_color=theme.CARD,
                      hover_color=theme.CARD_HOVER, command=self._close).pack(fill="x", padx=20, pady=(0, 16))

        self.cap = None
        self._running = True
        self.protocol("WM_DELETE_WINDOW", self._close)

        if not CAMERA_SUPPORT:
            self.status_label.configure(
                text="Camera scanning isn't available (opencv-python / pyzbar not installed).",
                text_color=theme.DANGER,
            )
            return

        self.after(150, self._init_camera)

    def _init_camera(self):
        try:
            self.cap = cv2.VideoCapture(0)
        except Exception:
            self.cap = None
        if not self.cap or not self.cap.isOpened():
            self.status_label.configure(
                text="No camera found, or it's being used by another app.", text_color=theme.DANGER
            )
            return
        self.status_label.configure(text="Point the barcode at the camera...")
        self._update_frame()

    def _update_frame(self):
        if not self._running or not self.cap:
            return
        ret, frame = self.cap.read()
        if ret:
            decoded = pyzbar.decode(frame)
            if decoded:
                code = decoded[0].data.decode("utf-8", errors="ignore")
                self._close()
                self.on_scanned(code)
                return

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb).resize((440, 330))
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(440, 330))
            self.video_label.configure(image=ctk_img, text="")
            self.video_label.image = ctk_img  # keep a reference so it isn't garbage-collected

        if self._running:
            self.after(30, self._update_frame)

    def _close(self):
        self._running = False
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
        self.destroy()
