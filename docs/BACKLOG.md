# Backlog — ideas & issues from real use

Living list. **Do not treat items here as committed roadmap dates.**  
Add new notes at the top of the right section when something shows up in daily use.

Status key: `idea` · `bug` · `investigate` · `wontfix` · `done`

---

## Suggested build order

Real-use priority (signatures first):

| # | Item | Why this order |
|---|------|----------------|
| **1** | **Pen mapping — display level** (Everyday full screen + Drawing aspect band) | See **[PEN_PHASE1_PLAN.md](PEN_PHASE1_PLAN.md)** (cause → fix). No drag-region yet. |
| **2** | **S Pen capture-style region** (drag a rectangle when you want) | Only after (1) feels right on a whole display. |
| **3** | **Pop-up keypad + custom symbols** | Orthogonal to pen; after pen is usable for daily signatures. |

Do **not** start (2) or (3) until (1) feels right in real signature apps.

---

## Open

### bug / investigate — Pen mapping feel (display level)

**Reported:** 2026-10-01 · **Plan:** [PEN_PHASE1_PLAN.md](PEN_PHASE1_PLAN.md)

**Agreed target:**

- **Everyday:** full pad → **whole** chosen display (`stretch`).
- **Drawing:** aspect-matched **pad band** → **whole** chosen display (`preserve`).
- Drag-to-select region: **later** (item below).

**Leading cause hypothesis:** Drawing uses fixed `tablet_aspect` (full Tab 1.6) while UV is relative to the `#pad` div (menu / fullscreen change the real aspect). Defaults already match the agreed modes; UX + pad-aspect wiring are the main fix path. Live corner test still required for Everyday.

---

### idea — Trackpad + pop-up keypad (digits + custom symbols)

**Reported:** 2026-10-01 (extended same day)

Pad stays the main surface. A **small menu / button** opens a panel (pop-in), not a permanent second layout unless the user wants that.

**Panel contents (tabs or pages — TBD):**

1. **Number pad** — digits and usual numpad keys → Windows key events.
2. **Custom symbol palette** — user-configured **emoji / emoticons / special characters** (not only 0–9). Examples people already bookmark elsewhere:
   - Circled / enclosed numbers and letters (`①②③…`, similar sets)
   - Common marks, arrows, shapes, check marks
   - Coding / “code” style emoji and symbols  
   Inspiration (reference only, not to copy wholesale):  
   [특수문자·이모티콘 정리](https://sharedfolder.tistory.com/35),  
   [Code emojis](https://emojidb.org/code-emojis)

**Behavior sketch:**

- Toggle: hide trackpad / hide keypad panel independently if useful; default = trackpad always, keypad on demand (“뿅”).
- Tapping a glyph **types/pastes that character into the focused Windows app** (Unicode via keyboard/IME injection or clipboard paste — choose when implementing).
- User can **edit the palette** (add/remove/reorder favorites); persist on Windows settings (same place as other prefs).
- Ship a small **starter set** (digits + a few circled numbers / checks); full lists stay optional imports.

**Open design questions (later):**

- Inject as Unicode text vs clipboard paste (app compatibility).
- How big the starter set is; whether “import from file” is needed.
- Same panel over Bluetooth (bandwidth irrelevant for rare key taps).

---

### idea — S Pen region: drag like screen capture (phase 2)

**Reported:** 2026-10-01 · **Blocked on:** phase 1 display mapping ([PEN_PHASE1_PLAN.md](PEN_PHASE1_PLAN.md))

When you want (not instead of display-level defaults): drag a rectangle on the PC
(like Win capture) and map the **full pad** onto that rectangle only — mini LCD tablet.

Not “pick a display subdivision in Advanced” as the main story — on-demand capture-style selection.

---

## Parking lot

_(Shorter notes; promote to Open when they grow clear enough.)_

_(empty)_

---

## Done

_(Move items here with a short “fixed in …” note when closed.)_

_(empty)_
