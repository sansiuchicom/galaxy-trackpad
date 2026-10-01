"""Session pad aspect from the tablet (#pad CSS size), for Drawing letterbox.

UV contacts are normalized to the pad element, not the full tablet bezel.
Fixed SETTINGS tablet_aspect (Tab S7 1.6) is only a fallback until hello arrives.
"""
from __future__ import annotations

import math
from typing import Any

# Live override from the tablet; None → use settings / default.
_session_pad_aspect: float | None = None


def get_session_pad_aspect() -> float | None:
    return _session_pad_aspect


def set_session_pad_aspect(aspect: float | None) -> bool:
    """Set or clear session aspect. Returns True if the stored value changed."""
    global _session_pad_aspect
    if aspect is None:
        changed = _session_pad_aspect is not None
        _session_pad_aspect = None
        return changed
    value = float(aspect)
    if not math.isfinite(value) or value <= 0.05 or value > 20:
        return False
    # Ignore tiny float noise from repeated hellos.
    if _session_pad_aspect is not None and abs(_session_pad_aspect - value) < 1e-4:
        return False
    _session_pad_aspect = value
    return True


def effective_tablet_aspect(fallback: float | None = None) -> float:
    if _session_pad_aspect is not None:
        return _session_pad_aspect
    if fallback is not None and math.isfinite(fallback) and fallback > 0:
        return float(fallback)
    from windows.core.pen_mapping import DEFAULT_TABLET_ASPECT

    return DEFAULT_TABLET_ASPECT


def apply_pad_aspect_from_message(packet: dict[str, Any]) -> bool:
    """Read optional pad_aspect from hello / get_state; refresh pen + state if changed."""
    if "pad_aspect" not in packet:
        return False
    raw = packet.get("pad_aspect")
    try:
        aspect = float(raw)
    except (TypeError, ValueError):
        return False
    if not set_session_pad_aspect(aspect):
        return False
    try:
        from windows.core.pen import notify_settings_reloaded

        notify_settings_reloaded()
    except Exception:
        pass
    try:
        from windows.transport.websocket import request_state_broadcast

        request_state_broadcast()
    except Exception:
        pass
    from windows.applog import info

    info(f"Pad aspect from tablet: {aspect:.4f} (Drawing letterbox uses pad box)")
    return True
