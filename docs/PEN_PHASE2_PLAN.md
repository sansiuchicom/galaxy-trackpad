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

**Start (Windows app only in v1)**

1. Button: **Select pen region** (main window; tray duplicate optional).  
2. **Clear pen region** next to it.  
3. Picker: dim the **chosen monitor**, drag a rectangle (capture-style), release = confirm, **Esc** = cancel.  
4. While picking: ignore tablet pen input; optionally hide/minimize the main window.  
5. Selecting a region switches active profile to **Drawing** and persists the region.

**After the region is set — what you see on the PC**

- Always show a **thin outline** of the active pen region on that monitor (semi-transparent border, not a heavy dim overlay).  
  Purpose: know where the pad maps without covering the signature UI.  
- Outside the box stays normal (no permanent dark veil).  
- Optional later: checkbox “Show region outline” to hide the line; **v1 default = on**.  
- Status text in the app: e.g. `Drawing · region` vs `Drawing · full display`.

**Tablet**

- Full-pad S Pen Area (stretch onto the region).  
- No region picker on the tablet in v1.

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

## 5. Locked decisions

1. **Region only in Drawing** (picker forces Drawing).  
2. **Persist** region in settings across restarts.  
3. Overlay / outline on the **chosen monitor only**.  
4. After set: **thin semi-transparent border always visible** on that region (v1); not a full-screen dim.  
5. **Clear** removes region + outline → display-level Drawing/Everyday again.

---

## 6. Out of scope (v1)

- Picking the region on the tablet  
- Keypad / symbol palette  
- Multiple saved regions / presets  
- Snapping to windows  

---

## 7. Success criteria

- Drag a box → pad corners map to that box; **thin outline** stays on screen.  
- Clear → outline gone; display mapping restored.  
- DPI 125% primary still correct (phase 1 awareness stays on).  
- Cancel / Esc leaves previous mapping unchanged.
