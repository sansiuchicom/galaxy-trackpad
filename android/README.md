# Galaxy Trackpad — Android (Phase 3)

WebView shell around the existing touchpad HTML.
Windows still owns the input engine, ADB reverse, and settings.

## Status

| Slice | Goal | Status |
|-------|------|--------|
| **3A** | App icon → WebView → same WS input as Chrome | Done |
| **3B** | Side menu, connection UI, pen profile sync, Drawing area | Done |
| **3C** | Long-run stability, reconnect polish, waiting page | Done |

### 3A design choice

Load **`http://127.0.0.1:8765/touchpad_v04.html`** from the Windows HTTP server
(via ADB reverse), **not** APK assets yet.

Why: prove Pointer Events + `ws://127.0.0.1:8766` parity with Chrome first.
Local assets + WebViewAssetLoader come after that works on the Tab S7.

---

## Prerequisites

1. **Windows app running** (`python -m windows`) with engine started / USB reverse OK  
2. **Android Studio** (Ladybug / Koala or newer) with SDK 35 + a device/USB driver  
3. Tab S7: **USB debugging** authorized for this PC  
4. This PC currently has **platform-tools** under the repo root for ADB

This machine may not have the Android SDK in PATH; open the `android/` folder in
Android Studio and let it install the SDK / Gradle wrapper on first sync.

---

## Open / build / install

```text
Android Studio → Open → C:\touchpad\android
```

1. Wait for Gradle sync.  
2. Connect Tab S7 over USB.  
3. Run ▸ `app` (debug).  
4. Or: **Build → Build Bundle(s) / APK(s) → Build APK(s)** then install the debug APK.

CLI (after Studio has created the wrapper jar once):

```powershell
cd C:\touchpad\android
.\gradlew.bat :app:installDebug
```

---

## Expected flow (3A)

1. Launch Windows Galaxy Trackpad → engine / reverse ready.  
2. Launch **Galaxy Trackpad** app on the Tab (not Chrome).  
3. Page shows Connecting… then **USB Connected**.  
4. Finger + S Pen behave like the Chrome prototype.

No IP typing. No PowerShell on the tablet. Windows still does ADB reverse.

---

## What 3A intentionally does NOT include

- Side menu / fullscreen chrome  
- Pen profile buttons or Drawing area overlay  
- Bidirectional settings protocol  
- APK-bundled HTML  
- Bluetooth / Wi-Fi  

---

## Phase test checklists (what you should do)

### 3A — Input parity (do this after first install)

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
