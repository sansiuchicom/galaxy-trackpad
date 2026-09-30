# Bluetooth lab (BT-1 / BT-2)

Independent RFCOMM lab. **GalaxyTrackpad.exe is NOT required.**

| Phase | Tab | PC | Done when |
|-------|-----|-----|-----------|
| BT-1 | GT BT Lab → Listen | `python -m bluetooth_lab.windows_client` | `BT-1 OK` HELLO/ACK PING/PONG |
| BT-2 | GT BT Lab → Listen (pad appears) | `python -m bluetooth_lab.windows_pad_client` | Finger on pad moves Windows cursor |

Wire format after `MODE FRAME`: **uint32 big-endian length + UTF-8 JSON** (same contact fields as USB WebSocket).

---

## Critical: real pairing first

On this PC, paired Classic devices must include the **Galaxy Tab**.

```powershell
python -m bluetooth_lab.windows_client
```

If you only see earbuds/speakers and **no Tab**, pair it in Windows Bluetooth settings.

Do **not** use `XX:XX:…` or `02:00:00:00:00:00`.

---

## BT-1 test

1. Pair Tab ↔ PC. Unplug USB.  
2. Tab: **GT BT Lab** → **Listen** (log: `Listening on FIXED channel 5`)  
3. PC:

```powershell
cd C:\touchpad
conda activate galaxytrackpad
python -m bluetooth_lab.windows_client
```

4. Success: `BT-1 OK - HELLO/ACK and PING/PONG succeeded`

---

## BT-2 test (cursor over Bluetooth)

1. Install latest debug APK (Listen must support FRAME mode).  
2. Tab: **GT BT Lab** → **Listen**  
3. PC:

```powershell
python -m bluetooth_lab.windows_pad_client
```

4. Tab should switch to the pad WebView (`PAD MODE`).  
5. Move one finger on the pad — Windows cursor should move.  
6. Try multitouch / S Pen tip if available.

Ctrl+C on PC releases contacts.

---

## Install / signature mismatch

If `INSTALL_FAILED_UPDATE_INCOMPATIBLE`:

```powershell
& "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" uninstall com.galaxytrackpad.app
& "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" install -r "C:\touchpad\android\app\build\outputs\apk\debug\app-debug.apk"
```

Channel **5** is lab-fixed so Windows can dial without SDP. Production later uses UUID discovery; channel numbers are not PC-specific.
