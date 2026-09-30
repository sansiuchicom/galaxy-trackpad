# Galaxy Trackpad — Bluetooth plan (updated)

Status: **BT-1 in progress** (lab code on branch `dev/bluetooth`)  
Stable USB release to preserve: **v0.9.1**  
Development line: **v0.10.0-dev** (branch `dev/bluetooth`)

Bluetooth is a **first-class connection mode**, not a side experiment that replaces USB.
USB remains the reference path. Bluetooth reuses the same input engine.

---

## 1. Product goal

| | USB (v0.9.1) | Bluetooth (target) |
|---|---|---|
| Multitouch / Windows gestures | Yes | Same engine — verify latency |
| S Pen (pressure / tilt) | Yes | Same engine — verify stability |
| Sensitivity / pen profiles | Yes | Same messages / Windows store |
| Auto reconnect | Yes | Goal |
| Network / Wi‑Fi | No | No |
| Cable | Required | Not required after pairing |

**Honest caveat:** Feature parity is the goal; *feel* parity is measured in BT-5. If BT is consistently worse, ship it with “USB recommended for drawing” rather than claiming identical UX.

### Daily UX (target after BT-4)

1. Windows Galaxy Trackpad in tray.  
2. Tab app opens → tries last Bluetooth session (and/or USB if plugged).  
3. Fingers = touchpad, S Pen = pen — same as USB.  
4. No Chrome, no IP typing, no Wi‑Fi requirement.

---

## 2. Architecture (locked)

Bluetooth is a **byte pipe for the existing JSON**, not a Bluetooth HID mouse/touchpad.

```text
Galaxy Tab (WebView)
    │  Pointer Events → contacts / control JSON
    ▼
Input Sender (shared)
    │
    ├── USB Transport     → WebSocket (ADB reverse :8766)
    └── Bluetooth Transport → RFCOMM framed stream
            │
            ▼
     Session / Mux (one active input path)
            │
            ▼
     Existing Windows input engine
     (touchpad + pen + sensitivity + profiles)
```

| Piece | Role |
|-------|------|
| USB Transport | Current WebSocket + ADB reverse — **do not break** |
| Bluetooth Transport | RFCOMM connect/send/recv/reconnect |
| Session controller | Exactly one transport feeds the engine; no duplicate contacts |
| Input engine | Untouched as much as possible |

HID / custom drivers / BLE GATT streaming are **out of scope** for v0.10.

---

## 3. Technology choices

| Topic | Decision | Notes |
|-------|----------|--------|
| Radio | **Bluetooth Classic RFCOMM** first | Continuous coordinate stream; BLE later only if needed |
| Who listens? | **Tab listens / Windows dials** (chosen in BT-1) | Fixed lab channel 5 for BT-1/2; UUID/SDP for production later |
| Windows BT code | **Python first** | Same process as today’s app. If OS APIs block us, add a small **C#/C++ helper** and keep Python as orchestrator |
| Android | RFCOMM via platform APIs | BT-1 = isolated test UI, not deep WebView hooks |
| Message body | Reuse existing JSON | `contacts` packets + `type: state / set_profile / hello` |
| Framing (RFCOMM) | **Length-prefixed JSON** from day one | e.g. `uint32_be length` + UTF-8 JSON (no bare newline-only framing) |
| Security | Paired devices only | Prefer authenticated/encrypted RFCOMM; reject strangers injecting input |

---

## 4. Phases

Work on branch **`dev/bluetooth`**. Do not ship over v0.9.1 until BT-5 is acceptable.

### BT-1 — RFCOMM lab (no input engine)

**Status (dev/bluetooth): DONE** — Tab listens on fixed RFCOMM channel 5; Windows client dials, HELLO/ACK + PING/PONG verified.

**Do not modify** the production USB path except behind a clearly separate lab entry.

1. Pair Tab ↔ PC once in system settings; unplug USB.  
2. Minimal Android RFCOMM test (extra Activity / debug screen).  
3. Minimal Windows RFCOMM test (script or tiny window).  
4. Exchange `HELLO` / `ACK` (and maybe a counter).  
5. Detect disconnect; manual reconnect once.  
6. Record which listen role worked better. → **Tab listens, Windows dials.**

