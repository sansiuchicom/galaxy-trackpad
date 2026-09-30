# Bluetooth lab (BT-1)

Independent **HELLO / ACK** test over Bluetooth Classic RFCOMM.  
Does **not** move the mouse. **`GalaxyTrackpad.exe` is NOT required.**

| Role | Who | Command / UI |
|------|-----|----------------|
| **Server (listen)** | Galaxy Tab | **GT BT Lab** → **Listen** |
| **Client (dial)** | Windows PC | `python -m bluetooth_lab.windows_client <TAB_MAC>` |

USB touchpad app (`Galaxy Trackpad` icon) is separate — leave it closed for this test.

---

## You do this

### 1) Pair (once)
1. PC + Tab Bluetooth **On**  
2. Pair in Windows / Tab settings  
3. **Unplug USB** for a clean BT test  

### 2) Tab listens
1. Open **GT BT Lab** (not Galaxy Trackpad)  
2. Allow Bluetooth / Nearby devices (+ Advertise if asked)  
3. Note the **MAC** in the log (`Tab Bluetooth name=… MAC=XX:XX:…`)  
4. Tap **Listen (wait for Windows)**  
5. Status: `Listening…`

### 3) Windows dials
Stop the old `windows_server` if it is still running (Ctrl+C).

```powershell
cd C:\touchpad
conda activate galaxytrackpad
python -m bluetooth_lab.windows_client XX:XX:XX:XX:XX:XX
```

Use the Tab MAC from the lab screen.  
Success looks like: `BT-1 OK — HELLO/ACK and PING/PONG succeeded`

### 4) Pass
- [ ] Works with USB unplugged  
- [ ] Windows log shows ACK + PONG  
- [ ] Tab log shows RECV HELLO / SEND ACK  

---

## FAQ

**Need GalaxyTrackpad.exe?**  
No. Only the Python client + GT BT Lab.

**Old error “socket might closed / timeout” with windows_server?**  
That mode (PC listen / Tab dial) is flaky on Windows Python. Use **Tab Listen + windows_client** instead.

**Still fails?**  
Send: Tab log lines + Windows client output + whether devices show as paired.
