# Galaxy Trackpad

Turn a Samsung Galaxy Tab (e.g. **Tab S7 / SM-T870**) into a **Windows Precision Touchpad** plus optional **S Pen** tablet.

**Current release: [v0.9.1](https://github.com/sansiuchicom/galaxy-trackpad/releases/tag/v0.9.1)** (pre-1.0 daily driver)  
**v1.0.0** comes after longer real-world use. Not on Play Store / Microsoft Store.

Connection: **USB + ADB reverse + WebSocket**.  
Input: Windows synthetic Precision Touchpad + pen. No custom kernel driver.

---

## Quick start (recommended)

### 1. Download

From the [**v0.9.1 release**](https://github.com/sansiuchicom/galaxy-trackpad/releases/tag/v0.9.1):

| File | What |
|------|------|
| `GalaxyTrackpad-windows-v0.9.1.zip` | Windows app + bundled `platform-tools` (ADB) |
| `GalaxyTrackpad-android-v0.9.1.zip` | Contains `GalaxyTrackpad-v0.9.1.apk` |

### 2. Windows PC

1. Unzip `GalaxyTrackpad-windows-v0.9.1.zip` anywhere (keep the folder together — do not delete `_internal` or `platform-tools`).
2. Run **`GalaxyTrackpad.exe`**.
3. Allow firewall prompts if Windows asks (localhost only is used).
4. Leave **Auto-start engine** on (default). Status should move toward USB ready / waiting for tablet.

Optional: enable **Start with Windows** in the GUI so it opens in the tray at logon.

### 3. Galaxy Tab

1. Enable **Developer options** → **USB debugging**.
2. Plug USB into the PC; accept the debugging RSA prompt on the tablet if shown.
3. Install the APK:
   - Copy `GalaxyTrackpad-v0.9.1.apk` to the Tab and open it (allow “install unknown apps” for your file manager), **or**
   - From the PC (with the Tab connected):  
     `adb install -r GalaxyTrackpad-v0.9.1.apk`
4. Open the **Galaxy Trackpad** app (landscape). You should see **CONNECTED / USB** when the Windows engine is ready.

No Chrome. No typing `http://127.0.0.1…`.

### 4. Use it

- **Fingers** on the dark pad → Windows touchpad (move, tap, scroll, pinch, 3/4-finger gestures).
- **S Pen** → Windows pen (pressure / tilt). Profiles: **Everyday** / **Drawing & Signature** (Android menu or Windows window; Windows stores the setting).
- **Fullscreen** on Android hides the side menu; **Menu** brings it back.
- Sensitivity / monitor / pen mapping details → Windows app (**Advanced**).

When done: Quit the Windows app (tray → Quit). The tablet app can stay installed.

---

## Daily loop

1. USB cable in  
2. `GalaxyTrackpad.exe` on PC  
3. Galaxy Trackpad icon on Tab  
4. Wait for **CONNECTED**

If the Tab shows **WAITING**: start/restart the Windows exe, check USB debugging, unplug/replug once. Close Chrome on the Tab if it was open (only one WebSocket client; newest wins).

---

## Features

### Touchpad
- 1–5 finger contacts  
- Tap, double-tap, drag, two-finger scroll / right-click, pinch zoom  
- Native Windows 3- and 4-finger gestures  
- Independent cursor & scroll sensitivity (does **not** change physical mouse settings)

### S Pen
- Auto: finger → touchpad, tip → pen  
- **Everyday** — stretch to the selected monitor  
- **Drawing & Signature** — preserve aspect ratio  
- Profile sync Windows ↔ Android  
- On-pad **S Pen Area** frame from Windows mapping  

### Apps
- Windows: GUI + system tray, USB auto reverse / reconnect, Start with Windows  
- Android: WebView client, connection status, fullscreen, keep-screen-on, offline waiting retry  

---

## Requirements

- Windows 11 PC  
- Samsung Galaxy Tab with **USB debugging** (verified: Tab S7 / SM-T870)  
- USB cable (data-capable)  
- Release zips from GitHub (recommended) **or** build from source (below)

---

## Build from source (developers)

```powershell
cd C:\touchpad
conda env create -f environment.yml   # once
conda activate galaxytrackpad
python -m windows                     # or build the exe:
powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
```

Android:

```powershell
cd C:\touchpad\android
$env:JAVA_HOME = "C:\Program Files\Microsoft\jdk-17.0.20.101-hotspot"  # JDK 17
.\gradlew.bat assembleRelease
# APK: app\build\outputs\apk\release\app-release.apk
```

More: [packaging/README.md](packaging/README.md), [android/README.md](android/README.md).

### Ports (localhost)

| Port | Role |
|------|------|
| 8765 | HTTP (pad HTML) |
| 8766 | WebSocket (input + state) |
| 8767 | Windows GUI ↔ engine only |

---

## Settings

| What | Where |
|------|--------|
| Cursor / scroll sensitivity | Windows app |
| Everyday / Drawing profile | Windows **or** Android (saved on Windows) |
| Monitor / area / mapping | Windows **Advanced** |
| Start with Windows, auto-start, debug | Windows app |
| Fullscreen / connection UI | Android app |

Packaged Windows settings file: next to `GalaxyTrackpad.exe` (`galaxytrackpad_settings.json`).  
Dev (`python -m windows`): `windows/galaxytrackpad_settings.json`.

---

## Tests

```powershell
python -m unittest tests.test_pen_mapping -v
```

Manual: [tests/REGRESSION.md](tests/REGRESSION.md).

---

## Roadmap

| Phase | Status |
|-------|--------|
| 1–3 — Windows engine + Android WebView | Done |
| 4A/4B — APK + Windows exe packaging | Done (`v0.9.1`) |
| Longer soak / polish | In progress |
| 5 — Bluetooth (first-class RFCOMM transport) | Planned — see [docs/BLUETOOTH.md](docs/BLUETOOTH.md) |
| **1.0.0** | After real-world soak |

---

## Notes

- Gestures are handled by Windows, not remapped to keys on Android.  
- Release binaries are attached to GitHub Releases — not stored in git (`dist/`, `*.apk` ignored).  
- Personal signing keystore for Android stays local (never commit).  
- Old prototypes: `archive/`.
