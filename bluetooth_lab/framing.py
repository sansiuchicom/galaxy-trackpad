"""Length-prefixed JSON framing for BT-2+ (uint32 BE length + UTF-8 JSON)."""
from __future__ import annotations

import json
import struct
from typing import Any, BinaryIO

MAX_FRAME = 1_000_000
_HEADER = struct.Struct(">I")


def encode_frame(obj: Any) -> bytes:
    body = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(body) > MAX_FRAME:
        raise ValueError(f"Frame too large: {len(body)} bytes")
    return _HEADER.pack(len(body)) + body


def write_frame(sock_or_file: BinaryIO | Any, obj: Any) -> None:
    data = encode_frame(obj)
    if hasattr(sock_or_file, "sendall"):
        sock_or_file.sendall(data)
    else:
        sock_or_file.write(data)
        sock_or_file.flush()


def read_exact(sock_or_file: BinaryIO | Any, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        if hasattr(sock_or_file, "recv"):
            chunk = sock_or_file.recv(n - len(buf))
        else:
            chunk = sock_or_file.read(n - len(buf))
        if not chunk:
            raise ConnectionError("Socket closed while reading frame")
        buf.extend(chunk)
    return bytes(buf)


def read_frame(sock_or_file: BinaryIO | Any) -> Any:
    header = read_exact(sock_or_file, 4)
    (length,) = _HEADER.unpack(header)
    if length > MAX_FRAME:
        raise ValueError(f"Frame length {length} exceeds max {MAX_FRAME}")
    body = read_exact(sock_or_file, length)
    return json.loads(body.decode("utf-8"))
