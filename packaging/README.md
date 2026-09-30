# Windows packaging (Phase 4B)

Build a double-clickable **GalaxyTrackpad.exe** (no conda required at runtime).

## Build

From the repo root, with the `galaxytrackpad` conda env (or any env that has `requirements.txt` + PyInstaller):

```powershell
cd C:\touchpad
conda activate galaxytrackpad
powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
```

Output folder:

```text
dist\GalaxyTrackpad\
  GalaxyTrackpad.exe
  platform-tools\          # copied from repo if present
  galaxytrackpad_settings.json   # copied once if you already had settings
  _internal\               # PyInstaller runtime (do not delete)
```

## Run

1. Quit any `python -m windows` session (ports 8765–8767).
2. Double-click `dist\GalaxyTrackpad\GalaxyTrackpad.exe`.
3. Keep `platform-tools` next to the exe (ADB reverse).
4. Use the Android app as usual.

## Notes

- Settings for the packaged app live next to the exe (`galaxytrackpad_settings.json`), not under `windows\` in the repo.
- “Start with Windows” registers the **exe** with `--tray`.
- Rebuild after Windows code changes; Android APK is separate (Phase 4A).
- `dist/` is gitignored — share the folder as a zip if you want.
