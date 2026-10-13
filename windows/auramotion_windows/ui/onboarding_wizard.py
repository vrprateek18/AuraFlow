"""
AuraMotion Pro - First-Launch Onboarding Wizard
Guides new users through hardware check, camera selection, hand calibration, gesture tutorial, and safety setup.
"""
import time
from typing import Optional, List, Tuple
import numpy as np

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QWidget, QFrame, QComboBox, QProgressBar
)

from .main_window import CameraPreviewWidget
from ..core.domain.models import AppSettings, CalibrationProfile, HandSample, GestureState, HandJointName


class OnboardingWizard(QDialog):
    """
    First-launch walkthrough wizard ensuring camera, hand calibration,
    gesture tutorial, and safety settings are tuned before first use.
    """
    onboarding_completed = Signal(AppSettings, CalibrationProfile)
    camera_switch_requested = Signal(int)

    def __init__(self, settings: AppSettings, profile: CalibrationProfile, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.profile = profile

        self.setWindowTitle("Welcome to AuraFlow Pro - First-Launch Setup")
        self.setFixedSize(880, 620)
        self.setStyleSheet("""
            QDialog { background-color: #0F1117; color: white; font-family: 'Segoe UI', sans-serif; }
            QLabel { color: #E0E0E0; font-size: 12px; }
            QPushButton {
                background-color: #00FFC8;
                color: #0B0E14;
                font-weight: bold;
                border-radius: 6px;
                padding: 10px 22px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #00DDAA; }
            QPushButton#secondaryBtn {
                background-color: rgba(255,255,255,0.08);
                color: white;
                border: 1px solid rgba(255,255,255,0.18);
            }
            QPushButton#secondaryBtn:hover {
                background-color: rgba(255,255,255,0.15);
            }
            QComboBox {
                background: #1C202A;
                color: #00FFC8;
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QProgressBar {
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 5px;
                background-color: rgba(0,0,0,0.4);
                text-align: center;
                color: white;
                font-size: 11px;
                font-weight: bold;
                height: 18px;
            }
            QProgressBar::chunk {
                background-color: #00FFC8;
                border-radius: 4px;
            }
        """)

        # Calibration accumulator for wizard step 3
        self._span_samples: List[float] = []
        self._pinch_samples: List[float] = []

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # Header Bar
        hdr_layout = QHBoxLayout()
        self.step_dots = QLabel("●  ○  ○  ○  ○")
        self.step_dots.setStyleSheet("color: #00FFC8; font-size: 16px; font-weight: bold; letter-spacing: 6px;")
        hdr_layout.addWidget(self.step_dots)

        hdr_layout.addStretch()

        self.step_header_lbl = QLabel("STEP 1: WELCOME")
        self.step_header_lbl.setStyleSheet("color: rgba(255,255,255,0.6); font-weight: bold; font-size: 11px; letter-spacing: 1px;")
        hdr_layout.addWidget(self.step_header_lbl)
        main_layout.addLayout(hdr_layout)

        # Stacked Pages
        self.stack = QStackedWidget()
        self._create_page_welcome()
        self._create_page_camera()
        self._create_page_calibration()
        self._create_page_tutorial()
        self._create_page_safety()
        main_layout.addWidget(self.stack, stretch=1)

        # Footer Navigation Buttons
        footer_layout = QHBoxLayout()
        self.btn_back = QPushButton("◀ Back")
        self.btn_back.setObjectName("secondaryBtn")
        self.btn_back.setVisible(False)
        self.btn_back.clicked.connect(self._go_back)
        footer_layout.addWidget(self.btn_back)

        footer_layout.addStretch()

        self.btn_next = QPushButton("Get Started ▶")
        self.btn_next.clicked.connect(self._go_next)
        footer_layout.addWidget(self.btn_next)

        main_layout.addLayout(footer_layout)

    # ── Page 1: Welcome ──
    def _create_page_welcome(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 20, 40, 20)
        layout.setSpacing(18)

        logo = QLabel("✨ AuraFlow Pro")
        logo.setStyleSheet("color: #00FFC8; font-size: 28px; font-weight: 800; letter-spacing: 1px;")
        layout.addWidget(logo)

        subtitle = QLabel("Next-Gen Touchless Gesture Control for Windows 11")
        subtitle.setStyleSheet("color: white; font-size: 16px; font-weight: 600;")
        layout.addWidget(subtitle)

        desc = QLabel(
            "Control your PC effortlessly with natural hand gestures in mid-air. "
            "Engineered specifically for your Lenovo LOQ with RTX 4050 DirectML GPU hardware acceleration."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: rgba(255,255,255,0.75); font-size: 13px; line-height: 1.5;")
        layout.addWidget(desc)

        # Highlights Grid
        cards_layout = QHBoxLayout()
        features = [
            ("⚡ 60 FPS Low-Latency", "Ultra-smooth cursor interpolation with 1-Euro adaptive noise filtering."),
            ("✋ Natural Gestures", "Point, left-click, drag-and-drop, and scroll with ergonomic fingertip micro-gestures."),
            ("🛡️ Safety Watchdogs", "F8 emergency stop, automatic mouse release watchdog, and physical mouse yielding.")
        ]
        for title, body in features:
            card = QFrame()
            card.setStyleSheet("background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 14px;")
            cl = QVBoxLayout(card)
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet("color: #00FFC8; font-weight: bold; font-size: 13px;")
            cl.addWidget(t_lbl)
            b_lbl = QLabel(body)
            b_lbl.setWordWrap(True)
            b_lbl.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 11px;")
            cl.addWidget(b_lbl)
            cards_layout.addWidget(card)

        layout.addLayout(cards_layout)
        layout.addStretch()
        self.stack.addWidget(page)

    # ── Page 2: Camera Setup ──
    def _create_page_camera(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setSpacing(20)

        # Left: Live Preview
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("LIVE WEBCAM PREVIEW:"))
        self.cam_preview = CameraPreviewWidget(self)
        self.cam_preview.setFixedHeight(360)
        left_layout.addWidget(self.cam_preview)
        layout.addLayout(left_layout, stretch=3)

        # Right: Camera selection and checklist
        right_layout = QVBoxLayout()
        right_layout.setSpacing(12)

        t_lbl = QLabel("Camera Selection & Permissions")
        t_lbl.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        right_layout.addWidget(t_lbl)

        right_layout.addWidget(QLabel("Active Camera Device:"))
        self.cam_combo = QComboBox()
        self.cam_combo.currentIndexChanged.connect(self._on_cam_selected)
        right_layout.addWidget(self.cam_combo)

        # Lenovo LOQ Checklist
        chk_card = QFrame()
        chk_card.setStyleSheet("background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 12px;")
        cl = QVBoxLayout(chk_card)
        cl.addWidget(QLabel("Lenovo LOQ Hardware Quick-Check:"))
        items = [
            "1. Physical E-Shutter Switch: Open (Right edge of laptop)",
            "2. Windows 11 Privacy: Allow desktop apps camera access",
            "3. Optimal Lighting: Ensure hand is well-lit in front of screen"
        ]
        for itm in items:
            l = QLabel(f"• {itm}")
            l.setStyleSheet("color: rgba(255,255,255,0.75); font-size: 11px;")
            cl.addWidget(l)
        right_layout.addWidget(chk_card)

        self.cam_status_lbl = QLabel("Status: Camera stream active")
        self.cam_status_lbl.setStyleSheet("color: #00FFC8; font-weight: bold; font-size: 12px;")
        right_layout.addWidget(self.cam_status_lbl)

        right_layout.addStretch()
        layout.addLayout(right_layout, stretch=2)
        self.stack.addWidget(page)

    # ── Page 3: Hand Calibration ──
    def _create_page_calibration(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setSpacing(20)

        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("CALIBRATION CAMERA FEED:"))
        self.cal_preview = CameraPreviewWidget(self)
        self.cal_preview.setFixedHeight(360)
        left_layout.addWidget(self.cal_preview)
        layout.addLayout(left_layout, stretch=3)

        right_layout = QVBoxLayout()
        right_layout.setSpacing(12)

        title = QLabel("Guided Hand Calibration")
        title.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        right_layout.addWidget(title)

        desc = QLabel(
            "Hold your hand open facing the camera to measure your hand span, "
            "then touch thumb and index tips together to calibrate pinch activation."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 12px;")
        right_layout.addWidget(desc)

        self.cal_step_lbl = QLabel("Hold hand open facing camera...")
        self.cal_step_lbl.setStyleSheet("color: #00FFC8; font-size: 13px; font-weight: bold;")
        right_layout.addWidget(self.cal_step_lbl)

        self.cal_progress = QProgressBar()
        self.cal_progress.setRange(0, 30)
        self.cal_progress.setValue(0)
        right_layout.addWidget(self.cal_progress)

        self.cal_result_lbl = QLabel("Hand Span: Calibrating...")
        self.cal_result_lbl.setStyleSheet("font-family: 'Consolas', monospace; color: rgba(255,255,255,0.7); font-size: 11px;")
        right_layout.addWidget(self.cal_result_lbl)

        btn_skip_cal = QPushButton("Skip Hand Calibration (Use Defaults)")
        btn_skip_cal.setObjectName("secondaryBtn")
        btn_skip_cal.clicked.connect(self._go_next)
        right_layout.addWidget(btn_skip_cal)

        right_layout.addStretch()
        layout.addLayout(right_layout, stretch=2)
        self.stack.addWidget(page)

    # ── Page 4: Gesture Tutorial & Practice ──
    def _create_page_tutorial(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setSpacing(20)

        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("PRACTICE CAMERA FEED:"))
        self.tut_preview = CameraPreviewWidget(self)
        self.tut_preview.setFixedHeight(360)
        left_layout.addWidget(self.tut_preview)
        layout.addLayout(left_layout, stretch=3)

        right_layout = QVBoxLayout()
        right_layout.setSpacing(12)

        title = QLabel("Quick Gesture Practice")
        title.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        right_layout.addWidget(title)

        # Gestures reference
        ref_card = QFrame()
        ref_card.setStyleSheet("background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 10px;")
        rl = QVBoxLayout(ref_card)
        gestures = [
            ("👉 Point & Move", "Extend index finger to navigate cursor"),
            ("👌 Left Click", "Quickly tap thumb to index fingertip"),
            ("✊ Drag & Drop", "Pinch thumb + index and hold while moving"),
            ("✌️ Two-Finger Scroll", "Move index + middle fingers together vertically")
        ]
        for g_title, g_desc in gestures:
            lbl = QLabel(f"<b>{g_title}</b>: {g_desc}")
            lbl.setStyleSheet("font-size: 11px; color: rgba(255,255,255,0.85);")
            rl.addWidget(lbl)
        right_layout.addWidget(ref_card)

        self.live_gesture_feedback = QLabel("Try pointing or pinching in front of camera...")
        self.live_gesture_feedback.setStyleSheet("color: #00FFC8; font-weight: bold; font-size: 13px;")
        right_layout.addWidget(self.live_gesture_feedback)

        right_layout.addStretch()
        layout.addLayout(right_layout, stretch=2)
        self.stack.addWidget(page)

    # ── Page 5: Safety & Finish ──
    def _create_page_safety(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 20, 40, 20)
        layout.setSpacing(16)

        title = QLabel("🛡️ Safety Controls & Emergency Pause")
        title.setStyleSheet("color: #00FFC8; font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        desc = QLabel("You're fully in control at all times with built-in hardware safety guards:")
        desc.setStyleSheet("color: white; font-size: 13px;")
        layout.addWidget(desc)

        safety_card = QFrame()
        safety_card.setStyleSheet("background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 16px;")
        sl = QVBoxLayout(safety_card)
        sl.setSpacing(10)
        guards = [
            ("🛑 F8 Hotkey Emergency Stop", "Press F8 anywhere at any time to instantly freeze/unfreeze gesture injection."),
            ("🖱️ Physical Mouse Arbitration", "The instant you touch your physical mouse or touchpad, gestures automatically pause."),
            ("⏱️ Auto-Release Watchdog", "If your hand leaves the camera frame while dragging, the mouse button releases in under 180ms.")
        ]
        for g_title, g_body in guards:
            h = QLabel(g_title)
            h.setStyleSheet("color: #00FFC8; font-weight: bold; font-size: 13px;")
            sl.addWidget(h)
            b = QLabel(g_body)
            b.setStyleSheet("color: rgba(255,255,255,0.75); font-size: 11px;")
            sl.addWidget(b)
        layout.addWidget(safety_card)

        layout.addStretch()
        self.stack.addWidget(page)

    def populate_cameras(self, devices: List[Tuple[int, str]], current_index: int):
        self.cam_combo.blockSignals(True)
        self.cam_combo.clear()
        for idx, name in devices:
            self.cam_combo.addItem(name, idx)
        for i in range(self.cam_combo.count()):
            if self.cam_combo.itemData(i) == current_index:
                self.cam_combo.setCurrentIndex(i)
                break
        self.cam_combo.blockSignals(False)

    def _on_cam_selected(self, index: int):
        cam_idx = self.cam_combo.itemData(index)
        if cam_idx is not None:
            self.settings.camera_index = cam_idx
            self.camera_switch_requested.emit(cam_idx)

    def update_frame(self, frame: Optional[np.ndarray], sample: Optional[HandSample], state: GestureState = GestureState.IDLE):
        """Called every frame from the active pipeline."""
        curr_page = self.stack.currentIndex()
        if curr_page == 1:
            self.cam_preview.update_frame(frame, sample, is_connected=(frame is not None), error_msg="")
        elif curr_page == 2:
            self.cal_preview.update_frame(frame, sample, is_connected=(frame is not None), error_msg="")
            self._handle_calibration_step(sample)
        elif curr_page == 3:
            self.tut_preview.update_frame(frame, sample, is_connected=(frame is not None), error_msg="")
            self._handle_tutorial_step(sample, state)

    def _handle_calibration_step(self, sample: Optional[HandSample]):
        if sample is None or not sample.joints:
            self.cal_step_lbl.setText("✋ Hold hand steadily facing camera...")
            return

        scale = sample.scale_reference
        if len(self._span_samples) < 30 and scale and scale > 0.08:
            self._span_samples.append(scale)
            self.cal_progress.setValue(len(self._span_samples))
            self.cal_step_lbl.setText(f"Measuring hand span... ({len(self._span_samples)}/30)")
            if len(self._span_samples) >= 30:
                med_scale = float(np.median(self._span_samples))
                self.profile.hand_scale_reference = med_scale
                self.profile.is_calibrated = True
                self.profile.calibrated_at = time.strftime("%Y-%m-%d %H:%M:%S")
                self.cal_step_lbl.setText("✅ Hand span calibrated successfully!")
                self.cal_result_lbl.setText(f"Hand Scale Reference: {med_scale:.3f}")

    def _handle_tutorial_step(self, sample: Optional[HandSample], state: GestureState):
        if sample is None or not sample.joints:
            self.live_gesture_feedback.setText("✋ Place hand in camera frame to test")
            return

        state_names = {
            GestureState.POINTING: "✅ Pointing detected! Moving mouse cursor",
            GestureState.PINCH_ARMED: "✅ Pinch detected! Left click trigger",
            GestureState.DRAGGING: "✅ Dragging active! Moving item",
            GestureState.SCROLLING: "✅ Two-Finger Scroll active!",
            GestureState.PAUSED: "🛑 F8 Paused!",
            GestureState.IDLE: "Ready — try pointing with index finger",
        }
        self.live_gesture_feedback.setText(state_names.get(state, f"Gesture State: {state.display_name}"))

    def _go_next(self):
        curr = self.stack.currentIndex()
        if curr < self.stack.count() - 1:
            self.stack.setCurrentIndex(curr + 1)
            self._update_navigation_state()
        else:
            # Finish wizard
            self.settings.first_launch_completed = True
            self.onboarding_completed.emit(self.settings, self.profile)
            self.accept()

    def _go_back(self):
        curr = self.stack.currentIndex()
        if curr > 0:
            self.stack.setCurrentIndex(curr - 1)
            self._update_navigation_state()

    def _update_navigation_state(self):
        idx = self.stack.currentIndex()
        total = self.stack.count()

        # Update dots
        dots = ["●" if i == idx else "○" for i in range(total)]
        self.step_dots.setText("  ".join(dots))

        step_titles = [
            "STEP 1: WELCOME",
            "STEP 2: CAMERA SETUP",
            "STEP 3: HAND CALIBRATION",
            "STEP 4: GESTURE TUTORIAL",
            "STEP 5: SAFETY CONTROLS"
        ]
        self.step_header_lbl.setText(step_titles[idx])

        self.btn_back.setVisible(idx > 0)
        if idx == total - 1:
            self.btn_next.setText("Finish & Start AuraFlow ✨")
        else:
            self.btn_next.setText("Next ▶")
