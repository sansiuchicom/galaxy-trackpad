# Backlog — ideas & issues from real use

Living list. **Do not treat items here as committed roadmap dates.**  
Add new notes at the top of the right section when something shows up in daily use.

Status key: `idea` · `bug` · `investigate` · `wontfix` · `done`

---

## Suggested build order

Real-use priority (signatures first):

| # | Item | Why this order |
|---|------|----------------|
| **1a** | ~~Pen DPI / whole-display Everyday~~ | **Done** (`8074402`, verified) |
| **1b** | ~~Drawing pad-aspect~~ | **Done** (`ffee08b`, verified USB) |
| **2** | ~~S Pen capture-style region~~ | **Done** (verified USB) — [PEN_PHASE2_PLAN.md](PEN_PHASE2_PLAN.md) |
| **3** | ~~Pop-up keypad v1~~ | **Done in v0.11.0** — [KEYPAD_PLAN.md](KEYPAD_PLAN.md) |
| **3b** | ~~Pen region Esc cancel~~ | **Done** (verified) — keyboard grab / Window focus |
| **3c** | Tablet Drawing sync after region pick | PC→tablet state push (USB + BT) |
| **4** | Keypad page(s) | Extra layers (e.g. circled digits) without growing the grid |
| **5** | Keypad custom symbols | User-editable special-character slots |
| **6** | Per-gesture sensitivity | Separate 1-finger vs 2+ finger feel |
| **7** | Touch feedback | Keypad taps / UI actions feel confirmed |

---

## Open

### bug — Pen region select does not refresh tablet Drawing / region UI

Starting region select forces Drawing on Windows and saves, but the tablet often stays on the old profile / overlay until the user taps **Drawing & Signature** again. Re-picking a region can also feel like it does not take until a manual profile tap. Likely PC→tablet state push gap (RELOAD broadcast is WebSocket-oriented; Bluetooth may not get a fresh `state`), plus possible stale `profilePending` / deferred pen-map apply.

### idea — Keypad page(s)

Extra keypad page(s) beyond v1’s single layer — e.g. page-2 circled digits `⓪①…⑨` on the numpad faces (ops row unchanged).  
See [KEYPAD_PLAN.md](KEYPAD_PLAN.md) § Future.

### idea — Keypad custom symbols

Let the user set the left special-character slots (replace the hard-coded 20 glyphs) via a small favorites / edit UI. Persist with settings.

### idea — 1-finger vs 2+ finger sensitivity

Separate cursor / scroll (or move) sensitivity when one finger is down vs when two or more fingers are active — so pointing and multi-touch gestures can feel different. Windows app settings; persist.

### idea — Keypad size slider

User-adjustable keypad scale (persist on Windows). v1 uses a fixed larger size tuned for Tab S7 landscape.

### idea — Touch feedback (keypad / pad actions)

Haptic and/or visual press feedback when tapping keypad keys and other pad UI actions (buttons, toggles), so presses feel confirmed without looking. Prefer short Android vibration / ripple where available; keep optional/quiet.

---

## Parking lot

_(empty)_

---

## Done

### done — Pen region picker Esc cancel

**Fixed:** overlay `Window` + ApplicationModal; `grabKeyboard` with local flag (no `keyboardGrabber`); Esc shortcut.  
**Verified:** 2026-10-03 — drag + Esc cancels; drag + release still commits.

### done — Pop-up keypad v1 (symbols + Win numpad)


**Released:** **v0.11.0** — translucent 4+4×5 overlay; menu/fullscreen chrome;  
digits via main-row VKs (NumLock-safe); left symbols via Unicode; USB + BT `type:"key"`.  
Also: stale-port reclaim on START, safer Quit, status error colors.  
**Doc:** [KEYPAD_PLAN.md](KEYPAD_PLAN.md).

### done — S Pen capture-style region (phase 2)

**Fixed:** `6c316a5`–`48f26c5` — Drawing region in settings, Select/Clear picker,
thin outline (Qt coords), pen injection (Win32).  
**Verified:** 2026-10-01 over USB.

### done — Drawing letterbox uses live #pad aspect

**Fixed:** `ffee08b` — session `pad_aspect` from tablet hello.  
**Verified:** 2026-10-01 over USB.
