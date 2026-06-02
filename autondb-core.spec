# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for AutonDB core binary.

Build with:
    uv run pyinstaller autondb-core.spec

Produces a standalone binary at dist/autondb-core (or .exe on Windows)
that the Tauri app invokes as a sidecar.
"""
import sys
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

a = Analysis(
    ['src/bridge.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=collect_submodules('src') + [
        'aiosqlite',
        'asyncpg',
        'aiomysql',
        'openai',
        'anthropic',
        'pydantic',
        'dotenv',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'PIL',
        'scipy',
        'IPython',
        'jupyter',
    ],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='autondb-core',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
