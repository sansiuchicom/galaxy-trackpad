# ==========================================
# Galaxy Trackpad v0.3
# Windows Integrated Launcher
# ==========================================

import asyncio
import subprocess
import socket
import sys
import threading

from pathlib import Path
from functools import partial
from http.server import (
    ThreadingHTTPServer,
    SimpleHTTPRequestHandler
)

import touchpad_live_v02


# ==========================================
# 1. Configuration
# ==========================================

ROOT = Path(__file__).resolve().parent

ADB = (
    ROOT.parent
    / "platform-tools"
    / "adb.exe"
)

HTTP_PORT = 8765
WS_PORT = 8766


# ==========================================
# 2. ADB utilities
# ==========================================

def run_adb(*args):

    result = subprocess.run(
        [str(ADB), *args],
        capture_output=True,
        text=True,
        timeout=15
    )

    if result.returncode != 0:

        raise RuntimeError(
            result.stderr
            or result.stdout
            or "ADB command failed"
        )

    return result.stdout


def check_device():

    if not ADB.is_file():

        raise RuntimeError(
            f"ADB not found: {ADB}"
        )

    output = run_adb("devices")

    devices = []

    for line in output.splitlines()[1:]:

        parts = line.split()

        if len(parts) >= 2:
            devices.append(parts)

    ready = [
        d for d in devices
        if d[1] == "device"
    ]

    if len(ready) != 1:

        raise RuntimeError(
            "Expected exactly one authorized "
            "Android device.\n\n"
            + output
        )

    print(
        f"[OK] Galaxy Tab detected: "
        f"{ready[0][0]}"
    )


# ==========================================
# 3. USB connection
# ==========================================

def setup_usb():

    run_adb(
        "reverse",
        f"tcp:{HTTP_PORT}",
        f"tcp:{HTTP_PORT}"
    )

    run_adb(
        "reverse",
        f"tcp:{WS_PORT}",
        f"tcp:{WS_PORT}"
    )

    print("[OK] USB port forwarding ready")


# ==========================================
# 4. Check available ports
# ==========================================

def check_ports():

    for port in (HTTP_PORT, WS_PORT):

        with socket.socket() as sock:

            try:

                sock.bind(
                    ("127.0.0.1", port)
                )

            except OSError:

                raise RuntimeError(
                    f"Port {port} is already in use.\n"
                    "Please stop old servers."
                )


# ==========================================
# 5. HTTP server
# ==========================================

class QuietHandler(SimpleHTTPRequestHandler):

    def log_message(self, *args):
        pass


def start_http():

    handler = partial(
        QuietHandler,
        directory=str(ROOT)
    )

    server = ThreadingHTTPServer(
        ("127.0.0.1", HTTP_PORT),
        handler
    )

    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True
    )

    thread.start()

    print(
        f"[OK] HTTP server: {HTTP_PORT}"
    )

    return server, thread


# ==========================================
# 6. Main
# ==========================================

def main():

    print()
    print("==============================")
    print(" GALAXY TRACKPAD v0.3")
    print("==============================")
    print()

    server = None
    thread = None

    try:

        check_ports()

        check_device()

        server, thread = start_http()

        setup_usb()

        print()
        print("[OK] All services ready")
        print()
        print("Open on Galaxy Tab:")
        print(
            "http://127.0.0.1:8765/"
            "touchpad.html"
        )

        print()
        print("Press Ctrl+C to stop.")
        print()

        # Reuse the existing working engine.
        asyncio.run(
            touchpad_live_v02.main()
        )

    except KeyboardInterrupt:

        print("\nShutting down...")

    except Exception as error:

        print()
        print("[ERROR]", error)

    finally:

        if server:

            server.shutdown()
            server.server_close()

        if thread:
            thread.join(timeout=2)

        print("Galaxy Trackpad stopped.")


if __name__ == "__main__":
    main()