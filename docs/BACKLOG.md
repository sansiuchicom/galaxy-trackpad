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
| **4** | Keypad page(s) | Extra layers (e.g. circled digits) without growing the grid |
| **5** | Keypad custom symbols | User-editable special-character slots |
| **6** | Per-gesture sensitivity | Separate 1-finger vs 2+ finger feel |

---

## Open

### idea — Keypad page(s)

Extra keypad page(s) beyond v1’s single layer — e.g. page-2 circled digits `⓪①…⑨` on the numpad faces (ops row unchanged).  
See [KEYPAD_PLAN.md](KEYPAD_PLAN.md) § Future.

### idea — Keypad custom symbols

Let the user set the left special-character slots (replace the hard-coded 20 glyphs) via a small favorites / edit UI. Persist with settings.

### idea — 1-finger vs 2+ finger sensitivity

Separate cursor / scroll (or move) sensitivity when one finger is down vs when two or more fingers are active — so pointing and multi-touch gestures can feel different. Windows app settings; persist.

### idea — Keypad size slider

User-adjustable keypad scale (persist on Windows). v1 uses a fixed larger size tuned for Tab S7 landscape.

---

## Parking lot

_(empty)_

---

## Done

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
