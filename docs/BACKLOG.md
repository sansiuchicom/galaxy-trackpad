# Backlog — ideas & issues from real use

Living list. **Do not treat items here as committed roadmap dates.**  
Add new notes at the top of the right section when something shows up in daily use.

Status key: `idea` · `bug` · `investigate` · `wontfix` · `done`

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

### idea — Trackpad + number pad on one screen

**Reported:** 2026-10-01

Show a **trackpad surface** and a **numeric keypad** together on the tablet UI.

- Both visible at once when wanted.
- Each panel can be **turned on/off** independently (trackpad only, numpad only, or both).
- Numpad should send normal digit / numpad key events to Windows (exact key codes TBD when implementing).

**Rough UI sketch:** split layout (pad + keypad), with toggles in the side menu or settings sheet.

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
