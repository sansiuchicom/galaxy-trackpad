"""
BT-1 Windows RFCOMM lab CLIENT.

Connects to the Tab's RFCOMM lab server (Tab listens, PC dials).
GalaxyTrackpad.exe is NOT required.

Usage:
  python -m bluetooth_lab.windows_client
  python -m bluetooth_lab.windows_client AA:BB:CC:DD:EE:FF
"""
from __future__ import annotations

import argparse
import re
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

_DEV_RE = re.compile(r"BTHENUM\\\\DEV_([0-9A-F]{12})", re.I)
_PLACEHOLDER = re.compile(r"^(XX:)+XX$", re.I)


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _normalize_mac(raw: str) -> str:
    h = "".join(c for c in raw.upper() if c.isalnum())
    if len(h) != 12:
        raise ValueError(f"Bad MAC: {raw!r}")
    return ":".join(h[i : i + 2] for i in range(0, 12, 2))


def list_paired_classic_devices() -> list[tuple[str, str]]:
    """Return [(friendly_name, mac), ...] for Classic BTHENUM\\DEV_ devices."""
    ps = r"""
    Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue |
      Where-Object { $_.InstanceId -match 'BTHENUM\\DEV_' } |
      ForEach-Object { "{0}`t{1}" -f $_.FriendlyName, $_.InstanceId }
    """
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=20,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.SubprocessError) as exc:
        _log(f"Could not query paired devices: {exc}")
        return []

    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for line in out.splitlines():
        if "\t" not in line:
            continue
        name, iid = line.split("\t", 1)
        m = _DEV_RE.search(iid.replace("\\", "\\\\")) if False else None
        # InstanceId comes with single backslashes: BTHENUM\DEV_AABB...
        m = re.search(r"DEV_([0-9A-Fa-f]{12})", iid)
        if not m:
            continue
        mac = _normalize_mac(m.group(1))
        if mac in seen:
            continue
        seen.add(mac)
        found.append((name.strip() or "(no name)", mac))
    return found


def _pick_mac_interactive(devices: list[tuple[str, str]]) -> str | None:
    if not devices:
        return None
    _log("Paired Classic Bluetooth devices on this PC:")
    for i, (name, mac) in enumerate(devices, 1):
        mark = " <- likely Tab" if re.search(r"Galaxy|Tab|SM-|T870", name, re.I) else ""
        _log(f"  [{i}] {name}  {mac}{mark}")
    _log("Enter number (or full MAC), then Enter:")
    try:
        choice = input("> ").strip()
    except EOFError:
        return None
    if not choice:
        return None
    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(devices):
            return devices[idx - 1][1]
        return None
    try:
        return _normalize_mac(choice)
    except ValueError:
        return None


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
    channels = [RFCOMM_CHANNEL] + [c for c in range(1, 31) if c != RFCOMM_CHANNEL]
    _log(f"Connecting to {mac} (trying RFCOMM channels)...")
    for ch in channels:
        _log(f"  try channel {ch}...")
        sock = _try_connect(mac, ch)
        if sock is not None:
            _log(f"Connected on channel {ch}")
            return sock, ch
    raise ConnectionError(
        f"Could not connect to {mac} on channels 1-30.\n"
        "  - Is GT BT Lab on Listen?\n"
        "  - Is this the Tab real MAC from the list (not XX:XX or 02:00:00:00:00:00)?\n"
        "  - Is the Tab paired under Windows -> Bluetooth?"
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

    _log("BT-1 OK - HELLO/ACK and PING/PONG succeeded")
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
    parser.add_argument("mac", nargs="?", help="Tab Bluetooth MAC (from paired list)")
    args = parser.parse_args(argv)

    _log("Galaxy Trackpad BT-1 lab - Windows CLIENT")
    _log("GalaxyTrackpad.exe is NOT required.")
    _log(f"Service UUID: {SERVICE_UUID}")
    _log("-" * 60)

    devices = list_paired_classic_devices()
    if not devices:
        _log("No Classic Bluetooth devices paired on this PC.")
        _log("Windows Settings -> Bluetooth -> add your Galaxy Tab.")
        _log("Android Settings -> Bluetooth must show this PC as paired too.")
        _log("Then run GT BT Lab -> Listen, and run this client again.")
        return 2

    _log("Paired Classic devices:")
    for i, (name, mac) in enumerate(devices, 1):
        mark = " <- likely Tab" if re.search(r"Galaxy|Tab|SM-|T870", name, re.I) else ""
        _log(f"  [{i}] {name}  {mac}{mark}")

    tab_like = [d for d in devices if re.search(r"Galaxy|Tab|SM-|T870", d[0], re.I)]
    if not tab_like:
        _log("")
        _log("*** Galaxy Tab is NOT in this list yet - pair it in Windows Settings first. ***")
        _log("Buds / speakers alone are not enough.")

    mac = args.mac
    if mac and _PLACEHOLDER.match(mac.replace(" ", "")):
        _log("You passed a placeholder MAC (XX:XX:...). That was only an example.")
        mac = None
    if mac:
        try:
            mac = _normalize_mac(mac)
            if mac in ("02:00:00:00:00:00", "00:00:00:00:00:00"):
                _log("That MAC is Android's hidden/fake address - unusable.")
                mac = None
        except ValueError as exc:
            _log(str(exc))
            mac = None

    if not mac:
        if len(tab_like) == 1:
            mac = tab_like[0][1]
            _log(f"Auto-selected Tab: {tab_like[0][0]}  {mac}")
        else:
            mac = _pick_mac_interactive(devices)
            if not mac:
                _log("No MAC selected.")
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
