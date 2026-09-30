"""
BT-1 Windows RFCOMM lab CLIENT.

Connects to the Tab's RFCOMM lab server (Tab listens, PC dials).
Does NOT need GalaxyTrackpad.exe and does NOT touch the USB engine.

Usage:
  cd C:\\touchpad
  conda activate galaxytrackpad
  python -m bluetooth_lab.windows_client
  # or with MAC:
  python -m bluetooth_lab.windows_client AA:BB:CC:DD:EE:FF
"""
from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import time

from bluetooth_lab.constants import (
    MSG_ACK,
    MSG_HELLO,
    MSG_PING,
    MSG_PONG,
    RFCOMM_CHANNEL,
    SERVICE_UUID,
)

AF_BTH = getattr(socket, "AF_BTH", 32)
BTPROTO_RFCOMM = getattr(socket, "BTPROTO_RFCOMM", 3)


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _normalize_mac(raw: str) -> str:
    h = "".join(c for c in raw.upper() if c.isalnum())
    if len(h) != 12:
        raise ValueError(f"Bad MAC: {raw!r}")
    return ":".join(h[i : i + 2] for i in range(0, 12, 2))


def _guess_tab_macs() -> list[str]:
    """Best-effort paired device names/MACs from PowerShell (may be empty)."""
    ps = r"""
    Get-PnpDevice -Class Bluetooth -Status OK -ErrorAction SilentlyContinue |
      Where-Object { $_.FriendlyName -match 'Tab|Galaxy|SM-|Tablet' } |
      Select-Object -ExpandProperty InstanceId
    """
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    found: list[str] = []
    for line in out.splitlines():
        # InstanceId often contains BTHENUM\DEV_AABBCCDDEEFF\...
        if "DEV_" in line.upper():
            part = line.upper().split("DEV_")[-1].split("\\")[0]
            part = "".join(c for c in part if c.isalnum())[:12]
            if len(part) == 12:
                try:
                    found.append(_normalize_mac(part))
                except ValueError:
                    pass
    return list(dict.fromkeys(found))


def _try_connect(mac: str, channel: int, timeout: float = 3.0) -> socket.socket | None:
    sock = socket.socket(AF_BTH, socket.SOCK_STREAM, BTPROTO_RFCOMM)
    sock.settimeout(timeout)
    try:
        sock.connect((mac, channel))
        return sock
    except OSError:
        try:
            sock.close()
        except OSError:
            pass
        return None


def _connect(mac: str) -> tuple[socket.socket, int]:
    # Prefer lab channel, then scan — Android service-record channel is dynamic.
    channels = [RFCOMM_CHANNEL] + [c for c in range(1, 31) if c != RFCOMM_CHANNEL]
    _log(f"Connecting to {mac} (trying RFCOMM channels)…")
    for ch in channels:
        _log(f"  try channel {ch}…")
        sock = _try_connect(mac, ch)
        if sock is not None:
            _log(f"Connected on channel {ch}")
            return sock, ch
    raise ConnectionError(
        f"Could not connect to {mac} on channels 1–30. "
        "Is GT BT Lab listening on the Tab? Are devices paired?"
    )


def _session(sock: socket.socket) -> None:
    sock.settimeout(30.0)
    def send(line: str) -> None:
        sock.sendall((line.strip() + "\n").encode("utf-8"))
        _log(f"SEND >> {line.strip()}")

    def recv_line() -> str:
        buf = b""
        while b"\n" not in buf:
            chunk = sock.recv(256)
            if not chunk:
                raise ConnectionError("Socket closed while reading")
            buf += chunk
        return buf.split(b"\n", 1)[0].decode("utf-8", errors="replace").strip()

    send(f"{MSG_HELLO} from Windows")
    line = recv_line()
    _log(f"RECV << {line}")
    if not line.upper().startswith(MSG_ACK):
        _log("Unexpected reply (wanted ACK)")

    send(MSG_PING)
    line = recv_line()
    _log(f"RECV << {line}")
    if not line.upper().startswith(MSG_PONG):
        _log("Unexpected reply (wanted PONG)")

    _log("BT-1 OK — HELLO/ACK and PING/PONG succeeded")
    _log("You can Ctrl+C or just close this window.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        _log("Bye")


def main(argv: list[str] | None = None) -> int:
    if sys.platform != "win32":
        _log("Windows only")
        return 1

    parser = argparse.ArgumentParser(description="BT-1 Windows → Tab RFCOMM client")
    parser.add_argument(
        "mac",
        nargs="?",
        help="Tab Bluetooth MAC, e.g. AA:BB:CC:DD:EE:FF (shown in GT BT Lab)",
    )
    args = parser.parse_args(argv)

    _log("Galaxy Trackpad BT-1 lab — Windows CLIENT")
    _log("GalaxyTrackpad.exe is NOT required for this test.")
    _log("1) Pair Tab ↔ PC")
    _log("2) On Tab open GT BT Lab → tap Listen")
    _log("3) Run this client with the Tab MAC shown on screen")
    _log(f"Service UUID (for reference): {SERVICE_UUID}")
    _log("-" * 60)

    mac = args.mac
    if not mac:
        guessed = _guess_tab_macs()
        if len(guessed) == 1:
            mac = guessed[0]
            _log(f"Using guessed Tab MAC: {mac}")
        elif guessed:
            _log("Possible Tab MACs:")
            for g in guessed:
                _log(f"  {g}")
            _log("Re-run: python -m bluetooth_lab.windows_client AA:BB:CC:DD:EE:FF")
            return 2
        else:
            _log("Pass the Tab MAC from GT BT Lab status line, e.g.")
            _log("  python -m bluetooth_lab.windows_client AA:BB:CC:DD:EE:FF")
            return 2

    try:
        mac = _normalize_mac(mac)
    except ValueError as exc:
        _log(str(exc))
        return 2

    try:
        sock, _ch = _connect(mac)
    except ConnectionError as exc:
        _log(str(exc))
        return 1

    try:
        _session(sock)
    except (OSError, ConnectionError) as exc:
        _log(f"Session failed: {exc}")
        return 1
    finally:
        try:
            sock.close()
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
