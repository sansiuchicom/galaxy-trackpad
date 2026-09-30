# Galaxy Trackpad v0.4
# Integrated Windows launcher with USB auto-reconnect

import asyncio
import logging
import select
import socket
import subprocess
import threading

from functools import partial

from http.server import (
    SimpleHTTPRequestHandler,
    ThreadingHTTPServer
)

from pathlib import Path

from websockets.exceptions import ConnectionClosedError


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

ADB_SERVER = (
    "127.0.0.1",
    5037
)


# ==========================================
# 2. Exception handling
# ==========================================

class StopRequested(Exception):
    pass


class IgnoreExpectedUSBDisconnect(logging.Filter):

    def filter(self, record):

        if (
            record.getMessage() == "connection handler failed"
            and record.exc_info
        ):

            return not isinstance(
                record.exc_info[1],
                ConnectionClosedError
            )

        return True


# ==========================================
# 3. ADB commands
# ==========================================

def run_adb(*args):

    result = subprocess.run(
        [str(ADB), *args],
        capture_output=True,
        text=True,
        timeout=15,
        creationflags=getattr(
            subprocess,
            "CREATE_NO_WINDOW",
            0
        )
    )

    if result.returncode:

        raise RuntimeError(
            (
                result.stderr
                or result.stdout
                or "ADB command failed"
            ).strip()
        )

    return result.stdout


# ==========================================
# 4. ADB event reader
# ==========================================

def read_exact(sock, count, stop):

    data = bytearray()

    while len(data) < count:

        if stop.is_set():
            raise StopRequested

        readable, _, _ = select.select(
            [sock],
            [],
            [],
            0.5
        )

        if not readable:
            continue

        block = sock.recv(
            count - len(data)
        )

        if not block:

            raise ConnectionError(
                "ADB tracking socket closed"
            )

        data.extend(block)

    return bytes(data)


def track_snapshots(stop):

    with socket.create_connection(
        ADB_SERVER,
        timeout=5
    ) as sock:

        sock.settimeout(None)

        command = b"host:track-devices"

        request = (
            f"{len(command):04x}".encode("ascii")
            + command
        )

        sock.sendall(request)

        response = read_exact(
            sock,
            4,
            stop
        )

        if response != b"OKAY":

            raise RuntimeError(
                "ADB rejected track-devices: "
                + repr(response)
            )

        print(
            "[ADB] Listening for USB connection events",
            flush=True
        )

        while not stop.is_set():

            header = read_exact(
                sock,
                4,
                stop
            )

            size = int(
                header.decode("ascii"),
                16
            )

            snapshot = read_exact(
                sock,
                size,
                stop
            ).decode(
                "utf-8",
                "replace"
            )

            yield snapshot


# ==========================================
# 5. USB connection manager
# ==========================================

def usb_watcher(stop):

    configured_serial = None

    last_state = None

    ports = (
        HTTP_PORT,
        WS_PORT
    )

    while not stop.is_set():

        try:

            run_adb("start-server")

            configured_serial = None

            for snapshot in track_snapshots(stop):

                if stop.is_set():
                    return

                devices = {}

                for line in snapshot.splitlines():

                    parts = line.split()

                    if len(parts) >= 2:

                        devices[parts[0]] = parts[1]

                ready = [
                    serial
                    for serial, status in devices.items()
                    if status == "device"
                ]

                # --------------------------
                # Device unavailable
                # --------------------------

                if len(ready) != 1:

                    if len(ready) > 1:

                        state = "multiple devices"

                    elif "unauthorized" in devices.values():

                        state = "authorization needed"

                    else:

                        state = "waiting for device"

                    if state != last_state:

                        print(
                            f"[USB] {state}",
                            flush=True
                        )

                    configured_serial = None

                    last_state = state

                    continue

                serial = ready[0]

                # --------------------------
                # Check existing ports
                # --------------------------

                current = run_adb(
                    "-s",
                    serial,
                    "reverse",
                    "--list"
                )

                present = all(
                    f"tcp:{p} tcp:{p}" in current
                    for p in ports
                )

                if (
                    serial == configured_serial
                    and present
                ):

                    continue

                # --------------------------
                # Restore USB forwarding
                # --------------------------

                print(
                    "[USB] Authorized device detected; "
                    "restoring ports",
                    flush=True
                )

                for port in ports:

                    run_adb(
                        "-s",
                        serial,
                        "reverse",
                        f"tcp:{port}",
                        f"tcp:{port}"
                    )

                # --------------------------
                # Verify registration
                # --------------------------

                verified = run_adb(
                    "-s",
                    serial,
                    "reverse",
                    "--list"
                )

                if not all(
                    f"tcp:{p} tcp:{p}" in verified
                    for p in ports
                ):

                    raise RuntimeError(
                        "Reverse ports disappeared "
                        "during setup"
                    )

                configured_serial = serial

                last_state = "connected"

                print(
                    "[USB] Reverse ports "
                    "8765 and 8766 ready",
                    flush=True
                )

        except StopRequested:

            return

        except (
            OSError,
            ValueError,
            RuntimeError,
            ConnectionError
        ) as exc:

            if not stop.is_set():

                print(
                    f"[ADB] Tracker error: {exc}",
                    flush=True
                )

                print(
                    "[ADB] Retrying after 2 seconds",
                    flush=True
                )

                configured_serial = None

                stop.wait(2)


