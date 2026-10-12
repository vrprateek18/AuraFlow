# AuraFlow Technical Architecture

AuraFlow delivers a unified user experience through platform-native high-performance engines.

---

## 🏛️ Platform Engine Comparison

```text
┌─────────────────────────────────┬─────────────────────────────────┐
│         Windows Engine          │          macOS Engine           │
├─────────────────────────────────┼─────────────────────────────────┤
│ Language: Python 3.12           │ Language: Swift 6               │
│ UI Framework: PySide6 (Qt)      │ UI Framework: SwiftUI + AppKit  │
│ Vision: MediaPipe + OpenCV      │ Vision: Apple Vision Framework  │
│ Hardware: DirectML / CPU XNNPACK│ Hardware: Apple Neural Engine   │
│ Video Pipeline: DirectShow DSHOW│ Video Pipeline: AVFoundation    │
│ Input: Win32 SendInput (Tagged) │ Input: CGEvent Synthesis        │
│ Arbitration: WH_MOUSE_LL Hook   │ Arbitration: C11 Lock-Free Tap  │
│ Hotkey: Global F8 Hook          │ Hotkey: Carbon / Status Bar     │
│ Packaging: PyInstaller / Wheel  │ Packaging: Swift Package / App  │
└─────────────────────────────────┴─────────────────────────────────┘
```

---

## 🔄 Interaction State Machine

Both engines enforce a deterministic, finite state machine:

```text
           [ NO HAND ]
                │ (Hand detected)
                ▼
            [ IDLE ]
                │ (Index finger raised)
                ▼
          [ POINTING ] ──────────┐ (Two fingers extended)
                │                ▼
                │          [ SCROLLING ]
                │
                ├──────────────── (Thumb-index pinch < 250ms)
                ▼
        [ PINCH_ARMED ] ──► [ CLICKED ]
                │
                │ (Hold pinch > 250ms & move)
                ▼
          [ DRAGGING ]
```

---

## ⚡ Zero PCIe Transfer Bottleneck

* **Windows:** The capture mailbox runs decoupled on a dedicated worker thread using triple-buffering (`Mailbox.latest`), preventing UI thread stalls.
* **macOS:** Zero-copy `CVPixelBuffer` frames stream directly from `AVCaptureSession` to Apple Vision without crossing process boundaries.
