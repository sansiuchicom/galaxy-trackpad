# Galaxy Trackpad — Android

WebView shell around the existing touchpad HTML.
Windows still owns the input engine, ADB reverse, and settings.

**App version:** `0.12.1` (pre-1.0 daily build — not a store release)

## Status

| Slice | Goal | Status |
|-------|------|--------|
| **3A–3C** | WebView app, menu, sync, stability | Done |
| **4A** | Signed shareable APK (`0.9.x`) | Done |
| **4B** | Windows `.exe` / onedir package | Done — see [packaging/README.md](../packaging/README.md) |

---

## Phase 4A — Make an APK you can keep (no Play Store)

Goal: install once, then **quit Android Studio**. Daily use = tap the app icon.

### What you should have open / closed

| Thing | Now |
|-------|-----|
| Windows Galaxy Trackpad | Optional (only needed to *test* the pad) |
| Android Studio | **Open** `C:\touchpad\android` |
| Tab USB | Connected + debugging allowed |

### Build the release APK (click path)

1. Android Studio → Open → `C:\touchpad\android` (if not already).
2. Wait until Gradle sync finishes (bottom status).
3. Menu: **Build → Generate App Bundles or APKs → Generate APKs**  
   (wording may be **Build → Build Bundle(s) / APK(s) → Build APK(s)**).
4. Choose **release** if asked.
5. When done, click **locate** / open the folder. Typical path:

```text
C:\touchpad\android\app\build\outputs\apk\release\app-release.apk
```

6. Install on the Tab (pick one):
   - Studio still connected: **Run** is fine for debug; for the release file use:
     ```powershell
     cd C:\touchpad
     .\platform-tools\adb.exe install -r android\app\build\outputs\apk\release\app-release.apk
     ```
   - Or copy `app-release.apk` to the Tab and open it (may need “install unknown apps”).

7. On the phone or tablet, open **Galaxy Trackpad** — Settings sheet / About should reflect **0.12.1** (or check app info in Android settings).

After that you can **close Android Studio**. Rebuild only when we change the Android app.

### Signing (already set up on this PC)

- Keystore: `android/keystore/galaxy-trackpad.jks` (**not in git**)
- Passwords: `android/keystore.properties` (**not in git**)
- Example template: `android/keystore.properties.example`

**Back up** the `.jks` + `keystore.properties` somewhere safe (USB / password manager).  
If you lose them, a new key cannot update the same installed app.

This is **personal signing**, not Play Store.

### CLI (optional)

Needs **JDK 17** on PATH / `JAVA_HOME` (Android Studio’s JBR may be newer than Gradle 8.9 supports).

```powershell
cd C:\touchpad\android
$env:JAVA_HOME = "C:\Program Files\Microsoft\jdk-17.0.20.101-hotspot"  # adjust if needed
.\gradlew.bat :app:assembleRelease
```

Output: `app\build\outputs\apk\release\app-release.apk` (signed when `keystore.properties` exists locally).

---

## Prerequisites (daily use)

1. **Windows app running** (`python -m windows`) with engine / USB reverse OK  
2. Tab: **USB debugging** authorized  
3. Galaxy Trackpad Android app installed (`0.9.0` release or Studio debug)

---

## Open / build / install (dev)

```text
Android Studio → Open → C:\touchpad\android
```

1. Wait for Gradle sync.  
2. Connect Tab S7 over USB.  
3. Run ▸ `app` (debug, version name gets `-debug` suffix).  
4. Prefer **4A release APK** for daily driving.

CLI:

```powershell
cd C:\touchpad\android
.\gradlew.bat :app:installDebug
```

---

## Design note (HTML source)

Still loads **`http://127.0.0.1:8765/touchpad_v04.html`** from Windows over ADB reverse
(not fully bundled in the APK yet). Offline **WAITING** page is local if HTTP is down.

---

## Phase test checklists

### 4A — Release APK

- [ ] Gradle sync OK after pull
- [ ] Build release APK → `app/build/outputs/apk/release/app-release.apk`
- [ ] `adb install -r` (or copy) onto Tab
- [ ] App info shows version **0.9.0**
- [ ] Pad still connects with Windows running
- [ ] Android Studio closed; app icon still works next day

