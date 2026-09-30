"""JSON settings store. Cursor/scroll gains never touch Windows mouse config."""
from __future__ import annotations

import json
import math

from windows.paths import SETTINGS_PATH

DEFAULTS = {
    "cursor_sensitivity": 1.0,
    "scroll_sensitivity": 1.0,
    "pen_enabled": True,
    "pen_monitor": "Primary Monitor",
    "auto_connect": True,
}

SETTINGS = {
    "cursor_sensitivity": 1.0,
    "scroll_sensitivity": 1.0,
    "pen_enabled": True,
}


def clamp(value, low, high):
    return max(low, min(high, value))


def load_config() -> dict:
    try:
        with SETTINGS_PATH.open("r", encoding="utf-8") as file:
            saved = json.load(file)
        return {**DEFAULTS, **saved} if isinstance(saved, dict) else DEFAULTS.copy()
    except (FileNotFoundError, OSError, ValueError):
        return DEFAULTS.copy()


def save_config(config: dict) -> None:
    with SETTINGS_PATH.open("w", encoding="utf-8") as file:
        json.dump(config, file, indent=4, ensure_ascii=False)


def reload_settings() -> dict:
    """Live changes affect subsequent touch deltas only."""
    data = {}
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    except (FileNotFoundError, OSError, ValueError):
        pass

    def gain(name):
        try:
            value = float(data.get(name, 1.0))
            return clamp(value, 0.5, 2.0) if math.isfinite(value) else 1.0
        except (TypeError, ValueError):
            return 1.0

    SETTINGS.update({
        "cursor_sensitivity": gain("cursor_sensitivity"),
        "scroll_sensitivity": gain("scroll_sensitivity"),
        "pen_enabled": bool(data.get("pen_enabled", True)),
    })
    print(
        "[SETTINGS] Cursor={:.2f}x Scroll={:.2f}x (Pen: next START)".format(
            SETTINGS["cursor_sensitivity"],
            SETTINGS["scroll_sensitivity"],
        ),
        flush=True,
    )
    return SETTINGS
