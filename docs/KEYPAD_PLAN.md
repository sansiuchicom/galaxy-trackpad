# Keypad / symbols panel

**Status:** shipped in **v0.11.0**; **2-page flip** on tablet (HTML)  
**Page:** `windows/static/touchpad_v04.html` (USB live-serve + Android `assets` via `sourceSets`)  
**PC inject:** `windows/core/keyboard.py`  
**Transport:** USB WebSocket + Bluetooth both accept `type: "key"`

Occasional digits and a few marks without leaving the pad. Not a full keyboard.

---

## How to use

1. Connect tablet (USB or Bluetooth) so the pad shows **CONNECTED**.
2. Tap **Keypad** in the side menu, or **Keypad** in fullscreen chrome.
3. Focus a Windows text field (Notepad, browser, Excel cell, …).
4. Tap keys on the translucent overlay.
5. Close with **✕**, tap empty overlay, toggle **Keypad** again, open Settings, or disconnect.

---

## Layout (locked)

One screen, **4 + 4 columns × 5 rows**, same key cell size both sides.  
Panel centered in the **pad/content column** (`position: fixed; left: var(--menu-w)`): with the side menu open that is the menu-mode middle; in fullscreen `--menu-w` is 0 so it centers on the full screen. Overlay background transparent; only keys have light fill.

```text
   symbols 4×5              Win-style numpad 4×5
  ,  …  ⋮  ·               ⌫   /   *   −
  ✓  ✔  ☐  ☑               7   8   9   +
  ←  →  ↑  ↓               4   5   6   +
  ⇒  ⇔  ※  ★               1   2   3   ↵
  ○  ●  ▲  ▼               0       .   ↵
```

| Side | Content |
|------|---------|
| **Left** | Non-Shift marks (arrows, ellipses, checks, shapes) + **`,`** only punctuation exception |
| **Right** | Windows numpad geometry: wide `0`, tall `+` / `Enter`; `⌫` instead of NumLock |

**Not on left:** `@ # $ %` and other Shift-easy ASCII — use a real keyboard.  
**Pages:** two full-panel pages (left + right flip together). Toggle `1/2` next to ✕; reopen resets to page 1.

---

## Wire protocol

Tablet → PC (USB JSON or BT framed JSON), one tap one message:

```json
{ "type": "key", "vk": "num7" }
{ "type": "key", "text": "✓" }
```

| Field | Meaning |
|-------|---------|
| `vk` | Named virtual key — see table below |
| `text` | One Unicode glyph (max 8 chars enforced on PC); `,` special-cased to a real comma key |

Handlers: `windows/transport/websocket.py`, `windows/transport/bluetooth.py` (`_handle_control`).

### `vk` names → Windows keys

| Name | Injected as | Notes |
|------|-------------|--------|
| `num0`…`num9` | Main row `0`–`9` (`VK 0x30`–`0x39`) | **Not** `VK_NUMPAD*` — works with NumLock **off** |
| `decimal` | `VK_OEM_PERIOD` | Same NumLock-safe reason |
| `divide` `multiply` `subtract` `add` | Numpad ops | Not NumLock-sensitive |
| `backspace` | `VK_BACK` | |
| `enter` | `VK_RETURN` | |
| `comma` | `VK_OEM_COMMA` | Used when `text` is `,` |

**NumLock decision:** no NumLock key on the panel. Digits always type digits. Real numpad scan codes are not required for v1 target apps (Notepad, Office, browsers).

Left symbols (except `,`) use `KEYEVENTF_UNICODE` via `SendInput`.

---

## Code map

| Piece | Role |
|-------|------|
| `touchpad_v04.html` | Overlay UI, **Keypad** buttons, `sendKey` → `sendRaw` |
| `windows/core/keyboard.py` | `apply_key_packet` / `tap_vk` / `tap_text` |
| `websocket.py` / `bluetooth.py` | Route `type:"key"` before contact packets |
| `tests/test_keyboard.py` | Struct size + name map (no live typing) |

Android APK picks up HTML from `windows/static` (`android/app/build.gradle.kts` assets `srcDir`). **Rebuild APK** after HTML changes for Bluetooth; USB serves the file live after engine restart / refresh.

---

## Behaviour notes

- Opening keypad **releases** active touch/pen contacts.
- Overlay sits above the pad (`z-index` 15); Settings sheet is higher (20) and closes the keypad when opened.
- Disconnect closes the keypad.
- Taps while disconnected are ignored (`isOpen()`).
- Inject goes to the **focused** Windows window — focus Notepad (etc.) first.
- Some elevated / DirectInput-only apps may ignore synthetic keys (OS limitation).

---

## Tests / smoke

```powershell
python -m unittest tests.test_keyboard -v
```

Manual (after engine start + CONNECTED):

- [ ] Menu **Keypad** opens overlay; pad grid visible underneath
- [ ] Fullscreen **Keypad** works
- [ ] Notepad: `123` `0` `.` `⌫` `↵` and `/ * − +`
- [ ] Notepad: `,` `…` `✓` `←` etc.
- [ ] NumLock **off** on PC — digits still type digits
- [ ] ✕ / backdrop / Settings / disconnect close overlay
- [ ] USB path; rebuild APK and spot-check Bluetooth if needed
- [ ] `1/2` toggles **both** sides; reopen starts on page 1
- [ ] Page 2: `₩` `①` `÷` `≠` type in Notepad

---

## Touch feedback

Discrete taps (keys / chrome) call `GalaxyPad.haptic()` in the Android WebView. Windows **Touch feedback** toggle sets `state.haptic`. Pad moves do not vibrate.

---

## Custom left symbols

Windows app → **Edit keypad symbols…** (TOUCHPAD section).  
Persists under `touchpad.keypad.pages[].symbols` (20 glyphs × 2 pages).  
Engine includes them in `state.keypad`; tablet HTML replaces left grids. Right numpad is not editable.

---

## Pages (current)

| Page | Left (4×5) | Right |
|------|------------|--------|
| **1** | `, … ⋮ ·` / checks / arrows / marks / shapes | Win numpad (`/` `*` `−` `+` `.` digits) |
| **2** | `₩€$¥` / fractions·π / `©®™§` / `•†‡°` / `℃µΩ∞` | Circled digits + `÷×±`; tall `≠` (like +); bottom `≈` (⌫ ↵ kept) |

Toggle control: `#keypadPageBtn` on the panel. Both grids rebuild via `renderKeypadPage()`.

---

## Future

| Item | Intent |
|------|--------|
| Symbol edit UI | Replace hard-coded left (and maybe page-2) glyphs |
| **Keypad size slider** | Persist scale; v1 is fixed larger for Tab S7 |
| Optional real-numpad mode | Only if an app truly needs `VK_NUMPAD*` |

---

## Decision log (v1)

1. One screen, 4+4 × 5; same key size  
2. `,` on left only  
3. Panel centered on **`#stage`** (menu-mode pad middle / fullscreen full); translucent keys  
4. Win numpad geometry; no NumLock key — digits via main-row VKs  
5. Left: non-Shift marks only (+ `,`)  
6. Circled digits deferred to page 2  
7. Key size: fixed large for Tab S7; user scale control later (BACKLOG)
8. Two pages; left+right flip together; page 2 = misc + circled/math ops
