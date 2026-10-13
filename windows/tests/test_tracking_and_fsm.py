"""
Unit Tests for AuraMotion Windows Port
Verifies mathematical algorithms, state machine transitions, and input structures.
"""
import unittest
import math
import time

from auramotion_windows.core.domain.models import (
    Point2D, HandJoint, HandJointName, HandSample,
    GestureState, GestureCommand, FingerShortcut, PalmSwipeDirection,
    CalibrationProfile
)
from auramotion_windows.core.tracking.one_euro_filter import OneEuroFilter1D, OneEuroFilter2D
from auramotion_windows.core.tracking.fusion import HandCursorFusion
from auramotion_windows.core.tracking.confidence_gate import ConfidenceGate
from auramotion_windows.core.interaction.engagement_clutch import EngagementClutch
from auramotion_windows.core.interaction.pose_classifier import PoseClassifier
from auramotion_windows.core.interaction.pinch_detector import PinchDetector, PinchDecisionType
from auramotion_windows.core.interaction.scroll_detector import ScrollDetector, ScrollController
from auramotion_windows.core.interaction.state_machine import GestureStateMachine, GestureStateMachineListener

def create_mock_sample(thumb_x=0.38, thumb_y=0.55, index_x=0.5, index_y=0.35, wrist_x=0.5, wrist_y=0.8, conf=0.9):
    joints = {
        HandJointName.WRIST: HandJoint(HandJointName.WRIST, Point2D(wrist_x, wrist_y), conf),
        HandJointName.THUMB_CMC: HandJoint(HandJointName.THUMB_CMC, Point2D(0.45, 0.7), conf),
        HandJointName.THUMB_MCP: HandJoint(HandJointName.THUMB_MCP, Point2D(0.42, 0.6), conf),
        HandJointName.THUMB_IP: HandJoint(HandJointName.THUMB_IP, Point2D(0.45, 0.5), conf),
        HandJointName.THUMB_TIP: HandJoint(HandJointName.THUMB_TIP, Point2D(thumb_x, thumb_y), conf),
        HandJointName.INDEX_MCP: HandJoint(HandJointName.INDEX_MCP, Point2D(0.5, 0.6), conf),
        HandJointName.INDEX_PIP: HandJoint(HandJointName.INDEX_PIP, Point2D(0.5, 0.5), conf),
        HandJointName.INDEX_DIP: HandJoint(HandJointName.INDEX_DIP, Point2D(0.5, 0.45), conf),
        HandJointName.INDEX_TIP: HandJoint(HandJointName.INDEX_TIP, Point2D(index_x, index_y), conf),
        HandJointName.MIDDLE_MCP: HandJoint(HandJointName.MIDDLE_MCP, Point2D(0.55, 0.6), conf),
        HandJointName.MIDDLE_PIP: HandJoint(HandJointName.MIDDLE_PIP, Point2D(0.55, 0.55), conf),
        HandJointName.MIDDLE_DIP: HandJoint(HandJointName.MIDDLE_DIP, Point2D(0.55, 0.58), conf),
        HandJointName.MIDDLE_TIP: HandJoint(HandJointName.MIDDLE_TIP, Point2D(0.55, 0.62), conf),
        HandJointName.RING_MCP: HandJoint(HandJointName.RING_MCP, Point2D(0.6, 0.6), conf),
        HandJointName.RING_PIP: HandJoint(HandJointName.RING_PIP, Point2D(0.6, 0.62), conf),
        HandJointName.RING_DIP: HandJoint(HandJointName.RING_DIP, Point2D(0.6, 0.65), conf),
        HandJointName.RING_TIP: HandJoint(HandJointName.RING_TIP, Point2D(0.6, 0.68), conf),
        HandJointName.LITTLE_MCP: HandJoint(HandJointName.LITTLE_MCP, Point2D(0.65, 0.65), conf),
        HandJointName.LITTLE_PIP: HandJoint(HandJointName.LITTLE_PIP, Point2D(0.65, 0.68), conf),
        HandJointName.LITTLE_DIP: HandJoint(HandJointName.LITTLE_DIP, Point2D(0.65, 0.70), conf),
        HandJointName.LITTLE_TIP: HandJoint(HandJointName.LITTLE_TIP, Point2D(0.65, 0.72), conf),
    }
    return HandSample(
        host_timestamp=time.time(),
        presentation_time_seconds=time.time(),
        is_presentation_time_estimated=False,
        joints=joints,
        overall_confidence=conf,
        estimated_handedness="right",
        tracking_id=1
    )

