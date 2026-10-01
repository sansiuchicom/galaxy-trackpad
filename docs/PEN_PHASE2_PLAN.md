# Pen phase 2 — capture-style region (plan)

**Status:** planning (no code yet)  
**Depends on:** phase 1 done (DPI + live `#pad` aspect), verified over USB.

When you want a signature box (or any sub-rectangle), drag on the PC like
Win+Shift+S / screen capture. After that, **full pad ↔ that rectangle**
(absolute pen), until cleared or a new region is chosen.

---

## 1. Product (locked from discussion)

| Mode | Target | Pad |
|------|--------|-----|
| Everyday (no region) | Whole chosen display, `stretch` | Full pad |
| Drawing (no region) | Whole chosen display, `preserve` / aspect band | Aspect band on pad |
| **Region active** | User-dragged rectangle on the **chosen display** | **Full pad** stretch onto that rect |

- Region is **optional and on-demand**, not the default.  
- One monitor only (the profile’s selected display). Drag stays inside that monitor.  
- Not multi-monitor spanning.  
- Clear region → back to display-level Everyday/Drawing behavior.

---

## 2. UX sketch

**Windows app**

1. Button: **Select pen region** (main window and/or Advanced, Drawing-focused).  
2. Optional: dim/hide Galaxy Trackpad window briefly.  
3. Full-screen (or monitor-sized) overlay: crosshair, drag rectangle, **Enter/click** confirm, **Esc** cancel.  
4. While picking: ignore tablet pen input (or overlay topmost so ink doesn’t land in the wrong app).  
5. After confirm: toast / status “Pen region set”, engine reloads mapping.  
6. **Clear pen region** restores display-wide mapping.

**Tablet**

- No drag UI in v1 (PC picks the region; tablet just writes).  
- S Pen Area frame: when region is active, show **full pad** (stretch target is the region).  
- Optional later: small label “Region” vs “Display”.

---

## 3. Data model

Store on the **Drawing** profile (Everyday can ignore region, or we allow region only while Drawing is active — prefer **Drawing-only** for v1):

```text
pen.profiles.drawing:
  monitor_id
  mapping                  # stretch | preserve_aspect_ratio (display-level)
  area_size
  region: null | {
    # Normalized to the chosen monitor [0,1]²  (survives resolution/DPI changes better)
    left, top, right, bottom
  }
```

**Why monitor-relative 0–1:** phase 1 decided single-monitor; absolute virtual-screen pixels break when scale/layout changes. Clamp on load if invalid.

At runtime:

```text
target_pixels = map region (or full monitor) → PixelRect
if region:
    map UV with stretch onto target_pixels   # full pad → region
else:
    existing Everyday/Drawing display mapping
```

Reuse `map_uv_to_monitor` / `PenMapConfig` by setting `monitor=` to the target `PixelRect`.

---

## 4. Work slices

| Slice | What | Risk |
|-------|------|------|
| **2a** | Schema + migrate + `PenMapConfig` uses region rect when set; unit tests | Low |
| **2b** | Region picker overlay widget (drag, Esc, confirm); pause pen while open | Medium (Win32/Qt overlay, multi-DPI) |
| **2c** | Wire buttons, Clear, reload pen, state `active_rect` for tablet | Low |
| **2d** | Docs / BACKLOG; USB verify signature flow; BT smoke later | Low |

Suggested order: **2a → 2b → 2c → 2d**. Discuss overlay details before 2b if needed.

---

## 5. Open decisions (answer before coding 2b)

1. **Region only in Drawing**, or also Everyday? → Recommend **Drawing only**.  
2. **Persist across restarts?** → Recommend **yes** (in settings JSON).  
3. Overlay covers **one monitor** vs all virtual desktop? → Recommend **chosen monitor only**.  
4. After set region, force profile to Drawing? → Recommend **yes** if user started picker from a global button.

---

## 6. Out of scope (v1)

- Picking the region on the tablet  
- Keypad / symbol palette  
- Multiple saved regions / presets  
- Snapping to windows  

---

## 7. Success criteria

- Drag a box over a PDF signature field → pad corners map to that box corners.  
- Clear → Drawing/Everyday display mapping restored.  
- DPI 125% primary still correct (phase 1 awareness stays on).  
- Cancel / Esc leaves previous mapping unchanged.
