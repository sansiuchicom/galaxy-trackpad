# Galaxy Trackpad

Turn a Samsung Galaxy Tab (e.g. **Tab S7 / SM-T870**) into a **Windows Precision Touchpad** plus optional **S Pen** tablet.

**Status:** Phase 1–2 complete. Phase **3A** Android WebView shell is in the repo
(`android/`) — still loads the Windows-served HTML over ADB reverse.  
**Next:** Verify 3A on Tab S7, then 3B UI + profile sync.

Connection today: **USB + ADB reverse + WebSocket**.  
Input: Windows `CreateSyntheticPointerDevice2` / `InjectSyntheticPointerInput` (`PT_TOUCHPAD`, pen). No custom kernel driver.

---

## Features

### Touchpad
- 1–5 finger contacts
- Tap, double-tap, drag, two-finger scroll / right-click, pinch zoom
- Native Windows 3- and 4-finger gestures
- Independent cursor & scroll sensitivity (does **not** change physical mouse settings)

### S Pen
- Auto switch: finger → touchpad, S Pen tip → Windows pen (pressure + tilt)
- **Everyday** — stretch map to the selected monitor (default)
- **Drawing & Signature** — preserve aspect ratio for art / signatures
- Per-profile monitor, mapping, and active area (Advanced Settings)
- Safe reload while the tip is down (applies after lift)

### Windows app
- PySide6 GUI + system tray
- START / STOP, auto-start engine, Start with Windows (`--tray`)
- USB auto reverse / reconnect, quiet logs + optional debug
- Clear connection states (waiting, authorize USB debugging, connected, error, …)

---

## Layout

```
windows/
  core/         # synthetic pointer, touchpad, pen, sensitivity, displays, mapping
  transport/    # HTTP, ADB/USB, WebSocket, GUI control port
  settings/     # nested JSON + v0.8 migration
  ui/           # main window, Advanced, monitor picker
  static/       # touchpad_v04.html (served to the tablet)
  engine.py     # --engine process
  applog.py     # info / debug / error / state lines
android/        # WebView app (Phase 3A shell — see android/README.md)
tests/          # regression checklist + mapping unit tests
archive/        # frozen prototypes (do not run daily)
platform-tools/ # local ADB — not in git
```

---

## Requirements

- Windows 11
- Conda env `galaxytrackpad` (Python 3.13) **or** `pip install -r requirements.txt`
- [platform-tools](https://developer.android.com/tools/releases/platform-tools) unzipped to `platform-tools/adb.exe` at the repo root
- Galaxy Tab with **USB debugging** authorized for this PC

```powershell
conda env create -f environment.yml
conda activate galaxytrackpad
# or: pip install -r requirements.txt
```

---

## Run

From the **repo root**:

```powershell
cd C:\touchpad
conda activate galaxytrackpad
python -m windows
```

| Mode | Command |
|------|---------|
| GUI | `python -m windows` |
| Tray only | `python -m windows --tray` |
| Engine only | `python -m windows --engine` |

With **Auto-start engine** on, the engine starts when the app opens.  
**Start with Windows** registers an HKCU Run entry that launches `--tray` at logon.

### Tablet

**Preferred (Phase 3A):** install the Android app from `android/` (Android Studio →
Open → Run). It loads the same page over reverse without typing a URL.
Details / test checklist: [android/README.md](android/README.md).

**Fallback (Chrome):**

1. Plug in USB and allow debugging if prompted.
2. Wait until the GUI shows USB ready / connected path.
3. On the Tab, open: `http://127.0.0.1:8765/touchpad_v04.html`

### Ports (localhost only)

| Port | Role |
|------|------|
| 8765 | HTTP (HTML) |
| 8766 | WebSocket (touch / pen) |
| 8767 | GUI ↔ engine (`RELOAD` / `STOP`) |

Settings: `windows/galaxytrackpad_settings.json` (example: `windows/settings.example.json`).

---

## Settings (short)

| Area | What |
|------|------|
| Touchpad | Cursor / scroll sensitivity (live) |
| S Pen | Everyday vs Drawing on the main window; monitor / area / mapping in **Advanced** |
| General | Start with Windows, auto-start engine, show debug logs |

Preserve-aspect mapping keeps **tablet CSS-pixel isotropy** on the target monitor’s pixel grid (not EDID millimetres).

---

## Tests

```powershell
python -m unittest tests.test_pen_mapping -v
```

Manual checklist: [tests/REGRESSION.md](tests/REGRESSION.md).

---

## Roadmap

| Phase | Status |
|-------|--------|
| 1 — Package structure, single entry, preserve v0.8 | Done |
| 2 — S Pen profiles, UX, autostart, reliability | Done |
| 3A — Android WebView shell (HTTP URL) | Done |
| 3B — Menu / status / pen sync UI | Done |
| 3C — Stability + release APK | In progress — device verify |
| 4 — Windows installer / APK packaging | Later |
| 5 — Bluetooth transport | Later |

---

## Notes

- Native Windows touchpad gestures — not remapped to keyboard shortcuts.
- Cursor/scroll gain only scales injected coordinates.
- Old prototypes live under `archive/`.
