"""Bluetooth Classic RFCOMM client transport (Tab listens, Windows dials)."""
from __future__ import annotations

import re
import socket
import threading
import time
from typing import Any, Callable

from windows.applog import debug, info, state
from windows.settings.store import (
    PROFILE_DRAWING,
    PROFILE_STANDARD,
    load_config,
    reload_settings,
    save_config,
    set_active_profile,
)
from windows.transport.framing import read_frame, write_frame
from windows.transport.session import SharedInput
from windows.transport.state_sync import build_client_state

# Reuse proven lab dialer.
from bluetooth_lab import windows_client as bt1


def _mode() -> str:
    cfg = load_config()
    raw = str(cfg.get("general", {}).get("connection_mode", "usb")).lower()
    if raw in ("auto", "bluetooth", "bt"):
        return "bluetooth" if raw in ("bluetooth", "bt") else "auto"
    return "usb"


def _prefer_channel() -> int | None:
    cfg = load_config()
    ch = cfg.get("general", {}).get("bluetooth_channel")
    try:
        n = int(ch)
        return n if 1 <= n <= 30 else None
    except (TypeError, ValueError):
        return None


def _pick_mac() -> str | None:
    cfg = load_config()
    saved = cfg.get("general", {}).get("bluetooth_mac")
    if saved:
        try:
            return bt1._normalize_mac(str(saved))
        except ValueError:
            pass
    devices = bt1.list_paired_classic_devices()
    tab_like = [
        d for d in devices if re.search(r"Galaxy|Tab|SM-|T870", d[0], re.I)
    ]
    if len(tab_like) == 1:
        return tab_like[0][1]
    if len(devices) == 1:
        return devices[0][1]
    return None


def _remember_mac(mac: str) -> None:
    cfg = load_config()
    if cfg.get("general", {}).get("bluetooth_mac") == mac:
        return
    cfg.setdefault("general", {})["bluetooth_mac"] = mac
    save_config(cfg)


def _handle_packet(shared: SharedInput, sock: socket.socket, packet: Any) -> None:
    if not isinstance(packet, dict):
        return
    msg_type = packet.get("type")
    if msg_type in ("hello", "get_state"):
        write_frame(sock, build_client_state())
        return
    if msg_type == "set_profile":
        try:
            name = str(packet.get("profile", PROFILE_STANDARD))
            wanted = (
                PROFILE_DRAWING
                if name in (PROFILE_DRAWING, "drawing_signature")
                else PROFILE_STANDARD
            )
            config = set_active_profile(load_config(), wanted)
            save_config(config)
            reload_settings()
            write_frame(
                sock,
                {
                    "type": "ack",
                    "action": "set_profile",
                    "profile": wanted,
                    "ok": True,
                },
            )
            write_frame(sock, build_client_state())
        except OSError as exc:
            write_frame(
                sock,
                {
                    "type": "ack",
                    "action": "set_profile",
                    "ok": False,
                    "error": str(exc),
                },
            )
        return
    if msg_type not in (None, "input") and "contacts" not in packet:
        return
    shared.apply(SharedInput.BT, packet)


def _run_one_session(
    shared: SharedInput,
    stop: threading.Event,
    should_abort: Callable[[], bool],
) -> None:
    mac = _pick_mac()
    if not mac:
        info("Bluetooth: no paired Galaxy Tab MAC - pair in Windows Settings")
        stop.wait(5)
        return

    info(f"Bluetooth: dialing {mac} (SDP lookup, not a fixed channel)")
    sock: socket.socket | None = None
    try:
        sock, ch = bt1._connect(mac, should_abort=should_abort)
        if should_abort():
            raise ConnectionError("Bluetooth dial aborted (USB active or stop)")
        _remember_mac(mac)
        io = bt1._LineBuf(sock)
        sock.settimeout(5.0)
        io.send("MODE FRAME")
        line = io.recv_line()
        if "FRAME" not in line.upper() or not line.upper().startswith("ACK"):
            raise ConnectionError(f"Expected ACK FRAME, got {line!r}")
        if io.buf:
            raise ConnectionError("Unexpected leftover after MODE FRAME")

        shared.claim(SharedInput.BT)
        state(tablet="connected", transport="bluetooth")
        info(f"Bluetooth pad session on channel {ch}")
        write_frame(sock, build_client_state())
        sock.settimeout(30.0)
        while not stop.is_set():
            try:
                packet = read_frame(sock)
            except socket.timeout:
                continue
            _handle_packet(shared, sock, packet)
    finally:
        shared.release_owner(SharedInput.BT)
        if not shared.usb_connected:
            state(tablet="disconnected", transport="none")
        bt1._safe_close(sock)


def run_bluetooth_worker(shared: SharedInput, stop: threading.Event) -> None:
    """Dial the Tab only when this engine was started in Bluetooth mode."""
    mode = _mode()
    info(f"Connection mode for this engine run: {mode}")
    if mode != "bluetooth":
        info("Bluetooth dial is off. Stop the engine and set Bluetooth before Start to use it.")
        while not stop.is_set():
            stop.wait(5.0)
        info("Bluetooth worker stopped")
        return

    info("Bluetooth mode: dialing Tab (no USB fallback)")
    fail_streak = 0
    while not stop.is_set():
        def should_abort() -> bool:
            return stop.is_set()

        try:
            _run_one_session(shared, stop, should_abort)
            fail_streak = 0
        except (OSError, ConnectionError) as exc:
            if stop.is_set() or "aborted" in str(exc).lower():
                break
            fail_streak += 1
            delay = min(30.0, 3.0 * fail_streak)
            info(f"Bluetooth: retry in {delay:.0f}s ({exc})")
            stop.wait(delay)
            continue
        except Exception as exc:  # noqa: BLE001
            fail_streak += 1
            info(f"Bluetooth: unexpected error {exc}")
            stop.wait(min(30.0, 5.0 * fail_streak))
            continue
        stop.wait(2.0)
    info("Bluetooth worker stopped")
