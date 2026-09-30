"""
BT lab, reversed roles: PC advertises and waits, the Tab picks this PC and dials.

Usage:
  python -m bluetooth_lab.windows_pad_server

Then on the Tab: GT BT Lab -> "Connect to a PC" -> pick this PC.
After connect the protocol is the same as windows_pad_client
(HELLO/ACK, PING/PONG, MODE FRAME, framed JSON contacts).
"""
from __future__ import annotations

import platform
import sys
import time

from bluetooth_lab import windows_client as bt1
from bluetooth_lab import windows_pad_client as pad
from bluetooth_lab.constants import SERVICE_UUID


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main() -> int:
    if sys.platform != "win32":
        _log("Windows only")
        return 1
    from bluetooth_lab.winrt_rfcomm import RfcommServer

    if "--no-pacing" in sys.argv:
        pad.PACING = False

    _log("Galaxy Trackpad BT lab - Windows PAD SERVER (Tab dials PC)")
    _log(f"Service UUID: {SERVICE_UUID}")
    try:
        server = RfcommServer()
    except Exception as exc:
        _log(f"Could not advertise the Bluetooth service: {exc}")
        return 1
    _log(f"Advertising as '{platform.node()}'. On the Tab: Connect to a PC -> pick this PC.")
    try:
        while True:
            sock = None
            while sock is None:
                sock = server.accept(timeout=0.5)
            _log(f"Tab connected: {sock.peer_name}")
            try:
                if not bt1._handshake(sock, 0):
                    _log("Peer did not speak Galaxy Trackpad - dropped")
                    continue
                pad._upgrade_frame(sock)
                pad._run_pad_session_interruptible(sock)
            except (OSError, ConnectionError, ValueError) as exc:
                _log(f"Session ended: {exc}")
            finally:
                sock.close()
            _log("Waiting for the Tab again...")
    except KeyboardInterrupt:
        _log("Stopped")
    finally:
        server.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
