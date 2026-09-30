"""Process launch helpers for GUI → engine and Start-with-Windows."""
from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False)) and hasattr(sys, "_MEIPASS")


def engine_command() -> tuple[str, list[str]]:
    """Program + args to spawn the input engine child process."""
    if is_frozen():
        return sys.executable, ["--engine"]
    return sys.executable, ["-u", "-m", "windows", "--engine"]


def tray_autostart_command() -> str:
    """Quoted command line for HKCU Run (logon)."""
    if is_frozen():
        return f'"{Path(sys.executable).resolve()}" --tray'
    script = Path(__file__).resolve().parent / "main.py"
    return f'"{sys.executable}" -u "{script}" --tray'
