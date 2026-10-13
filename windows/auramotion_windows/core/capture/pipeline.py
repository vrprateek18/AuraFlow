"""
Camera Capture Pipeline with Auto-Reconnection & Hardware Error Reporting
Engineered for Windows 11 with DirectShow, MediaFoundation, and Lenovo E-Shutter auto-detection.
"""
import cv2
import threading
import time
from typing import Optional, Tuple, List
import numpy as np

class FrameMailbox:
    """Thread-safe bounded mailbox keeping strictly the newest frame for inference."""
    def __init__(self):
        self._lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None
        self._latest_timestamp: float = 0.0
        self._frame_count: int = 0
        self._dropped_count: int = 0
        self._has_new: bool = False

    def put(self, frame: np.ndarray, timestamp: float):
        with self._lock:
            if self._has_new:
                self._dropped_count += 1
            self._latest_frame = frame
            self._latest_timestamp = timestamp
            self._frame_count += 1
            self._has_new = True

    def get(self) -> Tuple[Optional[np.ndarray], float, bool]:
        with self._lock:
            if not self._has_new or self._latest_frame is None:
                return None, self._latest_timestamp, False
            self._has_new = False
            return self._latest_frame, self._latest_timestamp, True

    def peek(self) -> Optional[np.ndarray]:
        """Returns the latest frame without consuming it (useful for GUI preview)."""
        with self._lock:
            return self._latest_frame.copy() if self._latest_frame is not None else None

    @property
    def stats(self) -> Tuple[int, int]:
        with self._lock:
            return self._frame_count, self._dropped_count


class CameraCapturePipeline:
    def __init__(self, camera_index: int = 0, target_fps: int = 60, width: int = 1280, height: int = 720):
        self.camera_index = camera_index
        self.target_fps = target_fps
        self.width = width
        self.height = height

        self.mailbox = FrameMailbox()
        self._cap: Optional[cv2.VideoCapture] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

        self.actual_fps: float = 0.0
        self._fps_counter = 0
        self._fps_timer = time.time()

        self.is_connected = False
        self.last_error = ""

        self._switch_index: Optional[int] = None
        self._reconnect_requested = False
        self._pending_resolution: Optional[Tuple[int, int]] = None

    def set_resolution(self, width: int, height: int):
        """Thread-safely requests capture resolution change."""
        self._pending_resolution = (width, height)

    def start(self) -> bool:
        if self._running:
            return True

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        self._close_camera()

    def switch_device(self, new_camera_index: int):
        """Thread-safely switches camera stream to a different device index."""
        self._switch_index = new_camera_index

    def reconnect(self):
        """Thread-safely requests an immediate camera reconnection cycle."""
        self._reconnect_requested = True

    def _open_camera(self) -> bool:
        self._close_camera()

        # Try standard OpenCV capture
        try:
            # Try DirectShow first, then Default
            cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(self.camera_index)

            if cap.isOpened():
                # Configure camera format optimized for Windows hardware ISP
                try:
                    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                except Exception:
                    pass
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                cap.set(cv2.CAP_PROP_FPS, self.target_fps)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                # Verify we can read a valid frame
                ret, frame = cap.read()
                if ret and frame is not None:
                    self._cap = cap
                    self.is_connected = True
                    self.last_error = ""
                    self._fps_timer = time.time()
                    self._fps_counter = 0
                    return True
                else:
                    cap.release()
                    self.last_error = (
                        "Camera hardware connected but returned blank frames.\n"
                        "Check: 1) Physical E-Shutter switch on laptop right edge. 2) Lenovo Vantage Camera Privacy Mode."
                    )
            else:
                self.last_error = (
                    f"Camera {self.camera_index} access denied or device disconnected.\n"
                    "Check: 1) Windows 11 Camera Privacy (Allow desktop apps). 2) Close other camera apps (Zoom, Teams). 3) Lenovo E-Shutter switch."
                )
        except Exception as e:
            self.last_error = str(e)

        self.is_connected = False
        return False

    def _close_camera(self):
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None
        self.is_connected = False

    def _capture_loop(self):
        last_reconnect_attempt = 0.0

        while self._running:
            # Thread-safe handling of device switch or reconnection requests
            if self._switch_index is not None:
                new_idx = self._switch_index
                self._switch_index = None
                self.camera_index = new_idx
                self._open_camera()
                last_reconnect_attempt = time.time()
                continue

            if self._reconnect_requested:
                self._reconnect_requested = False
                self._open_camera()
                last_reconnect_attempt = time.time()
                continue

            if self._pending_resolution is not None:
                rw, rh = self._pending_resolution
                self._pending_resolution = None
                self.width = rw
                self.height = rh
                if self._cap and self._cap.isOpened():
                    self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

            # If camera is not opened, attempt reconnection periodically
            if self._cap is None or not self._cap.isOpened():
                now = time.time()
                if now - last_reconnect_attempt >= 1.5:
                    last_reconnect_attempt = now
                    self._open_camera()
                time.sleep(0.05)
                continue

            try:
                ret, frame = self._cap.read()
                if not ret or frame is None:
                    # Device might have been switched off or disconnected
                    self.is_connected = False
                    self.last_error = "Stream interrupted (Camera may be covered or shutter switched off)."
                    self._close_camera()
                    time.sleep(0.1)
                    continue

                ts = time.time()
                self.is_connected = True
                self.last_error = ""
                self.mailbox.put(frame, ts)

                self._fps_counter += 1
                now = time.time()
                elapsed = now - self._fps_timer
                if elapsed >= 1.0:
                    self.actual_fps = self._fps_counter / elapsed
                    self._fps_counter = 0
                    self._fps_timer = now

            except Exception as e:
                self.last_error = str(e)
                self._close_camera()
                time.sleep(0.1)

    def get_latest_frame(self) -> Tuple[Optional[np.ndarray], float, bool]:
        return self.mailbox.get()

    def get_preview_frame(self) -> Optional[np.ndarray]:
        return self.mailbox.peek()


def enumerate_available_cameras(max_devices: int = 3) -> List[Tuple[int, str]]:
    """Probes Windows DirectShow camera indices and returns list of (index, displayName)."""
    devices: List[Tuple[int, str]] = []
    for idx in range(max_devices):
        try:
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                if idx == 0:
                    label = "Camera 0 (Integrated Webcam)"
                else:
                    label = f"Camera {idx} (External / USB Webcam)"
                devices.append((idx, label))
            else:
                cap.release()
        except Exception:
            pass

    if not devices:
        devices.append((0, "Camera 0 (Default)"))
    return devices


SUPPORTED_RESOLUTIONS = [
    (640, 480, "640x480 (VGA 60 FPS - Lowest Latency)"),
    (1280, 720, "1280x720 (720p HD 60 FPS - Balanced)"),
    (1920, 1080, "1920x1080 (1080p FHD 30 FPS - High Detail)"),
]
