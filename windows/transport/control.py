"""Local TCP control channel for GUI RELOAD / STOP (port 8767)."""
from __future__ import annotations

import asyncio

from windows.applog import info, state
from windows.paths import CONTROL_PORT
from windows.settings.store import reload_settings


async def run_with_control(engine_coro):
    stopped = asyncio.Event()

    async def control(reader, writer):
        try:
            cmd = (await asyncio.wait_for(reader.readline(), 3)).strip()
            if cmd == b"RELOAD":
                reload_settings()
                writer.write(b"OK\n")
            elif cmd == b"PEN_PAUSE":
                from windows.core.pen import set_pen_input_blocked

                set_pen_input_blocked(True)
                writer.write(b"OK\n")
            elif cmd == b"PEN_RESUME":
                from windows.core.pen import set_pen_input_blocked

                set_pen_input_blocked(False)
                writer.write(b"OK\n")
            elif cmd == b"STOP":
                info("Shutdown requested")
                state(engine="stopping")
                stopped.set()
                writer.write(b"OK\n")
            else:
                writer.write(b"UNKNOWN\n")
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(control, "127.0.0.1", CONTROL_PORT)
    info(f"GUI control ready on {CONTROL_PORT}")
    # Keep legacy token so older GUI parsers still unlock STOP.
    print("[OK] GUI control ready: 8767", flush=True)
    engine = asyncio.create_task(engine_coro)
    stop_task = asyncio.create_task(stopped.wait())
    try:
        done, _ = await asyncio.wait(
            (engine, stop_task),
            return_when=asyncio.FIRST_COMPLETED,
        )
        if engine in done:
            await engine
    finally:
        engine.cancel()
        stop_task.cancel()
        for task in (engine, stop_task):
            try:
                await task
            except asyncio.CancelledError:
                pass
        server.close()
        await server.wait_closed()
        info("Control server stopped")
