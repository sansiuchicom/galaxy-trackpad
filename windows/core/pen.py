"""Experimental Windows Ink / S Pen injection with profile mapping."""
from __future__ import annotations

import ctypes as c
import time
from typing import Any

from windows.applog import debug, info
from windows.core.displays import resolve_monitor
from windows.core.pen_mapping import PenMapConfig, PixelRect
from windows.core.synthetic import (
    INPUT,
    PARAMS,
    POINT,
    POINTER_INFO,
    TOUCH_INFO,
    PT_PEN,
    create,
    destroy,
)
from windows.settings.store import SETTINGS, active_pen_profile, clamp

PEN_DOWN = 0x00010016
PEN_MOVE = 0x00020016
PEN_UP = 0x00040000
PEN_MASK = 0x0000000D

_active_pen: "PenBridge | None" = None
_pen_input_blocked = False


def set_pen_input_blocked(blocked: bool) -> None:
    """GUI region picker asks the engine to ignore tablet pen while open."""
    global _pen_input_blocked
    _pen_input_blocked = bool(blocked)
    if _pen_input_blocked and _active_pen is not None:
        try:
            _active_pen.release()
        except OSError:
            pass


def is_pen_input_blocked() -> bool:
    return _pen_input_blocked


class PEN_INFO(c.Structure):
    _fields_ = [
        ("pointerInfo", POINTER_INFO),
        ("penFlags", c.c_uint32),
        ("penMask", c.c_uint32),
        ("pressure", c.c_uint32),
        ("rotation", c.c_uint32),
        ("tiltX", c.c_int32),
        ("tiltY", c.c_int32),
    ]


class POINTER_UNION(c.Union):
    _fields_ = [("touchInfo", TOUCH_INFO), ("penInfo", PEN_INFO)]


class PEN_INPUT(c.Structure):
    _fields_ = [("type", c.c_uint32), ("data", POINTER_UNION)]


assert c.sizeof(PEN_INPUT) == c.sizeof(INPUT) == 152

_user32 = c.WinDLL("user32", use_last_error=True)
_pen_inject = _user32.InjectSyntheticPointerInput
_pen_inject.argtypes = [c.c_void_p, c.c_void_p, c.c_uint32]
_pen_inject.restype = c.c_int


def notify_settings_reloaded() -> None:
    if _active_pen is not None:
        _active_pen.reload_config()


def build_pen_map_from_settings(pen_block: dict[str, Any] | None = None) -> PenMapConfig:
    from windows.core.pen_mapping import norm_region_to_pixels, parse_norm_region
    from windows.settings.store import PROFILE_DRAWING

    profile = active_pen_profile(pen_block)
    monitor = resolve_monitor(profile["monitor_id"])
    full = PixelRect(monitor.left, monitor.top, monitor.right, monitor.bottom)

    # Drawing + capture region → map an aspect-matched pad band onto that box
    # (S Pen Area follows the dragged region's proportions).
    if profile["name"] == PROFILE_DRAWING and profile.get("region_active"):
        region = parse_norm_region(profile.get("region"))
        if region is not None:
            target = norm_region_to_pixels(region, full)
            if target.width >= 2 and target.height >= 2:
                return PenMapConfig(
                    mapping="preserve_aspect_ratio",
                    area_size=1.0,
                    monitor=target,
                    tablet_aspect=profile["tablet_aspect"],
                )

    return PenMapConfig(
        mapping=profile["mapping"],
        area_size=profile["area_size"],
        monitor=full,
        tablet_aspect=profile["tablet_aspect"],
    )


