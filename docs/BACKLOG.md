# Backlog — ideas & issues from real use

Living list. **Do not treat items here as committed roadmap dates.**  
Add new notes at the top of the right section when something shows up in daily use.

Status key: `idea` · `bug` · `investigate` · `wontfix` · `done`

---

## Suggested build order

Real-use priority (signatures first):

| # | Item | Why this order |
|---|------|----------------|
| **1** | **Pen mapping bug** (full monitor ↔ full pad) | Blocking signatures / drawing today. Smallest surface: `pen_mapping.py` + profile defaults + verify Everyday vs Drawing. |
| **2** | **S Pen drawing mode** (drag a PC region) | Needs correct mapping math from (1). Bigger UI (region picker on Windows). |
| **3** | **Pop-up keypad + custom symbols** | Orthogonal to pen; large tablet UI + Unicode inject. Do after pen is usable for daily signatures. |

Do **not** start (2) or (3) until (1) feels right in real signature apps.

---

## Open

### bug — Pen only covers the left part of the monitor

**Reported:** 2026-10-01 (real use after v0.10.0)

On the current Everyday / Drawing setup, S Pen input feels mapped to only a **left strip** of the Windows display instead of the **whole monitor ↔ whole pad**.

**Desired:** Full selected monitor (or full chosen area at 100%) maps edge-to-edge onto the pad surface — left/right/top/bottom of the pad = left/right/top/bottom of that region.

**Likely related code (for whoever picks this up later):**

- `windows/core/pen.py` — `active_rect()` / mapping
- Pen profiles in settings: `mapping` (`stretch` vs `preserve_aspect_ratio`), `area_size`
- Pad UI “S Pen Area” frame driven by server `active_rect` (`touchpad_v04.html`)

**Notes for investigation (not started):**

- Confirm which profile was active (Everyday = stretch, Drawing = preserve aspect by default).
- Confirm monitor selection and `area_size` in Advanced.
- Aspect-ratio “letterboxing” can look like unused bands; a **left-only** active region is a stronger signal of wrong rect math or wrong monitor bounds.

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

### idea — S Pen “drawing mode”: drag a PC region, use pad as LCD tablet

**Reported:** 2026-10-01

Workflow:

1. Enter a drawing / tablet mode on the tablet (or Windows).
2. **Drag a rectangle** on the Windows desktop (or on a preview) to choose the target region.
3. That rectangle becomes the **S Pen absolute mapping** area.
4. The tablet then acts like a **small LCD tablet** for that region (absolute pen), not relative trackpad.

Related to the full-screen mapping bug above, but this feature is about **user-chosen arbitrary regions**, not only “whole monitor”.

**Open design questions (later):**

- Who draws the selection overlay — Windows app, or tablet remote UI?
- Persist last region per profile?
- How this interacts with Everyday / Drawing profiles and Bluetooth latency.

---

## Parking lot

_(Shorter notes; promote to Open when they grow clear enough.)_

_(empty)_

---

## Done

_(Move items here with a short “fixed in …” note when closed.)_

_(empty)_
