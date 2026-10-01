# Pen phase 2 — capture-style region (plan)

**Status:** planning (no code yet)  
**Depends on:** phase 1 done (DPI + live `#pad` aspect), verified over USB.

When you want a signature box (or any sub-rectangle), drag on the PC like
Win+Shift+S / screen capture. After that, **full pad ↔ that rectangle**
(absolute pen), until cleared or a new region is chosen.

---

## 1. Product (locked)

| Mode | Target | Pad |
|------|--------|-----|
| Everyday (no region) | Whole chosen display, `stretch` | Full pad |
| Drawing (no region) | Whole chosen display, aspect band (`preserve`) | Letterboxed pad |
| **Region active** (Drawing) | User rectangle on chosen display | **Full pad** `stretch` → that rect |

- Start picker from **Windows app** only (v1).  
- Persist region; Drawing-only; chosen monitor only.  
- After set: **thin semi-transparent border always on** that box (no permanent dim outside).  
- Clear → region + outline gone → display-level mapping again.

---

## 2. End-to-end UX (concrete)

```text
[Main window · S PEN card]
  ( ) Everyday   (•) Drawing & Signature
  Status: Drawing · full display   |   Drawing · region
  [ Select pen region ]   [ Clear region ]

Select pen region
  → force Drawing + save
  → pause tablet pen
  → overlay on chosen monitor (dim while dragging only)
  → user drags box, release = OK, Esc = cancel
  → save region {l,t,r,b} in 0..1 on that monitor
  → engine reload; outline window shows thin border
  → tablet state: active_rect = full pad (0..1)

Clear region
  → region = null; hide outline; reload; status back to full display
```

---

## 3. Data model

```text
pen.profiles.drawing:
  monitor_id
  mapping      # display-level only when region is null
  area_size
  region: null | { left, top, right, bottom }   # monitor-normalized [0,1]
```

Runtime (`build_pen_map_from_settings`):

```text
mon = resolve_monitor(monitor_id)           # physical pixels (DPI-aware)
if active profile is drawing AND region is set:
    target = PixelRect from mon + region 0..1
    PenMapConfig(mapping="stretch", area_size=1, monitor=target, ...)
else:
    existing display mapping (stretch / preserve + area_size)
```

Tablet `state.pen.active_rect`: UV on the pad.  
With region → `{0,0,1,1}` (whole pad). Without → current letterbox/full.

---

## 4. Work slices (what 2a / 2b / 2c / 2d mean)

Order: **2a → 2b → 2c → 2d**. Each slice should leave the repo buildable; commit after each.

### 2a — Mapping brain (no UI yet)

**Goal:** If Drawing has a `region` in settings, pen already maps full pad → that pixel box. Prove with tests / temporary settings edit.

| Do | Files (expected) |
|----|------------------|
| Add `region` to Drawing profile defaults + `migrate_config` (null / validate / clamp) | `windows/settings/store.py` |
| Helpers: norm rect ↔ `PixelRect` on a monitor | `windows/core/pen_mapping.py` (or small helper next to it) |
| `build_pen_map_from_settings`: if Drawing+region → stretch onto region pixels | `windows/core/pen.py` |
| `active_pen_profile` / state expose whether region is active | `store.py`, `state_sync.py` |
| Unit tests: region corners → correct pixels; invalid region ignored; no region = old behavior | `tests/test_pen_mapping.py` |

**Done when:** Manually putting a region in `galaxytrackpad_settings.json` and restarting the engine makes S Pen hit only that box (Everyday unchanged; Drawing without region unchanged). No picker UI yet.

**Not in 2a:** overlay, buttons, outline window.

---

### 2b — Capture picker + always-on outline (UI chrome)

**Goal:** User can drag a region on the chosen monitor; while a region exists, a **thin border** stays visible on that box.

| Do | Files (expected) |
|----|------------------|
| Full-monitor (or monitor-geometry) frameless Qt overlay: dim during drag, rubber-band rect, Esc cancel, release confirm | e.g. `windows/ui/region_picker.py` |
| Separate click-through or tool-window **outline** (1–2px semi-transparent border, always on top of that monitor, no fill / no dim) while region set | e.g. `windows/ui/region_outline.py` |
| API: `pick_region(monitor) -> NormRect \| None`, `show_outline(pixel_rect)`, `hide_outline()` | same modules |
| While picker open: signal engine/GUI to **ignore pen** (flag or local block) | picker ↔ `pen` / control hook (minimal) |

**Done when:** From a tiny test hook or temporary button, you can drag, confirm, see outline stay; Esc cancels with no change. Coordinates match DPI-aware monitor.

**Not in 2b:** wiring into main S PEN card / Clear / profile force / persist flow end-to-end (that’s 2c). Outline may be driven by temporary callbacks.

---

### 2c — Product wiring

**Goal:** Real buttons and status; save/load; tablet + engine stay in sync.

| Do | Files (expected) |
|----|------------------|
| S PEN card: **Select pen region** / **Clear region**; status `Drawing · region` vs `… · full display` | `windows/ui/main_window.py` |
| Select → Drawing + picker → save `region` + `save_config` + `reload_settings` + show outline | main_window + store |
| Clear → `region=null` + hide outline + reload | same |
| On app/engine start: if Drawing has region, show outline | main_window / engine ready path |
| Tray optional: same two actions | main_window tray menu |
| Tablet: `active_rect` full pad when region on; profile still Drawing | `state_sync.py` (mostly falls out of 2a) |

**Done when:** USB daily path works without editing JSON: Select → outline + pen in box → Clear → full display Drawing again.

---

### 2d — Docs & verify

| Do |
|----|
| Update `BACKLOG.md` / this plan status → done notes |
| USB: signature-field style test on 125% DPI primary |
| Note BT: same mapping; outline is PC-only (no APK required for core) |
| Remove any temporary test hooks from 2b |

---

## 5. Locked decisions (checklist)

1. Region only in **Drawing** (picker forces Drawing).  
2. **Persist** in settings.  
3. Picker + outline on **chosen monitor only**.  
4. After set: **thin outline always visible** (v1 default on).  
5. **Clear** drops region + outline.  
6. Tablet does not start the picker in v1.

---

## 6. Out of scope (v1)

- Tablet-side region pick  
- Keypad / symbols  
- Multiple presets / snap-to-window  
- “Hide outline” checkbox (can add later; default stays show)

---

## 7. Success criteria

- Select → drag over a signature field → pad corners = box corners; thin border visible.  
- Clear → border gone; Drawing display mapping back.  
- Esc during pick → nothing saved.  
- DPI 125% still correct.  
- Everyday never uses `region`.