class PenBridge:
    """Tip contact, pressure and tilt with profile-based monitor mapping."""

    def __init__(self):
        global _active_pen
        params = PARAMS(PT_PEN, 1, 3, None, 0, 0, 0)
        self.handle = create(c.byref(params))
        if not self.handle:
            raise c.WinError(c.get_last_error())
        self.pressed = False
        self.last_contact = None
        self.ticks = 1
        self.last_clock = time.monotonic()
        self._pending_config: dict[str, Any] | None = None
        self._repro_miss_logged = False
        self.map_config = build_pen_map_from_settings()
        _active_pen = self
        active = self.map_config.active_rect()
        info(
            "Pen ready mapping={} area={:.0f}% monitor=({},{} {}x{})".format(
                self.map_config.mapping,
                self.map_config.area_size * 100,
                self.map_config.monitor.left,
                self.map_config.monitor.top,
                self.map_config.monitor.width,
                self.map_config.monitor.height,
            )
        )
        debug(
            "Pen activeUV=({:.3f},{:.3f})-({:.3f},{:.3f})".format(
                active.left, active.top, active.right, active.bottom
            )
        )

    def reload_config(self) -> None:
        """Apply SETTINGS pen block now, or after the tip lifts."""
        snapshot = {
            "active_profile": SETTINGS["pen"]["active_profile"],
            "tablet_aspect": SETTINGS["pen"]["tablet_aspect"],
            "profiles": SETTINGS["pen"]["profiles"],
        }
        if self.pressed:
            self._pending_config = snapshot
            info("Pen config queued until tip releases")
            return
        self._apply_config(snapshot)

    def _apply_config(self, pen_block: dict[str, Any]) -> None:
        self.map_config = build_pen_map_from_settings(pen_block)
        self._pending_config = None
        info(
            "Pen applied mapping={} area={:.0f}% bounds=({},{} {}x{})".format(
                self.map_config.mapping,
                self.map_config.area_size * 100,
                self.map_config.monitor.left,
                self.map_config.monitor.top,
                self.map_config.monitor.width,
                self.map_config.monitor.height,
            )
        )

    def _send(self, contact, state, x: int, y: int):
        arr = (PEN_INPUT * 1)()
        arr[0].type = PT_PEN
        info = arr[0].data.penInfo
        p = info.pointerInfo
        p.pointerType = PT_PEN
        p.pointerId = 0
        p.pointerFlags = state
        p.ptPixelLocation = POINT(x, y)
        info.penMask = PEN_MASK
        info.pressure = round(clamp(float(contact.get("pressure", 0.5)), 0, 1) * 1024)
        info.tiltX = round(clamp(float(contact.get("tiltX", 0)), -90, 90))
        info.tiltY = round(clamp(float(contact.get("tiltY", 0)), -90, 90))
        now = time.monotonic()
        self.ticks += max(1, round((now - self.last_clock) * 1000))
        self.last_clock = now
        p.dwTime = self.ticks
        if not _pen_inject(self.handle, c.byref(arr), 1):
            raise c.WinError(c.get_last_error())

    def update(self, pens):
        if is_pen_input_blocked():
            self.release()
            self._repro_miss_logged = False
            return
        if not pens:
            self.release()
            self._repro_miss_logged = False
            return

        contact = pens[0]
        try:
            u = float(contact["x"])
            v = float(contact["y"])
        except (KeyError, TypeError, ValueError):
            return

        mapped = self.map_config.map_point(u, v)
        if mapped is None:
            # Outside active area: end stroke cleanly; do not jump-map.
            if self.pressed:
                self.release()
            elif not self._repro_miss_logged:
                self._repro_miss_logged = True
                active = self.map_config.active_rect()
                debug(
                    "Pen miss uv=({:.3f},{:.3f}) mode={} active=({:.2f},{:.2f})-({:.2f},{:.2f})".format(
                        u,
                        v,
                        self.map_config.mapping,
                        active.left,
                        active.top,
                        active.right,
                        active.bottom,
                    )
                )
            return

        x, y = mapped
        self._repro_miss_logged = False
        if not self.pressed:
            active = self.map_config.active_rect()
            mon = self.map_config.monitor
            debug(
                "Pen down uv=({:.3f},{:.3f}) -> ({},{}) mode={} "
                "active=({:.2f},{:.2f})-({:.2f},{:.2f}) monitor=({},{} {}x{})".format(
                    u,
                    v,
                    x,
                    y,
                    self.map_config.mapping,
                    active.left,
                    active.top,
                    active.right,
                    active.bottom,
                    mon.left,
                    mon.top,
                    mon.width,
                    mon.height,
                )
            )
        self._send(contact, PEN_MOVE if self.pressed else PEN_DOWN, x, y)
        self.pressed = True
        self.last_contact = {**contact, "_pixel": (x, y)}

    def release(self):
        if self.pressed:
            try:
                contact = self.last_contact or {"pressure": 0, "tiltX": 0, "tiltY": 0}
                x, y = contact.get("_pixel", (
                    self.map_config.monitor.left,
                    self.map_config.monitor.top,
                ))
                self._send(contact, PEN_UP, x, y)
            finally:
                self.pressed = False
                self.last_contact = None
        if self._pending_config is not None:
            self._apply_config(self._pending_config)

    def close(self):
        global _active_pen
        try:
            self.release()
        finally:
            destroy(self.handle)
            if _active_pen is self:
                _active_pen = None
            info("Pen removed")