# ==========================================
# 6. HTTP server
# ==========================================

class QuietHandler(SimpleHTTPRequestHandler):

    def log_message(self, *args):
        pass


def assert_port_available(port):

    with socket.socket() as sock:

        try:

            sock.bind(
                ("127.0.0.1", port)
            )

        except OSError as exc:

            raise RuntimeError(
                f"Port {port} is already in use. "
                "Stop the old server first."
            ) from exc


# ==========================================
# 7. Main launcher
# ==========================================

def main():

    print(
        "\n=== GALAXY TRACKPAD v0.4 ===\n",
        flush=True
    )

    # Check required files.

    if not ADB.is_file():

        raise FileNotFoundError(
            f"ADB not found: {ADB}"
        )

    required = (
        "touchpad_lab.py",
        "touchpad_live_v02.py",
        "touchpad_v04.html"
    )

    for name in required:

        if not (ROOT / name).is_file():

            raise FileNotFoundError(
                f"Missing {name} in {ROOT}"
            )

    # Check ports.

    for port in (
        HTTP_PORT,
        WS_PORT
    ):

        assert_port_available(port)

    httpd = None

    stop = threading.Event()

    watcher = None

    # Suppress only expected WebSocket
    # disconnect tracebacks.

    expected_disconnect_filter = (
        IgnoreExpectedUSBDisconnect()
    )

    ws_logger = logging.getLogger(
        "websockets.server"
    )

    ws_logger.addFilter(
        expected_disconnect_filter
    )

    try:

        # --------------------------
        # Start HTTP server
        # --------------------------

        handler = partial(
            QuietHandler,
            directory=str(ROOT)
        )

        httpd = ThreadingHTTPServer(
            ("127.0.0.1", HTTP_PORT),
            handler
        )

        threading.Thread(
            target=httpd.serve_forever,
            daemon=True
        ).start()

        print(
            "[OK] HTTP server started "
            "on port 8765",
            flush=True
        )

        # --------------------------
        # Start USB event watcher
        # --------------------------

        watcher = threading.Thread(
            target=usb_watcher,
            args=(stop,),
            daemon=True
        )

        watcher.start()

        print(
            "[OK] USB event watcher started",
            flush=True
        )

        print(
            "[TAB] Open "
            "http://127.0.0.1:8765/"
            "touchpad_v04.html",
            flush=True
        )

        print(
            "[INFO] Keep this window open; "
            "press Ctrl+C to exit.\n",
            flush=True
        )

        # --------------------------
        # Start existing input engine
        # --------------------------

        import touchpad_live_v02

        asyncio.run(
            touchpad_live_v02.main()
        )

    except KeyboardInterrupt:

        print(
            "\n[EXIT] Stopping Galaxy Trackpad...",
            flush=True
        )

    finally:

        # Stop USB watcher.

        stop.set()

        if watcher:

            watcher.join(
                timeout=3
            )

        # Stop HTTP server.

        if httpd:

            httpd.shutdown()

            httpd.server_close()

        ws_logger.removeFilter(
            expected_disconnect_filter
        )

        print(
            "[EXIT] Servers stopped",
            flush=True
        )


# ==========================================
# 8. Entry point
# ==========================================

if __name__ == "__main__":

    try:

        main()

    except (
        FileNotFoundError,
        RuntimeError,
        OSError
    ) as exc:

        print(
            f"[ERROR] {exc}"
        )