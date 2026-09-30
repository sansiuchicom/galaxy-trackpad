"""Engine process: HTTP + ADB USB watcher + WebSocket input + GUI control port."""
from __future__ import annotations

import asyncio
import logging
import threading

from windows.applog import error, info, state
from windows.paths import (
    ADB,
    CONTROL_PORT,
    HTTP_PORT,
    STATIC_DIR,
    WS_PORT,
)
from windows.settings.store import reload_settings
from windows.transport.adb import (
    IgnoreExpectedUSBDisconnect,
    assert_port_available,
    usb_watcher,
)
from windows.transport.control import run_with_control
from windows.transport.http import start_http_server
from windows.transport.websocket import run_input_server


def engine_main() -> None:
    try:
        reload_settings()
        for port in (HTTP_PORT, WS_PORT, CONTROL_PORT):
            assert_port_available(port)
        if not ADB.is_file():
            raise FileNotFoundError(f"ADB not found: {ADB}")
        html = STATIC_DIR / "touchpad_v04.html"
        if not html.is_file():
            raise FileNotFoundError(f"Missing tablet page: {html}")
    except (FileNotFoundError, RuntimeError, OSError) as exc:
        error(str(exc))
        state(engine="error", usb="unknown", tablet="disconnected")
        raise

    stop = threading.Event()
    httpd = None
    watcher = None
    ws_logger = logging.getLogger("websockets.server")
    quiet_expected = IgnoreExpectedUSBDisconnect()
    ws_logger.addFilter(quiet_expected)
    try:
        httpd = start_http_server(STATIC_DIR)
        watcher = threading.Thread(target=usb_watcher, args=(stop,), daemon=True)
        watcher.start()
        info("HTTP + USB watcher started")
        state(engine="running", usb="waiting", tablet="disconnected")
        asyncio.run(run_with_control(run_input_server()))
    except KeyboardInterrupt:
        info("Keyboard interrupt")
    finally:
        stop.set()
        if watcher:
            watcher.join(timeout=3)
        if httpd:
            httpd.shutdown()
            httpd.server_close()
        ws_logger.removeFilter(quiet_expected)
        info("Servers stopped")
        state(engine="stopped", usb="unknown", tablet="disconnected")
