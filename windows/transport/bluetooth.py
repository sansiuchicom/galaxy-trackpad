"""Bluetooth Classic RFCOMM transport: the PC advertises, the Tab picks this PC and dials.

After connect: HELLO/ACK, PING/PONG, MODE FRAME/ACK FRAME as text lines, then
uint32 BE length + JSON frames (same contact packets as USB).
"""
from __future__ import annotations

import platform
import threading
from typing import Any

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
from windows.transport.pacing import PacedInput
from windows.transport.session import SharedInput
from windows.transport.state_sync import build_client_state

_HANDSHAKE_TIMEOUT_S = 5.0
_ADVERTISE_RETRY_S = 15.0


class _Lines:
    def __init__(self, sock) -> None:
        self.sock = sock
        self.buf = b""

    def send(self, line: str) -> None:
        self.sock.sendall((line.strip() + "\n").encode("utf-8"))

    def recv(self) -> str:
        while b"\n" not in self.buf:
            chunk = self.sock.recv(256)
            if not chunk:
                raise ConnectionError("Tab closed the link during handshake")
            self.buf += chunk
        line, self.buf = self.buf.split(b"\n", 1)
        return line.decode("utf-8", errors="replace").strip()


def _handshake(sock) -> str:
    """Confirm the peer is Galaxy Trackpad and switch to frames. Returns the Tab's name."""
    sock.settimeout(_HANDSHAKE_TIMEOUT_S)
    io = _Lines(sock)
    io.send(f"HELLO {platform.node()}")
    ack = io.recv()
    if not ack.upper().startswith("ACK"):
        raise ConnectionError(f"not Galaxy Trackpad (got {ack!r})")
    name = ack.split("name=", 1)[1].strip() if "name=" in ack else "Galaxy Tab"
    io.send("PING")
    if not io.recv().upper().startswith("PONG"):
        raise ConnectionError("no PONG")
    io.send("MODE FRAME")
    reply = io.recv()
    if not (reply.upper().startswith("ACK") and "FRAME" in reply.upper()):
        raise ConnectionError(f"expected ACK FRAME, got {reply!r}")
    # The Tab may start sending frames right behind ACK FRAME.
    sock.unread(io.buf)
    sock.settimeout(None)
    return name


def _handle_control(sock, packet: dict[str, Any]) -> bool:
    msg_type = packet.get("type")
    if msg_type in ("hello", "get_state"):
        from windows.settings.pad_aspect import apply_pad_aspect_from_message

        apply_pad_aspect_from_message(packet)
        write_frame(sock, build_client_state())
        return True
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
            write_frame(sock, {"type": "ack", "action": "set_profile", "profile": wanted, "ok": True})
            write_frame(sock, build_client_state())
        except OSError as exc:
            write_frame(sock, {"type": "ack", "action": "set_profile", "ok": False, "error": str(exc)})
        return True
    if msg_type == "key":
        try:
            from windows.core.keyboard import apply_key_packet

            apply_key_packet(packet)
        except (OSError, ValueError) as exc:
            debug(f"key inject failed: {exc}")
        return True
    return msg_type not in (None, "input") and "contacts" not in packet


def _run_session(shared: SharedInput, sock, stop: threading.Event) -> None:
    name = _handshake(sock)
    done = threading.Event()

    def close_on_stop() -> None:
        while not done.wait(0.5):
            if stop.is_set():
                sock.close()
                return

    threading.Thread(target=close_on_stop, name="bt-stop", daemon=True).start()
    pacer = PacedInput(sink=lambda packet: shared.apply(SharedInput.BT, packet))
    shared.claim(SharedInput.BT)
    info(f"Bluetooth: {name} connected")
    state(tablet="connected", transport="bluetooth", peer=name)
    try:
        write_frame(sock, build_client_state())
        while not stop.is_set():
            packet = read_frame(sock)
            if isinstance(packet, dict) and not _handle_control(sock, packet):
                pacer.apply_packet(packet)
    except (OSError, ConnectionError, ValueError) as exc:
        if not stop.is_set():
            info(f"Bluetooth: {name} disconnected ({exc})")
    finally:
        done.set()
        pacer.close()
        shared.release_owner(SharedInput.BT)
        if not shared.usb_connected:
            state(tablet="disconnected", transport="none")
        sock.close()


def run_bluetooth_worker(shared: SharedInput, stop: threading.Event) -> None:
    """Advertise Galaxy Trackpad over Bluetooth and serve one Tab at a time."""
    server = None
    while not stop.is_set() and server is None:
        try:
            from windows.transport.winrt_rfcomm import RfcommServer

            server = RfcommServer()
        except Exception as exc:  # noqa: BLE001 - adapter off, driver missing, winrt absent
            info(f"Bluetooth unavailable ({exc}); USB still works. Retrying in {_ADVERTISE_RETRY_S:.0f}s")
            stop.wait(_ADVERTISE_RETRY_S)
    if server is None:
        return
    info(f"Bluetooth: waiting for a tablet (this PC appears as '{platform.node()}')")
    try:
        while not stop.is_set():
            sock = server.accept(timeout=0.5)
            if sock is None:
                continue
            debug(f"Bluetooth: incoming link from {sock.peer_name}")
            try:
                _run_session(shared, sock, stop)
            except (OSError, ConnectionError, ValueError) as exc:
                info(f"Bluetooth: link dropped during handshake ({exc})")
                sock.close()
    finally:
        server.close()
        info("Bluetooth worker stopped")
