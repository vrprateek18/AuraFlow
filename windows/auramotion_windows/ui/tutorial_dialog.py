"""
AuraMotion Pro - Interactive Gesture Tutorial & Practice Mode
Guided interactive practice with real-time recognition feedback and failure diagnostic hints.
"""
import time
import math
from typing import Optional, Dict, Any
import numpy as np

try:
    import winsound
except ImportError:
    winsound = None

from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QComboBox
)

from .main_window import CameraPreviewWidget
from .auraflow_theme import (
    get_auraflow_stylesheet,
    COLOR_PRIMARY_CYAN, COLOR_ICE_BLUE, COLOR_SUCCESS, COLOR_BORDER, COLOR_BG_CARD
)
from ..core.domain.models import HandSample, GestureState, HandJointName


GESTURES_LIST = [
    {
        "id": "pointing",
        "title": "1. Pointing & Cursor Tracking",
        "badge": "POINTER",
        "instruction": "Extend your index finger and move it across the frame with your palm facing the camera. The mouse cursor tracks your index fingertip smoothly.",
        "target_state": [GestureState.POINTING, GestureState.IDLE],
        "success_threshold": 30,  # continuous frames
    },
    {
        "id": "click",
        "title": "2. Left Click (Pinch & Release)",
        "badge": "CLICK",
        "instruction": "Tap your thumb tip and index fingertip together and release immediately. A quick pinch triggers a standard left click.",
        "target_state": [GestureState.PINCH_ARMED],
        "success_threshold": 3,   # successful clicks
    },
    {
        "id": "right_click",
        "title": "3. Right Click (Middle Finger Pinch)",
        "badge": "RIGHT CLICK",
        "instruction": "Touch your thumb tip and middle fingertip together and release immediately. A quick pinch triggers a standard right click.",
        "target_state": [GestureState.PINCH_ARMED],
        "success_threshold": 3,
    },
    {
        "id": "drag",
        "title": "4. Drag & Drop (Pinch & Move)",
        "badge": "DRAG",
        "instruction": "Pinch thumb and index together firmly, then move your hand across the screen. Release your pinch to drop the item.",
        "target_state": [GestureState.DRAGGING],
        "success_threshold": 25,  # continuous dragging frames
    },
    {
        "id": "scroll",
        "title": "5. Two-Finger Smooth Scrolling",
        "badge": "SCROLL",
        "instruction": "Extend index and middle fingers together side-by-side. Move your hand up or down to scroll smoothly.",
        "target_state": [GestureState.SCROLLING, GestureState.SCROLL_CANDIDATE],
        "success_threshold": 20,  # scrolling frames
    },
    {
        "id": "pause",
        "title": "6. Emergency Stop / Pause (F8)",
        "badge": "SAFETY",
        "instruction": "Press the F8 hotkey on your keyboard to instantly pause all gesture input injection. Press F8 again to resume.",
        "target_state": [GestureState.PAUSED],
        "success_threshold": 5,
    }
]


