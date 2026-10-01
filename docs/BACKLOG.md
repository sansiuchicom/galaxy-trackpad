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
| **3** | **Pop-up keypad + custom symbols** | Plan: **[KEYPAD_PLAN.md](KEYPAD_PLAN.md)** (layout first) |

---

## Open

### idea — Trackpad + pop-up keypad (digits + custom symbols)

**Plan:** [KEYPAD_PLAN.md](KEYPAD_PLAN.md) — layout under discussion (two-column overlay recommended).

Pad stays the main surface. Translucent panel; Windows-like numpad + starter favorites.
---

## Parking lot

_(empty)_

---

## Done

### done — S Pen capture-style region (phase 2)

**Fixed:** `6c316a5`–`48f26c5` — Drawing region in settings, Select/Clear picker,
thin outline (Qt coords), pen injection (Win32).  
**Verified:** 2026-10-01 over USB.

### done — Drawing letterbox uses live #pad aspect

**Fixed:** `ffee08b` — session `pad_aspect` from tablet hello.  
**Verified:** 2026-10-01 over USB.

### done — Pen only reached ~80% of the screen (DPI)

**Fixed:** `8074402` — per-monitor DPI awareness so bounds match injection pixels.  
**Verified:** 2026-10-01 Everyday corner test OK after restart.
