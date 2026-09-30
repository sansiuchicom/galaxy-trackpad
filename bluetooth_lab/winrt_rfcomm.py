"""Advertise our RFCOMM service on Windows (WinRT) and expose accepted links as sockets.

Python's AF_BTH server sockets never publish an SDP record, so the Tab could not
find the PC. RfcommServiceProvider does publish one, keyed by our service UUID.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import queue
import socket
import threading
import uuid as uuidlib

from winrt.windows.devices.bluetooth.rfcomm import RfcommServiceId, RfcommServiceProvider
from winrt.windows.networking.sockets import SocketProtectionLevel, StreamSocketListener
from winrt.windows.storage.streams import Buffer, DataWriter, InputStreamOptions

from bluetooth_lab.constants import SERVICE_UUID


class _LoopThread:
    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.loop.run_forever, name="winrt-bt", daemon=True).start()

    def submit(self, coro) -> concurrent.futures.Future:
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def run(self, coro, timeout: float | None = None):
        return self.submit(coro).result(timeout)


class WinRtSocket:
    """Minimal socket-like wrapper (recv/sendall/settimeout/close) over a WinRT StreamSocket."""

    def __init__(self, loop: _LoopThread, stream_socket) -> None:
        self._loop = loop
        self._sock = stream_socket
        self._writer = DataWriter(stream_socket.output_stream)
        self._timeout: float | None = None
        self._pending: concurrent.futures.Future | None = None
        self._buf = b""
        info = stream_socket.information
        self.peer_name = info.remote_host_name.display_name if info.remote_host_name else "?"

    def settimeout(self, timeout: float | None) -> None:
        self._timeout = timeout

    async def _read(self, n: int) -> bytes:
        result = await self._sock.input_stream.read_async(Buffer(n), n, InputStreamOptions.PARTIAL)
        return bytes(result)[: result.length]

    def recv(self, n: int) -> bytes:
        if self._buf:
            out, self._buf = self._buf[:n], self._buf[n:]
            return out
        # A timed-out read stays in flight; reuse it rather than starting a second one.
        if self._pending is None:
            self._pending = self._loop.submit(self._read(max(n, 1)))
        try:
            data = self._pending.result(self._timeout)
        except concurrent.futures.TimeoutError:
            raise socket.timeout("timed out") from None
        except Exception as exc:
            self._pending = None
            raise ConnectionError(str(exc)) from exc
        self._pending = None
        if len(data) > n:
            data, self._buf = data[:n], data[n:]
        return data

    async def _write(self, data: bytes) -> None:
        self._writer.write_bytes(data)
        await self._writer.store_async()

    def sendall(self, data: bytes) -> None:
        try:
            self._loop.run(self._write(bytes(data)), self._timeout)
        except concurrent.futures.TimeoutError:
            raise socket.timeout("send timed out") from None
        except Exception as exc:
            raise ConnectionError(str(exc)) from exc

    def close(self) -> None:
        try:
            self._sock.close()
        except Exception:
            pass


class RfcommServer:
    """Publishes the Galaxy Trackpad SDP record and queues incoming Tab connections."""

    def __init__(self, service_uuid: str = SERVICE_UUID) -> None:
        self._loop = _LoopThread()
        self._incoming: queue.Queue = queue.Queue()
        self._uuid = service_uuid
        self._provider = None
        self._listener = None
        self._loop.run(self._start(), timeout=15)

    async def _start(self) -> None:
        sid = RfcommServiceId.from_uuid(uuidlib.UUID(self._uuid))
        self._provider = await RfcommServiceProvider.create_async(sid)
        self._listener = StreamSocketListener()
        self._listener.add_connection_received(lambda _l, args: self._incoming.put(args.socket))
        await self._listener.bind_service_name_with_protection_level_async(
            self._provider.service_id.as_string(),
            SocketProtectionLevel.BLUETOOTH_ENCRYPTION_ALLOW_NULL_AUTHENTICATION,
        )
        self._provider.start_advertising(self._listener)

    def accept(self, timeout: float | None = None) -> WinRtSocket | None:
        try:
            raw = self._incoming.get(timeout=timeout)
        except queue.Empty:
            return None
        return WinRtSocket(self._loop, raw)

    def close(self) -> None:
        try:
            if self._provider is not None:
                self._provider.stop_advertising()
            if self._listener is not None:
                self._listener.close()
        except Exception:
            pass