### 3A — Input parity

**Prep**

1. `conda activate galaxytrackpad` → `python -m windows`  
2. Confirm Windows GUI: USB / reverse OK (not stuck on authorize).  
3. Install/run the Android app on Tab S7.  
4. Optional control: Chrome URL once → then close Chrome and use only the app.

**Connection**

- [ ] App opens landscape, dark pad, no Chrome URL bar  
- [ ] Status goes Connecting → USB Connected without typing an address  
- [ ] Unplug USB → Disconnected / Reconnecting…  
- [ ] Plug USB again → Connected again **without** force-stopping the app  
- [ ] Restart Windows app → tablet reconnects within a few seconds  

**Touchpad (same as Chrome)**

- [ ] 1-finger move / tap / double-tap / double-tap drag  
- [ ] 2-finger right-click + scroll  
- [ ] Pinch zoom  
- [ ] 3- and 4-finger Windows gestures  
- [ ] Up to 5 contacts  

**S Pen**

- [ ] Finger = touchpad, tip = Windows pen (auto)  
- [ ] Pressure + tilt in Paint / OneNote  
- [ ] Everyday / Drawing still switch **only on Windows** (3A has no Android profile UI)

**App lifecycle**

- [ ] Screen stays on while the app is foreground (no idle timeout dim-off from the app)  
- [ ] Home → return: no stuck fingers on Windows; reconnect if needed  
- [ ] Power button off/on: contacts cleared; usable again after unlock  

**Pass rule:** Feels the same as Chrome for touch + pen. If something differs, note it before 3B.

---

### 3B — UI + sync (do after Windows engine restart)

**Prep:** Quit/restart Windows Galaxy Trackpad (new WebSocket state protocol).  
Rebuild/reinstall Android app **or** force-stop the app and reopen (URL cache-bust `?v=3b`).

- [ ] Left menu visible; pad is the dark grid area only
- [ ] Menu taps do **not** move the Windows cursor
- [ ] CONNECTED only after link is ready (not forever Waiting with cable only)
- [ ] Everyday / Drawing on tablet → Windows radios follow within ~1s
- [ ] Everyday / Drawing on Windows → tablet buttons follow
- [ ] Drawing / Everyday both show S Pen Area frame from Windows rect
- [ ] Finger touchpad still works over the whole pad (including outside pen frame)
- [ ] Fullscreen hides menu; **Menu** button restores it; chrome does not inject touches
- [ ] Settings sheet opens/closes without sending pad input

---

### 3C — Daily driver

**Prep:** Android Studio ▶ Run (version `0.3.0-3c`). Windows engine running.

- [ ] Cold start with USB **unplugged** → local WAITING page (not a Chrome error)
- [ ] Plug USB → page loads → CONNECTED without force-stopping the app
- [ ] Unplug / replug USB 5–10 times → recovers; no stuck Windows contacts
- [ ] Home button then return → no stuck fingers; hello/state refreshes
- [ ] Power button off/on → usable after unlock
- [ ] Windows STOP/START → tablet reconnects
- [ ] Leave foreground 30+ minutes → still works when you come back
- [ ] Screen stays on while app is foreground
- [ ] Optional: Build → Build APK(s); APK under `android/app/build/outputs/apk/debug/`

---

## Ports (unchanged)

| Port | Role | Android? |
|------|------|----------|
| 8765 | HTTP HTML | loads page |
| 8766 | WebSocket input | Yes |
| 8767 | GUI ↔ engine | **No** — do not expose |

---

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Stuck on Connecting… / Disconnected Reconnecting… | Windows engine running? Close **Chrome** on the Tab (old WS held the only slot). STOP/START engine, then reopen the app. |
| White/blank WebView | Cleartext / network security; confirm `http://127.0.0.1:8765/...` in Chrome still works |
| Local WAITING forever | Windows not running or ADB reverse missing for 8765 |
| Gestures missing | Confirm Chrome still OK — if Chrome OK and app not, report as WebView issue |
| Screen turns off | Confirm app is foreground; `FLAG_KEEP_SCREEN_ON` is set |
