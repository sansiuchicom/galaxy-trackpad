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


def info(message: str) -> None:
    print(f"[INFO] {message}", flush=True)


def debug(message: str) -> None:
    if _DEBUG:
        print(f"[DEBUG] {message}", flush=True)


def error(message: str) -> None:
    print(f"[ERROR] {message}", flush=True)


def state(**fields: Any) -> None:
    """Machine-readable status for the GUI, e.g. engine=running usb=ready."""
    parts = [f"{key}={fields[key]}" for key in fields]
    print("[STATE] " + " ".join(parts), flush=True)
