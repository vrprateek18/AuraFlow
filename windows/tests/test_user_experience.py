"""
Unit tests for AuraMotion Pro User Experience Suite:
- First-launch Onboarding Wizard
- Guided Hand Calibration with Live Preview
- Persistent Settings for Sensitivity, Smoothing, Scroll Speed, and Gesture Thresholds
- Gesture Tutorial with Practice Mode & Recognition Diagnostics
"""
import unittest
import sys
import os
import tempfile
import numpy as np

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from auramotion_windows.core.config.settings_manager import SettingsManager
from auramotion_windows.core.domain.models import (
    AppSettings, CalibrationProfile, HandSample, GestureState, HandJoint, Point2D, HandJointName
)
from auramotion_windows.ui.calibration_dialog import GuidedCalibrationDialog
from auramotion_windows.ui.tutorial_dialog import GestureTutorialDialog, GESTURES_LIST
from auramotion_windows.ui.onboarding_wizard import OnboardingWizard
from auramotion_windows.ui.settings_dialog import SettingsDialog

app = QApplication.instance() or QApplication(sys.argv)


def create_mock_hand_sample(thumb_index_dist: float = 0.05, scale: float = 0.20, confidence: float = 0.95, touch_shortcut: bool = False) -> HandSample:
    thumb_x = 0.5 - thumb_index_dist
    ring_x = thumb_x + 0.03 if touch_shortcut else 0.6
    ring_y = 0.3 if touch_shortcut else 0.35
    joints = {
        HandJointName.WRIST: HandJoint(HandJointName.WRIST, Point2D(0.5, 0.7), confidence),
        HandJointName.MIDDLE_MCP: HandJoint(HandJointName.MIDDLE_MCP, Point2D(0.5, 0.7 - scale), confidence),
        HandJointName.INDEX_TIP: HandJoint(HandJointName.INDEX_TIP, Point2D(0.5, 0.3), confidence),
        HandJointName.THUMB_TIP: HandJoint(HandJointName.THUMB_TIP, Point2D(thumb_x, 0.3), confidence),
        HandJointName.RING_TIP: HandJoint(HandJointName.RING_TIP, Point2D(ring_x, ring_y), confidence),
        HandJointName.LITTLE_TIP: HandJoint(HandJointName.LITTLE_TIP, Point2D(0.65, 0.4), confidence),
    }
    time_now = 100.0
    return HandSample(
        host_timestamp=time_now,
        presentation_time_seconds=time_now,
        is_presentation_time_estimated=False,
        joints=joints,
        overall_confidence=confidence,
        estimated_handedness="right",
        tracking_id=1
    )


