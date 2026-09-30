# Galaxy Trackpad

Turn a Samsung Galaxy Tab (e.g. **Tab S7 / SM-T870**) into a **Windows Precision Touchpad** plus optional **S Pen** tablet.

**Status:** Phases **1–3** complete. Phase **4A** Android APK + **4B** Windows `.exe` packaging are in the repo.  
**Next:** Daily-drive `0.9.x`, then optional installer polish / Bluetooth. **v1.0.0** after longer real-world use.

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
- Profiles sync both ways (Windows GUI ↔ Android menu)
- On-pad **S Pen Area** frame from Windows mapping
- Safe reload while the tip is down (applies after lift)

### Windows app
- PySide6 GUI + system tray
- START / STOP, auto-start engine, Start with Windows (`--tray`)
- USB auto reverse / reconnect, quiet logs + optional debug
- Clear connection states (waiting, authorize USB debugging, connected, error, …)

### Android app
- Kotlin WebView shell (no Chrome URL typing)
- Landscape trackpad UI: side menu, connection status, fullscreen mode
- Loads pad HTML from Windows over ADB reverse (`8765` / `8766`)
- Offline **WAITING** page + auto-retry when USB / Windows is down
- Screen stays on while the app is foreground
- Build/install: open `android/` in Android Studio → Run (see [android/README.md](android/README.md))

---

## Layout

```
windows/
  core/         # synthetic pointer, touchpad, pen, sensitivity, displays, mapping
  transport/    # HTTP, ADB/USB, WebSocket (+ state sync), GUI control port
  settings/     # nested JSON + v0.8 migration
  ui/           # main window, Advanced, monitor picker
  static/       # touchpad HTML (served to the tablet / WebView)
  engine.py     # --engine process
  applog.py     # info / debug / error / state lines
android/        # Galaxy Trackpad APK (WebView) — see android/README.md
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
- Android Studio (to build/install the tablet app)

```powershell
conda env create -f environment.yml
conda activate galaxytrackpad
# or: pip install -r requirements.txt
```

---

## Run

### Windows

**Packaged (Phase 4B):** build once, then double-click:

```powershell
cd C:\touchpad
conda activate galaxytrackpad
powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
# then run: dist\GalaxyTrackpad\GalaxyTrackpad.exe
```

Details: [packaging/README.md](packaging/README.md).

**From source (dev):**

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
| Packaged GUI | `dist\GalaxyTrackpad\GalaxyTrackpad.exe` |
| Packaged tray | `GalaxyTrackpad.exe --tray` |

With **Auto-start engine** on, the engine starts when the app opens.  
**Start with Windows** registers an HKCU Run entry (`python … --tray` in dev, or the **exe --tray** when packaged).

### Android tablet

1. Plug in USB and allow debugging if prompted.
2. Start the Windows app and wait until reverse / engine is ready.
3. Android Studio → **Open** `C:\touchpad\android` → **Run** on the Tab.
4. Launch **Galaxy Trackpad** on the tablet (no URL typing).

Daily use: Windows app + tablet app icon only. Android Studio is only needed to rebuild.

**Fallback (Chrome):** `http://127.0.0.1:8765/touchpad_v04.html`  
Close Chrome when using the app (one WebSocket client at a time; newest wins).

### Ports (localhost only)

| Port | Role |
|------|------|
| 8765 | HTTP (HTML) |
| 8766 | WebSocket (touch / pen + state / profile) |
| 8767 | GUI ↔ engine (`RELOAD` / `STOP`) — not used by Android |

Settings: `windows/galaxytrackpad_settings.json` (example: `windows/settings.example.json`).

---

## Settings (short)

| Area | Where |
|------|--------|
| Cursor / scroll sensitivity | Windows app |
| Everyday vs Drawing profile | Windows **or** Android menu (Windows stores) |
| Monitor / area / mapping | Windows **Advanced** |
| Start with Windows, auto-start, debug logs | Windows app |
| Fullscreen / connection UI | Android app |

Preserve-aspect mapping keeps **tablet CSS-pixel isotropy** on the target monitor’s pixel grid (not EDID millimetres).

---

## Tests

```powershell
python -m unittest tests.test_pen_mapping -v
```

Manual checklists: [tests/REGRESSION.md](tests/REGRESSION.md), [android/README.md](android/README.md).

---

## Roadmap

| Phase | Status |
|-------|--------|
| 1 — Package structure, single entry, preserve v0.8 | Done |
| 2 — S Pen profiles, UX, autostart, reliability | Done |
| 3 — Android WebView app (menu, sync, stability) | Done |
| 4A — Signed shareable APK (`0.9.x`) | Done |
| 4B — Windows `.exe` (PyInstaller onedir) | Done |
| 5 — Bluetooth transport (keep USB path) | Later |

---

## Notes

- Native Windows touchpad gestures — not remapped to keyboard shortcuts.
- Cursor/scroll gain only scales injected coordinates.
- Android does not interpret gestures; it streams contacts to Windows.
- Old prototypes live under `archive/`.
