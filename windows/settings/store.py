"""JSON settings store with Phase 2 nested schema + flat v0.8 migration."""
from __future__ import annotations

import copy
import json
import math
from typing import Any

from windows.paths import SETTINGS_PATH

PROFILE_STANDARD = "standard"
PROFILE_DRAWING = "drawing"

DEFAULT_PROFILE = {
    "monitor_id": "primary",
    "mapping": "stretch",
    "area_size": 1.0,
}

DEFAULTS: dict[str, Any] = {
    "touchpad": {
        "cursor_sensitivity": 1.0,
        "scroll_sensitivity": 1.0,
        "input_area": "fullscreen",  # Phase 3: fullscreen | show_menu
    },
    "pen": {
        "active_profile": PROFILE_STANDARD,
        "tablet_aspect": 2560 / 1600,
        "profiles": {
            PROFILE_STANDARD: {
                "monitor_id": "primary",
                "mapping": "stretch",
                "area_size": 1.0,
            },
            PROFILE_DRAWING: {
                "monitor_id": "primary",
                "mapping": "preserve_aspect_ratio",
                "area_size": 1.0,
            },
        },
    },
    "general": {
        "start_with_windows": True,
        "auto_start_engine": True,
        "debug_log": False,
    },
}

# Runtime snapshot read by the engine (flat gains + pen block).
SETTINGS: dict[str, Any] = {
    "cursor_sensitivity": 1.0,
    "scroll_sensitivity": 1.0,
    "pen": copy.deepcopy(DEFAULTS["pen"]),
}


def clamp(value, low, high):
    return max(low, min(high, value))


def _gain(data: dict, *keys, default: float = 1.0) -> float:
    for key in keys:
        if key in data:
            try:
                value = float(data[key])
                return clamp(value, 0.5, 2.0) if math.isfinite(value) else default
            except (TypeError, ValueError):
                return default
    return default


def _area(value, default: float = 1.0) -> float:
    try:
        number = float(value)
        return clamp(number, 0.5, 1.0) if math.isfinite(number) else default
    except (TypeError, ValueError):
        return default


def _mapping(value: str | None, default: str = "stretch") -> str:
    raw = (value or default).lower().strip()
    if raw in ("preserve_aspect_ratio", "preserve", "aspect"):
        return "preserve_aspect_ratio"
    return "stretch"


def _profile_dict(raw: Any, fallback: dict) -> dict:
    src = raw if isinstance(raw, dict) else {}
    return {
        "monitor_id": str(src.get("monitor_id", fallback["monitor_id"]) or "primary"),
        "mapping": _mapping(src.get("mapping"), fallback["mapping"]),
        "area_size": _area(src.get("area_size", fallback["area_size"])),
    }


def migrate_config(raw: Any) -> dict[str, Any]:
    """Accept flat v0.8 or nested Phase 2 JSON; always return nested schema."""
    data = raw if isinstance(raw, dict) else {}
    out = copy.deepcopy(DEFAULTS)

    # Nested touchpad
    touch = data.get("touchpad") if isinstance(data.get("touchpad"), dict) else {}
    out["touchpad"]["cursor_sensitivity"] = _gain(
        touch, "cursor_sensitivity", default=_gain(data, "cursor_sensitivity")
    )
    out["touchpad"]["scroll_sensitivity"] = _gain(
        touch, "scroll_sensitivity", default=_gain(data, "scroll_sensitivity")
    )
    area = touch.get("input_area", data.get("input_area", "fullscreen"))
    out["touchpad"]["input_area"] = (
        "show_menu" if area in ("show_menu", "menu") else "fullscreen"
    )

    # Nested pen
    pen_in = data.get("pen") if isinstance(data.get("pen"), dict) else {}
    profiles_in = pen_in.get("profiles") if isinstance(pen_in.get("profiles"), dict) else {}
    legacy_monitor = data.get("pen_monitor", "primary")
    if legacy_monitor == "Primary Monitor":
        legacy_monitor = "primary"

    std_fallback = {
        **DEFAULTS["pen"]["profiles"][PROFILE_STANDARD],
        "monitor_id": str(legacy_monitor or "primary"),
    }
    draw_fallback = {
        **DEFAULTS["pen"]["profiles"][PROFILE_DRAWING],
        "monitor_id": str(legacy_monitor or "primary"),
    }
    out["pen"]["profiles"][PROFILE_STANDARD] = _profile_dict(
        profiles_in.get(PROFILE_STANDARD), std_fallback
    )
    out["pen"]["profiles"][PROFILE_DRAWING] = _profile_dict(
        profiles_in.get(PROFILE_DRAWING), draw_fallback
    )

    active = pen_in.get("active_profile", PROFILE_STANDARD)
    out["pen"]["active_profile"] = (
        PROFILE_DRAWING if active in (PROFILE_DRAWING, "drawing_signature") else PROFILE_STANDARD
    )
    try:
        aspect = float(pen_in.get("tablet_aspect", DEFAULTS["pen"]["tablet_aspect"]))
        out["pen"]["tablet_aspect"] = aspect if math.isfinite(aspect) and aspect > 0 else DEFAULTS["pen"]["tablet_aspect"]
    except (TypeError, ValueError):
        pass

    # pen_enabled is retired: S Pen always maps when the tip is down.
    # (Old false values are ignored on purpose.)

    general = data.get("general") if isinstance(data.get("general"), dict) else {}
    auto = general.get("auto_start_engine", data.get("auto_connect", True))
    out["general"]["auto_start_engine"] = bool(auto)
    out["general"]["start_with_windows"] = bool(
        general.get("start_with_windows", DEFAULTS["general"]["start_with_windows"])
    )
    out["general"]["debug_log"] = bool(
        general.get("debug_log", DEFAULTS["general"]["debug_log"])
    )
    return out


