# AuraFlow Safety & Reliability Architecture

AuraFlow guarantees user safety and eliminates accidental computer interactions.

---

## 🛡️ Core Safety Guarantees

### 1. 180ms Auto-Release Watchdog
If the left mouse button is pressed down (during a click or drag operation) and the hand tracking sample is lost or confidence drops below threshold for $> 180\text{ ms}$, the input coordinator automatically emits a hardware mouse release event (`MOUSEEVENTF_LEFTUP` on Windows / `.leftMouseUp` on macOS). This prevents runaway drag-and-drop or stuck mouse clicks.

### 2. Physical Mouse Yield (Zero Tug-of-War)
Whenever the user physically touches or moves their real hardware mouse:
* **Windows:** A low-level mouse hook (`WH_MOUSE_LL`) detects hardware movement (ignoring self-injected `EXTRA_INFO` events). AuraFlow immediately backs off and pauses injection for an arbitration cooldown interval (default 1.5 seconds).
* **macOS:** A C11 lock-free atomic event tap monitors hardware mouse moves and yields injection instantaneously.

### 3. Emergency Stop Hotkey (`F8`)
* System-wide global hotkey `F8` (and `Ctrl + Alt + P`) provides an immediate hardware kill-switch.
* Instantly terminates all gesture simulation, releases held buttons, and updates the floating HUD / menu bar to PAUSED.

### 4. Camera Disconnect & Recovery
* If the webcam is unplugged, switched off, or blocked by a hardware privacy shutter (e.g. Lenovo E-Shutter), AuraFlow transitions cleanly to `TRACKING_LOST` without crashing.
* Actionable recovery guidance provides direct shortcuts to Windows Camera Privacy Settings (`ms-settings:privacy-webcam`) or macOS System Settings.
