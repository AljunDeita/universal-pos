# UniversalPOS.spec
#
# PyInstaller build spec for Universal POS.
# Build with:  pyinstaller UniversalPOS.spec
#
# This bundles customtkinter's internal theme/font asset files correctly
# (a common gotcha — a plain `pyinstaller main.py` will run but show a
# blank/broken UI because those data files get skipped by default) and
# produces a one-folder build, which starts faster and is more reliable
# for Tkinter apps than --onefile.

from PyInstaller.utils.hooks import collect_data_files
import sys

block_cipher = None

datas = []
datas += collect_data_files("customtkinter")   # theme JSON + font files
datas += collect_data_files("pyzbar")          # bundles libzbar/libiconv DLLs on Windows
datas += collect_data_files("barcode")         # bundles the DejaVuSansMono.ttf label font

hiddenimports = [
    'PIL._tkinter_finder',
    'pyzbar.pyzbar',
    'cv2',
    'docx',
    'openpyxl',
    'reportlab.graphics.barcode',
]
if sys.platform == "win32":
    hiddenimports.append('win32timezone')  # commonly needed alongside pywin32 in frozen apps

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='UniversalPOS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # windowed app — no black console window
    icon='assets\\icon.ico',
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='UniversalPOS',
)
