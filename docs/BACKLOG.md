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
| **1b** | Drawing pad-aspect (letterbox matches real `#pad`) | Phase 1 remainder — [PEN_PHASE1_PLAN.md](PEN_PHASE1_PLAN.md) C2 |
| **2** | **S Pen capture-style region** (drag when you want) | After (1b); bigger UX |
| **3** | **Pop-up keypad + custom symbols** | After pen is comfortable for signatures |

---

## Open

### investigate — Drawing pad-aspect vs fixed tablet_aspect

**Plan:** [PEN_PHASE1_PLAN.md](PEN_PHASE1_PLAN.md) C2  

Drawing letterbox still uses `tablet_aspect` 1.6 (full Tab) while UV is the `#pad` box
(menu / fullscreen change the real aspect). Everyday whole-display stretch is OK after DPI fix.

---

### idea — S Pen region: drag like screen capture (phase 2)

**Reported:** 2026-10-01 · **Blocked on:** phase 1b  

When you want: drag a rectangle on the PC (like Win capture) and map the **full pad**
onto that rectangle — mini LCD tablet. Harder; discuss before coding.

---

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

### done — Pen only reached ~80% of the screen (DPI)

**Fixed:** `8074402` — per-monitor DPI awareness so bounds match injection pixels.  
**Verified:** 2026-10-01 Everyday corner test OK after restart.
