"""Win32 monitor enumeration for S Pen targeting."""
from __future__ import annotations

import ctypes as c
from ctypes import wintypes
from dataclasses import dataclass


user32 = c.WinDLL("user32", use_last_error=True)


class RECT(c.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class MONITORINFOEXW(c.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32),
    ]


MonitorEnumProc = c.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.HMONITOR,
    wintypes.HDC,
    c.POINTER(RECT),
    wintypes.LPARAM,
)

user32.EnumDisplayMonitors.argtypes = [
    wintypes.HDC, c.c_void_p, MonitorEnumProc, wintypes.LPARAM
]
user32.EnumDisplayMonitors.restype = wintypes.BOOL
user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, c.POINTER(MONITORINFOEXW)]
user32.GetMonitorInfoW.restype = wintypes.BOOL

MONITORINFOF_PRIMARY = 0x00000001


@dataclass(frozen=True)
class MonitorInfo:
    """One connected display in virtual-screen coordinates."""

    id: str
    name: str
    left: int
    top: int
    right: int
    bottom: int
    is_primary: bool

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def aspect(self) -> float:
        return self.width / self.height if self.height else 1.0


def list_monitors() -> list[MonitorInfo]:
    found: list[MonitorInfo] = []

    def _callback(hmon, _hdc, _lprc, _data):
        info = MONITORINFOEXW()
        info.cbSize = c.sizeof(MONITORINFOEXW)
        if not user32.GetMonitorInfoW(hmon, c.byref(info)):
            return True
        device = info.szDevice
        primary = bool(info.dwFlags & MONITORINFOF_PRIMARY)
        # Stable-ish id: GDI device name (\\.\DISPLAY1). Bounds are fallback hints.
        mon_id = device or f"monitor_{len(found)}"
        label = "Primary" if primary else f"Display {len(found) + 1}"
        if device:
            label = f"{label} ({device})"
        found.append(
            MonitorInfo(
                id=mon_id,
                name=label,
                left=info.rcMonitor.left,
                top=info.rcMonitor.top,
                right=info.rcMonitor.right,
                bottom=info.rcMonitor.bottom,
                is_primary=primary,
            )
        )
        return True

    cb = MonitorEnumProc(_callback)
    if not user32.EnumDisplayMonitors(None, None, cb, 0):
        raise c.WinError(c.get_last_error())
    found.sort(key=lambda m: (not m.is_primary, m.left, m.top, m.id))
    # Re-label non-primary sequentially for UI readability.
    display_index = 2
    relabeled = []
    for mon in found:
        if mon.is_primary:
            name = f"Display 1 · Primary ({mon.id})"
        else:
            name = f"Display {display_index} ({mon.id})"
            display_index += 1
        relabeled.append(
            MonitorInfo(
                id=mon.id,
                name=name,
                left=mon.left,
                top=mon.top,
                right=mon.right,
                bottom=mon.bottom,
                is_primary=mon.is_primary,
            )
        )
    return relabeled


def resolve_monitor(monitor_id: str | None, monitors: list[MonitorInfo] | None = None) -> MonitorInfo:
    mons = monitors if monitors is not None else list_monitors()
    if not mons:
        raise RuntimeError("No monitors available")
    primary = next((m for m in mons if m.is_primary), mons[0])
    if not monitor_id or monitor_id in ("primary", "Primary Monitor"):
        return primary
    for mon in mons:
        if mon.id == monitor_id:
            return mon
    # Legacy / stale id → primary fallback
    return primary
