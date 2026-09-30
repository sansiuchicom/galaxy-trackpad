"""Local TCP control channel for GUI RELOAD / STOP (port 8767)."""
from __future__ import annotations

import asyncio

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
            elif cmd == b"STOP":
                print("[GUI] Shutdown requested", flush=True)
                stopped.set()
                writer.write(b"OK\n")
            else:
                writer.write(b"UNKNOWN\n")
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(control, "127.0.0.1", CONTROL_PORT)
    print(f"[OK] GUI control ready: {CONTROL_PORT}", flush=True)
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
        print("[GUI] Control server stopped", flush=True)
