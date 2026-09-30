"""Application icon helpers for window + tray."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon

from windows.paths import PACKAGE_ROOT
from windows.runtime import is_frozen
import sys


def icon_path() -> Path | None:
    candidates: list[Path] = []
    if is_frozen():
        # Bundled beside package data and next to the exe.
        meipass = Path(getattr(sys, "_MEIPASS", ""))
        candidates += [
            meipass / "windows" / "assets" / "icon.ico",
            meipass / "windows" / "assets" / "icon.png",
            Path(sys.executable).resolve().parent / "icon.ico",
        ]
    candidates += [
        PACKAGE_ROOT / "assets" / "icon.ico",
        PACKAGE_ROOT / "assets" / "icon.png",
        PACKAGE_ROOT.parent / "branding" / "galaxy_trackpad.ico",
        PACKAGE_ROOT.parent / "branding" / "galaxy_trackpad_icon.png",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def app_icon() -> QIcon:
    path = icon_path()
    if path is None:
        return QIcon()
    return QIcon(str(path))
