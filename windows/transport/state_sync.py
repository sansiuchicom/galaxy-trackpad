"""Tablet ↔ Windows control/state messages (WebSocket, protocol v1)."""
from __future__ import annotations

from typing import Any

from windows.settings.store import active_pen_profile

PROTOCOL_VERSION = 1


def build_client_state() -> dict[str, Any]:
    """Authoritative snapshot for the Android / WebView client."""
    profile = active_pen_profile()
    active_rect = {"left": 0.0, "top": 0.0, "right": 1.0, "bottom": 1.0}
    try:
        from windows.core.pen import build_pen_map_from_settings

        rect = build_pen_map_from_settings().active_rect()
        active_rect = {
            "left": round(rect.left, 5),
            "top": round(rect.top, 5),
            "right": round(rect.right, 5),
            "bottom": round(rect.bottom, 5),
        }
    except Exception:
        pass

    return {
        "type": "state",
        "protocol": PROTOCOL_VERSION,
        "connection": "ready",
        "pen": {
            "active_profile": profile["name"],
            "mapping": profile["mapping"],
            "area_size": profile["area_size"],
            "active_rect": active_rect,
            "tablet_aspect": float(profile.get("tablet_aspect", 2560 / 1600)),
            "region_active": bool(profile.get("region_active")),
            "region": profile.get("region"),
        },
    }