class GestureTutorialDialog(QDialog):
    """Interactive practice studio with live gesture diagnostics and real-time guidance."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AuraFlow — Gesture Tutorial & Practice Mode")
        self.setFixedSize(860, 600)
        self.setStyleSheet(get_auraflow_stylesheet())

        self.current_idx = 0
        self.success_count = 0
        self.consecutive_frames = 0
        self.last_state: GestureState = GestureState.IDLE

        self._init_ui()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # ── Left: Camera & Skeleton Preview ──
        left_layout = QVBoxLayout()
        header = QLabel("LIVE CAMERA & RECOGNITION FEED")
        header.setStyleSheet("color: rgba(255,255,255,0.6); font-weight: bold; font-size: 10px; letter-spacing: 1px;")
        left_layout.addWidget(header)

        self.preview_widget = CameraPreviewWidget(self)
        self.preview_widget.setFixedHeight(500)
        left_layout.addWidget(self.preview_widget)
        main_layout.addLayout(left_layout, stretch=3)

        # ── Right: Practice Controls & Diagnostic Feedback ──
        right_layout = QVBoxLayout()
        right_layout.setSpacing(12)

        # Gesture Selector
        right_layout.addWidget(QLabel("SELECT PRACTICE GESTURE:"))
        self.combo_gesture = QComboBox()
        for g in GESTURES_LIST:
            self.combo_gesture.addItem(g["title"])
        self.combo_gesture.currentIndexChanged.connect(self._on_gesture_selected)
        right_layout.addWidget(self.combo_gesture)

        # Status & Instructions Card
        info_card = QFrame()
        info_card.setStyleSheet("background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 12px;")
        info_layout = QVBoxLayout(info_card)

        self.badge_lbl = QLabel("READY TO PRACTICE")
        self.badge_lbl.setStyleSheet("color: #00FFC8; font-weight: 800; font-size: 11px; letter-spacing: 1px;")
        info_layout.addWidget(self.badge_lbl)

        self.title_lbl = QLabel(GESTURES_LIST[0]["title"])
        self.title_lbl.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        info_layout.addWidget(self.title_lbl)

        self.desc_lbl = QLabel(GESTURES_LIST[0]["instruction"])
        self.desc_lbl.setWordWrap(True)
        self.desc_lbl.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 12px; line-height: 1.4;")
        info_layout.addWidget(self.desc_lbl)

        right_layout.addWidget(info_card)

        # Diagnostic Feedback Banner (Why gesture is not recognized)
        diag_card = QFrame()
        diag_card.setStyleSheet("background: rgba(0, 0, 0, 0.4); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 8px; padding: 12px;")
        diag_layout = QVBoxLayout(diag_card)

        diag_hdr = QLabel("LIVE GESTURE DIAGNOSTIC FEEDBACK:")
        diag_hdr.setStyleSheet("color: rgba(255,255,255,0.5); font-weight: bold; font-size: 10px; letter-spacing: 1px;")
        diag_layout.addWidget(diag_hdr)

        self.feedback_lbl = QLabel("✋ Raise hand in camera view to start")
        self.feedback_lbl.setWordWrap(True)
        self.feedback_lbl.setStyleSheet("color: #FFB703; font-size: 13px; font-weight: 600;")
        diag_layout.addWidget(self.feedback_lbl)

        self.metric_hint_lbl = QLabel("Pinch Distance: -- | Palm Facing: --")
        self.metric_hint_lbl.setStyleSheet("font-family: 'Consolas', monospace; color: rgba(255,255,255,0.6); font-size: 11px;")
        diag_layout.addWidget(self.metric_hint_lbl)

        right_layout.addWidget(diag_card)

        # Success Banner
        self.success_frame = QFrame()
        self.success_frame.setStyleSheet("background: rgba(0, 255, 200, 0.12); border: 1px solid #00FFC8; border-radius: 8px; padding: 10px;")
        success_layout = QHBoxLayout(self.success_frame)
        self.success_icon = QLabel("✨")
        self.success_icon.setStyleSheet("font-size: 20px;")
        success_layout.addWidget(self.success_icon)

        self.success_txt = QLabel("Gesture Recognized! (0 Trials)")
        self.success_txt.setStyleSheet("color: #00FFC8; font-weight: bold; font-size: 13px;")
        success_layout.addWidget(self.success_txt)
        right_layout.addWidget(self.success_frame)

        right_layout.addStretch()

        # Navigation Controls
        btn_layout = QHBoxLayout()
        self.btn_prev = QPushButton("◀ Previous")
        self.btn_prev.setObjectName("secondaryBtn")
        self.btn_prev.clicked.connect(self._prev_gesture)
        btn_layout.addWidget(self.btn_prev)

        self.btn_next = QPushButton("Next Gesture ▶")
        self.btn_next.clicked.connect(self._next_gesture)
        btn_layout.addWidget(self.btn_next)

        self.btn_close = QPushButton("Close")
        self.btn_close.setObjectName("secondaryBtn")
        self.btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_close)

        right_layout.addLayout(btn_layout)
        main_layout.addLayout(right_layout, stretch=2)

    def _on_gesture_selected(self, index: int):
        self.current_idx = index
        self.success_count = 0
        self.consecutive_frames = 0
        g = GESTURES_LIST[index]
        self.title_lbl.setText(g["title"])
        self.desc_lbl.setText(g["instruction"])
        self.badge_lbl.setText(f"PRACTICING: {g['badge']}")
        self.success_txt.setText(f"Trials Completed: 0")
        self.feedback_lbl.setText("Perform the gesture shown above...")

    def _next_gesture(self):
        next_idx = (self.current_idx + 1) % len(GESTURES_LIST)
        self.combo_gesture.setCurrentIndex(next_idx)

    def _prev_gesture(self):
        prev_idx = (self.current_idx - 1) % len(GESTURES_LIST)
        self.combo_gesture.setCurrentIndex(prev_idx)

    def update_frame(self, frame: Optional[np.ndarray], sample: Optional[HandSample], state: GestureState = GestureState.IDLE):
        """Called every frame from the active pipeline."""
        self.preview_widget.update_frame(frame, sample, is_connected=(frame is not None), error_msg="")

        current_g = GESTURES_LIST[self.current_idx]
        is_target_matched = state in current_g["target_state"]

        # Diagnostic analysis when not recognized
        if sample is None or not sample.joints:
            self.feedback_lbl.setText("❌ No hand detected — place hand within camera frame.")
            self.feedback_lbl.setStyleSheet("color: #FF4D6D; font-size: 13px; font-weight: 600;")
            self.metric_hint_lbl.setText("Pinch Ratio: -- | Hand Confidence: 0.0")
            self.consecutive_frames = 0
            return

        scale = sample.scale_reference or 0.18
        tt = sample.joint(HandJointName.THUMB_TIP, min_confidence=0.15)
        it = sample.joint(HandJointName.INDEX_TIP, min_confidence=0.15)
        mt = sample.joint(HandJointName.MIDDLE_TIP, min_confidence=0.15)

        pinch_ratio = 1.0
        if tt and it and scale > 0.01:
            pinch_ratio = tt.distance_to(it) / scale

        two_finger_dist = 1.0
        if it and mt and scale > 0.01:
            two_finger_dist = it.distance_to(mt) / scale

        self.metric_hint_lbl.setText(f"Pinch Ratio: {pinch_ratio:.2f} | Two-Finger: {two_finger_dist:.2f} | Confidence: {sample.overall_confidence:.2f}")

        # Real-time diagnostic evaluation
        if current_g["id"] == "pointing":
            if sample.overall_confidence < 0.5:
                self.feedback_lbl.setText("⚠️ Tracking confidence low — adjust room lighting or raise hand.")
                self.feedback_lbl.setStyleSheet("color: #FFB703; font-size: 13px; font-weight: 600;")
            elif pinch_ratio < 0.35:
                self.feedback_lbl.setText("⚠️ Fingers pinched — unpinch to point freely with index finger.")
                self.feedback_lbl.setStyleSheet("color: #FFB703; font-size: 13px; font-weight: 600;")
            else:
                self.feedback_lbl.setText("✅ Pointer tracking active! Move hand across camera view.")
                self.feedback_lbl.setStyleSheet("color: #00FFC8; font-size: 13px; font-weight: 600;")
                self.consecutive_frames += 1

        elif current_g["id"] == "click":
            if pinch_ratio > 0.40:
                self.feedback_lbl.setText(f"❌ Thumb and index apart (Gap: {pinch_ratio:.2f}) — touch tips together!")
                self.feedback_lbl.setStyleSheet("color: #FF6B6B; font-size: 13px; font-weight: 600;")
            elif is_target_matched or pinch_ratio < 0.32:
                self.feedback_lbl.setText("✅ Pinch contact registered! Now release quickly for click.")
                self.feedback_lbl.setStyleSheet("color: #00FFC8; font-size: 13px; font-weight: 600;")
                if self.last_state != state and state in (GestureState.PINCH_ARMED, GestureState.POINTING):
                    self.success_count += 1
                    self._play_feedback_chime()

        elif current_g["id"] == "drag":
            if pinch_ratio > 0.40:
                self.feedback_lbl.setText(f"❌ Not pinched (Gap: {pinch_ratio:.2f}) — pinch firmly to start drag.")
                self.feedback_lbl.setStyleSheet("color: #FF6B6B; font-size: 13px; font-weight: 600;")
            elif state == GestureState.DRAGGING:
                self.feedback_lbl.setText("✅ Dragging active! Keep moving hand while holding pinch.")
                self.feedback_lbl.setStyleSheet("color: #FFA500; font-size: 13px; font-weight: 600;")
                self.consecutive_frames += 1
            else:
                self.feedback_lbl.setText("⏳ Pinched — now move hand to engage drag mode.")
                self.feedback_lbl.setStyleSheet("color: #00FFC8; font-size: 13px; font-weight: 600;")

        elif current_g["id"] == "scroll":
            if two_finger_dist > 0.35:
                self.feedback_lbl.setText(f"❌ Fingers too far apart (Gap: {two_finger_dist:.2f}) — keep index & middle together.")
                self.feedback_lbl.setStyleSheet("color: #FF6B6B; font-size: 13px; font-weight: 600;")
            elif state in (GestureState.SCROLLING, GestureState.SCROLL_CANDIDATE):
                self.feedback_lbl.setText("✅ Two-finger scroll active! Move up/down to scroll content.")
                self.feedback_lbl.setStyleSheet("color: #00BFFF; font-size: 13px; font-weight: 600;")
                self.consecutive_frames += 1
            else:
                self.feedback_lbl.setText("⏳ Fingers aligned — move hand up or down to scroll.")
                self.feedback_lbl.setStyleSheet("color: #00FFC8; font-size: 13px; font-weight: 600;")

        elif current_g["id"] == "pause":
            if state == GestureState.PAUSED:
                self.feedback_lbl.setText("🛑 PAUSED: Gesture input suspended safely! Press F8 to resume.")
                self.feedback_lbl.setStyleSheet("color: #FF4D6D; font-size: 13px; font-weight: 600;")
                self.consecutive_frames += 1
            else:
                self.feedback_lbl.setText("Press F8 hotkey on your keyboard to test emergency pause.")
                self.feedback_lbl.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 13px;")

        # Update success counter
        if self.consecutive_frames >= current_g["success_threshold"]:
            self.success_count += 1
            self.consecutive_frames = 0
            self._play_feedback_chime()

        self.success_txt.setText(f"Trials Completed: {self.success_count}")
        self.last_state = state

    def _play_feedback_chime(self):
        try:
            if winsound:
                winsound.MessageBeep(winsound.MB_OK)
        except Exception:
            pass
