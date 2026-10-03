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
| **3b** | ~~Pen region Esc cancel~~ | **Done in v0.12.0** — keyboard grab / Window focus |
| **3c** | ~~Tablet Drawing sync after region pick~~ | **Done in v0.12.0** — USB + BT state push |
| **3d** | ~~Pinch zoom sensitivity~~ | **Done in v0.12.0** — Cursor / Scroll / Pinch sliders |
| **4** | ~~Keypad pages (2)~~ | **Done in v0.12.0** — full panel 1/2 flip |
| **5** | ~~Keypad custom symbols~~ | **Done in v0.12.0** — Windows edit UI → state |
---

## Open

### idea — Keypad size slider

User-adjustable keypad scale (persist on Windows). **v0.12.1** auto-fits to viewport height (verified Tab S7 + Galaxy S24); slider only if someone wants larger/smaller than auto.


---

## Parking lot

### parking — Touch feedback (tablet haptic)

Tried WebView `GalaxyPad.haptic` + `navigator.vibrate` + Windows toggle; no reliable feel on device. Dropped — not worth more time.

---

## Done

### done — Phone keypad fit + S24 verify (v0.12.1)

**Fixed:** keypad key size uses `100dvh` so 5 rows fit on short phone landscape; docs list Android phones/tablets (**Tab S7** + **Galaxy S24** verified).

### done — Keypad custom left symbols

**Fixed:** Windows **Edit keypad symbols…** edits left 20 keys per page; saved in settings; pushed in `state.keypad`. Right numpad fixed. Reset-to-defaults per page.  
**Verified:** 2026-10-03.

### done — Keypad pages (full panel 1/2)


**Fixed:** `1/2` toggle flips left symbols + right pad together. Page 2 = currency/misc + circled digits / math ops. Reopen → page 1.  
**Doc:** [KEYPAD_PLAN.md](KEYPAD_PLAN.md). **Verified:** 2026-10-03.

### done — Pinch zoom sensitivity


**Fixed:** `pinch_sensitivity` in settings + Windows **Pinch zoom sensitivity** slider (0.5–2.0x).  
`GestureScaler` amplifies 2-finger distance from centroid; cursor/scroll gains unchanged; default `1.0` = prior feel.  
**Verified:** 2026-10-03.

### done — Tablet Drawing sync after region pick


**Fixed:** shared `request_client_state_broadcast` (USB + BT); flush RELOAD after region pick; HTML always paints server profile.
**Verified:** 2026-10-03.

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
