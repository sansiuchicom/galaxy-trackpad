# Install guide

For people who just want to use Galaxy Trackpad.  
Developers who build from source: see the root [README](../README.md#build-from-source-developers), [packaging/README.md](../packaging/README.md), and [android/README.md](../android/README.md).

**Current release:** [v0.11.0](https://github.com/sansiuchicom/galaxy-trackpad/releases/tag/v0.11.0)

---

## What you need

| Item | Notes |
|------|--------|
| Windows PC | Developed and tested on **Windows 11** |
| Android tablet | Verified on **Samsung Galaxy Tab S7 (SM-T870)**. Other tablets may work; not verified. |
| Install once | USB cable (data-capable) **or** copy the APK another way |
| Daily use | **USB** (cable + USB debugging) **or** **Bluetooth** (devices paired in system settings) |

The app is **not** on the Play Store or Microsoft Store. You install the APK yourself (“unknown apps”).

---

## 1. Download

Open the [**v0.11.0 release**](https://github.com/sansiuchicom/galaxy-trackpad/releases/tag/v0.11.0) page and download:

| File | What it is |
|------|------------|
| [`GalaxyTrackpad-windows-v0.11.0.zip`](https://github.com/sansiuchicom/galaxy-trackpad/releases/download/v0.11.0/GalaxyTrackpad-windows-v0.11.0.zip) | Windows app + bundled ADB (`platform-tools`) |
| [`GalaxyTrackpad-v0.11.0.apk`](https://github.com/sansiuchicom/galaxy-trackpad/releases/download/v0.11.0/GalaxyTrackpad-v0.11.0.apk) | Android app (or use the android zip, which contains the same APK) |

---

## 2. Install on Windows

1. Unzip `GalaxyTrackpad-windows-v0.11.0.zip` anywhere you like.
2. Keep the folder together. Do **not** delete `_internal` or `platform-tools`.
3. Run **`GalaxyTrackpad.exe`**.
4. If Windows Firewall asks, allow it (the app uses localhost ports only).
5. Leave **Auto-start engine** on (default), or press **START**.
6. You should see the engine ready / waiting for a tablet. Bluetooth is advertised automatically while the engine runs; there is no separate “Bluetooth mode” on the PC.

Optional: enable **Start with Windows** in the app so it opens in the system tray at logon.

To exit completely: **QUIT** in the window, or tray → **Quit**. Closing the window alone may only hide it to the tray.

---

## 3. Install on the tablet (APK)

### Option A — copy the APK and open it

1. Copy `GalaxyTrackpad-v0.11.0.apk` to the tablet (USB file transfer, cloud drive, etc.).
2. On the tablet, open the file.
3. Allow **Install unknown apps** for that file manager / browser if Android asks.
4. Finish the install.

### Option B — install from the PC with ADB

1. On the tablet: **Settings → About tablet** → tap **Build number** seven times to unlock developer options (wording varies by device).
2. **Settings → Developer options** → enable **USB debugging**.
3. Plug the tablet into the PC with a data-capable USB cable. Accept the “Allow USB debugging?” prompt on the tablet if shown.
4. From a PowerShell window in the unzipped Windows folder (or any folder that has `adb`):

```powershell
.\platform-tools\adb.exe install -r path\to\GalaxyTrackpad-v0.11.0.apk
```

If you previously installed a **debug** build from Android Studio, uninstall that app first — the release APK is signed differently and will not update over it.

---

## 4. Connect and use

Start **`GalaxyTrackpad.exe`** on the PC first. Then open **Galaxy Trackpad** on the tablet (landscape is expected). Choose **one** transport for that launch:

### USB

1. USB debugging still enabled; cable plugged in.
2. On the tablet app, choose **USB**.
3. Wait for **CONNECTED · USB**.

The Windows app sets up ADB reverse ports automatically when it sees an authorized device. You do not type an IP address or open Chrome.

If the tablet stays on **WAITING**: restart the Windows app, confirm USB debugging, unplug/replug once, and close Chrome on the tablet if it was open (only one WebSocket client; newest wins).

### Bluetooth

1. Pair the tablet and the PC once in each device’s **Bluetooth settings** (OS pairing, not inside Galaxy Trackpad).
2. Start the Windows app / engine (it advertises the trackpad service while running).
3. On the tablet app, choose **Bluetooth**, then pick the PC from the list (last-used PC is listed first).
4. Wait for **CONNECTED · Bluetooth · &lt;PC name&gt;**.

You do **not** need the USB cable or USB debugging for a Bluetooth session after the APK is installed.  
You cannot switch USB ↔ Bluetooth mid-session; close the tablet app and choose again.

More detail: [BLUETOOTH.md](BLUETOOTH.md).

---

## 5. Everyday use

| Input | Result |
|-------|--------|
| Fingers on the dark pad | Windows Precision Touchpad (move, tap, scroll, pinch, 3/4-finger gestures) |
| S Pen tip | Windows pen (pressure / tilt), if your tablet has a supported pen |
| Everyday / Drawing | Pen mapping profiles (saved on Windows; switch from either app) |
| Fullscreen | Hides the side menu on the tablet; **Menu** brings it back |
| Sensitivity / monitor | Windows app → **Advanced** |

When finished on the PC: **QUIT**. The tablet app can stay installed.

---

## Upgrading

1. Download the newer release files.
2. Replace the Windows folder (or unzip over a fresh folder). Your settings file next to the exe (`galaxytrackpad_settings.json`) is created on first run.
3. Install the newer APK over the previous **release** APK (`adb install -r …` or open the new APK).

Debug ↔ release signature mismatch: uninstall the old app first.
