"""ADB helpers and USB reverse watcher (from verified launch_v04)."""
from __future__ import annotations

import logging
import select
import socket
import subprocess
import threading

from websockets.exceptions import ConnectionClosedError

from windows.paths import ADB, HTTP_PORT, WS_PORT

ADB_SERVER = ("127.0.0.1", 5037)


class StopRequested(Exception):
    pass


class IgnoreExpectedUSBDisconnect(logging.Filter):
    def filter(self, record):
        if record.getMessage() == "connection handler failed" and record.exc_info:
            return not isinstance(record.exc_info[1], ConnectionClosedError)
        return True


def run_adb(*args):
    result = subprocess.run(
        [str(ADB), *args],
        capture_output=True,
        text=True,
        timeout=15,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode:
        raise RuntimeError(
            (result.stderr or result.stdout or "ADB command failed").strip()
        )
    return result.stdout


def read_exact(sock, count, stop):
    data = bytearray()
    while len(data) < count:
        if stop.is_set():
            raise StopRequested
        readable, _, _ = select.select([sock], [], [], 0.5)
        if not readable:
            continue
        block = sock.recv(count - len(data))
        if not block:
            raise ConnectionError("ADB tracking socket closed")
        data.extend(block)
    return bytes(data)


def track_snapshots(stop):
    with socket.create_connection(ADB_SERVER, timeout=5) as sock:
        sock.settimeout(None)
        command = b"host:track-devices"
        request = f"{len(command):04x}".encode("ascii") + command
        sock.sendall(request)
        response = read_exact(sock, 4, stop)
        if response != b"OKAY":
            raise RuntimeError("ADB rejected track-devices: " + repr(response))
        print("[ADB] Listening for USB connection events", flush=True)
        while not stop.is_set():
            header = read_exact(sock, 4, stop)
            size = int(header.decode("ascii"), 16)
            snapshot = read_exact(sock, size, stop).decode("utf-8", "replace")
            yield snapshot


def usb_watcher(stop: threading.Event):
    configured_serial = None
    last_state = None
    ports = (HTTP_PORT, WS_PORT)

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
                    serial for serial, status in devices.items()
                    if status == "device"
                ]
                if len(ready) != 1:
                    if len(ready) > 1:
                        state = "multiple devices"
                    elif "unauthorized" in devices.values():
                        state = "authorization needed"
                    else:
                        state = "waiting for device"
                    if state != last_state:
                        print(f"[USB] {state}", flush=True)
                    configured_serial = None
                    last_state = state
                    continue

                serial = ready[0]
                current = run_adb("-s", serial, "reverse", "--list")
                present = all(f"tcp:{p} tcp:{p}" in current for p in ports)
                if serial == configured_serial and present:
                    continue

                print(
                    "[USB] Authorized device detected; restoring ports",
                    flush=True,
                )
                for port in ports:
                    run_adb(
                        "-s", serial, "reverse",
                        f"tcp:{port}", f"tcp:{port}",
                    )
                verified = run_adb("-s", serial, "reverse", "--list")
                if not all(f"tcp:{p} tcp:{p}" in verified for p in ports):
                    raise RuntimeError("Reverse ports disappeared during setup")
                configured_serial = serial
                last_state = "connected"
                print("[USB] Reverse ports 8765 and 8766 ready", flush=True)
        except StopRequested:
            return
        except (OSError, ValueError, RuntimeError, ConnectionError) as exc:
            if not stop.is_set():
                print(f"[ADB] Tracker error: {exc}", flush=True)
                print("[ADB] Retrying after 2 seconds", flush=True)
                configured_serial = None
                stop.wait(2)


def assert_port_available(port: int) -> None:
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError as exc:
            raise RuntimeError(
                f"Port {port} is already in use. Stop the old server first."
            ) from exc
