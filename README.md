# Galaxy Trackpad

Use a Samsung Galaxy Tab (e.g. Tab S7) as a Windows Precision Touchpad + optional S Pen tablet.

Current baseline: **v0.8** (USB + ADB reverse + WebSocket, `CreateSyntheticPointerDevice2` / `PT_TOUCHPAD`).

## Layout

```
windows/
  core/         # synthetic pointer, touchpad, pen, sensitivity, displays, pen_mapping
  transport/    # HTTP, ADB/USB, WebSocket, GUI control port
  settings/     # JSON config (nested Phase 2 schema + v0.8 migration)
  ui/           # PySide6 window + system tray
  static/       # touchpad_v04.html served to the tablet
  engine.py     # --engine process
android/        # WebView app (Phase 3)
tests/          # regression checklist
archive/        # frozen prototypes (do not run daily)
platform-tools/ # local ADB only — not in git
```

## Requirements

- Windows 11
- Conda env `galaxytrackpad` (Python 3.13) **or** pip + `requirements.txt`
- ADB: unzip [platform-tools](https://developer.android.com/tools/releases/platform-tools) into `platform-tools/` at the repo root
- Galaxy Tab with USB debugging authorized

```powershell
conda env create -f environment.yml
conda activate galaxytrackpad
# or: pip install -r requirements.txt
```

## Run

From the **repo root**:

```powershell
cd C:\touchpad
conda activate galaxytrackpad
python -m windows
```

Tray / logon style:

```powershell
python -m windows --tray
```

START in the GUI launches `python -m windows --engine`.
With **Auto-start engine** enabled, the engine starts automatically after the window opens.
**Start with Windows** writes an HKCU Run entry that launches `--tray` at logon.

Ports (localhost): HTTP `8765`, WebSocket `8766`, GUI control `8767`.

Settings file: `windows/galaxytrackpad_settings.json` (see `windows/settings.example.json`).

## Regression

See [tests/REGRESSION.md](tests/REGRESSION.md).

## Notes

- No custom kernel driver. Windows native touchpad gestures are used.
- Cursor/scroll gain scales injected coordinates only; physical mouse settings are untouched.
- Pre-restructure sources live under `archive/`.
