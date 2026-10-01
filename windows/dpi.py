"""Make Win32 monitor bounds match synthetic pen/touch injection pixels.

Without per-monitor DPI awareness, Windows lies about display size (e.g. a
3840x2160 panel at 125% is reported as 3072x1728). InjectSyntheticPointerInput
still targets the physical desktop, so the pen only reaches ~80% of the screen
from the top-left — matching the Step 0 reproduce log.
"""
from __future__ import annotations

import sys


def enable_dpi_awareness() -> bool:
    """Call once at process start, before enumerating monitors or creating Qt."""
    if sys.platform != "win32":
        return False
    import ctypes

    # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    if hasattr(user32, "SetProcessDpiAwarenessContext"):
        user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        user32.SetProcessDpiAwarenessContext.restype = ctypes.c_int
        if user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return True
    try:
        shcore = ctypes.WinDLL("shcore", use_last_error=True)
        # PROCESS_PER_MONITOR_DPI_AWARE = 2
        if shcore.SetProcessDpiAwareness(2) == 0:
            return True
    except OSError:
        pass
    return False
