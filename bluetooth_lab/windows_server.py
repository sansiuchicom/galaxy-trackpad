"""
BT-1 Windows RFCOMM lab server (Bluetooth Classic).

Listens on a fixed RFCOMM channel. The Tab app connects as client.
Does NOT touch the USB touchpad engine.

Usage:
  cd C:\\touchpad
  conda activate galaxytrackpad
  python -m bluetooth_lab.windows_server
"""
from __future__ import annotations

import socket
import sys
import threading
import time

from bluetooth_lab.constants import (
    MSG_ACK,
    MSG_HELLO,
    MSG_PING,
    MSG_PONG,
    RFCOMM_CHANNEL,
)

AF_BTH = getattr(socket, "AF_BTH", 32)
BTPROTO_RFCOMM = getattr(socket, "BTPROTO_RFCOMM", 3)
BDADDR_ANY = getattr(socket, "BDADDR_ANY", "00:00:00:00:00:00")


def _log(msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def _handle_client(conn: socket.socket, addr) -> None:
    _log(f"Client connected: {addr}")
    conn.settimeout(120.0)
    buf = ""
    try:
        while True:
            raw = conn.recv(1024)
            if not raw:
                _log("Client closed the socket")
                break
            buf += raw.decode("utf-8", errors="replace")
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                _log(f"RECV << {line}")
                upper = line.upper()
                if upper.startswith(MSG_HELLO):
                    reply = f"{MSG_ACK} Windows RFCOMM lab channel={RFCOMM_CHANNEL}\n"
                elif upper.startswith(MSG_PING):
                    reply = f"{MSG_PONG} {time.time():.3f}\n"
                else:
                    reply = f"{MSG_ACK} echo:{line}\n"
                conn.sendall(reply.encode("utf-8"))
                _log(f"SEND >> {reply.strip()}")
    except socket.timeout:
        _log("Idle timeout — closing client")
    except OSError as exc:
        _log(f"Client error: {exc}")
    finally:
        try:
            conn.close()
        except OSError:
            pass
        _log("Client handler finished")


def main() -> int:
    if sys.platform != "win32":
        _log("This lab server is Windows-only (AF_BTH).")
        return 1

    _log("Galaxy Trackpad BT-1 lab — Windows RFCOMM server")
    _log(f"Listening on RFCOMM channel {RFCOMM_CHANNEL}")
    _log("1) Pair Tab ↔ this PC in Windows Settings if not already")
    _log("2) Unplug USB (recommended for the real test)")
    _log("3) Tab: open **GT BT Lab** → pick this PC → Connect")
    _log("Ctrl+C to stop")
    _log("-" * 60)

    server = socket.socket(AF_BTH, socket.SOCK_STREAM, BTPROTO_RFCOMM)
    try:
        server.bind((BDADDR_ANY, RFCOMM_CHANNEL))
        server.listen(1)
    except OSError as exc:
        _log(f"Bind/listen failed: {exc}")
        _log("Is Bluetooth on? Is another process using RFCOMM channel "
             f"{RFCOMM_CHANNEL}?")
        return 1

    try:
        while True:
            _log("Waiting for Tab connection…")
            conn, addr = server.accept()
            threading.Thread(
                target=_handle_client, args=(conn, addr), daemon=True
            ).start()
    except KeyboardInterrupt:
        _log("Stopped by user")
    finally:
        try:
            server.close()
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