class TestSettingsPersistence(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()
        self.mgr = SettingsManager(self.temp_file.name)

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_save_and_load_roundtrip(self):
        s = AppSettings(
            first_launch_completed=True,
            camera_index=1,
            flip_horizontal=False,
            cursor_sensitivity=1.75,
            one_euro_beta=0.015,
            scroll_speed_multiplier=2.4,
            is_clutch_enabled=False,
            show_hud=False
        )
        p = CalibrationProfile(
            pinch_start_threshold=0.22,
            pinch_release_threshold=0.34,
            copy_contact_threshold=0.25,
            paste_contact_threshold=0.26,
            drag_deadband_points=15.0,
            scroll_deadband_points=6.0,
            hand_scale_reference=0.19,
            is_calibrated=True,
            calibrated_at="2026-10-12 16:00:00"
        )
        self.assertTrue(self.mgr.save(s, p))

        loaded_s, loaded_p = self.mgr.load()
        self.assertTrue(loaded_s.first_launch_completed)
        self.assertEqual(loaded_s.camera_index, 1)
        self.assertFalse(loaded_s.flip_horizontal)
        self.assertAlmostEqual(loaded_s.cursor_sensitivity, 1.75)
        self.assertAlmostEqual(loaded_s.one_euro_beta, 0.015)
        self.assertAlmostEqual(loaded_s.scroll_speed_multiplier, 2.4)
        self.assertFalse(loaded_s.is_clutch_enabled)
        self.assertFalse(loaded_s.show_hud)

        self.assertAlmostEqual(loaded_p.pinch_start_threshold, 0.22)
        self.assertAlmostEqual(loaded_p.pinch_release_threshold, 0.34)
        self.assertAlmostEqual(loaded_p.copy_contact_threshold, 0.25)
        self.assertAlmostEqual(loaded_p.paste_contact_threshold, 0.26)
        self.assertAlmostEqual(loaded_p.drag_deadband_points, 15.0)
        self.assertAlmostEqual(loaded_p.scroll_deadband_points, 6.0)
        self.assertAlmostEqual(loaded_p.hand_scale_reference, 0.19)
        self.assertTrue(loaded_p.is_calibrated)
        self.assertEqual(loaded_p.calibrated_at, "2026-10-12 16:00:00")


class TestGuidedHandCalibration(unittest.TestCase):
    def setUp(self):
        self.profile = CalibrationProfile()
        self.dlg = GuidedCalibrationDialog(self.profile)

    def tearDown(self):
        self.dlg.close()

    def test_step_progression_and_save(self):
        self.assertEqual(self.dlg.current_step, 1)

        # Feed step 1 samples (neutral span)
        mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        sample = create_mock_hand_sample(scale=0.20)
        for _ in range(35):
            self.dlg.update_frame(mock_frame, sample, GestureState.IDLE)

        # Should auto-advance to step 2 (pinch)
        self.assertEqual(self.dlg.current_step, 2)
        self.assertAlmostEqual(self.dlg.calibrated_scale, 0.20, places=2)

        # Feed step 2 samples (tight pinch)
        pinch_sample = create_mock_hand_sample(thumb_index_dist=0.03, scale=0.20)
        for _ in range(25):
            self.dlg.update_frame(mock_frame, pinch_sample, GestureState.PINCH_ARMED)

        # Should auto-advance to step 3 (shortcuts)
        self.assertEqual(self.dlg.current_step, 3)

        # Feed step 3 samples
        shortcut_sample = create_mock_hand_sample(thumb_index_dist=0.03, scale=0.20, touch_shortcut=True)
        for _ in range(20):
            self.dlg.update_frame(mock_frame, shortcut_sample, GestureState.IDLE)

        # Should reach step 4 (summary)
        self.assertEqual(self.dlg.current_step, 4)
        self.assertTrue(not self.dlg.btn_save.isHidden())

        # Test save signal
        saved_profiles = []
        self.dlg.calibration_saved.connect(lambda p: saved_profiles.append(p))
        self.dlg._save_calibration()

        self.assertEqual(len(saved_profiles), 1)
        self.assertTrue(saved_profiles[0].is_calibrated)
        self.assertAlmostEqual(saved_profiles[0].hand_scale_reference, 0.20, places=2)


class TestGestureTutorialDialog(unittest.TestCase):
    def setUp(self):
        self.dlg = GestureTutorialDialog()

    def tearDown(self):
        self.dlg.close()

    def test_gesture_navigation(self):
        self.assertEqual(self.dlg.current_idx, 0)
        self.assertEqual(self.dlg.title_lbl.text(), GESTURES_LIST[0]["title"])

        self.dlg._next_gesture()
        self.assertEqual(self.dlg.current_idx, 1)
        self.assertEqual(self.dlg.title_lbl.text(), GESTURES_LIST[1]["title"])

        self.dlg._prev_gesture()
        self.assertEqual(self.dlg.current_idx, 0)

    def test_diagnostic_feedback_no_hand(self):
        mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.dlg.update_frame(mock_frame, None, GestureState.IDLE)
        self.assertIn("No hand detected", self.dlg.feedback_lbl.text())

    def test_diagnostic_feedback_pinch_gap(self):
        # Select Left Click gesture (index 1)
        self.dlg._on_gesture_selected(1)
        mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        wide_sample = create_mock_hand_sample(thumb_index_dist=0.15, scale=0.20)  # gap ratio ~0.75 > 0.40
        self.dlg.update_frame(mock_frame, wide_sample, GestureState.POINTING)
        self.assertIn("Thumb and index apart", self.dlg.feedback_lbl.text())


class TestOnboardingWizard(unittest.TestCase):
    def setUp(self):
        self.settings = AppSettings()
        self.profile = CalibrationProfile()
        self.wiz = OnboardingWizard(self.settings, self.profile)

    def tearDown(self):
        self.wiz.close()

    def test_page_navigation_and_completion(self):
        self.assertEqual(self.wiz.stack.currentIndex(), 0)

        # Next to page 2 (camera)
        self.wiz._go_next()
        self.assertEqual(self.wiz.stack.currentIndex(), 1)

        # Next to page 3 (calibration)
        self.wiz._go_next()
        self.assertEqual(self.wiz.stack.currentIndex(), 2)

        # Next to page 4 (tutorial)
        self.wiz._go_next()
        self.assertEqual(self.wiz.stack.currentIndex(), 3)

        # Next to page 5 (safety)
        self.wiz._go_next()
        self.assertEqual(self.wiz.stack.currentIndex(), 4)
        self.assertEqual(self.wiz.btn_next.text(), "Finish & Start AuraFlow ✨")

        # Finish
        completed = []
        self.wiz.onboarding_completed.connect(lambda s, p: completed.append((s, p)))
        self.wiz._go_next()

        self.assertEqual(len(completed), 1)
        self.assertTrue(completed[0][0].first_launch_completed)


if __name__ == '__main__':
    unittest.main()
