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
| **3** | **Pop-up keypad + custom symbols** | Next big feature when you want it |

---

## Open

### idea — Trackpad + pop-up keypad (digits + custom symbols)

**Reported:** 2026-10-01 (extended same day)

Pad stays the main surface. A **small menu / button** opens a panel (pop-in).

1. **Number pad** → Windows key events  
2. **Custom symbol palette** — user favorites (emoji / special chars)  
   Refs: [특수문자 정리](https://sharedfolder.tistory.com/35), [Code emojis](https://emojidb.org/code-emojis)

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
