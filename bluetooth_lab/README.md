# Bluetooth lab (BT-1)

Independent **HELLO / ACK** test over Bluetooth Classic RFCOMM.  
Does **not** move the mouse or use the USB touchpad engine.

Stable USB app remains **v0.9.1**. This lives on branch `dev/bluetooth`.

| Role | Device | What runs |
|------|--------|-----------|
| Server | Windows PC | `python -m bluetooth_lab.windows_server` |
| Client | Galaxy Tab | Launcher icon **GT BT Lab** |

RFCOMM channel: **5** (fixed, lab only).

---

## What **you** do (this part is mostly you)

Bluetooth needs real radios, pairing screens, and physical distance. The agent cannot click those for you.

### A. One-time pairing

1. On **Windows**: Settings → Bluetooth → On.  
2. On **Tab**: Settings → Connections → Bluetooth → On.  
3. Pair them (Tab appears on PC / PC appears on Tab).  
4. Confirm both “Paired” / “Connected” in system UI at least once.  
5. **Unplug the USB cable** for the real BT-1 test (ADB can stay unused).

If pairing fails (dongle drivers, etc.), stop and fix that before the lab app — the code cannot help.

### B. Windows lab server

```powershell
cd C:\touchpad
conda activate galaxytrackpad
python -m bluetooth_lab.windows_server
```

You should see: `Waiting for Tab connection…`  
Leave this window open.

### C. Android lab app

Install a **debug** build that includes **GT BT Lab** (second launcher icon):

```powershell
cd C:\touchpad\android
$env:JAVA_HOME = "C:\Program Files\Microsoft\jdk-17.0.20.101-hotspot"
.\gradlew.bat installDebug
```

Or Android Studio ▶ Run.

On the Tab:

1. Open **GT BT Lab** (not “Galaxy Trackpad”).  
2. Allow **Nearby devices / Bluetooth** permission if asked.  
3. Tap **Refresh paired devices**.  
4. Tap **your PC** in the list.  
5. Status should become **CONNECTED**.  
6. Log should show `SEND >> HELLO` and `RECV << ACK …`.  
7. Tap **PING** — expect `PONG`.  
8. Tap **Disconnect**, then connect again once.

### D. Pass / fail

| Check | Pass |
|-------|------|
| USB unplugged | Still connects |
| HELLO → ACK | Both logs show it |
| PING → PONG | Both logs show it |
| Disconnect / reconnect | Works once without relaunching Windows |
| Galaxy Trackpad (USB app) | Still works when you plug USB again (regression) |

**Fail examples:** bind error on Windows (BT off / channel busy), Tab list empty (not paired), connect fails (wrong device / channel / PC server not running).

---

## What success unlocks

BT-1 pass → BT-2 (send real touch JSON over the same pipe).  
BT-1 fail → try swapping listen role or a small native helper (see `docs/BLUETOOTH.md`).
