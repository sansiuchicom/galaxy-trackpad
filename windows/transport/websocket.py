"""WebSocket input bridge: tablet contacts -> touchpad / pen engines."""
from __future__ import annotations

import asyncio
import json
import time

from websockets.asyncio.server import serve

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
        print(f"Pen unavailable; touchpad still works: {exc}")

    exclusive = asyncio.Lock()

    async def handler(websocket):
        nonlocal pen
        if exclusive.locked():
            await websocket.close(code=1008, reason="Only one tablet at a time")
            return
        async with exclusive:
            print("Galaxy Tab connected")
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
                                print("Pen injection failed; disabling pen:", exc)
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
                        print("Bad input:", exc)
                    except OSError as exc:
                        print("Windows input error:", exc)
                        print("If touch gestures stop, restart the program.")
            finally:
                try:
                    touchpad.release()
                    if pen:
                        pen.release()
                finally:
                    print("Galaxy Tab disconnected; all contacts released")

    try:
        async with serve(handler, "127.0.0.1", WS_PORT, max_size=1_000_000):
            print(f"Listening: ws://127.0.0.1:{WS_PORT}")
            print("Touch 1-5 fingers; try scroll, pinch, taps, 3/4 swipes")
            print("For pen: open Paint / OneNote before touching with S Pen")
            await asyncio.Future()
    finally:
        try:
            touchpad.close()
        finally:
            if pen:
                pen.close()
