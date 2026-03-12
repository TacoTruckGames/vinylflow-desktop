# -*- mode: python ; coding: utf-8 -*-
# VinylFlow PyInstaller spec — Windows only (PySide6 native UI)

import shutil
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files


FFMPEG_PATH = shutil.which('ffmpeg')

if not FFMPEG_PATH:
    raise RuntimeError('ffmpeg was not found on PATH. Install ffmpeg before building.')

# certifi CA bundle — needed so requests/discogs_client can verify HTTPS certs.
certifi_datas = collect_data_files('certifi')

DATA_FILES = [
    ('assets/VinylFlow.ico', 'assets'),
    *certifi_datas,
]

# PySide6 plugins and Qt modules needed at runtime
HIDDEN_IMPORTS = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtNetwork',
    'PySide6.QtMultimedia',
]

# Exclude unused Qt modules to reduce bundle size
EXCLUDES = [
    'PySide6.QtWebEngine',
    'PySide6.QtWebEngineCore',
    'PySide6.QtWebEngineWidgets',
    'PySide6.Qt3DCore',
    'PySide6.Qt3DRender',
    'PySide6.QtQuick',
    'PySide6.QtQml',
    'PySide6.QtBluetooth',
    'PySide6.QtPositioning',
    'PySide6.QtSensors',
    'PySide6.QtSerialPort',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[(FFMPEG_PATH, 'ffmpeg_bin')],
    datas=DATA_FILES,
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['rthooks/rthook_vinylflow.py'],
    excludes=EXCLUDES,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VinylFlow',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/VinylFlow.ico',
    version='version_info.txt',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    # ffmpeg.exe can be mis-flagged by AV when UPX-packed.
    upx_exclude=['ffmpeg.exe'],
    name='VinylFlow',
)
