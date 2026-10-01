# Keypad / symbols panel — v1 plan (layout first)

**Status:** planning (layout discussion → then implement)  
**Not started:** code.

Goal: occasional typing of digits and a few favorite marks without leaving the pad.
USB and Bluetooth share the same page (`touchpad_v04.html` + bridge / WebSocket).

---

## 1. Product (v1)

| | Choice |
|--|--------|
| Open | Small button in the side menu (or chrome) → panel pops in |
| Background | **Mostly transparent** — pad / fingers still visible underneath |
| Close | Same button, tap outside chrome, or ✕ |
| Tabs vs one screen | Prefer **one screen, two columns** (see §2) — not tab-switching for v1 |
| Digits | Windows-style numpad block |
| Symbols | Small starter favorites (①②… ✓ ←→ etc.); **edit UI later** |
| Transport | Same send path as today (packet or new `type: "keys"` / Unicode inject on PC) |

Out of scope v1: full emoji browser, custom editor, importing huge lists, holding trackpad+keypad as separate permanent panes.

---

## 2. Layout options (decide before coding)

Pad stays full-bleed. Panel is an overlay floating on top with a translucent scrim only behind the **keys**, not a solid card that hides the whole pad.

### Option A — Two columns, one glance (recommended)

```text
┌──────────────────────────────────────────────┐
│  pad (visible through transparent overlay)     │
│                                                │
│   ┌─────────────┐    ┌───────────────────┐   │
│   │  SYMBOLS    │    │   NUMBERS         │   │
│   │  (left)     │    │   (right)         │   │
│   │             │    │                   │   │
│   │  ① ② ③ ④   │    │   7  8  9         │   │
│   │  ⑤ ⑥ ⑦ ⑧   │    │   4  5  6         │   │
│   │  ✓  ←  →   │    │   1  2  3         │   │
│   │  …  ·  ※   │    │   0     .   ⌫    │   │
│   └─────────────┘    └───────────────────┘   │
│                                        [ ✕ ]   │
└──────────────────────────────────────────────┘
```

- **Right:** classic Win numpad feel — `789 / 456 / 123 / 0 . ⌫`  
- **Left:** favorites grid, same key size language, fewer columns so it doesn’t fight the numbers  
- One open action → both visible; no tab tap to switch  
- Fits “숫자랑 자주 쓰는 것들이 한눈에”

### Option B — Tabs (숫자 | 기호)

```text
        [ 숫자 ]  [ 기호 ]
        ┌─────────────────┐
        │   7 8 9         │
        │   4 5 6         │
        │   1 2 3         │
        │   0   .  ⌫      │
        └─────────────────┘
```

Simpler on narrow pads; worse for “한 화면에”. Secondary choice if A feels cramped on Tab S7 landscape.

### Option C — Numbers only centered; symbols in a thin strip above

Less “two panes”; easier to build; weaker for favorites. Fallback if A is too busy.

**Recommendation:** **Option A** on landscape Tab; if height is tight, shrink symbol rows first, keep numpad 4×3 intact.

---

## 3. Numpad key set (v1)

Fixed, Windows-like:

```text
7 8 9
4 5 6
1 2 3
0   .  ⌫
```

Optional later (not v1): `+` `−` `Enter`, NumLock.

PC side: send as keyboard digits / OEM period / Backspace (not clipboard), so focused apps get real key events.

---

## 4. Starter symbols (v1, hard-coded list)

Small set only — editable later:

- Circled digits: `①②③④⑤⑥⑦⑧⑨⑩` (or ①–⑨)  
- Marks: `✓` `✗` `※` `·` `…`  
- Arrows: `←` `→` `↑` `↓`  

Tap → insert Unicode into the focused Windows app (clipboard paste or Unicode inject — choose at implement time; prefer inject if reliable).

---

## 5. Visual rules

- Overlay root: transparent; only key cells have slight fill (`rgba` ~20–35% opacity) so pad texture shows through  
- Keys: large enough for finger (~48–56 CSS px), clear labels  
- Don’t dim the whole pad to black (lesson from region picker)  
- Panel anchored bottom or center-bottom so the top of the pad stays usable if we allow “half open” later; v1 can be center overlay with ✕  

---

## 6. Work slices (after layout lock)

| Slice | What |
|-------|------|
| **K1** | HTML/CSS overlay + Option A layout (no PC inject yet; log taps) |
| **K2** | PC: digit / backspace / `.` key injection |
| **K3** | PC: Unicode for starter symbols |
| **K4** | Wire open button; USB + BT smoke; docs |

---

## 7. Open decision (this chat)

1. **Layout:** A (two columns) vs B (tabs)? → leaning **A**  
2. **0 key:** wide `0` spanning two cells (true numpad) vs single cell + `.` + `⌫`?  
3. **Panel position:** center vs bottom dock?

Once those three are answered, implement K1.