class TestAuraMotionWindows(unittest.TestCase):

    def test_one_euro_filter_smoothing(self):
        f = OneEuroFilter1D(min_cutoff=1.0, beta=0.007)
        # Initial point
        res1 = f.filter(100.0, 1.0)
        self.assertEqual(res1, 100.0)

        # Small jitter step should be heavily smoothed
        res2 = f.filter(101.0, 1.016)
        self.assertLess(res2, 100.5)

        # Fast ballistic step should have higher cutoff (responsive)
        f.reset()
        f.filter(100.0, 1.0)
        res_fast = f.filter(200.0, 1.016)
        self.assertGreater(res_fast, 120.0)

    def test_hand_cursor_fusion(self):
        fusion = HandCursorFusion()
        sample = create_mock_sample()
        fused = fusion.update(sample)
        self.assertIsNotNone(fused)
        self.assertTrue(math.isfinite(fused.x))
        self.assertTrue(math.isfinite(fused.y))

    def test_pinch_detector_click(self):
        detector = PinchDetector(start_threshold=0.28, release_threshold=0.38)
        loc = Point2D(500, 300)

        # 1. Approach
        dec1 = detector.evaluate(normalized_distance=0.35, current_location=loc, timestamp=1.0)
        self.assertEqual(dec1.decision_type, PinchDecisionType.NONE)

        # 2. Enter pinch
        dec2 = detector.evaluate(normalized_distance=0.20, current_location=loc, timestamp=1.02)
        self.assertEqual(dec2.decision_type, PinchDecisionType.ARMED)

        # 3. Dwell 100ms and release -> Click!
        dec3 = detector.evaluate(normalized_distance=0.40, current_location=loc, timestamp=1.12)
        self.assertEqual(dec3.decision_type, PinchDecisionType.CLICK)
        self.assertEqual(dec3.anchor.x, 500)

    def test_scroll_controller_inertia(self):
        ctrl = ScrollController(is_inertia_enabled=True, friction_coefficient=0.8)
        res = ctrl.update(raw_delta_x=0.0, raw_delta_y=10.0)
        self.assertGreater(res.delta_y, 0.0)

        # Step inertia
        inertia1 = ctrl.compute_inertia_step()
        self.assertIsNotNone(inertia1)
        self.assertLess(inertia1.delta_y, res.delta_y)

    def test_state_machine_pointing_and_pause(self):
        fsm = GestureStateMachine()
        sample = create_mock_sample()
        loc = Point2D(600, 400)

        # Advance time past confidence gate reacquisition dwell (80ms) and clutch dwell (20ms)
        sample1 = create_mock_sample()
        sample1.host_timestamp = 1.0
        fsm.process_frame(sample1, loc)

        sample2 = create_mock_sample()
        sample2.host_timestamp = 1.15
        fsm.process_frame(sample2, loc)

        self.assertIn(fsm.current_state, [GestureState.IDLE, GestureState.POINTING])

        # Manual pause
        fsm.is_manual_paused = True
    def test_finger_shortcut_copy_paste(self):
        fsm = GestureStateMachine()
        sample = create_mock_sample()

        # Place middle finger tip touching thumb tip
        sample.joints[HandJointName.MIDDLE_TIP] = HandJoint(HandJointName.MIDDLE_TIP, Point2D(0.38, 0.55), 0.9)
        shortcut = fsm.shortcut_detector.evaluate(sample)
        # Advance confirmation
        sample.host_timestamp += 0.1
        shortcut = fsm.shortcut_detector.evaluate(sample)
        self.assertEqual(shortcut, FingerShortcut.COPY)

    def test_palm_swipe_left_right(self):
        from auramotion_windows.core.interaction.palm_swipe_detector import PalmSwipeDetector
        detector = PalmSwipeDetector(min_displacement=0.07, min_velocity=0.20)

        # Simulate left swipe
        sample1 = create_mock_sample()
        res1 = detector.evaluate(sample1, is_open_palm=True, timestamp=1.0)
        self.assertIsNone(res1)

        sample2 = create_mock_sample(wrist_x=0.35)
        sample2.joints[HandJointName.MIDDLE_MCP] = HandJoint(HandJointName.MIDDLE_MCP, Point2D(0.35, 0.6), 0.9)
        res2 = detector.evaluate(sample2, is_open_palm=True, timestamp=1.1)
        self.assertEqual(res2, PalmSwipeDirection.LEFT)

if __name__ == "__main__":
    unittest.main()
