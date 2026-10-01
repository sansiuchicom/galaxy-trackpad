"""S Pen coordinate mapping (stretch / preserve aspect / active area).

Preserve Aspect Ratio (Phase 2A definition)
------------------------------------------
We preserve **tablet CSS-pixel isotropy on the selected monitor's pixel grid**.

A circle drawn with equal tablet pixel Δx/Δy should appear circular on the
target monitor (in that monitor's pixels), not stretched by mismatched
aspect ratios.

Normalized tablet coords (u, v) ∈ [0, 1]² come from the WebView. With tablet
CSS size (Tw, Th) and monitor pixel size (Mw, Mh):

    active UV width/height  =  (Mw / Mh) * (Th / Tw)

is letterboxed into the unit square, then optionally shrunk by area_size
about its center, then stretched onto the monitor bounds.

Physical millimetres / EDID sizes are NOT used (often unreliable).
Default tablet aspect is Galaxy Tab S7 landscape CSS (2560/1600).
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class NormRect:
    """Axis-aligned rectangle in normalized tablet space [0, 1]²."""

    left: float
    top: float
    right: float
    bottom: float

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.bottom - self.top

    def contains(self, u: float, v: float) -> bool:
        return self.left <= u <= self.right and self.top <= v <= self.bottom


@dataclass(frozen=True)
class PixelRect:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


# Galaxy Tab S7 (SM-T870) default landscape CSS pixels.
DEFAULT_TABLET_ASPECT = 2560 / 1600  # 1.6


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def letterbox_rect(target_aspect: float) -> NormRect:
    """Largest centered rect inside the unit square with width/height = target_aspect."""
    if target_aspect <= 0:
        target_aspect = 1.0
    # Unit square aspect = 1. Compare target to 1.
    if target_aspect >= 1.0:
        # Wider than tall in UV: full width, reduced height.
        height = 1.0 / target_aspect
        top = (1.0 - height) / 2.0
        return NormRect(0.0, top, 1.0, top + height)
    width = target_aspect
    left = (1.0 - width) / 2.0
    return NormRect(left, 0.0, left + width, 1.0)


def scale_about_center(rect: NormRect, area_size: float) -> NormRect:
    scale = clamp(float(area_size), 0.5, 1.0)
    cx = (rect.left + rect.right) / 2.0
    cy = (rect.top + rect.bottom) / 2.0
    hw = rect.width * scale / 2.0
    hh = rect.height * scale / 2.0
    return NormRect(cx - hw, cy - hh, cx + hw, cy + hh)


def active_tablet_rect(
    mapping: str,
    area_size: float = 1.0,
    *,
    monitor_aspect: float,
    tablet_aspect: float = DEFAULT_TABLET_ASPECT,
) -> NormRect:
    """Compute the pen-sensitive region in tablet UV space."""
    mapping = (mapping or "stretch").lower()
    if mapping in ("preserve_aspect_ratio", "preserve", "aspect"):
        # UV aspect so tablet-pixel circles stay circles on the monitor.
        # Uw/Vh = (Mw/Mh) * (Th/Tw) = monitor_aspect / tablet_aspect
        uv_aspect = monitor_aspect / tablet_aspect if tablet_aspect else monitor_aspect
        base = letterbox_rect(uv_aspect)
    else:
        base = NormRect(0.0, 0.0, 1.0, 1.0)
    return scale_about_center(base, area_size)


def map_uv_to_monitor(
    u: float,
    v: float,
    active: NormRect,
    monitor: PixelRect,
) -> tuple[int, int] | None:
    """Map tablet UV into virtual-screen pixels, or None if outside active area."""
    if not active.contains(u, v) or active.width <= 0 or active.height <= 0:
        return None
    local_x = (u - active.left) / active.width
    local_y = (v - active.top) / active.height
    local_x = clamp(local_x, 0.0, 1.0)
    local_y = clamp(local_y, 0.0, 1.0)
    # Inclusive pixel range: map onto [left, right-1] x [top, bottom-1]
    x = monitor.left + round(local_x * max(monitor.width - 1, 0))
    y = monitor.top + round(local_y * max(monitor.height - 1, 0))
    return x, y


def parse_norm_region(raw: object) -> NormRect | None:
    """Validate a monitor-relative [0,1] region dict; None if missing/invalid."""
    if raw is None or not isinstance(raw, dict):
        return None
    try:
        left = float(raw["left"])
        top = float(raw["top"])
        right = float(raw["right"])
        bottom = float(raw["bottom"])
    except (KeyError, TypeError, ValueError):
        return None
    if not all(math.isfinite(x) for x in (left, top, right, bottom)):
        return None
    left = clamp(left, 0.0, 1.0)
    top = clamp(top, 0.0, 1.0)
    right = clamp(right, 0.0, 1.0)
    bottom = clamp(bottom, 0.0, 1.0)
    if right <= left or bottom <= top:
        return None
    # Reject tiny boxes (noise / mis-clicks); ~2% of the monitor minimum.
    if (right - left) < 0.02 or (bottom - top) < 0.02:
        return None
    return NormRect(left, top, right, bottom)


def norm_region_to_dict(region: NormRect) -> dict[str, float]:
    return {
        "left": round(region.left, 6),
        "top": round(region.top, 6),
        "right": round(region.right, 6),
        "bottom": round(region.bottom, 6),
    }


def norm_region_to_pixels(region: NormRect, monitor: PixelRect) -> PixelRect:
    """Map a normalized region onto monitor pixel bounds (exclusive right/bottom)."""
    left = monitor.left + int(round(region.left * monitor.width))
    top = monitor.top + int(round(region.top * monitor.height))
    right = monitor.left + int(round(region.right * monitor.width))
    bottom = monitor.top + int(round(region.bottom * monitor.height))
    if right <= left:
        right = left + 1
    if bottom <= top:
        bottom = top + 1
    left = max(monitor.left, min(left, monitor.right - 1))
    top = max(monitor.top, min(top, monitor.bottom - 1))
    right = max(left + 1, min(right, monitor.right))
    bottom = max(top + 1, min(bottom, monitor.bottom))
    return PixelRect(left, top, right, bottom)


@dataclass(frozen=True)
class PenMapConfig:
    mapping: str
    area_size: float
    monitor: PixelRect
    tablet_aspect: float = DEFAULT_TABLET_ASPECT

    def active_rect(self) -> NormRect:
        return active_tablet_rect(
            self.mapping,
            self.area_size,
            monitor_aspect=self.monitor.width / self.monitor.height
            if self.monitor.height else 1.0,
            tablet_aspect=self.tablet_aspect,
        )

    def map_point(self, u: float, v: float) -> tuple[int, int] | None:
        return map_uv_to_monitor(u, v, self.active_rect(), self.monitor)
