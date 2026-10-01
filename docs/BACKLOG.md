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
| **3** | ~~Pop-up keypad + custom symbols~~ | **Done in v0.11.0** — [KEYPAD_PLAN.md](KEYPAD_PLAN.md) |

---

## Open

### idea — Keypad size slider

User-adjustable keypad scale (persist on Windows). v1 uses a fixed larger size tuned for Tab S7 landscape.

### idea — Keypad page-2 circled digits

Layer button flips numpad `0–9` faces to `⓪①…⑨`. Ops row unchanged.  
See [KEYPAD_PLAN.md](KEYPAD_PLAN.md) § Future.

### idea — Keypad symbol edit UI

Replace the hard-coded left 20 glyphs with a small favorites editor.

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