def load_config() -> dict[str, Any]:
    try:
        with SETTINGS_PATH.open("r", encoding="utf-8") as file:
            saved = json.load(file)
    except (FileNotFoundError, OSError, ValueError):
        return copy.deepcopy(DEFAULTS)
    return migrate_config(saved)


def save_config(config: dict[str, Any]) -> None:
    normalized = migrate_config(config)
    with SETTINGS_PATH.open("w", encoding="utf-8") as file:
        json.dump(normalized, file, indent=4, ensure_ascii=False)


def active_pen_profile(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return the active pen profile fields.

    ``config`` may be a full settings dict, a ``pen`` block, or None (runtime SETTINGS).
    """
    if config is None:
        pen = SETTINGS.get("pen", DEFAULTS["pen"])
    elif isinstance(config.get("pen"), dict):
        pen = config["pen"]
    elif "profiles" in config:
        pen = config
    else:
        pen = SETTINGS.get("pen", DEFAULTS["pen"])
    name = pen.get("active_profile", PROFILE_STANDARD)
    if name not in (PROFILE_STANDARD, PROFILE_DRAWING):
        name = PROFILE_STANDARD
    profiles = pen.get("profiles") or {}
    profile = profiles.get(name) or DEFAULTS["pen"]["profiles"][name]
    from windows.settings.pad_aspect import effective_tablet_aspect

    stored = float(pen.get("tablet_aspect", DEFAULTS["pen"]["tablet_aspect"]))
    return {
        "name": name,
        "monitor_id": profile.get("monitor_id", "primary"),
        "mapping": _mapping(profile.get("mapping")),
        "area_size": _area(profile.get("area_size", 1.0)),
        "tablet_aspect": effective_tablet_aspect(stored),
    }


def apply_runtime_settings(config: dict[str, Any]) -> dict[str, Any]:
    """Update engine SETTINGS snapshot from nested config."""
    from windows.applog import set_debug

    normalized = migrate_config(config)
    SETTINGS["cursor_sensitivity"] = normalized["touchpad"]["cursor_sensitivity"]
    SETTINGS["scroll_sensitivity"] = normalized["touchpad"]["scroll_sensitivity"]
    SETTINGS["pen"] = copy.deepcopy(normalized["pen"])
    SETTINGS["debug_log"] = bool(normalized["general"].get("debug_log", False))
    # Deprecated key kept True for any leftover checks.
    SETTINGS["pen_enabled"] = True
    set_debug(SETTINGS["debug_log"])
    return normalized


def reload_settings() -> dict[str, Any]:
    from windows.applog import info

    config = load_config()
    apply_runtime_settings(config)
    profile = active_pen_profile()
    info(
        "Settings Cursor={:.2f}x Scroll={:.2f}x PenProfile={} mapping={} area={:.0f}%".format(
            SETTINGS["cursor_sensitivity"],
            SETTINGS["scroll_sensitivity"],
            profile["name"],
            profile["mapping"],
            profile["area_size"] * 100,
        )
    )
    try:
        from windows.core.pen import notify_settings_reloaded
        notify_settings_reloaded()
    except Exception as exc:  # pragma: no cover - engine-only path
        info(f"Pen reload note: {exc}")
    try:
        from windows.transport.websocket import request_state_broadcast
        request_state_broadcast()
    except Exception:
        pass
    return config


def set_active_profile(config: dict[str, Any], name: str) -> dict[str, Any]:
    config = migrate_config(config)
    config["pen"]["active_profile"] = (
        PROFILE_DRAWING if name == PROFILE_DRAWING else PROFILE_STANDARD
    )
    return config


def update_active_profile_fields(config: dict[str, Any], **fields) -> dict[str, Any]:
    config = migrate_config(config)
    name = config["pen"]["active_profile"]
    profile = config["pen"]["profiles"][name]
    if "monitor_id" in fields and fields["monitor_id"] is not None:
        profile["monitor_id"] = str(fields["monitor_id"])
    if "mapping" in fields and fields["mapping"] is not None:
        profile["mapping"] = _mapping(fields["mapping"])
    if "area_size" in fields and fields["area_size"] is not None:
        profile["area_size"] = _area(fields["area_size"])
    return config
