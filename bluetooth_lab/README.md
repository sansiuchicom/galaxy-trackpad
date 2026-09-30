# Bluetooth lab (BT-1)

Independent HELLO/ACK over Classic RFCOMM.  
**GalaxyTrackpad.exe is NOT required.**

| Role | Who | What |
|------|-----|------|
| Server | Tab | **GT BT Lab** → **Listen** |
| Client | PC | `python -m bluetooth_lab.windows_client` |

---

## Critical: real pairing first

On this PC, paired Classic devices must include the **Galaxy Tab**.

Check:

```powershell
python -m bluetooth_lab.windows_client
```

If you only see earbuds/speakers and **no Tab**, pair it:

1. Windows → Settings → Bluetooth → **Add device** → Bluetooth  
2. On Tab: Bluetooth on, make discoverable / accept pair  
3. Name like `석태의 Galaxy Tab S7` must appear as paired on **both** sides  

Do **not** use:

- `XX:XX:XX:XX:XX:XX` (example placeholder)  
- `02:00:00:00:00:00` (Android hides the real MAC)

---

## Test steps

1. Pair Tab ↔ PC (Classic). Unplug USB.  
2. Tab: **GT BT Lab** → **Listen**  
3. PC:

```powershell
cd C:\touchpad
conda activate galaxytrackpad
python -m bluetooth_lab.windows_client
```

4. Pick the Tab from the numbered list (or paste its MAC).  
5. Tab log should say `Listening on FIXED channel 5` then `Client accepted` / `RECV << HELLO`.  
6. Success: `BT-1 OK - HELLO/ACK and PING/PONG succeeded`

If PC says `Socket closed` / handshake failed on channel 5: install the **latest** BT Lab APK (fixed-channel listen), Stop → Listen, retry.
