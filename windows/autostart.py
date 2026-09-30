"""Register / unregister Galaxy Trackpad in the current user's Startup (HKCU Run)."""
from __future__ import annotations

import winreg

from windows.runtime import tray_autostart_command

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "GalaxyTrackpad"


def launch_command() -> str:
    """Command line used at Windows logon (no admin required)."""
    return tray_autostart_command()


def is_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, VALUE_NAME)
            return bool(value)
    except OSError:
        return False


def set_enabled(enabled: bool) -> None:
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE
    ) as key:
        if enabled:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, launch_command())
        else:
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass


def sync_from_config(start_with_windows: bool) -> None:
    """Make the registry match the saved preference."""
    want = bool(start_with_windows)
    if is_enabled() != want:
        set_enabled(want)
