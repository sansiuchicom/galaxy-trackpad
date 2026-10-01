# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — onedir GalaxyTrackpad.exe (Phase 4B)."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).resolve().parent

datas = [
    (str(ROOT / "windows" / "static"), "windows/static"),
    (str(ROOT / "windows" / "assets"), "windows/assets"),
]
binaries = []
hiddenimports = [
    "windows",
    "windows.__main__",
    "windows.engine",
    "windows.applog",
    "windows.autostart",
    "windows.runtime",
    "windows.paths",
    "windows.main",
    "windows.core",
    "windows.core.synthetic",
    "windows.core.touchpad",
    "windows.core.pen",
    "windows.core.pen_mapping",
    "windows.core.displays",
    "windows.core.sensitivity",
    "windows.core.keyboard",
    "windows.dpi",
    "windows.transport",
    "windows.transport.adb",
    "windows.transport.http",
    "windows.transport.websocket",
    "windows.transport.control",
    "windows.transport.state_sync",
    "windows.transport.session",
    "windows.transport.input_dispatch",
    "windows.transport.framing",
    "windows.transport.bluetooth",
    "bluetooth_lab",
    "bluetooth_lab.constants",
    "bluetooth_lab.framing",
    "bluetooth_lab.windows_client",
    "bluetooth_lab.sdp_winrt",
    "windows.transport.winrt_rfcomm",
    "windows.transport.pacing",
    "windows.settings",
    "windows.settings.store",
    "windows.settings.pad_aspect",
    "windows.ui",
    "windows.ui.main_window",
    "windows.ui.advanced_dialog",
    "windows.ui.monitor_picker",
    "windows.ui.widgets",
    "windows.ui.region_picker",
    "windows.ui.region_outline",
]

for pkg in ("PySide6", "shiboken6", "websockets"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    [str(ROOT / "packaging" / "windows_entry.py")],
    pathex=[str(ROOT)],
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

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="GalaxyTrackpad",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "branding" / "galaxy_trackpad.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="GalaxyTrackpad",
)
