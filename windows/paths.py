"""Shared paths and localhost ports for the Windows runtime."""
from __future__ import annotations

import sys
from pathlib import Path


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False)) and hasattr(sys, "_MEIPASS")


if _is_frozen():
    # Install directory (writable): exe + platform-tools + settings JSON.
    REPO_ROOT = Path(sys.executable).resolve().parent
    # Bundled read-only package data extracted by PyInstaller.
    PACKAGE_ROOT = Path(sys._MEIPASS) / "windows"  # type: ignore[attr-defined]
    SETTINGS_PATH = REPO_ROOT / "galaxytrackpad_settings.json"
else:
    PACKAGE_ROOT = Path(__file__).resolve().parent
    REPO_ROOT = PACKAGE_ROOT.parent
    # Keep the Phase 1–3 settings path for conda / python -m windows.
    SETTINGS_PATH = PACKAGE_ROOT / "galaxytrackpad_settings.json"

STATIC_DIR = PACKAGE_ROOT / "static"
ADB = REPO_ROOT / "platform-tools" / "adb.exe"

HTTP_PORT = 8765
WS_PORT = 8766
CONTROL_PORT = 8767

PAD_W, PAD_H = 10000, 6000
