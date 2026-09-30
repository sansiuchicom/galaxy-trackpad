"""Find the Tab's live RFCOMM channel for our service UUID via Windows SDP (WinRT).

Usage:
  python -m bluetooth_lab.sdp_winrt [MAC]
"""
from __future__ import annotations

import asyncio
import sys
import uuid as uuidlib

from winrt.windows.devices.bluetooth import BluetoothCacheMode, BluetoothDevice
from winrt.windows.devices.bluetooth.rfcomm import RfcommServiceId

from bluetooth_lab.constants import SERVICE_UUID

SDP_PROTOCOL_DESCRIPTOR_LIST = 0x0004


def _rfcomm_channel(attr: bytes) -> int | None:
    # UUID16 0x0003 (RFCOMM) followed by uint8 channel: 19 00 03 08 <ch>
    for i in range(len(attr) - 4):
        if attr[i : i + 4] == b"\x19\x00\x03\x08":
            return attr[i + 4]
    return None


async def find_channel(mac: str, service_uuid: str = SERVICE_UUID) -> tuple[int | None, str]:
    addr = int(mac.replace(":", ""), 16)
    dev = await BluetoothDevice.from_bluetooth_address_async(addr)
    if dev is None:
        return None, "device not found"
    sid = RfcommServiceId.from_uuid(uuidlib.UUID(service_uuid))
    res = await dev.get_rfcomm_services_for_id_with_cache_mode_async(sid, BluetoothCacheMode.UNCACHED)
    services = list(res.services)
    if not services:
        return None, "service not advertised (Tab app not listening)"
    for svc in services:
        attrs = await svc.get_sdp_raw_attributes_with_cache_mode_async(BluetoothCacheMode.UNCACHED)
        buf = attrs.lookup(SDP_PROTOCOL_DESCRIPTOR_LIST) if attrs.has_key(SDP_PROTOCOL_DESCRIPTOR_LIST) else None
        if buf is None:
            continue
        ch = _rfcomm_channel(bytes(buf))
        if ch:
            return ch, "ok"
    return None, "service found but no RFCOMM channel in record"


def main() -> int:
    mac = sys.argv[1] if len(sys.argv) > 1 else "BC:7A:BF:FF:71:85"
    ch, why = asyncio.run(find_channel(mac))
    print(f"CHANNEL={ch} ({why})")
    return 0 if ch else 3


if __name__ == "__main__":
    raise SystemExit(main())
