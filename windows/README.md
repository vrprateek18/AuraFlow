# AuraFlow for Windows

### High-Performance Computer-Vision Hand Gesture Control for Windows 11 / 10
*Engineered for Intel Core i5 (13th Gen) + NVIDIA GeForce RTX 4050 (DirectML / CUDA)*

---

## 🌟 Overview

**AuraFlow for Windows** is a production-grade, 1:1 architectural port of the macOS Swift/Vision application to native Windows. It transforms your webcam into a zero-touch gesture controller for pointer movement, clicking, dragging, high-resolution scrolling, window management, and application switching.

### Key Highlights
* **Zero-Lag Input**: Emits native Windows `SendInput` events tagged with `kAuraMotionEventMagicTag = 0x41555241`.
* **Hardware Acceleration**: GPU-accelerated DirectML execution provider leverages your **NVIDIA GeForce RTX 4050 (6GB VRAM)**.
* **Pixel-Perfect UI Parity**: Glassmorphic floating HUD, live hand skeleton visualizer, click ripple animation, and floating 3x3 command menu.
* **Physical Input Arbitration**: Low-level mouse hook (`WH_MOUSE_LL`) detects when you touch a physical mouse and seamlessly yields gesture control without fighting you.

---

## 📐 Architecture & Pipeline

```text
Webcam (DirectShow / MSMF) ──► Zero-Lag Bounded Mailbox ──► MediaPipe Tasks (DirectML GPU / XNNPACK)
                             ──► Landmark Extraction (21 Joints) ──► Hand-Cursor Fusion (Palm Centroid)
                             ──► 1€ Adaptive Velocity Filter    ──► Gesture State Machine
                             ──► Win32 SendInput (Tagged)       ──► Windows 11 Desktop
```

---

## 🖐️ Gesture Control Guide

| Action | Hand Gesture | Windows Desktop Behavior |
| :--- | :--- | :--- |
| **Move Cursor** | Point index finger | Smooth, stabilized pointer movement with One Euro filtering. |
| **Left Click** | Pinch thumb & index finger tip | Emits clean click at anchor coordinate with micro-drag rejection. |
| **Drag & Drop** | Pinch and hold, then move hand | Holds left mouse down and moves cursor; release pinch to drop. |
| **Two-Finger Scroll** | Extend index & middle fingers together (V-sign) | Smooth high-resolution vertical and horizontal scrolling with inertia decay. |
| **Copy (`Ctrl + C`)** | Touch thumb tip to middle finger tip | Copies selected text/item to Windows Clipboard. |
| **Paste (`Ctrl + V`)** | Touch thumb tip to ring finger tip | Pastes text/item from Windows Clipboard. |
| **Next App** | Open palm swipe right | Triggers `Alt + Tab` app switching. |
| **Previous App** | Open palm swipe left | Triggers `Alt + Shift + Tab` app switching. |
| **Open Command Menu** | Hold open palm still for ~0.9s | Opens 3x3 floating command grid. |
| **Select Command** | Point to highlight tile, pinch to confirm | Executes one of 9 actions (Right Click, Double Click, Task View, Snap Left, Snap Right, etc.). |
| **Pause / Resume** | Toggle via System Tray icon | Suspends or resumes tracking instantly. |

---

## 🚀 Getting Started

### 1. Launch with Virtual Environment
Simply double-click:
```bat
Start AuraFlow.bat
```
*(Or backwards-compatible `Start AuraMotion.bat`)*

Or run directly from PowerShell:
```powershell
..\venv\Scripts\python.exe start_auraflow.py
```

### 2. Run Diagnostics
Verifies camera connectivity, screen geometry, and DirectML GPU status:
```powershell
..\venv\Scripts\python.exe auramotion_windows\diagnostics.py
```

### 3. Run Test Suite (39 Tests)
Runs the complete automated test suite:
```powershell
..\venv\Scripts\python.exe -m unittest discover tests
```

---

## 📦 Building a Single Standalone `.exe` (Production Release)

To package AuraMotion Pro into a single standalone Windows executable:

```powershell
.\venv\Scripts\python.exe -m pip install pyinstaller
.\venv\Scripts\pyinstaller.exe --noconsole --onefile --name "AuraMotionPro" --add-data "hand_landmarker.task;." start_auramotion.py
```
The compiled binary will be generated in `dist/AuraMotionPro.exe`.
