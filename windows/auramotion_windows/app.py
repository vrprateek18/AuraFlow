"""
AuraMotion Pro for Windows - Main Application Coordinator
Integrates Vision Capture, Tracking, State Machine, Win32 Input, and Desktop GUI.
"""
import sys
import os
import time
from typing import Optional
import cv2

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

from .core.domain.models import (
    Point2D, GestureState, GestureCommand, FingerShortcut,
    PalmSwipeDirection, HandSample, AppSettings, CalibrationProfile
)
from .core.capture.pipeline import CameraCapturePipeline, enumerate_available_cameras
from .core.vision.inference import VisionInferenceWorker
from collections import deque
from .core.monitoring.system_perf import SystemPerformanceMonitor
from .core.tracking.one_euro_filter import OneEuroFilter2D
from .core.tracking.fusion import HandCursorFusion
from .core.interaction.state_machine import GestureStateMachine, GestureStateMachineListener
from .core.output.win32_input import Win32EventSynthesizer
from .core.output.arbitrator import PhysicalInputArbitrator
from .core.output.hotkey import GlobalEmergencyHotkey
from .core.config.settings_manager import SettingsManager

from .ui.main_window import AuraMotionMainWindow
from .ui.hud_window import FloatingHUDWindow
from .ui.click_feedback import ClickFeedbackOverlay
from .ui.command_menu_window import CommandMenuWindow
from .ui.tray import TrayController
from .ui.settings_dialog import SettingsDialog
from .ui.calibration_dialog import GuidedCalibrationDialog
from .ui.tutorial_dialog import GestureTutorialDialog
from .ui.onboarding_wizard import OnboardingWizard
from .ui.onboarding_flow import AuraFlowOnboardingFlow
from .ui.benchmark_dialog import BenchmarkDialog

