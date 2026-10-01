"""WebSocket input bridge: tablet contacts -> touchpad / pen engines."""
from __future__ import annotations

import asyncio
import json

from websockets.asyncio.server import serve

from windows.applog import debug, error, info, state
from windows.paths import WS_PORT
from windows.settings.store import (
    PROFILE_DRAWING,
    PROFILE_STANDARD,
    load_config,
    reload_settings,
    save_config,
    set_active_profile,
)
from windows.transport.session import SharedInput
from windows.transport.state_sync import build_client_state

# Thread-safe hooks for GUI RELOAD → push state to the tablet.
_loop: asyncio.AbstractEventLoop | None = None
_push_event: asyncio.Event | None = None
_active_ws = {"ws": None}


def request_state_broadcast() -> None:
    """Ask the WS loop to send the latest state (safe from other threads)."""
    loop = _loop
    event = _push_event
    if loop is None or event is None:
        return
    try:
        loop.call_soon_threadsafe(event.set)
    except RuntimeError:
        pass


async def _send_state(websocket) -> None:
    try:
        await websocket.send(json.dumps(build_client_state()))
    except Exception as exc:
        debug(f"state send failed: {exc}")


async def _apply_profile_request(name: str) -> str:
    """Persist profile from tablet; Windows remains source of truth after reload."""
    wanted = PROFILE_DRAWING if name in (PROFILE_DRAWING, "drawing_signature") else PROFILE_STANDARD
    config = set_active_profile(load_config(), wanted)
    save_config(config)
    reload_settings()
    return wanted


async def run_input_server(shared: SharedInput | None = None):
    global _loop, _push_event

    owns_shared = shared is None
    shared = shared or SharedInput()

    # Last client wins — Chrome leftover must not block the Android app.
    active = _active_ws
    gate = asyncio.Lock()
    _loop = asyncio.get_running_loop()
    _push_event = asyncio.Event()

    async def pusher():
        while True:
            await _push_event.wait()
            _push_event.clear()
            ws = active["ws"]
            if ws is not None:
                await _send_state(ws)

    push_task = asyncio.create_task(pusher())

    async def handler(websocket):
        async with gate:
            old = active["ws"]
            active["ws"] = websocket
            if old is not None and old is not websocket:
                info("Replacing previous tablet WebSocket (only one client)")
                try:
                    await old.close(code=4000, reason="Replaced by new client")
                except Exception:
                    pass
                await asyncio.sleep(0.05)
                shared.release_all()

        shared.claim(SharedInput.USB)
        shared.set_usb_connected(True)
        info("Galaxy Tab connected (USB WebSocket)")
        state(engine="running", tablet="connected", transport="usb")
        await _send_state(websocket)

        try:
            async for raw in websocket:
                try:
                    packet = json.loads(raw)
                except (TypeError, ValueError) as exc:
                    debug(f"Bad JSON: {exc}")
                    continue

                msg_type = packet.get("type")

                if msg_type in ("hello", "get_state"):
                    from windows.settings.pad_aspect import apply_pad_aspect_from_message

                    apply_pad_aspect_from_message(packet)
                    await _send_state(websocket)
                    continue

                if msg_type == "set_profile":
                    try:
                        applied = await _apply_profile_request(
                            str(packet.get("profile", PROFILE_STANDARD))
                        )
                        await websocket.send(
                            json.dumps(
                                {
                                    "type": "ack",
                                    "action": "set_profile",
                                    "profile": applied,
                                    "ok": True,
                                }
                            )
                        )
                    except OSError as exc:
                        error(f"set_profile failed: {exc}")
                        await websocket.send(
                            json.dumps(
                                {
                                    "type": "ack",
                                    "action": "set_profile",
                                    "ok": False,
                                    "error": str(exc),
                                }
                            )
                        )
                    await _send_state(websocket)
                    continue

                if msg_type == "key":
                    try:
                        from windows.core.keyboard import apply_key_packet

                        apply_key_packet(packet)
                    except (OSError, ValueError) as exc:
                        debug(f"key inject failed: {exc}")
                    continue

                if msg_type not in (None, "input") and "contacts" not in packet:
                    debug(f"Ignored message type={msg_type!r}")
                    continue

                shared.apply(SharedInput.USB, packet)
        finally:
            async with gate:
                if active["ws"] is websocket:
                    active["ws"] = None
            shared.set_usb_connected(False)
            shared.release_owner(SharedInput.USB)
            info("Galaxy Tab disconnected; all contacts released")
            state(engine="running", tablet="disconnected", transport="none")

    try:
        async with serve(handler, "127.0.0.1", WS_PORT, max_size=1_000_000):
            info(f"Listening ws://127.0.0.1:{WS_PORT}")
            debug("Open the tablet page after USB reverse is ready")
            await asyncio.Future()
    finally:
        push_task.cancel()
        try:
            await push_task
        except asyncio.CancelledError:
            pass
        _push_event = None
        _loop = None
        if owns_shared:
            shared.close()
