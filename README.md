# AuraFlow

### *Move naturally. Control effortlessly.*
**Premium Unified Gesture-Control Application for Windows & macOS**

AuraFlow brings intuitive, touchless computer control to your desktop using computer vision and natural hand gestures. Move your pointer, click, drag, scroll, and trigger window controls without touching a mouse or trackpad.

---

## 🎨 Brand Identity

* **Midnight Navy Background:** `#07111F`
* **Deep Blue Surfaces:** `#123149`
* **Primary Flow Cyan:** `#20BFEA`
* **Ice-Blue Highlights:** `#8CEBFF`
* **Emergency Stop Alert:** `#FF3B5C`

---

## 🏛️ Unified Architecture & 4-Screen Onboarding Flow

AuraFlow provides a unified onboarding and platform experience with native engines tailored specifically for each operating system:

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              AuraFlow Unified Flow                                      │
│                                                                                        │
│  Screen 1: Welcome        ──► AuraFlow Emblem, Tagline, Get Started, Skip Setup        │
│  Platform Selector        ──► Windows & macOS Cards with Auto-Detection & Laptop UX     │
│  Screen 2: Tutorial       ──► Visual Gesture Carousel & Interactive Practice Pad        │
│  Screen 3: Setup & Diag   ──► Hardware, Camera & OS Permission Checks + Action Recovery │
│  Screen 4: Control Center ──► Live Tracking, Telemetry, Cheatsheet, Calibration, F8     │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                 ┌──────────────────────────┴──────────────────────────┐
                 ▼                                                     ▼
┌──────────────────────────────────────────┐  ┌──────────────────────────────────────────┐
│         AuraFlow Windows Engine          │  │          AuraFlow macOS Engine           │
│      Python 3.12 · PySide6 · OpenCV      │  │        Swift 6 · SwiftUI · Vision        │
│       MediaPipe XNNPACK / DirectML       │  │       Apple Silicon Neural Engine        │
│         Win32 SendInput (Tagged)         │  │         C11 Lock-Free Event-Tap          │
│       Emergency Stop (F8 Hotkey)         │  │          Native Menu Bar Extra           │
└──────────────────────────────────────────┘  └──────────────────────────────────────────┘
```

Both engines are preserved independently in their native runtimes without forcing unnatural cross-runtime compromises or degrading performance.

---

## 📁 Repository Organization

* `windows/` — Complete native Windows application (Python 3.12, PySide6, OpenCV, MediaPipe, Win32 SendInput).
* `macos/` — Complete native macOS application (Swift 6, SwiftUI, Vision framework, C11 Event-Tap).
* `shared/branding/` — Unified color palette tokens and vector logo generators.
* `shared/docs/` — Universal gesture guide, safety policies, and architecture documentation.

---

## 🚀 Getting Started

### Windows 11 / 10

1. **Launch with Quick Batch Launcher:**
   Double-click from repository root:
   ```cmd
   Start AuraFlow.bat
   ```
   *(Or launch from inside `windows/Start AuraFlow.bat`)*

2. **Or run with Python directly:**
   ```powershell
   .\venv\Scripts\python.exe start_auraflow.py
   ```

3. **Run Windows Test Suite (39 Tests):**
   ```powershell
   .\venv\Scripts\python.exe run_tests.py
   ```
   *(Or `cd windows && ..\venv\Scripts\python.exe -m unittest discover tests`)*

---

### macOS (14+ Sonoma & Sequoia)

1. **Launch with Double-Click Launcher:**
   In the `macos/` directory, double-click:
   ```bash
   Start AuraFlow.command
   ```
   *(Backwards-compatible `Start AuraMotion.command` is also preserved)*

2. **Or build and run with Swift Package Manager:**
   ```bash
   cd macos
   swift run AuraFlow
   ```

3. **Run macOS Tests:**
   ```bash
   cd macos
   swift test
   ```

---

## 🖐️ Gesture Control Cheatsheet

| Action | Hand Gesture | Behavior |
| :--- | :--- | :--- |
| **Move Pointer** | Point index finger in air | Smooth, jitter-free cursor tracking with One Euro adaptive velocity filter. |
| **Left Click** | Touch thumb and index finger tip | Clean click emission locked at anchor position with micro-drag rejection. |
| **Right Click** | Touch thumb and middle finger tip | Context menu click. |
| **Two-Finger Scroll** | Extend index and middle fingers together | High-resolution vertical and horizontal scrolling with inertia. |
| **Drag & Drop** | Pinch thumb & index, hold and move | Holds mouse button down and moves; release fingers to drop. |
| **3x3 Radial Menu** | Hold open palm resting for ~0.6s | Opens quick command grid for window snapping, task view, and media controls. |
| **🛑 Emergency Stop** | Press `F8` or click red button | Instantly suspends gesture tracking and releases all held mouse inputs. |
| **⏸️ Pause / Resume** | Press `F8` or `Ctrl + Alt + P` | Toggles gesture input injection on or off from any application. |

---

## 🛡️ Safety & Reliability

* **Auto-Release Watchdog:** Automatically releases held mouse buttons if tracking disappears for $> 180$ ms or if the camera disconnects.
* **Physical Mouse Yield:** Seamlessly yields control to the physical mouse whenever you touch your hardware mouse, eliminating pointer tug-of-war.
* **Accidental Click Rejection:** Velocity gating prevents clicks during rapid hand repositioning or sweeping.
* **Camera Recovery:** Guided troubleshooting dialog with 1-click links to Windows Camera Privacy and camera hardware testing.
* **Empirical Benchmarking:** In-app benchmark studio testing CPU XNNPACK multi-threading against DirectML GPU acceleration.
