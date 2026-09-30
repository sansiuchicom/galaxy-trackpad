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


def _safe_close(sock: socket.socket | None) -> None:
    if sock is None:
        return
    try:
        sock.settimeout(0.25)
    except OSError:
        pass
    try:
        sock.close()
    except Exception:
        pass


class _LineBuf:
    """RFCOMM may coalesce READY+ACK into one recv — keep leftovers."""

    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock
        self.buf = b""

    def send(self, line: str) -> None:
        self.sock.sendall((line.strip() + "\n").encode("utf-8"))
        _log(f"SEND >> {line.strip()}")

    def recv_line(self) -> str:
        while b"\n" not in self.buf:
            chunk = self.sock.recv(256)
            if not chunk:
                raise ConnectionError("Socket closed while reading")
            self.buf += chunk
        line, self.buf = self.buf.split(b"\n", 1)
        return line.decode("utf-8", errors="replace").strip()


def _try_connect(mac: str, channel: int, timeout: float = 1.5) -> socket.socket | None:
    sock = socket.socket(AF_BTH, socket.SOCK_STREAM, BTPROTO_RFCOMM)
    sock.settimeout(timeout)
    try:
        sock.connect((mac, channel))
        return sock
    except OSError:
        _safe_close(sock)
        return None


def _handshake(sock: socket.socket, channel: int) -> bool:
    """
    Confirm this RFCOMM channel is our lab (not some other Tab service).
    Tab sends READY on accept; we then HELLO/ACK and PING/PONG.
    """
    sock.settimeout(2.5)
    io = _LineBuf(sock)
    try:
        io.send(f"{MSG_HELLO} from Windows")
        got_ack = False
        got_ready = False
        deadline = time.monotonic() + 2.5
        while time.monotonic() < deadline and not got_ack:
            remaining = max(0.15, deadline - time.monotonic())
            sock.settimeout(remaining)
            line = io.recv_line()
            _log(f"RECV << {line}")
            upper = line.upper()
            if upper.startswith("READY") and "GTBT" in upper:
                got_ready = True
                continue
            if upper.startswith(MSG_ACK):
                got_ack = True
                break
            _log(f"  channel {channel}: unexpected line, not lab")
            return False
        if not got_ack:
            _log(f"  channel {channel}: no ACK (is GT BT Lab on Listen?)")
            return False
        if not got_ready:
            _log("  (no READY banner — ACK still accepted)")
        io.send(MSG_PING)
        sock.settimeout(2.5)
        line = io.recv_line()
        _log(f"RECV << {line}")
        if not line.upper().startswith(MSG_PONG):
            _log(f"  channel {channel}: ACK ok but no PONG")
            return False
        return True
    except (OSError, ConnectionError, TimeoutError) as exc:
        _log(f"  channel {channel}: handshake failed ({exc})")
        return False


def _connect(mac: str, prefer: int | None = None) -> tuple[socket.socket, int]:
    first = prefer if prefer is not None else RFCOMM_CHANNEL
    channels = [first]
    for c in list(range(1, 16)) + list(range(16, 31)):
        if c not in channels:
            channels.append(c)
    _log(f"Connecting to {mac} (RFCOMM + READY/HELLO check)...")
    _log("Tab must show Listening (GT BT Lab icon, not USB app)")
    last_err = "no channel answered"
    for ch in channels:
        _log(f"  try channel {ch}...")
        sock = _try_connect(mac, ch)
        if sock is None:
            continue
        _log(f"  connect ok on channel {ch} — verifying GT BT Lab...")
        if _handshake(sock, ch):
            _log(f"Connected on channel {ch} (lab verified)")
            return sock, ch
        _safe_close(sock)
        last_err = f"channel {ch} accepted but was not GT BT Lab"
    raise ConnectionError(
        f"Could not reach GT BT Lab on {mac}.\n"
        f"  Last: {last_err}\n"
        "  1) Open GT BT Lab (not the USB Galaxy Trackpad icon)\n"
        "  2) Tap Listen — status must say Listening on channel N\n"
        "  3) Then re-run this Windows client"
    )


def _hold_open(sock: socket.socket) -> None:
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
        _hold_open(sock)
    except (OSError, ConnectionError) as exc:
        _log(f"Session failed: {exc}")
        return 1
    finally:
        _safe_close(sock)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
