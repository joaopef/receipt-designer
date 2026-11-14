# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Receipt Designer.

Run from repo root:
    pyinstaller ReceiptDesigner.spec
"""
from pathlib import Path

# SPECPATH is set by PyInstaller to the directory containing this spec file
SPEC_DIR = Path(SPECPATH).resolve()

# Package directory containing assets
PKG_DIR = SPEC_DIR / "receipt_designer"
ASSETS_DIR = PKG_DIR / "assets"
ICON_PATH = ASSETS_DIR / "icons" / "ReceiptDesigner128x128.ico"
VERSION_FILE = SPEC_DIR / "receipt_designer_version.txt"

# Collect assets - bundle into 'assets/' within the frozen app
# This matches the resource_path() lookup in app.py which expects assets/ at _MEIPASS root
datas = [
    (str(ASSETS_DIR), "assets"),
]

binaries = []
hiddenimports = []

# Optionally collect escpos if available (for thermal printer support)
try:
    from PyInstaller.utils.hooks import collect_all
    tmp_ret = collect_all('escpos')
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]
except Exception:
    pass  # escpos not installed, skip

a = Analysis(
    ['run_receipt_designer.py'],
    pathex=[str(SPEC_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# Qt on current Windows uses the operating system's ICU API. A foreign tool
# (for example Poppler) on PATH can make bindepend collect an incompatible ICU
# with version-suffixed exports instead. Do not redistribute that shadow DLL or
# copy Windows system binaries: let the Windows loader resolve its own ICU.
import sys
if sys.platform == 'win32':
    a.binaries = [entry for entry in a.binaries
                  if Path(entry[0]).name.lower() not in {'icuuc.dll', 'icudt78.dll'}]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ReceiptDesigner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(ICON_PATH)] if ICON_PATH.exists() else [],
    version=str(VERSION_FILE) if VERSION_FILE.exists() else None,
)
