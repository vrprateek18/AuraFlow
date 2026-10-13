"""
AuraMotion Pro - Comprehensive Persistent Settings & Thresholds Dialog
Allows fine-tuning of sensitivity, smoothing, scroll speed, gesture thresholds, and launching wizards.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QSlider, QDoubleSpinBox, QPushButton, QGroupBox, QFormLayout,
    QTabWidget, QWidget, QFrame
)
from ..core.domain.models import AppSettings, CalibrationProfile


class SettingsDialog(QDialog):
    open_calibration_signal = Signal()
    open_tutorial_signal = Signal()
    open_onboarding_signal = Signal()

    def __init__(self, settings: AppSettings, profile: CalibrationProfile, on_save=None, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.profile = profile
        self.on_save = on_save

        self.setWindowTitle("AuraFlow — Preferences & Gesture Tuning")
        self.setFixedSize(520, 620)
        self.setStyleSheet("""
            QDialog { background-color: #15171E; color: white; font-family: 'Segoe UI', sans-serif; }
            QLabel { color: #E0E0E0; font-size: 11px; }
            QTabWidget::pane { border: 1px solid rgba(255,255,255,0.12); border-radius: 8px; background: #1A1C24; }
            QTabBar::tab {
                background: #12141A;
                color: rgba(255,255,255,0.7);
                padding: 8px 16px;
                margin-right: 4px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: bold;
                font-size: 11px;
            }
            QTabBar::tab:selected {
                background: #1A1C24;
                color: #00FFC8;
                border-bottom: 2px solid #00FFC8;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 14px;
                color: #00FFC8;
                font-size: 11px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
            QCheckBox { color: #E0E0E0; font-size: 11px; spacing: 8px; }
            QDoubleSpinBox {
                background: #232733;
                color: white;
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: 4px;
                padding: 4px 8px;
                font-weight: bold;
            }
            QPushButton {
                background-color: #00FFC8;
                color: #0D1117;
                font-weight: bold;
                border-radius: 6px;
                padding: 7px 16px;
                font-size: 11px;
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
            QSlider::groove:horizontal { height: 4px; background: rgba(255,255,255,0.2); border-radius: 2px; }
            QSlider::handle:horizontal { background: #00FFC8; width: 14px; margin: -5px 0; border-radius: 7px; }
        """)

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        tabs = QTabWidget()
        tabs.addTab(self._create_tab_tracking(), "Tracking & Sensitivity")
        tabs.addTab(self._create_tab_thresholds(), "Gesture Thresholds")
        tabs.addTab(self._create_tab_tools(), "Wizards & Tools")
        main_layout.addWidget(tabs, stretch=1)

        # Footer Buttons
        btn_bar = QHBoxLayout()
        btn_reset = QPushButton("Reset Defaults")
        btn_reset.setObjectName("secondaryBtn")
        btn_reset.clicked.connect(self._reset_defaults)
        btn_bar.addWidget(btn_reset)

        btn_bar.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("secondaryBtn")
        btn_cancel.clicked.connect(self.reject)
        btn_bar.addWidget(btn_cancel)

        btn_save = QPushButton("Save & Apply")
        btn_save.clicked.connect(self._save)
        btn_bar.addWidget(btn_save)

        main_layout.addLayout(btn_bar)

    def _create_tab_tracking(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Interaction Toggles
        gen_group = QGroupBox("Camera & Interaction Behaviors")
        gen_layout = QFormLayout(gen_group)

        self.chk_flip = QCheckBox("Mirror camera horizontally (Selfie mode)")
        self.chk_flip.setChecked(self.settings.flip_horizontal)
        gen_layout.addRow(self.chk_flip)

        self.chk_clutch = QCheckBox("Engagement clutch (Rejects unintended rapid sweeps)")
        self.chk_clutch.setChecked(self.settings.is_clutch_enabled)
        gen_layout.addRow(self.chk_clutch)

        self.chk_swipe = QCheckBox("Open-palm window switching (Alt+Tab / Task View)")
        self.chk_swipe.setChecked(self.settings.is_palm_swipe_enabled)
        gen_layout.addRow(self.chk_swipe)

        self.chk_yield = QCheckBox("Yield to physical mouse & touchpad automatically")
        self.chk_yield.setChecked(self.settings.yield_to_physical_mouse)
        gen_layout.addRow(self.chk_yield)

        layout.addWidget(gen_group)

        # Sensitivity Tuning
        sens_group = QGroupBox("Speed & Smoothing Tuning")
        sens_layout = QFormLayout(sens_group)

        self.slider_sens = QSlider(Qt.Orientation.Horizontal)
        self.slider_sens.setRange(5, 25)
        self.slider_sens.setValue(int(self.settings.cursor_sensitivity * 10))
        self.lbl_sens_val = QLabel(f"{self.settings.cursor_sensitivity:.1f}x")
        self.slider_sens.valueChanged.connect(lambda v: self.lbl_sens_val.setText(f"{v/10.0:.1f}x"))
        row1 = QHBoxLayout()
        row1.addWidget(self.slider_sens)
        row1.addWidget(self.lbl_sens_val)
        sens_layout.addRow("Cursor Sensitivity:", row1)

        self.slider_smooth = QSlider(Qt.Orientation.Horizontal)
        self.slider_smooth.setRange(1, 25)
        self.slider_smooth.setValue(int(self.settings.one_euro_beta * 1000))
        self.lbl_smooth_val = QLabel(f"{self.settings.one_euro_beta:.3f}")
        self.slider_smooth.valueChanged.connect(lambda v: self.lbl_smooth_val.setText(f"{v/1000.0:.3f}"))
        row2 = QHBoxLayout()
        row2.addWidget(self.slider_smooth)
        row2.addWidget(self.lbl_smooth_val)
        sens_layout.addRow("Cursor Responsiveness:", row2)

        self.slider_speed = QSlider(Qt.Orientation.Horizontal)
        self.slider_speed.setRange(5, 30)
        self.slider_speed.setValue(int(self.settings.scroll_speed_multiplier * 10))
        self.lbl_speed_val = QLabel(f"{self.settings.scroll_speed_multiplier:.1f}x")
        self.slider_speed.valueChanged.connect(lambda v: self.lbl_speed_val.setText(f"{v/10.0:.1f}x"))
        row3 = QHBoxLayout()
        row3.addWidget(self.slider_speed)
        row3.addWidget(self.lbl_speed_val)
        sens_layout.addRow("Scroll Speed:", row3)

        layout.addWidget(sens_group)

        # Visual Feedback
        vis_group = QGroupBox("Visual Feedback Overlays")
        vis_layout = QFormLayout(vis_group)

        self.chk_hud = QCheckBox("Show floating telemetry mini-HUD on screen")
        self.chk_hud.setChecked(self.settings.show_hud)
        vis_layout.addRow(self.chk_hud)

        self.chk_ripple = QCheckBox("Show animated click pulse and dragging halo")
        self.chk_ripple.setChecked(self.settings.show_click_feedback)
        vis_layout.addRow(self.chk_ripple)

        layout.addWidget(vis_group)
        layout.addStretch()
        return tab

    def _create_tab_thresholds(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Calibration status card
        cal_status = QFrame()
        cal_status.setStyleSheet("background: rgba(0,255,200,0.06); border: 1px solid rgba(0,255,200,0.25); border-radius: 6px; padding: 10px;")
        csl = QVBoxLayout(cal_status)
        cal_txt = "Custom Hand Calibrated" if self.profile.is_calibrated else "Default Baseline Profile"
        self.lbl_cal_state = QLabel(f"Profile Status: {cal_txt}")
        self.lbl_cal_state.setStyleSheet("color: #00FFC8; font-weight: bold; font-size: 11px;")
        csl.addWidget(self.lbl_cal_state)
        if self.profile.calibrated_at:
            self.lbl_cal_date = QLabel(f"Last Calibrated: {self.profile.calibrated_at}")
            self.lbl_cal_date.setStyleSheet("color: rgba(255,255,255,0.6); font-size: 10px;")
            csl.addWidget(self.lbl_cal_date)
        layout.addWidget(cal_status)

        # Pinch thresholds
        pinch_group = QGroupBox("Pinch & Click Trigger Thresholds")
        pinch_layout = QFormLayout(pinch_group)

        self.spin_pinch_start = QDoubleSpinBox()
        self.spin_pinch_start.setRange(0.10, 0.60)
        self.spin_pinch_start.setSingleStep(0.01)
        self.spin_pinch_start.setValue(self.profile.pinch_start_threshold)
        pinch_layout.addRow("Pinch Activation Distance:", self.spin_pinch_start)

        self.spin_pinch_release = QDoubleSpinBox()
        self.spin_pinch_release.setRange(0.15, 0.70)
        self.spin_pinch_release.setSingleStep(0.01)
        self.spin_pinch_release.setValue(self.profile.pinch_release_threshold)
        pinch_layout.addRow("Pinch Release Distance:", self.spin_pinch_release)

        layout.addWidget(pinch_group)

        # Shortcut thresholds
        sc_group = QGroupBox("Shortcut & Deadband Tuning")
        sc_layout = QFormLayout(sc_group)

        self.spin_copy = QDoubleSpinBox()
        self.spin_copy.setRange(0.15, 0.50)
        self.spin_copy.setSingleStep(0.01)
        self.spin_copy.setValue(self.profile.copy_contact_threshold)
        sc_layout.addRow("Copy Contact (Thumb-Ring):", self.spin_copy)

        self.spin_paste = QDoubleSpinBox()
        self.spin_paste.setRange(0.15, 0.50)
        self.spin_paste.setSingleStep(0.01)
        self.spin_paste.setValue(self.profile.paste_contact_threshold)
        sc_layout.addRow("Paste Contact (Thumb-Pinky):", self.spin_paste)

        self.spin_drag_deadband = QDoubleSpinBox()
        self.spin_drag_deadband.setRange(5.0, 50.0)
        self.spin_drag_deadband.setSingleStep(1.0)
        self.spin_drag_deadband.setValue(self.profile.drag_deadband_points)
        sc_layout.addRow("Drag Deadband (points):", self.spin_drag_deadband)

        self.spin_scroll_deadband = QDoubleSpinBox()
        self.spin_scroll_deadband.setRange(2.0, 25.0)
        self.spin_scroll_deadband.setSingleStep(1.0)
        self.spin_scroll_deadband.setValue(self.profile.scroll_deadband_points)
        sc_layout.addRow("Scroll Deadband (points):", self.spin_scroll_deadband)

        layout.addWidget(sc_group)
        layout.addStretch()
        return tab

    def _create_tab_tools(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        t_lbl = QLabel("Wizards, Guided Calibration & Practice Tools")
        t_lbl.setStyleSheet("color: #00FFC8; font-weight: bold; font-size: 13px;")
        layout.addWidget(t_lbl)

        # Calibration Launcher Card
        c1 = QFrame()
        c1.setStyleSheet("background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 12px;")
        l1 = QHBoxLayout(c1)
        l1_txt = QVBoxLayout()
        h1 = QLabel("✋ Guided Hand Calibration")
        h1.setStyleSheet("color: white; font-weight: bold; font-size: 12px;")
        l1_txt.addWidget(h1)
        b1 = QLabel("Calibrate your hand span, pinch contact, and shortcuts with live camera preview.")
        b1.setWordWrap(True)
        b1.setStyleSheet("color: rgba(255,255,255,0.65); font-size: 10px;")
        l1_txt.addWidget(b1)
        l1.addLayout(l1_txt, stretch=1)
        btn_c = QPushButton("Launch Calibration")
        btn_c.clicked.connect(self._launch_calibration)
        l1.addWidget(btn_c)
        layout.addWidget(c1)

        # Tutorial Launcher Card
        c2 = QFrame()
        c2.setStyleSheet("background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 12px;")
        l2 = QHBoxLayout(c2)
        l2_txt = QVBoxLayout()
        h2 = QLabel("🎓 Gesture Tutorial & Practice Mode")
        h2.setStyleSheet("color: white; font-weight: bold; font-size: 12px;")
        l2_txt.addWidget(h2)
        b2 = QLabel("Practice pointing, clicking, dragging, and scrolling with live diagnostic error feedback.")
        b2.setWordWrap(True)
        b2.setStyleSheet("color: rgba(255,255,255,0.65); font-size: 10px;")
        l2_txt.addWidget(b2)
        l2.addLayout(l2_txt, stretch=1)
        btn_t = QPushButton("Open Tutorial")
        btn_t.clicked.connect(self._launch_tutorial)
        l2.addWidget(btn_t)
        layout.addWidget(c2)

        # Onboarding Launcher Card
        c3 = QFrame()
        c3.setStyleSheet("background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 12px;")
        l3 = QHBoxLayout(c3)
        l3_txt = QVBoxLayout()
        h3 = QLabel("🚀 First-Launch Onboarding Wizard")
        h3.setStyleSheet("color: white; font-weight: bold; font-size: 12px;")
        l3_txt.addWidget(h3)
        b3 = QLabel("Revisit the 5-step interactive walkthrough for camera setup, calibration, and safety.")
        b3.setWordWrap(True)
        b3.setStyleSheet("color: rgba(255,255,255,0.65); font-size: 10px;")
        l3_txt.addWidget(b3)
        l3.addLayout(l3_txt, stretch=1)
        btn_o = QPushButton("Rerun Onboarding")
        btn_o.clicked.connect(self._launch_onboarding)
        l3.addWidget(btn_o)
        layout.addWidget(c3)

        layout.addStretch()
        return tab

    def _launch_calibration(self):
        self.accept()
        self.open_calibration_signal.emit()

    def _launch_tutorial(self):
        self.accept()
        self.open_tutorial_signal.emit()

    def _launch_onboarding(self):
        self.accept()
        self.open_onboarding_signal.emit()

    def _reset_defaults(self):
        # Reset settings
        default_s = AppSettings()
        self.chk_flip.setChecked(default_s.flip_horizontal)
        self.chk_clutch.setChecked(default_s.is_clutch_enabled)
        self.chk_swipe.setChecked(default_s.is_palm_swipe_enabled)
        self.chk_yield.setChecked(default_s.yield_to_physical_mouse)
        self.slider_sens.setValue(int(default_s.cursor_sensitivity * 10))
        self.slider_smooth.setValue(int(default_s.one_euro_beta * 1000))
        self.slider_speed.setValue(int(default_s.scroll_speed_multiplier * 10))
        self.chk_hud.setChecked(default_s.show_hud)
        self.chk_ripple.setChecked(default_s.show_click_feedback)

        # Reset thresholds
        default_p = CalibrationProfile()
        self.spin_pinch_start.setValue(default_p.pinch_start_threshold)
        self.spin_pinch_release.setValue(default_p.pinch_release_threshold)
        self.spin_copy.setValue(default_p.copy_contact_threshold)
        self.spin_paste.setValue(default_p.paste_contact_threshold)
        self.spin_drag_deadband.setValue(default_p.drag_deadband_points)
        self.spin_scroll_deadband.setValue(default_p.scroll_deadband_points)

    def _save(self):
        # Update settings
        self.settings.flip_horizontal = self.chk_flip.isChecked()
        self.settings.is_clutch_enabled = self.chk_clutch.isChecked()
        self.settings.is_palm_swipe_enabled = self.chk_swipe.isChecked()
        self.settings.yield_to_physical_mouse = self.chk_yield.isChecked()
        self.settings.cursor_sensitivity = self.slider_sens.value() / 10.0
        self.settings.one_euro_beta = self.slider_smooth.value() / 1000.0
        self.settings.scroll_speed_multiplier = self.slider_speed.value() / 10.0
        self.settings.show_hud = self.chk_hud.isChecked()
        self.settings.show_click_feedback = self.chk_ripple.isChecked()

        # Update profile thresholds
        self.profile.pinch_start_threshold = float(self.spin_pinch_start.value())
        self.profile.pinch_release_threshold = float(self.spin_pinch_release.value())
        self.profile.copy_contact_threshold = float(self.spin_copy.value())
        self.profile.copy_release_threshold = float(self.spin_copy.value()) + 0.12
        self.profile.paste_contact_threshold = float(self.spin_paste.value())
        self.profile.paste_release_threshold = float(self.spin_paste.value()) + 0.12
        self.profile.drag_deadband_points = float(self.spin_drag_deadband.value())
        self.profile.scroll_deadband_points = float(self.spin_scroll_deadband.value())

        if self.on_save:
            self.on_save(self.settings, self.profile)
        self.accept()
