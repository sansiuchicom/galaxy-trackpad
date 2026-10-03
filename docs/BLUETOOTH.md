# Galaxy Trackpad — Bluetooth

Shipped in **v0.10.0**. USB still works exactly as in v0.9.1.  
Pad UI updates (keypad pages, custom symbols, pinch sensitivity, phone fit) continue in later releases such as **v0.12.1**.

Bluetooth is a **byte pipe for the same pad JSON** as USB — not a Bluetooth HID mouse/touchpad.
Same pad page, same Windows input engine, same settings and pen profiles.

---

## 1. How to use it

1. Pair the tablet and the PC once in the OS Bluetooth settings.
2. Run Galaxy Trackpad on the PC and press **START**. The engine is always ready for USB **and** Bluetooth;
   there is no mode switch on the PC.
3. Open the tablet app and choose **Bluetooth**, then pick the PC from the list (last used PC is on top).
4. The pad shows **CONNECTED · Bluetooth · &lt;PC name&gt;**.

One transport per launch. Plugging in USB during a Bluetooth session does not switch; close the app and
choose USB instead. If the link drops, the tablet offers **Reconnect** or **Other PC**.

USB is still recommended for drawing: Bluetooth adds a small, steady delay (see §4).

---

## 2. Architecture

```text
Galaxy Tab app
  touchpad_v04.html (same file Windows serves over USB, bundled into the APK)
    │  USB: WebSocket via ADB reverse :8766
    │  Bluetooth: GalaxyBT bridge → RfcommPadClient (RFCOMM, dials the PC)
    ▼
Windows engine
  websocket.py (USB) ─┐
  bluetooth.py (BT) ──┼─ SharedInput (touch/pen) + keyboard.apply_key_packet (`type:"key"`)
                      ▼
               touchpad + pen + keypad injection
```

| Piece | File |
|-------|------|
| Pad HTML (USB + BT asset) | `windows/static/touchpad_v04.html` |
| Keypad inject | `windows/core/keyboard.py` — see [KEYPAD_PLAN.md](KEYPAD_PLAN.md) |
| RFCOMM service (WinRT, SDP-advertised) | `windows/transport/winrt_rfcomm.py` |
| BT session: handshake, frames, state/profile | `windows/transport/bluetooth.py` |
| Jitter buffer for BT input | `windows/transport/pacing.py` |
| Tablet RFCOMM client | `android/.../bluetooth/RfcommPadClient.kt` |
| Transport choice + PC picker | `android/.../MainActivity.kt` |

### Discovery

- The PC advertises service UUID `a1b2c3d4-e5f6-7890-abcd-ef1234567890` through WinRT
  `RfcommServiceProvider`. The RFCOMM channel number is assigned by Windows and **differs per PC**;
  nothing hardcodes it.
- The tablet connects with `createRfcommSocketToServiceRecord(UUID)` (SDP lookup). Only
  `BLUETOOTH_CONNECT` permission is needed.
- Plain Python `AF_BTH` server sockets do not publish SDP records, which is why the PC side uses WinRT (pywinrt).

### Wire protocol

1. PC → `HELLO <pc name>`, tablet → `ACK name=<tablet name>`
2. `PING` / `PONG <ms>`
3. `MODE FRAME` / `ACK FRAME`
4. Then both directions: `uint32 big-endian length` + UTF-8 JSON — the same messages as the USB WebSocket
   (`contacts` packets, `hello`, `state`, `set_profile`, `ack`, and keypad `type:"key"`).

---

## 3. Latency work (why it feels smooth)

| Problem | Fix |
|---------|-----|
| Many tiny reads/writes | PC reads 8 KB chunks; tablet writes header+body in one write |
| Too many packets for the radio | Bluetooth page sends at most one move per display frame with all fingers, short numbers, pressure/tilt only for the pen |
| Radio falls behind | Tablet keeps only the newest pending move; down/up are never dropped or reordered |
| Bursty arrival → stutter | PC replays packets on the tablet's timeline with an adaptive buffer (80th percentile jitter, 5–25 ms), 1 ms timer |

USB behavior is unchanged by all of the above.

---

## 4. Known limits

- Adds up to ~25 ms of smoothing delay on top of the radio.
- One tablet session at a time (newest wins, same as USB).
- No automatic reconnect across app launches; the tablet remembers the last PC and puts it first.
- HID, BLE and Wi‑Fi transports are out of scope.

---

## 5. Lab tools

`bluetooth_lab/` keeps the standalone test tools used to build this (GT BT Lab activity on the tablet,
Python lab server/clients on the PC). See [bluetooth_lab/README.md](../bluetooth_lab/README.md).
