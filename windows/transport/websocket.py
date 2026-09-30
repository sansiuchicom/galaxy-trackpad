"""WebSocket input bridge: tablet contacts -> touchpad / pen engines."""
from __future__ import annotations

import asyncio
import json
import time

from websockets.asyncio.server import serve

from windows.applog import debug, error, info, state
from windows.core.pen import PenBridge
from windows.core.touchpad import ScaledTouchpad
from windows.paths import WS_PORT


async def run_input_server():
    touchpad = ScaledTouchpad()
    # S Pen is always available when the tip is detected (no ON/OFF toggle).
    pen = None
    try:
        pen = PenBridge()
    except OSError as exc:
        info(f"Pen unavailable; touchpad still works: {exc}")

    exclusive = asyncio.Lock()

    async def handler(websocket):
        nonlocal pen
        if exclusive.locked():
            await websocket.close(code=1008, reason="Only one tablet at a time")
            return
        async with exclusive:
            info("Galaxy Tab connected")
            state(engine="running", tablet="connected")
            pen_cooldown_until = 0.0
            try:
                async for raw in websocket:
                    try:
                        packet = json.loads(raw)
                        contacts = packet.get("contacts", [])
                        if not isinstance(contacts, list):
                            continue
                        fingers = [c for c in contacts if c.get("tool") == "touch"]
                        pens = [c for c in contacts if c.get("tool") == "pen"]

                        if pen and pens:
                            touchpad.release()
                            try:
                                pen.update(pens)
                            except OSError as exc:
                                error(f"Pen injection failed; disabling pen: {exc}")
                                try:
                                    pen.close()
                                except OSError:
                                    pass
                                pen = None
                            pen_cooldown_until = time.monotonic() + 0.18
                        else:
                            if pen and pen.pressed:
                                pen.release()
                                pen_cooldown_until = time.monotonic() + 0.18
                            if time.monotonic() >= pen_cooldown_until:
                                touchpad.update(fingers)
                            else:
                                touchpad.release()
                    except (KeyError, TypeError, ValueError) as exc:
                        debug(f"Bad input: {exc}")
                    except OSError as exc:
                        error(f"Windows input error: {exc}")
                        info("If touch gestures stop, restart the engine from the GUI.")
            finally:
                try:
                    touchpad.release()
                    if pen:
                        pen.release()
                finally:
                    info("Galaxy Tab disconnected; all contacts released")
                    state(engine="running", tablet="disconnected")

    try:
        async with serve(handler, "127.0.0.1", WS_PORT, max_size=1_000_000):
            info(f"Listening ws://127.0.0.1:{WS_PORT}")
            debug("Open the tablet page after USB reverse is ready")
            await asyncio.Future()
    finally:
        try:
            touchpad.close()
        finally:
            if pen:
                pen.close()
