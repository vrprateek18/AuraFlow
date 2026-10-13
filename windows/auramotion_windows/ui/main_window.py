"""
AuraMotion Pro for Windows - Main Desktop Application Window
Full interactive GUI with live camera feed, hand skeleton visualizer, and hardware controls.
"""
import cv2
import numpy as np
import math
from typing import Optional

from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, Signal
from PySide6.QtGui import (
    QImage, QPixmap, QPainter, QColor, QPen, QBrush, QFont, QPainterPath
)
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QSlider, QComboBox, QGroupBox, QFrame, QSplitter, QScrollArea
)

from ..core.domain.models import (
    HandSample, GestureState, HandJointName, AppSettings, CalibrationProfile
)
from .auraflow_theme import (
    get_auraflow_stylesheet, COLOR_PRIMARY_CYAN, COLOR_ICE_BLUE,
    COLOR_ACCENT_CORAL, COLOR_BG_CARD, COLOR_SUCCESS, COLOR_TEXT_MUTED
)

class CameraPreviewWidget(QWidget):
    """Draws live webcam feed with hand skeleton and gesture landmarks overlaid."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(480, 360)
        self.frame: Optional[np.ndarray] = None
        self.sample: Optional[HandSample] = None
        self.is_camera_connected = False
        self.error_message = ""

    def update_frame(self, frame: Optional[np.ndarray], sample: Optional[HandSample], is_connected: bool = True, error: str = "", error_msg: str = ""):
        self.frame = frame
        self.sample = sample
        self.is_camera_connected = is_connected
        self.error_message = error or error_msg
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()

        # Dark background
        painter.fillRect(0, 0, w, h, QColor(14, 16, 22))

        if self.is_camera_connected and self.frame is not None:
            # Draw live camera frame
            fh, fw = self.frame.shape[:2]
            scale = min(w / fw, h / fh)
            disp_w = int(fw * scale)
            disp_h = int(fh * scale)
            off_x = (w - disp_w) // 2
            off_y = (h - disp_h) // 2

            rgb = np.ascontiguousarray(cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB))
            bytes_per_line = 3 * fw
            qimg = QImage(rgb.data, fw, fh, bytes_per_line, QImage.Format.Format_RGB888).copy()
            painter.drawImage(QRectF(off_x, off_y, disp_w, disp_h), qimg)

            # Draw hand skeleton overlay
            if self.sample is not None and self.sample.joints:
                self._draw_landmarks(painter, off_x, off_y, disp_w, disp_h)
        else:
            # Draw helpful camera status placeholder
            self._draw_placeholder(painter, w, h)

    def _draw_placeholder(self, painter: QPainter, w: int, h: int):
        if not self.error_message:
            painter.setPen(QColor(0, 255, 200))
            painter.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
            painter.drawText(QRectF(0, h // 2 - 30, w, 30), Qt.AlignmentFlag.AlignCenter, "🔄 Initializing Camera Stream...")
            painter.setPen(QColor(180, 180, 180))
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(QRectF(0, h // 2 + 10, w, 24), Qt.AlignmentFlag.AlignCenter, "DirectShow capture starting up...")
            return

        painter.setPen(QColor(255, 100, 100))
        painter.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        painter.drawText(QRectF(0, h // 2 - 90, w, 30), Qt.AlignmentFlag.AlignCenter, "📷 Camera Locked / Disconnected")

        painter.setPen(QColor(220, 220, 220))
        painter.setFont(QFont("Segoe UI", 10))
        lines = [
            "Lenovo LOQ Physical Privacy Switch Checklist:",
            "1. Locate the physical E-Shutter switch on the RIGHT side edge of your laptop.",
            "2. Slide the switch to OPEN (camera enabled).",
            "3. Ensure 'Camera Privacy Mode' is OFF in Lenovo Vantage.",
            "AuraFlow will automatically detect the camera the instant it is switched on!"
        ]
        y = h // 2 - 40
        for line in lines:
            painter.drawText(QRectF(20, y, w - 40, 22), Qt.AlignmentFlag.AlignCenter, line)
            y += 24

    def _draw_landmarks(self, painter: QPainter, off_x: int, off_y: int, disp_w: int, disp_h: int):
        bones = [
            (HandJointName.WRIST, HandJointName.THUMB_CMC),
            (HandJointName.THUMB_CMC, HandJointName.THUMB_MCP),
            (HandJointName.THUMB_MCP, HandJointName.THUMB_IP),
            (HandJointName.THUMB_IP, HandJointName.THUMB_TIP),
            (HandJointName.WRIST, HandJointName.INDEX_MCP),
            (HandJointName.INDEX_MCP, HandJointName.INDEX_PIP),
            (HandJointName.INDEX_PIP, HandJointName.INDEX_DIP),
            (HandJointName.INDEX_DIP, HandJointName.INDEX_TIP),
            (HandJointName.WRIST, HandJointName.MIDDLE_MCP),
            (HandJointName.MIDDLE_MCP, HandJointName.MIDDLE_PIP),
            (HandJointName.MIDDLE_PIP, HandJointName.MIDDLE_DIP),
            (HandJointName.MIDDLE_DIP, HandJointName.MIDDLE_TIP),
            (HandJointName.WRIST, HandJointName.RING_MCP),
            (HandJointName.RING_MCP, HandJointName.RING_PIP),
            (HandJointName.RING_PIP, HandJointName.RING_DIP),
            (HandJointName.RING_DIP, HandJointName.RING_TIP),
            (HandJointName.WRIST, HandJointName.LITTLE_MCP),
            (HandJointName.LITTLE_MCP, HandJointName.LITTLE_PIP),
            (HandJointName.LITTLE_PIP, HandJointName.LITTLE_DIP),
            (HandJointName.LITTLE_DIP, HandJointName.LITTLE_TIP),
            (HandJointName.INDEX_MCP, HandJointName.MIDDLE_MCP),
            (HandJointName.MIDDLE_MCP, HandJointName.RING_MCP),
            (HandJointName.RING_MCP, HandJointName.LITTLE_MCP),
        ]

        # Draw bone connections
        pen_bone = QPen(QColor(0, 255, 200, 200), 2.5)
        painter.setPen(pen_bone)

        for j1, j2 in bones:
            p1 = self.sample.joint(j1, min_confidence=0.1)
            p2 = self.sample.joint(j2, min_confidence=0.1)
            if p1 and p2:
                x1 = off_x + p1.x * disp_w
                y1 = off_y + p1.y * disp_h
                x2 = off_x + p2.x * disp_w
                y2 = off_y + p2.y * disp_h
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # Draw landmark nodes
        painter.setPen(Qt.PenStyle.NoPen)
        for name, joint in self.sample.joints.items():
            jx = off_x + joint.position.x * disp_w
            jy = off_y + joint.position.y * disp_h
            if name == HandJointName.INDEX_TIP:
                painter.setBrush(QBrush(QColor(0, 255, 255, 255)))
                painter.drawEllipse(QPointF(jx, jy), 6, 6)
            elif name == HandJointName.THUMB_TIP:
                painter.setBrush(QBrush(QColor(0, 255, 200, 255)))
                painter.drawEllipse(QPointF(jx, jy), 6, 6)
            else:
                painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
                painter.drawEllipse(QPointF(jx, jy), 3.5, 3.5)

        # Highlight pinch proximity between thumb tip and index tip
        tt = self.sample.joint(HandJointName.THUMB_TIP, min_confidence=0.1)
        it = self.sample.joint(HandJointName.INDEX_TIP, min_confidence=0.1)
        if tt and it:
            tx, ty = off_x + tt.x * disp_w, off_y + tt.y * disp_h
            ix, iy = off_x + it.x * disp_w, off_y + it.y * disp_h
            dist_px = math.hypot(tx - ix, ty - iy)
            scale_px = self.sample.scale_reference * disp_w
            norm_dist = dist_px / max(scale_px, 1.0)

            if norm_dist < 0.40:
                is_pinched = norm_dist < 0.28
                color = QColor(0, 255, 200, 240) if is_pinched else QColor(255, 200, 0, 180)
                pen_pinch = QPen(color, 3 if is_pinched else 1.5, Qt.PenStyle.SolidLine if is_pinched else Qt.PenStyle.DashLine)
                painter.setPen(pen_pinch)
                painter.drawLine(QPointF(tx, ty), QPointF(ix, iy))


class AuraMotionMainWindow(QMainWindow):
    reconnect_camera_signal = Signal(int)
    switch_camera_signal = Signal(int)
    switch_resolution_signal = Signal(int, int)
    emergency_stop_signal = Signal()
    test_click_signal = Signal()
    test_command_menu_signal = Signal()
    open_settings_signal = Signal()
    open_calibration_signal = Signal()
    open_tutorial_signal = Signal()
    open_onboarding_signal = Signal()
    open_benchmark_signal = Signal()

    def __init__(self, settings: AppSettings, profile: CalibrationProfile, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.profile = profile
        self.is_paused = False

        self.setWindowTitle("AuraFlow Pro — Desktop Control Center")
        self.resize(1020, 680)
        self.setMinimumSize(880, 560)
        self.setStyleSheet(get_auraflow_stylesheet())

        self._init_ui()

    def _init_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(16)

        # ── Left: Camera & Vision Canvas ──
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)

        header_lbl = QLabel("LIVE CAMERA & HAND TRACKING")
        header_lbl.setStyleSheet("font-weight: 700; color: #00FFC8; font-size: 12px; letter-spacing: 1px;")
        left_layout.addWidget(header_lbl)

        self.preview_widget = CameraPreviewWidget(self)
        left_layout.addWidget(self.preview_widget, stretch=1)

        # Camera selector toolbar
        cam_bar = QHBoxLayout()
        cam_bar.addWidget(QLabel("Camera Device:"))

        self.cam_combo = QComboBox()
        self.cam_combo.addItems(["Camera 0 (Integrated Webcam)", "Camera 1 (External)", "Camera 2"])
        self.cam_combo.currentIndexChanged.connect(self._on_cam_combo_changed)
        cam_bar.addWidget(self.cam_combo)

        self.btn_reconnect = QPushButton("Reconnect Camera")
        self.btn_reconnect.setObjectName("secondaryBtn")
        self.btn_reconnect.clicked.connect(self._on_reconnect_clicked)
        cam_bar.addWidget(self.btn_reconnect)

        self.btn_open_win_settings = QPushButton("⚙️ Windows Camera Privacy")
        self.btn_open_win_settings.setObjectName("secondaryBtn")
        self.btn_open_win_settings.clicked.connect(self._open_windows_camera_settings)
        cam_bar.addWidget(self.btn_open_win_settings)

        self.btn_open_cam_app = QPushButton("📸 Test in Camera App")
        self.btn_open_cam_app.setObjectName("secondaryBtn")
        self.btn_open_cam_app.clicked.connect(self._open_windows_camera_app)
        cam_bar.addWidget(QLabel("Resolution:"))
        self.res_combo = QComboBox()
        self.res_combo.addItem("640x480 (VGA 60 FPS - Low Latency)", (640, 480))
        self.res_combo.addItem("1280x720 (720p HD)", (1280, 720))
        self.res_combo.addItem("1920x1080 (1080p FHD)", (1920, 1080))
        # Select current resolution
        for i in range(self.res_combo.count()):
            val = self.res_combo.itemData(i)
            if val == (self.settings.camera_width, self.settings.camera_height):
                self.res_combo.setCurrentIndex(i)
                break
        self.res_combo.currentIndexChanged.connect(self._on_res_combo_changed)
        cam_bar.addWidget(self.res_combo)

        cam_bar.addStretch()
        left_layout.addLayout(cam_bar)

        root_layout.addLayout(left_layout, stretch=3)

        # ── Right: Status & Controls (Scrollable for any laptop screen specification) ──
        self.right_scroll = QScrollArea()
        self.right_scroll.setWidgetResizable(True)
        self.right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.right_scroll.setStyleSheet("background: transparent;")

        right_widget = QWidget()
        right_widget.setStyleSheet("background: transparent;")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 8, 0)
        right_layout.setSpacing(12)

        # 0. Prominent Emergency Stop / Pause Button
        self.btn_emergency_stop = QPushButton("🛑 EMERGENCY STOP (F8)")
        self.btn_emergency_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_emergency_stop.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLOR_ACCENT_CORAL}, stop:1 #D90429);
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 800;
                padding: 12px 16px;
                border-radius: 8px;
                letter-spacing: 1px;
                border: 2px solid #FF5C7A;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF5C7A, stop:1 #EF233C);
                border: 2px solid #FFFFFF;
            }}
        """)
        self.btn_emergency_stop.clicked.connect(self._on_emergency_stop_clicked)
        right_layout.addWidget(self.btn_emergency_stop)

        # 1. State Card
        state_group = QGroupBox("Gesture Status")
        state_layout = QVBoxLayout(state_group)

        self.state_badge = QLabel("READY")
        self.state_badge.setStyleSheet(f"""
            background: rgba(32, 191, 234, 0.18);
            color: {COLOR_PRIMARY_CYAN};
            font-size: 16px;
            font-weight: bold;
            padding: 8px;
            border-radius: 6px;
            text-align: center;
        """)
        self.state_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        state_layout.addWidget(self.state_badge)

        self.action_lbl = QLabel("Point index finger to control pointer")
        self.action_lbl.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 11px;")
        self.action_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        state_layout.addWidget(self.action_lbl)

        right_layout.addWidget(state_group)

        # 1.5 Gesture Bindings Cheatsheet (Screen 7 in artwork)
        gesture_card = QGroupBox("Active Gesture Bindings")
        g_lay = QVBoxLayout(gesture_card)
        g_lay.setSpacing(6)
        bindings = [
            ("👆 Move Pointer", "Index finger in air"),
            ("🤏 Left Click", "Thumb & index pinch"),
            ("✌️ Right Click", "Thumb & middle pinch"),
            ("📜 Scroll", "Two fingers pan up/down"),
            ("✊ Drag & Drop", "Pinch & hold + move"),
            ("🖐️ 3x3 Radial Menu", "Open palm rest 0.6s")
        ]
        for name, gesture in bindings:
            row = QHBoxLayout()
            l_n = QLabel(name)
            l_n.setStyleSheet("font-weight: 600; color: #FFFFFF; font-size: 11px;")
            l_g = QLabel(gesture)
            l_g.setStyleSheet(f"color: {COLOR_PRIMARY_CYAN}; font-size: 10px; font-weight: bold;")
            row.addWidget(l_n)
            row.addStretch()
            row.addWidget(l_g)
            g_lay.addLayout(row)
        right_layout.addWidget(gesture_card)

        # 2. Hardware Acceleration Card
        hw_group = QGroupBox("Engine & Hardware Performance")
        hw_layout = QVBoxLayout(hw_group)
        self.gpu_lbl = QLabel("⚡ Hardware: DirectML / MediaPipe XNNPACK")
        hw_layout.addWidget(self.gpu_lbl)

        self.e2e_latency_lbl = QLabel("E2E Latency: 0.0 ms (P95: 0.0 ms)")
        self.e2e_latency_lbl.setStyleSheet("font-family: 'Consolas', monospace; color: #00FFC8; font-weight: bold;")
        hw_layout.addWidget(self.e2e_latency_lbl)

        self.fps_lbl = QLabel("CAP: 0 FPS | INF: 0 FPS | Dropped: 0")
        self.fps_lbl.setStyleSheet("font-family: 'Consolas', monospace; color: #00FFC8;")
        hw_layout.addWidget(self.fps_lbl)

        self.util_lbl = QLabel("CPU: 0% | GPU: 0%")
        self.util_lbl.setStyleSheet("font-family: 'Consolas', monospace; color: #BB86FC;")
        hw_layout.addWidget(self.util_lbl)

        self.btn_benchmark = QPushButton("⚡ Benchmark CPU vs GPU")
        self.btn_benchmark.setObjectName("secondaryBtn")
        self.btn_benchmark.setToolTip("Empirically test latency and throughput of CPU vs DirectML GPU on this machine")
        self.btn_benchmark.clicked.connect(self.open_benchmark_signal.emit)
        hw_layout.addWidget(self.btn_benchmark)

        right_layout.addWidget(hw_group)

        # 3. Settings Toggles
        ctrl_group = QGroupBox("Control Toggles")
        ctrl_layout = QVBoxLayout(ctrl_group)

        self.chk_enable_gesture = QCheckBox("Enable Cursor Control (Input Injection)")
        self.chk_enable_gesture.setChecked(True)
        ctrl_layout.addWidget(self.chk_enable_gesture)

        self.chk_hud = QCheckBox("Show Floating Mini-HUD (Draggable Anywhere)")
        self.chk_hud.setChecked(self.settings.show_hud)
        ctrl_layout.addWidget(self.chk_hud)

        self.chk_multimon = QCheckBox("Span All Monitors (Virtual Desktop)")
        self.chk_multimon.setChecked(self.settings.span_multi_monitors)
        self.chk_multimon.setToolTip("Enable pointer movement across all connected monitors (Win32 MOUSEEVENTF_VIRTUALDESK)")
        ctrl_layout.addWidget(self.chk_multimon)

        self.chk_ripple = QCheckBox("Show Animated Click Pulse & Drag Halo")
        self.chk_ripple.setChecked(self.settings.show_click_feedback)
        ctrl_layout.addWidget(self.chk_ripple)

        self.chk_mirror = QCheckBox("Mirror Camera (Selfie Mode)")
        self.chk_mirror.setChecked(self.settings.flip_horizontal)
        ctrl_layout.addWidget(self.chk_mirror)

        self.chk_yield = QCheckBox("Yield to Physical Mouse Interruption")
        self.chk_yield.setChecked(self.settings.yield_to_physical_mouse)
        ctrl_layout.addWidget(self.chk_yield)

        right_layout.addWidget(ctrl_group)

        # 4. Sensitivity Sliders
        sens_group = QGroupBox("Sensitivity Tuning")
        sens_layout = QVBoxLayout(sens_group)

        sens_layout.addWidget(QLabel("Cursor Sensitivity (Speed Multiplier):"))
        self.slider_sens = QSlider(Qt.Orientation.Horizontal)
        self.slider_sens.setRange(5, 25)
        self.slider_sens.setValue(int(self.settings.cursor_sensitivity * 10))
        sens_layout.addWidget(self.slider_sens)

        sens_layout.addWidget(QLabel("Cursor Smoothing / Responsiveness:"))
        self.slider_smooth = QSlider(Qt.Orientation.Horizontal)
        self.slider_smooth.setRange(1, 20)
        self.slider_smooth.setValue(int(self.settings.one_euro_beta * 1000))
        sens_layout.addWidget(self.slider_smooth)

        sens_layout.addWidget(QLabel("Scroll Speed Multiplier:"))
        self.slider_scroll = QSlider(Qt.Orientation.Horizontal)
        self.slider_scroll.setRange(5, 30)
        self.slider_scroll.setValue(int(self.settings.scroll_speed_multiplier * 10))
        sens_layout.addWidget(self.slider_scroll)

        right_layout.addWidget(sens_group)

        # 5. Interactive Practice, Calibration & Setup
        ux_group = QGroupBox("Experience, Calibration & Tutorial")
        ux_layout = QVBoxLayout(ux_group)

        ux_row1 = QHBoxLayout()
        self.btn_tutorial = QPushButton("🎓 Tutorial & Practice")
        self.btn_tutorial.clicked.connect(self.open_tutorial_signal.emit)
        ux_row1.addWidget(self.btn_tutorial)

        self.btn_cal = QPushButton("✋ Calibrate Hand")
        self.btn_cal.clicked.connect(self.open_calibration_signal.emit)
        ux_row1.addWidget(self.btn_cal)
        ux_layout.addLayout(ux_row1)

        ux_row2 = QHBoxLayout()
        self.btn_onboarding = QPushButton("🚀 Setup Tour")
        self.btn_onboarding.setObjectName("secondaryBtn")
        self.btn_onboarding.clicked.connect(self.open_onboarding_signal.emit)
        ux_row2.addWidget(self.btn_onboarding)

        self.btn_settings = QPushButton("⚙️ Preferences")
        self.btn_settings.setObjectName("secondaryBtn")
        self.btn_settings.clicked.connect(self.open_settings_signal.emit)
        ux_row2.addWidget(self.btn_settings)
        ux_layout.addLayout(ux_row2)

        right_layout.addWidget(ux_group)

        # 6. Test & Action Buttons
        btn_bar = QHBoxLayout()
        btn_test_click = QPushButton("Test Click Ripple")
        btn_test_click.setObjectName("secondaryBtn")
        btn_test_click.clicked.connect(self.test_click_signal.emit)
        btn_bar.addWidget(btn_test_click)

        btn_test_menu = QPushButton("Test 3x3 Menu")
        btn_test_menu.setObjectName("secondaryBtn")
        btn_test_menu.clicked.connect(self.test_command_menu_signal.emit)
        btn_bar.addWidget(btn_test_menu)

        right_layout.addLayout(btn_bar)

        right_layout.addStretch()

        btn_hide = QPushButton("Hide to System Tray")
        btn_hide.clicked.connect(self.hide)
        right_layout.addWidget(btn_hide)

        self.right_scroll.setWidget(right_widget)
        root_layout.addWidget(self.right_scroll, stretch=2)

    def _on_reconnect_clicked(self):
        idx = self.cam_combo.currentIndex()
        self.reconnect_camera_signal.emit(idx)

    def _on_res_combo_changed(self, index: int):
        data = self.res_combo.itemData(index)
        if data and isinstance(data, (tuple, list)):
            w, h = data
            self.switch_resolution_signal.emit(w, h)

    def _open_windows_camera_settings(self):
        import os
        os.system("start ms-settings:privacy-webcam")

    def _open_windows_camera_app(self):
        import os
        os.system("start microsoft.windows.camera:")

    def update_telemetry(
        self,
        state: GestureState,
        frame: Optional[np.ndarray],
        sample: Optional[HandSample],
        cap_fps: float,
        inf_fps: float,
        p95_ms: float,
        is_connected: bool,
        error_msg: str,
        e2e_ms: float = 0.0,
        dropped_frames: int = 0,
        cpu_pct: float = 0.0,
        gpu_pct: float = 0.0,
        gpu_name: str = "NVIDIA GeForce RTX 4050"
    ):
        self.preview_widget.update_frame(frame, sample, is_connected, error_msg)

        # Update state badge
        self.state_badge.setText(state.display_name)
        color = COLOR_PRIMARY_CYAN
        bg_alpha = "0.18"

        if state == GestureState.DRAGGING:
            color = "#FFA500"
            bg_alpha = "0.25"
        elif state == GestureState.SCROLLING:
            color = COLOR_ICE_BLUE
        elif state in (GestureState.PALM_REST, GestureState.COMMAND_MENU):
            color = "#C084FC"
        elif state == GestureState.PAUSED:
            color = COLOR_ACCENT_CORAL
            bg_alpha = "0.25"
        elif state == GestureState.TRACKING_LOST:
            color = "#8EABC0"

        self.state_badge.setStyleSheet(f"""
            background: rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, {bg_alpha});
            color: {color};
            font-size: 16px;
            font-weight: bold;
            padding: 8px;
            border-radius: 6px;
        """)

        # Action guidance label
        action_texts = {
            GestureState.IDLE: "Hand visible: Point index finger to control pointer",
            GestureState.TRACKING_LOST: "Searching for hand in camera view...",
            GestureState.PAUSED: "Gesture control paused",
            GestureState.POINTING: "Pointing active: Cursor tracks index finger",
            GestureState.PINCH_ARMED: "Pinching: Touch thumb & index to click or drag",
            GestureState.DRAGGING: "Dragging active: Release fingers to drop",
            GestureState.SCROLLING: "Two-finger scroll active",
            GestureState.PALM_REST: "Open palm rest (Hold still to open 3x3 menu)",
            GestureState.COMMAND_MENU: "Hand command menu open: Point to select tile"
        }
        self.action_lbl.setText(action_texts.get(state, state.display_name))

        # Hardware metrics
        lat_txt = f"{e2e_ms:.1f} ms" if e2e_ms > 0 else f"{p95_ms:.1f} ms"
        self.e2e_latency_lbl.setText(f"E2E Latency: {lat_txt} (Inf P95: {p95_ms:.1f} ms)")
        self.fps_lbl.setText(f"CAP: {int(cap_fps)} FPS | INF: {int(inf_fps)} FPS | Dropped: {dropped_frames}")
        self.util_lbl.setText(f"CPU: {cpu_pct:.1f}% | GPU: {gpu_pct:.1f}%")
        if gpu_name:
            self.gpu_lbl.setText(f"⚡ Hardware: {gpu_name}")

    def _on_emergency_stop_clicked(self):
        self.emergency_stop_signal.emit()

    def set_paused_ui(self, is_paused: bool):
        self.is_paused = is_paused
        if is_paused:
            self.btn_emergency_stop.setText("▶ RESUME GESTURE CONTROL (F8)")
            self.btn_emergency_stop.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLOR_PRIMARY_CYAN}, stop:1 #0096C7);
                    color: #050B14;
                    font-size: 13px;
                    font-weight: 800;
                    padding: 12px 16px;
                    border-radius: 8px;
                    letter-spacing: 1px;
                    border: 2px solid {COLOR_ICE_BLUE};
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLOR_ICE_BLUE}, stop:1 {COLOR_PRIMARY_CYAN});
                    border: 2px solid #FFFFFF;
                }}
            """)
        else:
            self.btn_emergency_stop.setText("🛑 EMERGENCY STOP (F8)")
            self.btn_emergency_stop.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLOR_ACCENT_CORAL}, stop:1 #D90429);
                    color: #FFFFFF;
                    font-size: 13px;
                    font-weight: 800;
                    padding: 12px 16px;
                    border-radius: 8px;
                    letter-spacing: 1px;
                    border: 2px solid #FF5C7A;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF5C7A, stop:1 #EF233C);
                    border: 2px solid #FFFFFF;
                }}
            """)

    def _on_cam_combo_changed(self, index: int):
        cam_id = self.cam_combo.itemData(index)
        if cam_id is None:
            cam_id = index
        self.switch_camera_signal.emit(cam_id)

    def populate_camera_list(self, devices, current_index: int):
        self.cam_combo.blockSignals(True)
        self.cam_combo.clear()
        selected_idx = 0
        for i, (cam_id, label) in enumerate(devices):
            self.cam_combo.addItem(label, cam_id)
            if cam_id == current_index:
                selected_idx = i
        self.cam_combo.setCurrentIndex(selected_idx)
        self.cam_combo.blockSignals(False)

    def closeEvent(self, event):
        # Minimize to tray instead of abrupt exit unless quit requested
        event.ignore()
        self.hide()
