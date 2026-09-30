# Galaxy Trackpad

Use a Samsung Galaxy Tab (e.g. Tab S7) as a Windows Precision Touchpad + optional S Pen tablet.

Current baseline: **v0.8** (USB + ADB reverse + WebSocket, `CreateSyntheticPointerDevice2` / `PT_TOUCHPAD`).

## Layout

```
windows/     # Windows app + input engine (run from here)
android/     # Android WebView app (Phase 3)
tests/       # Automated / regression tests (WIP)
archive/     # Frozen prototypes (test_files, backup_v04/v07)
platform-tools/  # Local ADB only — not in git
```

## Requirements

- Windows 11
- Conda env `galaxytrackpad` (Python 3.13) **or** pip + `requirements.txt`
- ADB: unzip [platform-tools](https://developer.android.com/tools/releases/platform-tools) into `platform-tools/` at the repo root so `platform-tools/adb.exe` exists
- Galaxy Tab with USB debugging authorized

```bash
conda env create -f environment.yml
conda activate galaxytrackpad
# or: pip install -r requirements.txt
```

## Run

From the **repo root** (`C:\touchpad`):

```bash
python -m windows
```

START in the GUI launches the engine subprocess (`python -m windows --engine`).

Equivalent:

```bash
python windows/main.py
```

Ports (localhost only): HTTP `8765`, WebSocket `8766`, GUI control `8767`.

Copy `windows/settings.example.json` → `windows/galaxytrackpad_settings.json` if you want defaults on disk (the app also creates settings as you change sliders).

## Archive

Pre-restructure prototypes are under `archive/` (including the original `test_files` tree). Do not run those for daily use.

## License / notes

Local synthetic pointer injection; no custom kernel driver. Physical Windows mouse settings are not modified for cursor/scroll gain.