**Done when:** USB unplugged, bidirectional messages work, logs show connect/disconnect cleanly.

### BT-2 — Pipe real pad data (still thin UI)

**Status (dev/bluetooth): DONE (lab)** — GT BT Lab WebView pad → framed RFCOMM → `windows_pad_client` / `InputSession`. USB MainActivity / GalaxyTrackpad.exe integration is BT-3.

1. Reuse WebView contact collection (no new gesture logic).  
2. Bridge WebView → native (`JavascriptInterface` in lab; production may use `WebMessageListener`).  
3. Send framed JSON over RFCOMM (`uint32_be` + UTF-8).  
4. Windows BT receiver unwraps JSON → **existing** touchpad/pen update path (`windows/transport/input_dispatch.py`).  
5. Prove: 1-finger move → multitouch → S Pen.

**Done when:** Cursor/gestures/pen work over BT with USB cable out (engine path shared).

### BT-3 — Integrate into real apps

**Status (dev/bluetooth): in progress** — shared `InputSession`, Windows `connection_mode` (auto/usb/bluetooth), engine BT worker, MainActivity USB→BT fallback after ~8s.

1. Connection mode (simple): **Automatic / USB / Bluetooth** (or equivalent clear labels).  
2. Automatic = prefer USB when healthy; else BT — **never switch mid-gesture**; wait for all contacts up.  
3. Share state/profile sync messages over BT.  
4. Hide lab-only UI; keep USB v0.9 behavior as default fallback.

**Done when:** One Windows app + one Android app can use either transport without a separate test binary for daily use.

### BT-4 — Auto connect / reconnect

1. Remember last peer after successful session.  
2. Tray Windows waits; Tab open → connect attempt.  
3. Reconnect with backoff; on drop → release all Windows contacts.  
4. Pairing ≠ session: UI copy must say so.

**Done when:** Cold start (no cable) reaches CONNECTED without manual RFCOMM plumbing each time.

### BT-5 — Soak & latency

| Check | Goal |
|-------|------|
| Latency | Measure vs USB (same gestures) |
| Move stream | No multi-second cursor lag (coalesce moves if queued) |
| Down/up | Never coalesce; order preserved |
| Multitouch / pen | No stuck contacts after drop |
| Long run | Hours without leak / wedged BT |

**Done when:** Good enough to tag **v0.10.0** (or document limitations and still ship).

---

## 5. Repo layout (incremental — don’t create empty shells early)

Add modules only after BT-1 proves the link:

```text
windows/transport/
  websocket.py      # existing USB
  bluetooth.py      # NEW after BT-1
  session.py        # NEW when muxing (BT-3)

android/.../bluetooth/   # NEW lab first, then production

bluetooth-lab/           # OPTIONAL scratch for BT-1 only
tests/bluetooth/         # NEW checklists / tiny scripts

docs/BLUETOOTH.md        # this plan
```

Optional `bluetooth-helper/` only if Python RFCOMM is insufficient.

---

## 6. Non‑negotiables

1. **v0.9.1 USB stays usable** — branch away; don’t break main daily driver.  
2. **No duplicate injection** if USB and BT are both up.  
3. **Release contacts** on any transport drop.  
4. **No HID rewrite** of the Windows touchpad stack.  
5. **No Wi‑Fi dependency** for the BT path.  
6. Version: develop as **0.10.0-dev**; release **0.10.0** when BT-5 passes.

---

## 7. Immediate next actions (when coding starts)

1. Branch `dev/bluetooth` — **done**.  
2. Pair Tab + PC; confirm both OS UIs show paired (cable out).  
3. BT-1 lab: see **[bluetooth_lab/README.md](../bluetooth_lab/README.md)**  
   - Windows: `python -m bluetooth_lab.windows_server`  
   - Tab: **GT BT Lab** icon → connect → HELLO/ACK  
4. Decide listen role + Python vs helper from real logs.  
5. Only then touch WebView → engine wiring (BT-2).

---

## 8. Explicitly deferred

- BLE as primary transport  
- Play/Store packaging for BT builds  
- Fancy multi-PC device pickers (beyond “last device”)  
- Claiming identical latency to USB before BT-5 numbers exist  
