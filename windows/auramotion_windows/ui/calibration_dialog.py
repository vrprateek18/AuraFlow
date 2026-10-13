"""
AuraMotion Pro - Guided Hand Calibration Dialog
Interactive step-by-step calibration of user's hand size and pinch thresholds with live preview.
"""
import time
import math
from typing import Optional, List
import numpy as np

from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QStackedWidget, QWidget, QFrame
)

from .main_window import CameraPreviewWidget
from .auraflow_theme import get_auraflow_stylesheet
from ..core.domain.models import CalibrationProfile, HandSample, GestureState, HandJointName


class GuidedCalibrationDialog(QDialog):
    """
    Step-by-step interactive hand calibration wizard with live camera preview.
    Tuning hand scale reference, pinch activation, and shortcut thresholds.
    """
    calibration_saved = Signal(CalibrationProfile)

    def __init__(self, current_profile: CalibrationProfile, parent=None):
        super().__init__(parent)
        self.profile = current_profile
        self.current_step = 1  # 1: Span, 2: Pinch, 3: Pinky/Ring shortcuts, 4: Summary
        self.setWindowTitle("AuraFlow — Guided Hand Calibration")
        self.setFixedSize(780, 560)
        self.setStyleSheet(get_auraflow_stylesheet())

        # Calibration data accumulators
        self._span_samples: List[float] = []
        self._pinch_samples: List[float] = []
        self._shortcut_samples: List[float] = []

        # Results
        self.calibrated_scale: float = self.profile.hand_scale_reference
        self.calibrated_pinch_start: float = self.profile.pinch_start_threshold
        self.calibrated_pinch_release: float = self.profile.pinch_release_threshold
        self.calibrated_copy: float = self.profile.copy_contact_threshold
        self.calibrated_paste: float = self.profile.paste_contact_threshold

        self._init_ui()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # ── Left: Live Camera Preview ──
        left_layout = QVBoxLayout()
        preview_header = QLabel("LIVE CAMERA & HAND TRACKING")
        preview_header.setStyleSheet("color: rgba(255,255,255,0.6); font-weight: bold; font-size: 10px; letter-spacing: 1px;")
        left_layout.addWidget(preview_header)

        self.preview_widget = CameraPreviewWidget(self)
        self.preview_widget.setFixedHeight(460)
        left_layout.addWidget(self.preview_widget)
        main_layout.addLayout(left_layout, stretch=3)

        # ── Right: Step Guidance & Metrics ──
        right_layout = QVBoxLayout()
        right_layout.setSpacing(14)

        # Step Breadcrumbs
        self.step_tracker = QLabel("STEP 1 OF 3: HAND SPAN")
        self.step_tracker.setStyleSheet("color: #00FFC8; font-weight: 800; font-size: 12px; letter-spacing: 1px;")
        right_layout.addWidget(self.step_tracker)

        # Step Title
        self.step_title = QLabel("Hold Hand Open (Rest Span)")
        self.step_title.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        right_layout.addWidget(self.step_title)

        # Step Instructions
        self.step_desc = QLabel(
            "Hold your hand open and relaxed facing the camera with fingers naturally spread. "
            "This measures your unique hand geometry and scale."
        )
        self.step_desc.setWordWrap(True)
        self.step_desc.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 12px; line-height: 1.4;")
        right_layout.addWidget(self.step_desc)

        # Live Metric Card
        metric_card = QFrame()
        metric_card.setStyleSheet("background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 10px;")
        metric_layout = QVBoxLayout(metric_card)

        self.live_metric_lbl = QLabel("Live Reading: Waiting for hand...")
        self.live_metric_lbl.setStyleSheet("font-family: 'Consolas', monospace; color: #00FFC8; font-size: 13px; font-weight: bold;")
        metric_layout.addWidget(self.live_metric_lbl)

        self.target_hint_lbl = QLabel("Target: Hold steady in frame")
        self.target_hint_lbl.setStyleSheet("color: rgba(255,255,255,0.6); font-size: 11px;")
        metric_layout.addWidget(self.target_hint_lbl)

        right_layout.addWidget(metric_card)

        # Step Progress
        right_layout.addWidget(QLabel("Sample Progress:"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 30)
        self.progress_bar.setValue(0)
        right_layout.addWidget(self.progress_bar)

        # Summary Frame (Hidden until step 4)
        self.summary_frame = QFrame()
        self.summary_frame.setVisible(False)
        self.summary_frame.setStyleSheet("background: rgba(0, 255, 200, 0.08); border: 1px solid rgba(0, 255, 200, 0.3); border-radius: 8px; padding: 12px;")
        summary_layout = QVBoxLayout(self.summary_frame)
        self.summary_txt = QLabel("Calibration Complete!")
        self.summary_txt.setStyleSheet("color: #00FFC8; font-size: 12px; font-weight: bold;")
        self.summary_txt.setWordWrap(True)
        summary_layout.addWidget(self.summary_txt)
        right_layout.addWidget(self.summary_frame)

        right_layout.addStretch()

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.btn_action = QPushButton("Skip Step")
        self.btn_action.setObjectName("secondaryBtn")
        self.btn_action.clicked.connect(self._on_action_clicked)
        btn_layout.addWidget(self.btn_action)

        self.btn_save = QPushButton("Save Calibration")
        self.btn_save.setVisible(False)
        self.btn_save.clicked.connect(self._save_calibration)
        btn_layout.addWidget(self.btn_save)

        self.btn_close = QPushButton("Cancel")
        self.btn_close.setObjectName("secondaryBtn")
        self.btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_close)

        right_layout.addLayout(btn_layout)
        main_layout.addLayout(right_layout, stretch=2)

    def update_frame(self, frame: Optional[np.ndarray], sample: Optional[HandSample], state: GestureState = GestureState.IDLE):
        """Called every camera frame from the main app loop."""
        self.preview_widget.update_frame(frame, sample, is_connected=(frame is not None), error_msg="")

        if sample is None or not sample.joints:
            self.live_metric_lbl.setText("Live Reading: ✋ No hand in frame")
            return

        scale = sample.scale_reference
        tt = sample.joint(HandJointName.THUMB_TIP, min_confidence=0.15)
        it = sample.joint(HandJointName.INDEX_TIP, min_confidence=0.15)
        rt = sample.joint(HandJointName.RING_TIP, min_confidence=0.15)
        pt = sample.joint(HandJointName.LITTLE_TIP, min_confidence=0.15)

        if self.current_step == 1:
            # Measure hand resting span (scale reference)
            if scale and scale > 0.08:
                self._span_samples.append(scale)
                self.progress_bar.setValue(len(self._span_samples))
                self.live_metric_lbl.setText(f"Hand Span: {scale:.3f} (Samples: {len(self._span_samples)}/30)")
                self.target_hint_lbl.setText("Keep holding still facing camera...")

                if len(self._span_samples) >= 30:
                    self.calibrated_scale = float(np.median(self._span_samples))
                    self._advance_to_step(2)

        elif self.current_step == 2:
            # Measure pinch contact distance
            if tt and it and scale:
                pinch_dist = tt.distance_to(it)
                ratio = pinch_dist / scale
                self.live_metric_lbl.setText(f"Thumb-Index Ratio: {ratio:.3f} (Contact Target: < 0.32)")

                if ratio < 0.35:
                    self._pinch_samples.append(ratio)
                    self.progress_bar.setValue(len(self._pinch_samples))
                    self.target_hint_lbl.setText("Good contact! Hold pinch firmly...")
                    if len(self._pinch_samples) >= 20:
                        median_pinch = float(np.median(self._pinch_samples))
                        self.calibrated_pinch_start = round(median_pinch * 1.35, 3)
                        self.calibrated_pinch_release = round(median_pinch * 1.85, 3)
                        self._advance_to_step(3)
                else:
                    self.target_hint_lbl.setText("Bring thumb tip and index tip firmly together")

        elif self.current_step == 3:
            # Measure pinky/ring shortcut contact
            if tt and scale:
                dist_pinky = tt.distance_to(pt) if pt else 1.0
                dist_ring = tt.distance_to(rt) if rt else 1.0
                min_shortcut_dist = min(dist_pinky, dist_ring)
                ratio = min_shortcut_dist / scale
                self.live_metric_lbl.setText(f"Shortcut Proximity: {ratio:.3f}")

                if ratio < 0.38:
                    self._shortcut_samples.append(ratio)
                    self.progress_bar.setValue(len(self._shortcut_samples))
                    self.target_hint_lbl.setText("Touch registered! Hold thumb to pinky/ring...")
                    if len(self._shortcut_samples) >= 15:
                        med_sc = float(np.median(self._shortcut_samples))
                        self.calibrated_copy = round(med_sc * 1.25, 3)
                        self.calibrated_paste = round(med_sc * 1.25, 3)
                        self._advance_to_step(4)
                else:
                    self.target_hint_lbl.setText("Touch thumb to pinky or ring finger tip")

    def _advance_to_step(self, step: int):
        self.current_step = step
        if step == 2:
            self.step_tracker.setText("STEP 2 OF 3: PINCH SENSITIVITY")
            self.step_title.setText("Touch Thumb & Index Tips")
            self.step_desc.setText(
                "Touch your thumb and index tips together firmly (like pinching a grain of sand). "
                "This sets your zero-effort click and drag sensitivity."
            )
            self.progress_bar.setRange(0, 20)
            self.progress_bar.setValue(0)
            self.btn_action.setText("Skip to Shortcuts")
        elif step == 3:
            self.step_tracker.setText("STEP 3 OF 3: FINGER SHORTCUTS")
            self.step_title.setText("Touch Thumb to Pinky / Ring")
            self.step_desc.setText(
                "Touch your thumb tip to your pinky finger (Paste) or ring finger (Copy). "
                "This calibrates gesture triggers for high precision."
            )
            self.progress_bar.setRange(0, 15)
            self.progress_bar.setValue(0)
            self.btn_action.setText("Skip to Summary")
        elif step == 4:
            self.step_tracker.setText("CALIBRATION COMPLETE")
            self.step_title.setText("Hand Profile Ready!")
            self.step_desc.setText("Your custom hand profile has been computed.")
            self.live_metric_lbl.setText("Status: Calibrated & Ready")
            self.target_hint_lbl.setText("Click 'Save Calibration' to apply to live tracker.")
            self.progress_bar.setVisible(False)
            self.summary_frame.setVisible(True)
            self.summary_txt.setText(
                f"• Calibrated Hand Scale: {self.calibrated_scale:.3f}\n"
                f"• Pinch Activation Threshold: {self.calibrated_pinch_start:.3f}\n"
                f"• Pinch Release Threshold: {self.calibrated_pinch_release:.3f}\n"
                f"• Copy/Paste Contact: {self.calibrated_copy:.3f}"
            )
            self.btn_action.setText("Recalibrate")
            self.btn_save.setVisible(True)

    def _on_action_clicked(self):
        if self.current_step < 4:
            self._advance_to_step(self.current_step + 1)
        else:
            # Recalibrate
            self._span_samples.clear()
            self._pinch_samples.clear()
            self._shortcut_samples.clear()
            self.progress_bar.setVisible(True)
            self.summary_frame.setVisible(False)
            self.btn_save.setVisible(False)
            self._advance_to_step(1)

    def _save_calibration(self):
        new_profile = CalibrationProfile(
            pinch_start_threshold=self.calibrated_pinch_start,
            pinch_release_threshold=self.calibrated_pinch_release,
            copy_contact_threshold=self.calibrated_copy,
            copy_release_threshold=self.calibrated_copy + 0.12,
            paste_contact_threshold=self.calibrated_paste,
            paste_release_threshold=self.calibrated_paste + 0.12,
            drag_deadband_points=self.profile.drag_deadband_points,
            scroll_deadband_points=self.profile.scroll_deadband_points,
            hand_scale_reference=self.calibrated_scale,
            is_calibrated=True,
            calibrated_at=time.strftime("%Y-%m-%d %H:%M:%S")
        )
        self.calibration_saved.emit(new_profile)
        self.accept()
