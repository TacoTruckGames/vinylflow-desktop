# -*- mode: python ; coding: utf-8 -*-
# VinylFlow PyInstaller spec — Windows only

import shutil
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files


FFMPEG_PATH = shutil.which('ffmpeg')

if not FFMPEG_PATH:
    raise RuntimeError('ffmpeg was not found on PATH. Install ffmpeg before building.')

# certifi CA bundle — needed so requests/discogs_client can verify HTTPS certs.
certifi_datas = collect_data_files('certifi')

# pythonnet — edgechromium (WebView2) backend needs clr / pythonnet at runtime.
try:
    pythonnet_datas = collect_data_files('pythonnet')
except Exception:
    pythonnet_datas = []

DATA_FILES = [
    ('backend/static', 'backend/static'),
    ('assets/VinylFlow.ico', 'assets'),
    *certifi_datas,
    *pythonnet_datas,
]

HIDDEN_IMPORTS = [
    'backend.api',
    'webview',
    'webview.platforms.edgechromium',
    'clr',
    'clr_loader',
]

a = Analysis(
    ['desktop_launcher.py'],
    pathex=[],
    binaries=[(FFMPEG_PATH, 'ffmpeg_bin')],
    datas=DATA_FILES,
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['rthooks/rthook_vinylflow.py'],
    excludes=[],
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
    # UPX can corrupt .NET assemblies and third-party executables.
    # ffmpeg.exe in particular can be mis-flagged by AV when UPX-packed.
    upx_exclude=['Python.Runtime.dll', 'ffmpeg.exe'],
    name='VinylFlow',
)
