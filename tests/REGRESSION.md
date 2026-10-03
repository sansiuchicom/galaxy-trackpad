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
- [ ] Scroll slider changes two-finger pan/scroll live
- [ ] Pinch zoom slider changes pinch in/out scale; at **1.0x** matches previous (unscaled) pinch
- [ ] Raising pinch does **not** make one-finger cursor jumpier; raising cursor does **not** change pinch
- [ ] Values stay within ~0.5x–2.0x

## S Pen

- [ ] Finger vs S Pen auto switch
- [ ] Pen pressure / tilt in Paint or OneNote
- [ ] Pen always active when tip detected (no ON/OFF toggle)

## Connection / lifecycle

- [ ] START / STOP from GUI
- [ ] USB connect → reverse ports 8765/8766
- [ ] USB unplug → safe release; reconnect recovers
- [ ] WebSocket reconnect after tablet refresh
- [ ] STOP / Quit releases active contacts
- [ ] System tray hide / reopen / Quit

## Phase 2A — S Pen mapping

- [ ] Standard profile → Stretch on Display 1 / Display 2
- [ ] Drawing profile → Preserve aspect; circle/square look round on target monitor
- [ ] Active area 50–100%: pen outside area ignored; no stroke jump on re-entry
- [ ] Change mapping while tip down → applies only after tip up
- [ ] Profile change does **not** affect finger touchpad / sensitivity
- [ ] Old flat settings migrate (cursor/scroll preserved)

```powershell
python -m unittest tests.test_pen_mapping -v
```

## Phase 2B — Windows UX

- [ ] Everyday / Drawing radios with short hints
- [ ] Advanced: monitor map click-select + Identify Displays
- [ ] Standard / Drawing profiles edit independently and persist
- [ ] Start with Windows registers HKCU Run (`python ... main.py --tray`)
- [ ] `--tray` starts hidden in system tray
- [ ] Auto-start engine launches engine after GUI opens (waits if no USB)
- [ ] Touchpad sensitivities and gestures still unaffected by pen profile edits

## Phase 2C — Reliability

- [ ] Status distinguishes Waiting / Unauthorized / USB ready / Connected / Stopping / Error
- [ ] Normal log has no continuous `Fingers:` spam
- [ ] Show debug logs checkbox reveals finger-count / verbose lines
- [ ] USB unplug releases contacts; reconnect restores reverse ports
- [ ] Missing ADB / busy port surfaces as `[ERROR]` without hanging the GUI
- [ ] STOP / tray Quit still cleanly release inputs

## Phase 3A — Android WebView shell

See also [android/README.md](../android/README.md).

**Setup:** Windows GUI + engine + USB reverse as usual. Install debug APK from `android/`
(Android Studio → Open `C:\touchpad\android` → Run). Do **not** open Chrome for the pass.

- [ ] App launches landscape; loads pad without typing a URL
- [ ] Status: Connecting → USB Connected
- [ ] All Phase 1 touchpad gesture checks above via the **app**
- [ ] S Pen auto + pressure/tilt via the **app**
- [ ] USB unplug → reconnect without force-stopping the app
- [ ] Windows restart → tablet WS recovers
- [ ] Home / power briefly → no stuck Windows contacts
- [ ] Screen stays on while app is foreground
- [ ] Chrome path still works (regression: HTTP page unchanged)

**Out of scope for 3A:** side menu, profile sync UI, Drawing overlay, bundled HTML assets.

## Phase 3B — Menu + profile sync

Requires **Windows engine restart** (state protocol + last-client-wins WS).

- [ ] Side menu + grid pad; menu clicks do not move cursor
- [ ] CONNECTED after Windows `state` message
- [ ] Profile sync both directions (tablet ↔ Windows Everyday/Drawing)
- [ ] S Pen Area frame for Everyday and Drawing; fingers still full pad
- [ ] Fullscreen / Menu chrome excluded from input
- [ ] Settings sheet is informational only (no duplicate sensitivity controls)
- [ ] **Keypad:** menu / fullscreen open; Notepad digits + symbols; NumLock off still types digits; close via ✕ / backdrop (see [docs/KEYPAD_PLAN.md](../docs/KEYPAD_PLAN.md))

## Phase 3C — Stability

- [ ] Offline WAITING page when Windows HTTP unreachable; auto-retry
- [ ] USB unplug/replug and Windows STOP/START recover without app reinstall
- [ ] Pause/resume clears contacts; no stuck inputs
- [ ] Screen stays on in foreground
- [ ] Debug APK builds from Android Studio (`app/build/outputs/apk/debug/`)

## Keypad pages

- [ ] `1/2` flips **both** left and right grids
- [ ] Close + reopen returns to page 1
- [ ] Page 2 types `₩` `①` `÷` in Notepad

## Keypad custom symbols

- [ ] Windows **Edit keypad symbols…** opens; change a Page 1 cell; OK
- [ ] Tablet keypad left key shows the new glyph (USB; BT after APK if needed)
- [ ] Reset this page restores defaults
- [ ] Right numpad unchanged

## Touch feedback

- [ ] Keypad key tap buzzes briefly on tablet
- [ ] Pad finger move does **not** buzz continuously
- [ ] Windows checkbox off → no buzz; on → buzz returns after reconnect/state
