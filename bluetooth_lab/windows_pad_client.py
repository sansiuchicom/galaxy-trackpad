"""
BT-2 Windows pad client: RFCOMM + length-prefixed JSON → local input engine.

Tab listens (GT BT Lab). This script dials, upgrades to framed mode, and
injects contacts into the same ScaledTouchpad / PenBridge path as USB WS.

Usage:
  python -m bluetooth_lab.windows_pad_client
  python -m bluetooth_lab.windows_pad_client AA:BB:CC:DD:EE:FF

GalaxyTrackpad.exe is NOT required (engine runs in-process).
"""
from __future__ import annotations

import argparse
import re
import socket
import sys
import time

from bluetooth_lab import windows_client as bt1
from bluetooth_lab.constants import SERVICE_UUID
from bluetooth_lab.framing import read_frame, write_frame
from windows.applog import info
from windows.transport.input_dispatch import InputSession
from windows.transport.state_sync import build_client_state

_PLACEHOLDER = re.compile(r"^(XX:)+XX$", re.I)


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _upgrade_frame(sock: socket.socket) -> None:
    io = bt1._LineBuf(sock)
    sock.settimeout(5.0)
    io.send("MODE FRAME")
    line = io.recv_line()
    _log(f"RECV << {line}")
    if "FRAME" not in line.upper() or not line.upper().startswith("ACK"):
        raise ConnectionError(f"Expected ACK FRAME, got: {line!r}")
    _log("Framed mode ON (uint32 BE length + JSON)")
    if io.buf:
        # Should be empty; framed reads use raw socket next.
        raise ConnectionError("Unexpected leftover bytes after MODE FRAME")


def _run_pad_session(sock: socket.socket) -> None:
    sock.settimeout(60.0)
    session = InputSession()
    info("BT-2 pad session: move a finger on the Tab pad")
    _log("Engine ready - touch the Tab pad (USB not needed)")
    try:
        write_frame(sock, build_client_state())
        _log("SEND frame type=state")
        while True:
            try:
                packet = read_frame(sock)
            except socket.timeout:
                continue
            if not isinstance(packet, dict):
                continue
            msg_type = packet.get("type")
            if msg_type in ("hello", "get_state"):
                write_frame(sock, build_client_state())
                continue
            if msg_type == "set_profile":
                # BT-2: acknowledge only; profile writes stay USB/WS for now.
                write_frame(
                    sock,
                    {
                        "type": "ack",
                        "action": "set_profile",
                        "ok": False,
                        "error": "set_profile over BT deferred to BT-3",
                    },
                )
                continue
            if msg_type not in (None, "input") and "contacts" not in packet:
                continue
            session.apply_packet(packet)
            event = packet.get("event")
            contacts = packet.get("contacts") or []
            if event in ("down", "up") or not contacts:
                tools = ",".join(sorted({str(c.get("tool")) for c in contacts})) if contacts else "-"
                _log(f"input event={event} n={len(contacts)} tools={tools}")
    finally:
        session.close()
        _log("Pad session ended - contacts released")


def main(argv: list[str] | None = None) -> int:
    if sys.platform != "win32":
        _log("Windows only")
        return 1

    parser = argparse.ArgumentParser(description="BT-2 Windows pad client")
    parser.add_argument("mac", nargs="?", help="Tab Bluetooth MAC")
    parser.add_argument(
        "--channel",
        type=int,
        default=None,
        help="Prefer RFCOMM channel shown on Tab Listen status",
    )
    args = parser.parse_args(argv)

    _log("Galaxy Trackpad BT-2 lab - Windows PAD CLIENT")
    _log("GalaxyTrackpad.exe is NOT required (engine in-process).")
    _log(f"Service UUID: {SERVICE_UUID}")
    _log("-" * 60)

    devices = bt1.list_paired_classic_devices()
    if not devices:
        _log("No Classic Bluetooth devices paired.")
        return 2

    _log("Paired Classic devices:")
    for i, (name, mac) in enumerate(devices, 1):
        mark = " <- likely Tab" if re.search(r"Galaxy|Tab|SM-|T870", name, re.I) else ""
        _log(f"  [{i}] {name}  {mac}{mark}")

    tab_like = [d for d in devices if re.search(r"Galaxy|Tab|SM-|T870", d[0], re.I)]
    mac = args.mac
    if mac and _PLACEHOLDER.match(mac.replace(" ", "")):
        mac = None
    if mac:
        try:
            mac = bt1._normalize_mac(mac)
            if mac in ("02:00:00:00:00:00", "00:00:00:00:00:00"):
                mac = None
        except ValueError:
            mac = None

    if not mac:
        if len(tab_like) == 1:
            mac = tab_like[0][1]
            _log(f"Auto-selected Tab: {tab_like[0][0]}  {mac}")
        else:
            mac = bt1._pick_mac_interactive(devices)
            if not mac:
                _log("No MAC selected.")
                return 2

    sock: socket.socket | None = None
    prefer = args.channel if args.channel and 1 <= args.channel <= 30 else None
    if prefer:
        _log(f"Prefer RFCOMM channel {prefer}")
    try:
        sock, ch = bt1._connect(mac, prefer=prefer)
        # _connect already completed HELLO/ACK/PING/PONG verification.
        _log(f"Lab channel {ch} verified - upgrading to framed pad mode")
        _upgrade_frame(sock)
        _run_pad_session(sock)
    except (OSError, ConnectionError, ValueError) as exc:
        _log(f"Failed: {exc}")
        return 1
    finally:
        if sock is not None:
            bt1._safe_close(sock)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
