# Pen mapping — cause analysis & fix plan (phase 1)

**Status:** analysis only (no feature code yet)  
**Agreed product (2026-10-01):**

| Mode | Pad | Chosen display | Notes |
|------|-----|----------------|--------|
| **Everyday** | Full pad active (`stretch`) | Whole display reachable | Distortion OK |
| **Drawing** | Only the **aspect-matched** pad region active (`preserve_aspect_ratio`) | Whole display reachable | Circles stay round |
| **Later** | Drag a rectangle like Win screen capture | That rect only | Out of scope for phase 1 |

Region-drag / multi-monitor spanning: **not in this plan.**

---

## 1. What the code does today

Pipeline: tablet `#pad` UV `(u,v) ∈ [0,1]²` → `active_rect` → pixels on the chosen monitor (`windows/core/pen_mapping.py` → `pen.py`).

| Profile default (settings) | Mapping | Active UV on pad |
|----------------------------|---------|------------------|
| Everyday (`standard`) | `stretch` | Full `[0,1]²` |
| Drawing (`drawing`) | `preserve_aspect_ratio` | Letterboxed / pillarboxed sub-rect |

Outside `active_rect` → `map_point` returns `None` → **no pen** (stroke ends).

Pad UI draws **S Pen Area** from server `pen.active_rect` (`touchpad_v04.html`).

This machine (dev settings): both profiles target `\\.\DISPLAY2` (primary **3072×1728**), `tablet_aspect = 1.6`, `area_size = 1.0`. Unit tests for the math all **pass**.

---

## 2. Measured behavior on this PC

Primary `3072×1728` (aspect ≈ 1.778), `tablet_aspect = 1.6`:

| Mode | Active pad UV | Pad corners | Active-region corners → monitor |
|------|---------------|-------------|----------------------------------|
| Everyday | Full | Map to all four monitor corners | Same |
| Drawing | **Full width**, height ≈ **0.90** (≈5% dead **top and bottom**) | Pad TL/TR/BL/BR → **dead** | Active corners → **all four monitor corners** |

So under Drawing on the primary, the designed dead zones are **top/bottom**, not a left strip. Math already sends the **whole monitor** from the active band.

Second display on this PC: `960×640` at odd virtual coords — under preserve that would get **left/right** dead bands. Settings currently point Everyday/Drawing at the primary, not this panel.

---

## 3. Causes (ranked)

### C0 — DPI virtualization (**confirmed by Step 0 logs, 2026-10-01**)

Engine / Python were **DPI-unaware**. On this PC the primary is **3840×2160 @ 125%**,
but unaware code saw **3072×1728**. Pen injection used the lie-sized bounds, so the
cursor only reached ~80% of the physical screen from the top-left — matches
“right/bottom stop short (~5/6)”.

**Fix:** `windows/dpi.py` + call at process start (`__main__` / `engine_main`) →
Per-Monitor DPI awareness V2 so `list_monitors` and pen use physical pixels.

### C1 — Product vs expectation (partly resolved in discussion)

Earlier “map the whole pad to the whole screen” sounded like **stretch**.  
Agreed Drawing goal is **preserve**: whole **display**, only matching **pad** band.  

Defaults in JSON **already match** that agreement (`standard`/`stretch`, `drawing`/`preserve`).  
Much of the pain may be **unclear UX** (dead bands look “broken”) rather than wrong defaults.

### C2 — Wrong `tablet_aspect` vs real `#pad` aspect (**fixed**)

Tablet now sends `pad_aspect` (= `#pad` CSS width/height) on `hello` (and resize /
fullscreen). Session override drives Drawing letterbox; settings `tablet_aspect`
remains fallback only.


### C3 — Weak / confusing pad feedback

S Pen Area is a quiet border; dead zones are not explained. Easy to read as “only part of the pad / screen works” without knowing Drawing is intentional letterboxing.

### C4 — If Everyday fails “whole screen” in a live corner test (**then** real bug)

Math on primary stretch already maps pad corners → monitor corners. If real use still misses screen edges, investigate next:

- DPI / coordinate space vs `InjectSyntheticPointerInput`  
- Stale / wrong `monitor_id`  
- Profile not actually `stretch` / `area_size < 1` at runtime  

Not proven from static analysis alone.

### C5 — Deferred

Custom drag region (capture-style): **phase 2**, after phase 1 is solid.

---

## 4. Fix plan (phase 1 only)

### Step 0 — Live reproduce (short, before coding)

On device, with engine log if useful:

1. **Everyday:** tip at pad TL / TR / BL / BR → cursor must hit the four corners of the **chosen** display.  
2. **Drawing:** confirm S Pen Area band; tip inside band → same four **monitor** corners; tip in dead band → no move.  
3. Note menu vs fullscreen (pad shape change).

Pass/fail of (1) decides how much of C4 we need.

### Step 1 — Align Drawing math with the real pad (**C2**)

**Goal:** `tablet_aspect` (or equivalent) = **current pad width/height in CSS pixels**, not a fixed full-tablet constant.

Options (pick one when implementing):

- **Preferred:** WebView sends `pad_aspect` (or `pad_w`/`pad_h`) on `hello` / resize / profile change; Windows stores session aspect for mapping + `active_rect` in state.  
- Fallback: derive from known layout; worse if menu/fullscreen toggles.

Redraw S Pen Area from the rect computed with that aspect.

Add unit tests: preserve with pad_aspect ≠ 1.6 still maps active corners to full monitor corners; outside → `None`.

### Step 2 — Everyday whole-display check (**C4** only if Step 0 fails)

- Confirm runtime profile/monitor/area.  
- If corners miss: DPI awareness or monitor bounds fix (minimal change).  
- Do **not** change Everyday away from stretch unless a bug requires it.

### Step 3 — UX clarity (**C1/C3**)

- Drawing: copy like “Pen area (keeps proportions)” / dim dead zone.  
- Everyday: full-pad frame or lighter “full screen” hint.  
- Advanced: keep mapping dropdown; defaults stay stretch / preserve as agreed.

### Step 4 — Docs

- Update `docs/BACKLOG.md` (bug status → in progress / done notes).  
- Short note in README or BLUETOOTH-adjacent only if user-facing behavior changes.

### Explicitly not in phase 1

- Drag-to-select region (capture-like)  
- Numpad / symbol palette  
- Changing Drawing default to stretch  

---

## 5. Success criteria

| Check | Pass |
|-------|------|
| Everyday | Four pad corners → four corners of chosen display |
| Drawing | Active band (aspect-matched to **pad**) → four corners of chosen display; dead band silent |
| Fullscreen toggle | Drawing band updates with pad aspect |
| Tests | Existing + new aspect/session cases green |

---

## 6. Implementation order when coding starts

1. Step 0 reproduce (you + logs)  
2. Step 1 pad-aspect plumbing + tests  
3. Step 3 overlay/copy  
4. Step 2 only if Everyday corner test failed  
5. Commit / push; phase 2 region picker stays backlog  

---

## 7. Locked decisions (from discussion)

1. Phase 1 = **display-sized** mapping only.  
2. Everyday ≈ today’s stretch; must cover **whole** chosen display.  
3. Drawing = whole display ↔ **aspect-matched pad region** (not full-pad stretch).  
4. Capture-style region drag = **after** phase 1.
