import unittest
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPoint, QPointF
from auramotion_windows.ui.hud_window import FloatingHUDWindow, HandSkeletonWidget
from auramotion_windows.core.domain.models import HandSample, GestureState, HandJoint, Point2D, HandJointName

# Ensure single QApplication instance for tests
app = QApplication.instance() or QApplication(sys.argv)

class TestFloatingHUDWindow(unittest.TestCase):
    def setUp(self):
        self.hud = FloatingHUDWindow()

    def tearDown(self):
        self.hud.close()

    def test_hud_initial_state(self):
        self.assertFalse(self.hud.is_compact)
        self.assertEqual(self.hud.width(), 230)
        self.assertEqual(self.hud.cursor().shape(), Qt.CursorShape.SizeAllCursor)

    def test_hud_dragging(self):
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtCore import QEvent

        self.hud.move(500, 500)
        # Press left mouse button at HUD local coordinate (10, 10) -> global (510, 510)
        press_event = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(10, 10),
            QPointF(510, 510),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.hud.mousePressEvent(press_event)
        self.assertEqual(self.hud.cursor().shape(), Qt.CursorShape.ClosedHandCursor)

        # Move mouse to global (610, 610) -> moves HUD to (600, 600)
        move_event = QMouseEvent(
            QEvent.Type.MouseMove,
            QPointF(110, 110),
            QPointF(610, 610),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.hud.mouseMoveEvent(move_event)
        self.assertEqual(self.hud.pos(), QPoint(600, 600))

        # Release mouse
        release_event = QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            QPointF(110, 110),
            QPointF(610, 610),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier
        )
        self.hud.mouseReleaseEvent(release_event)
        self.assertEqual(self.hud.cursor().shape(), Qt.CursorShape.SizeAllCursor)

    def test_dock_cycle_corners(self):
        initial_pos = self.hud.pos()
        self.hud._cycle_dock_corner()
        pos_1 = self.hud.pos()
        self.assertNotEqual(initial_pos, pos_1)

        self.hud._cycle_dock_corner()
        pos_2 = self.hud.pos()
        self.assertNotEqual(pos_1, pos_2)

        self.hud._cycle_dock_corner()
        pos_3 = self.hud.pos()
        self.assertNotEqual(pos_2, pos_3)

        self.hud._cycle_dock_corner()
        pos_4 = self.hud.pos()
        # Should return to top-right
        self.assertEqual(pos_4, initial_pos)

    def test_compact_toggle(self):
        self.assertFalse(self.hud.is_compact)
        self.hud._toggle_compact()
        self.assertTrue(self.hud.is_compact)
        self.assertTrue(self.hud.skeleton_widget.isHidden())

        self.hud._toggle_compact()
        self.assertFalse(self.hud.is_compact)
        self.assertFalse(self.hud.skeleton_widget.isHidden())

    def test_visibility_changed_signal(self):
        signals_received = []
        self.hud.visibility_changed.connect(lambda v: signals_received.append(v))

        self.hud.hide()
        self.hud.show()

        self.assertEqual(signals_received, [False, True])

    def test_telemetry_update(self):
        joints = {
            HandJointName.WRIST: HandJoint(HandJointName.WRIST, Point2D(0.5, 0.5), 0.95),
            HandJointName.INDEX_TIP: HandJoint(HandJointName.INDEX_TIP, Point2D(0.6, 0.3), 0.98),
            HandJointName.THUMB_TIP: HandJoint(HandJointName.THUMB_TIP, Point2D(0.4, 0.4), 0.92)
        }
        sample = HandSample(
            host_timestamp=100.0,
            presentation_time_seconds=100.0,
            is_presentation_time_estimated=False,
            joints=joints,
            overall_confidence=0.95,
            estimated_handedness="right",
            tracking_id=1
        )
        self.hud.update_telemetry(
            state=GestureState.POINTING,
            sample=sample,
            cap_fps=60.0,
            inf_fps=59.5,
            p95_ms=12.4,
            dropped=1
        )
        self.assertEqual(self.hud.status_pill.text(), "POINTING")
        self.assertIn("12.4", self.hud.latency_lbl.text())
        self.assertIn("60", self.hud.cap_lbl.text())
        self.assertIn("DROP 1", self.hud.drop_lbl.text())

if __name__ == '__main__':
    unittest.main()
