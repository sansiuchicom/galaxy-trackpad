# Phase 1 regression checklist

Run after restructuring. Compare against the archived v0.8 prototype behavior.

## Setup

```powershell
cd C:\touchpad
conda activate galaxytrackpad
python -m windows
```

Tablet: open `http://127.0.0.1:8765/touchpad_v04.html` after USB reverse is ready.

## Core touchpad

- [ ] One-finger cursor move
- [ ] One-finger tap / double-tap
- [ ] Double-tap drag
- [ ] Two-finger right-click
- [ ] Two-finger vertical / horizontal scroll
- [ ] Pinch zoom in / out
- [ ] Three-finger Windows gestures
- [ ] Four-finger Windows gestures
- [ ] Up to five contacts tracked

## Sensitivity

- [ ] Cursor slider changes move speed live (no Windows mouse settings change)
- [ ] Scroll slider changes two-finger scroll live; pinch scale stays normal
- [ ] Values stay within ~0.5x–2.0x

## S Pen

- [ ] Finger vs S Pen auto switch
- [ ] Pen pressure / tilt in Paint or OneNote
- [ ] Disabling S Pen applies on next START

## Connection / lifecycle

- [ ] START / STOP from GUI
- [ ] USB connect → reverse ports 8765/8766
- [ ] USB unplug → safe release; reconnect recovers
- [ ] WebSocket reconnect after tablet refresh
- [ ] STOP / Quit releases active contacts
- [ ] System tray hide / reopen / Quit

## Smoke (no device)

```powershell
python -c "from windows.engine import engine_main; from windows.core import ScaledTouchpad; print('ok')"
```
