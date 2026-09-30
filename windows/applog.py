"""Lightweight process logging for engine ↔ GUI (stdout lines).

Info lines are always printed. Debug lines only when enabled via
GALAXYTRACKPAD_DEBUG=1 or set_debug(True) after settings reload.
"""
from __future__ import annotations

import os
from typing import Any

_DEBUG = os.environ.get("GALAXYTRACKPAD_DEBUG", "").strip().lower() in {
    "1", "true", "yes", "on",
}


def set_debug(enabled: bool) -> None:
    global _DEBUG
    _DEBUG = bool(enabled)


def is_debug() -> bool:
    return _DEBUG


def _safe_print(line: str) -> None:
    try:
        print(line, flush=True)
    except UnicodeEncodeError:
        print(line.encode("ascii", "replace").decode("ascii"), flush=True)


def info(message: str) -> None:
    _safe_print(f"[INFO] {message}")


def debug(message: str) -> None:
    if _DEBUG:
        _safe_print(f"[DEBUG] {message}")


def error(message: str) -> None:
    _safe_print(f"[ERROR] {message}")


def state(**fields: Any) -> None:
    """Machine-readable status for the GUI, e.g. engine=running usb=ready."""
    parts = [f"{key}={fields[key]}" for key in fields]
    _safe_print("[STATE] " + " ".join(parts))
