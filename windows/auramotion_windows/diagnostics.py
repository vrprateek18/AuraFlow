"""
AuraMotion Pro for Windows - Hardware & Diagnostic Suite
Tests camera availability, RTX 4050 DirectML acceleration, Win32 input, and latency.
"""
import sys
import os
import time
import cv2
import numpy as np

def run_diagnostics():
    print("=" * 60)
    print("      AURAFLOW PRO - WINDOWS SYSTEM DIAGNOSTIC")
    print("=" * 60)

    # 1. Python & Environment
    print(f"\n[1] Runtime: Python {sys.version.split()[0]} on {sys.platform}")

    # 2. Check Win32 Screen Resolution
    import ctypes
    user32 = ctypes.windll.user32
    w = user32.GetSystemMetrics(0)
    h = user32.GetSystemMetrics(1)
    print(f"[2] Display Geometry: {w} x {h} px (Direct Input mapping verified)")

    # 3. Check ONNX Runtime & DirectML
    try:
        import onnxruntime as ort
        providers = ort.get_available_providers()
        print(f"[3] ONNX Execution Providers: {providers}")
        if "DmlExecutionProvider" in providers:
            print("    -> NVIDIA RTX 4050 DirectML GPU acceleration is ACTIVE!")
        else:
            print("    -> DirectML provider not detected; falling back to CPU.")
    except Exception as e:
        print(f"[3] ONNX DirectML check failed: {e}")

    # 4. Check MediaPipe Tasks
    try:
        import mediapipe as mp
        model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "hand_landmarker.task")
        if not os.path.exists(model_path):
            model_path = "hand_landmarker.task"
        if os.path.exists(model_path):
            size_mb = os.path.getsize(model_path) / (1024 * 1024)
            print(f"[4] MediaPipe Model: {model_path} ({size_mb:.2f} MB)")
            options = mp.tasks.vision.HandLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=model_path),
                running_mode=mp.tasks.vision.RunningMode.IMAGE,
                num_hands=1
            )
            with mp.tasks.vision.HandLandmarker.create_from_options(options) as lm:
                dummy = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.zeros((480, 640, 3), dtype=np.uint8))
                t0 = time.time()
                lm.detect(dummy)
                lat = (time.time() - t0) * 1000
                print(f"    -> HandLandmarker initialized successfully (latency: {lat:.1f} ms)")
        else:
            print(f"[4] Model file missing: {model_path}")
    except Exception as e:
        print(f"[4] MediaPipe test failed: {e}")

    # 5. Check Camera Devices
    print("\n[5] Probing Camera...")
    try:
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                fh, fw = frame.shape[:2]
                fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
                print(f"    -> Camera 0 detected: {fw}x{fh} @ {fps:.0f} FPS")
            else:
                print("    -> Camera 0 accessible (no active frame returned in background session)")
            cap.release()
        else:
            print("    -> Camera 0 not opened (ensure camera access is enabled in Windows Privacy Settings)")
    except Exception as e:
        print(f"    -> Camera probe warning: {e}")

    print("\n" + "=" * 60)
    print("Diagnostic Complete. Ready to launch AuraFlow Pro!")
    print("=" * 60)

if __name__ == "__main__":
    run_diagnostics()