class AuraMotionApp(QObject, GestureStateMachineListener):
    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.settings_manager = SettingsManager()
        self.settings, self.profile = self.settings_manager.load()
        self.active_dialog = None
        self.available_cameras = []

        # Hardware Performance Telemetry
        self.perf_monitor = SystemPerformanceMonitor()
        self.e2e_latencies = deque(maxlen=60)
        self.last_perf_sample_time = 0.0
        self.cached_perf = self.perf_monitor.sample()

        # Output & Windows input
        self.synthesizer = Win32EventSynthesizer()

        # Tracking & Interaction
        self.fusion = HandCursorFusion()
        self.cursor_filter = OneEuroFilter2D(
            min_cutoff=self.settings.one_euro_min_cutoff,
            beta=self.settings.one_euro_beta,
            d_cutoff=self.settings.one_euro_d_cutoff
        )
        self.fsm = GestureStateMachine(listener=self)
        self.fsm.update_calibration(self.profile)

        # Arbitrator (yields when real mouse is clicked)
        self.arbitrator = PhysicalInputArbitrator(
            on_physical_input=self._on_physical_mouse_detected,
            cooldown_seconds=1.2
        )

        # UI Components
        self.main_window = AuraMotionMainWindow(self.settings, self.profile)
        self.hud = FloatingHUDWindow()
        self.feedback = ClickFeedbackOverlay()
        self.menu_window = CommandMenuWindow()
        self.tray = TrayController()

        # Connect MainWindow controls
        self.main_window.emergency_stop_signal.connect(self._toggle_emergency_pause)
        self.main_window.switch_camera_signal.connect(self._on_switch_camera)
        self.main_window.switch_resolution_signal.connect(self._on_switch_resolution)
        self.main_window.open_benchmark_signal.connect(self._open_benchmark)
        self.main_window.reconnect_camera_signal.connect(self._on_reconnect_camera)
        self.main_window.test_click_signal.connect(self._test_click_ripple)
        self.main_window.test_command_menu_signal.connect(self._test_command_menu)
        self.main_window.chk_hud.toggled.connect(self._toggle_hud)
        self.main_window.chk_multimon.toggled.connect(self._toggle_multimon)
        self.main_window.chk_ripple.toggled.connect(self._toggle_ripple)
        self.main_window.chk_mirror.toggled.connect(self._toggle_mirror)
        self.main_window.chk_yield.toggled.connect(self._toggle_yield)
        self.main_window.slider_sens.valueChanged.connect(self._on_sens_changed)
        self.main_window.slider_smooth.valueChanged.connect(self._on_smooth_changed)
        self.main_window.slider_scroll.valueChanged.connect(self._on_scroll_speed_changed)
        self.main_window.open_settings_signal.connect(self._open_settings)
        self.main_window.open_calibration_signal.connect(self._open_calibration)
        self.main_window.open_tutorial_signal.connect(self._open_tutorial)
        self.main_window.open_onboarding_signal.connect(self._open_onboarding)

        # Connect HUD signals
        self.hud.visibility_changed.connect(self._on_hud_visibility_changed)

        # Connect Tray signals
        self.tray.open_control_center_signal.connect(self._show_main_window)
        self.tray.toggle_pause_signal.connect(self._set_paused)
        self.tray.toggle_hud_signal.connect(self._toggle_hud)
        self.tray.open_settings_signal.connect(self._open_settings)
        self.tray.open_calibration_signal.connect(self._open_calibration)
        self.tray.open_tutorial_signal.connect(self._open_tutorial)
        self.tray.open_onboarding_signal.connect(self._open_onboarding)
        self.tray.quit_signal.connect(self._quit_app)

        # Connect application exit signal for clean release
        self.app.aboutToQuit.connect(self._on_app_exit)

        # Global Emergency Keyboard Hotkey (F8 & Ctrl+Alt+P)
        self.hotkey = GlobalEmergencyHotkey(on_toggle=self._toggle_emergency_pause, parent=self)

        # Capture & Inference
        model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "hand_landmarker.task")
        if not os.path.exists(model_path):
            model_path = "hand_landmarker.task"

        self.inference_worker = VisionInferenceWorker(model_path=model_path, flip_horizontal=self.settings.flip_horizontal)
        self.pipeline = CameraCapturePipeline(camera_index=self.settings.camera_index, target_fps=60)

        # Safety watchdog tracking timestamp
        self.last_valid_sample_time = time.time()

        # Main processing timer (~60 Hz)
        self.loop_timer = QTimer(self)
        self.loop_timer.setInterval(16)
        self.loop_timer.timeout.connect(self._process_frame_tick)

        self.last_cursor_point: Optional[Point2D] = None

    def start(self):
        # Register system-wide emergency hotkey
        self.hotkey.start()

        # Enumerate and populate connected cameras in UI
        self.available_cameras = enumerate_available_cameras()
        self.main_window.populate_camera_list(self.available_cameras, self.settings.camera_index)

        # Start arbitrator
        if self.settings.yield_to_physical_mouse:
            self.arbitrator.start()

        # Initialize vision worker
        if not self.inference_worker.initialize():
            print("Warning: Vision inference worker failed to initialize.")

        # Start capture pipeline with configured resolution
        if self.settings.camera_width > 0 and self.settings.camera_height > 0:
            self.pipeline.set_resolution(self.settings.camera_width, self.settings.camera_height)
        self.pipeline.start()

        # Show Desktop UI
        self.main_window.show()
        if self.settings.show_hud:
            self.hud.show()
        if self.settings.show_click_feedback:
            self.feedback.show()
        self.tray.show()

        # Start processing loop
        self.loop_timer.start()

        # First-launch onboarding check
        if not self.settings.first_launch_completed:
            QTimer.singleShot(400, self._open_onboarding)

    def _process_frame_tick(self):
        # ── SAFETY WATCHDOG: Automatically release held mouse buttons if tracking disappears ──
        if self.synthesizer.is_left_down:
            if (time.time() - self.last_valid_sample_time) > 0.18:
                self.on_emergency_release()

        frame, timestamp, has_new = self.pipeline.get_latest_frame()

        if not has_new or frame is None:
            # If camera is disconnected, force emergency release immediately
            if not self.pipeline.is_connected:
                self.on_emergency_release()
                _, dropped = self.pipeline.mailbox.stats
                self.main_window.update_telemetry(
                    state=GestureState.TRACKING_LOST,
                    frame=None,
                    sample=None,
                    cap_fps=0.0,
                    inf_fps=0.0,
                    p95_ms=0.0,
                    is_connected=False,
                    error_msg=self.pipeline.last_error,
                    e2e_ms=0.0,
                    dropped_frames=dropped,
                    cpu_pct=self.cached_perf.cpu_percent,
                    gpu_pct=self.cached_perf.gpu_percent,
                    gpu_name=self.cached_perf.gpu_name
                )
            return

        # End-to-end latency measurement from hardware capture timestamp to current loop tick
        now = time.time()
        curr_e2e_ms = max(0.0, (now - timestamp) * 1000.0)
        self.e2e_latencies.append(curr_e2e_ms)
        avg_e2e = sum(self.e2e_latencies) / len(self.e2e_latencies)

        # Sample CPU/GPU hardware utilization every 500ms
        if now - self.last_perf_sample_time >= 0.5:
            self.cached_perf = self.perf_monitor.sample()
            self.last_perf_sample_time = now

        # Run inference on live camera frame
        sample = self.inference_worker.process_frame(frame, timestamp)
        if sample is not None:
            self.last_valid_sample_time = time.time()

        mapped_screen_pt: Optional[Point2D] = None
        if sample is not None:
            is_pinch_or_two_finger = (
                self.fsm.current_state in (GestureState.PINCH_ARMED, GestureState.DRAGGING, GestureState.SCROLLING)
            )
            fused_point = self.fusion.update(sample, is_pinch_or_two_finger=is_pinch_or_two_finger)

            if fused_point is not None:
                # Filter point
                smooth_norm = self.cursor_filter.filter(fused_point, timestamp)

                # Active margin easing scaled by cursor_sensitivity
                active_margin = max(0.02, 0.12 / max(0.2, self.settings.cursor_sensitivity))
                u = max(0.0, min(1.0, (smooth_norm.x - active_margin) / max(0.01, 1.0 - 2.0 * active_margin)))
                v = max(0.0, min(1.0, (smooth_norm.y - active_margin) / max(0.01, 1.0 - 2.0 * active_margin)))

                if self.settings.span_multi_monitors and self.synthesizer.num_monitors > 1:
                    # Multi-monitor virtual desktop spanning
                    mapped_screen_pt = Point2D(
                        x=float(self.synthesizer.vx) + u * float(self.synthesizer.vw),
                        y=float(self.synthesizer.vy) + v * float(self.synthesizer.vh)
                    )
                else:
                    # Primary screen mapping
                    screen_w = float(self.synthesizer.screen_width)
                    screen_h = float(self.synthesizer.screen_height)
                    mapped_screen_pt = Point2D(x=u * screen_w, y=v * screen_h)

                self.last_cursor_point = mapped_screen_pt

        # Check physical arbitration and user toggle
        is_injection_allowed = self.main_window.chk_enable_gesture.isChecked()
        if self.settings.yield_to_physical_mouse and self.arbitrator.is_yielding:
            is_injection_allowed = False

        # Feed to State Machine
        self.fsm.process_frame(
            sample=sample,
            mapped_cursor_location=mapped_screen_pt,
            is_injection_allowed=is_injection_allowed
        )

        # Update Command Menu UI
        if self.fsm.command_menu.is_open:
            self.menu_window.update_snapshot(self.fsm.command_menu.snapshot)
        else:
            self.menu_window.update_snapshot(None)

        # Update HUD Telemetry
        _, dropped = self.pipeline.mailbox.stats
        self.hud.update_telemetry(
            state=self.fsm.current_state,
            sample=sample,
            cap_fps=self.pipeline.actual_fps,
            inf_fps=self.inference_worker.inference_fps,
            p95_ms=self.inference_worker.p95_latency_ms,
            dropped=dropped,
            e2e_ms=avg_e2e,
            cpu_pct=self.cached_perf.cpu_percent,
            gpu_pct=self.cached_perf.gpu_percent
        )

        # Update Main Desktop Window Preview (align flip with landmarks)
        preview_frame = cv2.flip(frame, 1) if self.settings.flip_horizontal else frame
        self.main_window.update_telemetry(
            state=self.fsm.current_state,
            frame=preview_frame,
            sample=sample,
            cap_fps=self.pipeline.actual_fps,
            inf_fps=self.inference_worker.inference_fps,
            p95_ms=self.inference_worker.p95_latency_ms,
            is_connected=self.pipeline.is_connected,
            error_msg=self.pipeline.last_error,
            e2e_ms=avg_e2e,
            dropped_frames=dropped,
            cpu_pct=self.cached_perf.cpu_percent,
            gpu_pct=self.cached_perf.gpu_percent,
            gpu_name=self.cached_perf.gpu_name
        )

        # Update any active modal dialog (Calibration, Tutorial, or Onboarding Wizard)
        if self.active_dialog is not None and hasattr(self.active_dialog, "update_frame"):
            try:
                self.active_dialog.update_frame(preview_frame, sample, self.fsm.current_state)
            except Exception:
                pass

    # ── Gesture State Machine Listener Callbacks ──
    def on_transition(self, state: GestureState):
        pass

    def on_move(self, location: Point2D):
        self.synthesizer.move_to(location.x, location.y, span_virtual_desktop=self.settings.span_multi_monitors)

    def on_click(self, anchor: Point2D):
        self.synthesizer.click(anchor.x, anchor.y, span_virtual_desktop=self.settings.span_multi_monitors)
        if self.settings.show_click_feedback:
            self.feedback.trigger_click(anchor.x, anchor.y)

    def on_drag_start(self, anchor: Point2D):
        self.synthesizer.move_to(anchor.x, anchor.y, span_virtual_desktop=self.settings.span_multi_monitors)
        self.synthesizer.mouse_down()
        if self.settings.show_click_feedback:
            self.feedback.update_drag(current=anchor, anchor=anchor)

    def on_drag_move(self, location: Point2D):
        self.synthesizer.move_to(location.x, location.y, span_virtual_desktop=self.settings.span_multi_monitors)
        if self.settings.show_click_feedback:
            self.feedback.update_drag(current=location)

    def on_drag_end(self, location: Optional[Point2D]):
        self.synthesizer.mouse_up()
        if self.settings.show_click_feedback:
            self.feedback.update_drag(current=None, anchor=None)

    def on_scroll(self, delta):
        scaled_dx = delta.delta_x * self.settings.scroll_speed_multiplier
        scaled_dy = delta.delta_y * self.settings.scroll_speed_multiplier
        self.synthesizer.scroll(scaled_dx, scaled_dy)

    def on_swipe(self, direction: PalmSwipeDirection):
        self.synthesizer.post_swipe(direction)

    def on_shortcut(self, shortcut: FingerShortcut):
        self.synthesizer.post_shortcut(shortcut)

    def on_command(self, command: GestureCommand, target: Point2D):
        self.synthesizer.post_command(command, target)

    def on_emergency_release(self):
        self.synthesizer.trigger_emergency_release()
        if self.settings.show_click_feedback:
            self.feedback.update_drag(current=None, anchor=None)

    # ── User Interface Handlers ──
    def _show_main_window(self):
        self.main_window.show()
        self.main_window.activateWindow()

    def _on_reconnect_camera(self, camera_index: int):
        self.on_emergency_release()
        self.settings.camera_index = camera_index
        self.pipeline.reconnect()

    def _on_switch_camera(self, camera_index: int):
        self.on_emergency_release()
        self.settings.camera_index = camera_index
        self.pipeline.switch_device(camera_index)

    def _on_switch_resolution(self, width: int, height: int):
        self.settings.camera_width = width
        self.settings.camera_height = height
        self.pipeline.set_resolution(width, height)
        self.settings_manager.save(self.settings, self.profile)

    def _open_benchmark(self):
        dlg = BenchmarkDialog(parent=self.main_window)
        dlg.exec()

    def _toggle_multimon(self, enabled: bool):
        self.settings.span_multi_monitors = enabled
        self.settings_manager.save(self.settings, self.profile)

    def _test_click_ripple(self):
        screen_w = self.synthesizer.screen_width
        screen_h = self.synthesizer.screen_height
        self.feedback.show()
        self.feedback.trigger_click(screen_w / 2, screen_h / 2)

    def _test_command_menu(self):
        from .core.interaction.command_menu import CommandMenuSnapshot
        screen_w = self.synthesizer.screen_width
        screen_h = self.synthesizer.screen_height
        snap = CommandMenuSnapshot(
            selected=GestureCommand.RIGHT_CLICK,
            pointer=Point2D(0.5, 0.5),
            target=Point2D(screen_w / 2, screen_h / 2),
            awaiting_pointer=False
        )
        self.menu_window.update_snapshot(snap)

    def _on_physical_mouse_detected(self):
        self.on_emergency_release()

    def _toggle_emergency_pause(self):
        new_paused = not self.fsm.is_manual_paused
        self._set_paused(new_paused)

    def _set_paused(self, paused: bool):
        self.fsm.is_manual_paused = paused
        if paused:
            self.on_emergency_release()
        self.main_window.set_paused_ui(paused)
        self.tray.act_pause.blockSignals(True)
        self.tray.act_pause.setChecked(paused)
        self.tray.act_pause.blockSignals(False)

    def _toggle_hud(self, visible: bool):
        self.settings.show_hud = visible
        if visible:
            self.hud.show()
        else:
            self.hud.hide()
        self.main_window.chk_hud.blockSignals(True)
        self.main_window.chk_hud.setChecked(visible)
        self.main_window.chk_hud.blockSignals(False)
        self.settings_manager.save(self.settings, self.profile)

    def _on_hud_visibility_changed(self, visible: bool):
        self.settings.show_hud = visible
        self.main_window.chk_hud.blockSignals(True)
        self.main_window.chk_hud.setChecked(visible)
        self.main_window.chk_hud.blockSignals(False)
        self.settings_manager.save(self.settings, self.profile)

    def _toggle_ripple(self, visible: bool):
        self.settings.show_click_feedback = visible
        if visible:
            self.feedback.show()
        else:
            self.feedback.hide()
        self.settings_manager.save(self.settings, self.profile)

    def _toggle_mirror(self, mirrored: bool):
        self.settings.flip_horizontal = mirrored
        self.inference_worker.flip_horizontal = mirrored
        self.settings_manager.save(self.settings, self.profile)

    def _toggle_yield(self, yield_enabled: bool):
        self.settings.yield_to_physical_mouse = yield_enabled
        self.settings_manager.save(self.settings, self.profile)

    def _on_sens_changed(self, val: int):
        sens = val / 10.0
        self.settings.cursor_sensitivity = sens
        self.settings_manager.save(self.settings, self.profile)

    def _on_smooth_changed(self, val: int):
        beta = val / 1000.0
        self.settings.one_euro_beta = beta
        self.cursor_filter.beta = beta
        self.settings_manager.save(self.settings, self.profile)

    def _on_scroll_speed_changed(self, val: int):
        self.settings.scroll_speed_multiplier = val / 10.0
        self.settings_manager.save(self.settings, self.profile)

    def _open_settings(self):
        dlg = SettingsDialog(self.settings, self.profile, on_save=self._on_settings_saved, parent=self.main_window)
        dlg.open_calibration_signal.connect(self._open_calibration)
        dlg.open_tutorial_signal.connect(self._open_tutorial)
        dlg.open_onboarding_signal.connect(self._open_onboarding)
        dlg.exec()

    def _open_calibration(self):
        dlg = GuidedCalibrationDialog(self.profile, parent=self.main_window)
        dlg.calibration_saved.connect(self._on_calibration_saved)
        self.active_dialog = dlg
        try:
            dlg.exec()
        finally:
            self.active_dialog = None

    def _open_tutorial(self):
        dlg = GestureTutorialDialog(parent=self.main_window)
        self.active_dialog = dlg
        try:
            dlg.exec()
        finally:
            self.active_dialog = None

    def _open_onboarding(self):
        dlg = AuraFlowOnboardingFlow(self.settings, self.profile, parent=self.main_window)
        dlg.flow_completed.connect(self._on_onboarding_completed)
        self.active_dialog = dlg
        try:
            dlg.exec()
        finally:
            self.active_dialog = None

    def _on_settings_saved(self, new_settings: AppSettings, new_profile: CalibrationProfile):
        self.settings = new_settings
        self.profile = new_profile
        self.cursor_filter.beta = self.settings.one_euro_beta
        self.inference_worker.flip_horizontal = self.settings.flip_horizontal
        self.fsm.update_calibration(self.profile)
        self.settings_manager.save(self.settings, self.profile)

        # Sync main window UI controls
        self.main_window.chk_hud.blockSignals(True)
        self.main_window.chk_hud.setChecked(self.settings.show_hud)
        self.main_window.chk_hud.blockSignals(False)

        self.main_window.chk_ripple.blockSignals(True)
        self.main_window.chk_ripple.setChecked(self.settings.show_click_feedback)
        self.main_window.chk_ripple.blockSignals(False)

        self.main_window.chk_mirror.blockSignals(True)
        self.main_window.chk_mirror.setChecked(self.settings.flip_horizontal)
        self.main_window.chk_mirror.blockSignals(False)

        self.main_window.chk_multimon.blockSignals(True)
        self.main_window.chk_multimon.setChecked(self.settings.span_multi_monitors)
        self.main_window.chk_multimon.blockSignals(False)

        self.main_window.chk_yield.blockSignals(True)
        self.main_window.chk_yield.setChecked(self.settings.yield_to_physical_mouse)
        self.main_window.chk_yield.blockSignals(False)

        self.main_window.slider_sens.setValue(int(self.settings.cursor_sensitivity * 10))
        self.main_window.slider_smooth.setValue(int(self.settings.one_euro_beta * 1000))
        self.main_window.slider_scroll.setValue(int(self.settings.scroll_speed_multiplier * 10))

    def _on_calibration_saved(self, new_profile: CalibrationProfile):
        self.profile = new_profile
        self.fsm.update_calibration(self.profile)
        self.settings_manager.save(self.settings, self.profile)

    def _on_onboarding_completed(self, new_settings: AppSettings, new_profile: CalibrationProfile):
        self.settings = new_settings
        self.profile = new_profile
        self.settings.first_launch_completed = True
        self.fsm.update_calibration(self.profile)
        self.settings_manager.save(self.settings, self.profile)

    def _on_app_exit(self):
        self.on_emergency_release()
        self.loop_timer.stop()
        self.hotkey.stop()
        self.pipeline.stop()
        self.inference_worker.close()
        self.arbitrator.stop()
        self.perf_monitor.close()

    def _quit_app(self):
        self._on_app_exit()
        self.app.quit()


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    auramotion = AuraMotionApp(app)
    auramotion.start()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
