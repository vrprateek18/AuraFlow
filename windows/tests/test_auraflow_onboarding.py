"""
Unit tests for AuraFlow Unified Branding, Theme, Platform Selection & Onboarding Flow:
- Design tokens and stylesheet validation
- Vector logo rendering
- Real OS detection and interactive platform selection (Windows vs macOS)
- Platform information views (Windows specs & macOS guidance)
- Diagnostic check routines
"""
import unittest
import sys
import os
import platform
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap, QPainter, QImage
from PySide6.QtCore import Qt

from auramotion_windows.core.domain.models import AppSettings, CalibrationProfile
from auramotion_windows.ui.auraflow_theme import (
    get_auraflow_stylesheet, draw_auraflow_logo,
    COLOR_BG_DARK, COLOR_PRIMARY_CYAN, COLOR_ICE_BLUE, COLOR_SURFACE
)
from auramotion_windows.ui.onboarding_flow import AuraFlowOnboardingFlow, LogoWidget

# Ensure single QApplication instance for Qt tests
_qt_app = QApplication.instance() or QApplication(sys.argv)


class TestAuraFlowOnboarding(unittest.TestCase):
    def setUp(self):
        self.settings = AppSettings()
        self.profile = CalibrationProfile()
        self.flow = AuraFlowOnboardingFlow(self.settings, self.profile)

    def tearDown(self):
        self.flow.close()

    def test_auraflow_theme_stylesheet_and_tokens(self):
        """Verify AuraFlow color tokens and generated stylesheet."""
        ss = get_auraflow_stylesheet()
        self.assertIsInstance(ss, str)
        self.assertIn("#07111F", ss)  # Midnight Navy
        self.assertIn("#20BFEA", ss)  # Primary Flow Cyan
        self.assertIn("#123149", ss)  # Deep Blue surface
        self.assertIn("QGroupBox", ss)
        self.assertIn("QPushButton", ss)

    def test_vector_logo_painter(self):
        """Verify vector logo painter renders cleanly on a QPainter canvas without errors."""
        img = QImage(128, 128, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        painter = QPainter(img)
        try:
            draw_auraflow_logo(painter, 64.0, 64.0, size=64.0, pulse_phase=1.0)
        finally:
            painter.end()

        # Image should not be empty (should have painted non-zero alpha pixels)
        has_pixels = any(img.pixelColor(x, y).alpha() > 0 for x in range(30, 90, 5) for y in range(30, 90, 5))
        self.assertTrue(has_pixels)

    def test_platform_auto_detection_and_interactive_selection(self):
        """Verify OS auto-detection and interactive manual platform switching."""
        expected_platform = "windows" if platform.system().lower() == "windows" else "macos"
        self.assertEqual(self.flow.selected_platform, expected_platform)
        self.assertEqual(self.flow.detected_os, platform.system())

        # Test user selecting macOS
        self.flow._select_platform("macos")
        self.assertEqual(self.flow.selected_platform, "macos")

        # Test user switching back to Windows
        self.flow._select_platform("windows")
        self.assertEqual(self.flow.selected_platform, "windows")

    def test_platform_info_screen_content(self):
        """Verify Windows and macOS info cards render appropriate specifications."""
        # Windows selected
        self.flow._select_platform("windows")
        self.flow._update_info_screen_content()
        self.assertEqual(self.flow.btn_info_action.text(), "Continue to Interactive Tutorial →")

        # macOS selected
        self.flow._select_platform("macos")
        self.flow._update_info_screen_content()
        # On Windows host, it should offer switching back or viewing Mac instructions
        if platform.system().lower() == "windows":
            self.assertEqual(self.flow.btn_info_action.text(), "← Switch to Windows Engine")

    def test_diagnostic_routines(self):
        """Verify live diagnostic steps for Python, dependencies, and model file."""
        # 1. Python check
        self.flow._step_check_python()
        icon, _, status = self.flow.diag_labels["python"]
        self.assertEqual(icon.text(), "✅")
        self.assertIn("Found", status.text())

        # 2. Package check
        self.flow._step_check_packages()
        icon, _, status = self.flow.diag_labels["packages"]
        self.assertEqual(icon.text(), "✅")
        self.assertIn("Installed", status.text())

        # 3. Model file check
        self.flow._step_check_model()
        icon, _, status = self.flow.diag_labels["model"]
        self.assertEqual(icon.text(), "✅")
        self.assertIn("Found", status.text())

        # 4. Input permissions check
        self.flow._step_check_permissions()
        icon, _, status = self.flow.diag_labels["permissions"]
        self.assertEqual(icon.text(), "✅")
        self.assertIn("Granted", status.text())

    def test_screen_navigation_indices(self):
        """Verify stack contains all 7 screens in correct sequence."""
        self.assertEqual(self.flow.stack.count(), 7)
        # Splash -> Welcome -> Platform Selection -> Info -> Tutorial -> Diagnostics -> Camera
        for idx in range(7):
            self.flow.stack.setCurrentIndex(idx)
            self.assertEqual(self.flow.stack.currentIndex(), idx)

    def test_tutorial_screen_gestures_and_practice(self):
        """Verify tutorial gesture carousel and interactive practice pad."""
        self.flow.stack.setCurrentIndex(4)  # Tutorial screen
        self.assertEqual(self.flow.tutorial_idx, 0)
        self.assertIn("1 of 6", self.flow.tutorial_counter_lbl.text())
        self.assertIn("Pointing", self.flow.tut_title.text())

        # Test practicing: clicking target increments trials
        initial_trials = self.flow.tutorial_trials
        self.flow.practice_target.click()
        self.assertEqual(self.flow.tutorial_trials, initial_trials + 1)
        self.assertIn("1", self.flow.tut_success_lbl.text())
        self.assertIn("recognized", self.flow.tut_hint_lbl.text().lower())

        # Test next gesture
        self.flow._next_tutorial_gesture()
        self.assertEqual(self.flow.tutorial_idx, 1)
        self.assertIn("Left Click", self.flow.tut_title.text())

        # Test previous gesture
        self.flow._prev_tutorial_gesture()
        self.assertEqual(self.flow.tutorial_idx, 0)

        # Test skip tutorial
        self.flow._skip_tutorial()
        self.assertEqual(self.flow.stack.currentIndex(), 5)  # Jumped to Diagnostics

    def test_welcome_skip_setup(self):
        """Verify Skip Setup directly marks onboarding complete and accepts dialog."""
        self.flow.settings.first_launch_completed = False
        self.flow._finish_and_launch()
        self.assertTrue(self.flow.settings.first_launch_completed)


if __name__ == "__main__":
    unittest.main()
