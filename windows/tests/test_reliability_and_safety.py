"""
Unit tests for AuraMotion Pro Reliability and Safety Features:
- Auto-release of held mouse buttons on tracking loss
- Emergency stop and pause
- Anti-repetition shortcut cooldown
- Accidental click velocity gating
- Click vs drag exclusivity
"""
import unittest
import time
from typing import Optional
from auramotion_windows.core.domain.models import (
    Point2D, GestureState, HandSample, HandJoint, HandJointName,
    FingerShortcut, CalibrationProfile
)
from auramotion_windows.core.interaction.pinch_detector import PinchDetector, PinchDecisionType
from auramotion_windows.core.interaction.finger_shortcut_detector import FingerShortcutDetector
from auramotion_windows.core.interaction.state_machine import GestureStateMachine, GestureStateMachineListener
from auramotion_windows.core.output.win32_input import Win32EventSynthesizer


class MockStateMachineListener(GestureStateMachineListener):
    def __init__(self):
        self.transitions = []
        self.clicks = []
        self.drag_starts = []
        self.drag_ends = []
        self.shortcuts = []
        self.emergency_releases = 0

    def on_transition(self, state: GestureState):
        self.transitions.append(state)

    def on_move(self, location: Point2D):
        pass

    def on_click(self, anchor: Point2D):
        self.clicks.append(anchor)

    def on_drag_start(self, anchor: Point2D):
        self.drag_starts.append(anchor)

    def on_drag_move(self, location: Point2D):
        pass

    def on_drag_end(self, location: Optional[Point2D]):
        self.drag_ends.append(location)

    def on_scroll(self, delta):
        pass

    def on_swipe(self, direction):
        pass

    def on_shortcut(self, shortcut: FingerShortcut):
        self.shortcuts.append(shortcut)

    def on_command(self, command, target: Point2D):
        pass

    def on_emergency_release(self):
        self.emergency_releases += 1


class TestReliabilityAndSafety(unittest.TestCase):
    def test_emergency_release_synthesizer(self):
        synth = Win32EventSynthesizer()
        synth.is_left_down = True
        synth.trigger_emergency_release()
        self.assertFalse(synth.is_left_down, "is_left_down should be False after emergency release")

    def test_auto_release_on_tracking_loss(self):
        listener = MockStateMachineListener()
        fsm = GestureStateMachine(listener=listener)

        # Send None sample to simulate tracking disappearance
        fsm.process_frame(sample=None, mapped_cursor_location=None)
        self.assertEqual(fsm.current_state, GestureState.TRACKING_LOST)
        self.assertGreater(listener.emergency_releases, 0, "Emergency release must trigger on tracking loss")

    def test_velocity_gating_prevents_accidental_clicks(self):
        detector = PinchDetector(max_pinch_entry_speed=600.0)

        # Move fast from (100, 100) to (500, 500) in 0.05 seconds (speed = 5656 px/s)
        t0 = 1.00
        p0 = Point2D(100.0, 100.0)
        dec0 = detector.evaluate(normalized_distance=0.50, current_location=p0, timestamp=t0)
        self.assertEqual(dec0.decision_type, PinchDecisionType.NONE)

        t1 = 1.05
        p1 = Point2D(500.0, 500.0)
        # Even with pinch distance below start_threshold (0.20), speed is too high!
        dec1 = detector.evaluate(normalized_distance=0.20, current_location=p1, timestamp=t1)
        self.assertEqual(dec1.decision_type, PinchDecisionType.NONE, "Fast hand sweep must NOT trigger pinch entry")
        self.assertFalse(detector.is_pinching)

    def test_click_prevents_unintended_drag(self):
        detector = PinchDetector(dwell_threshold_seconds=0.35, drag_deadband_points=32.0)

        t = 1.00
        p = Point2D(200.0, 200.0)
        # Enter pinch
        dec0 = detector.evaluate(normalized_distance=0.20, current_location=p, timestamp=t)
        self.assertEqual(dec0.decision_type, PinchDecisionType.ARMED)

        # Dwell 0.10s -> Click emitted
        t = 1.10
        dec1 = detector.evaluate(normalized_distance=0.20, current_location=p, timestamp=t)
        self.assertEqual(dec1.decision_type, PinchDecisionType.CLICK)
        self.assertTrue(detector.click_emitted)

        # Later, hand slightly drifts past drag deadband (displacement > 32)
        t = 1.45
        p_drift = Point2D(250.0, 200.0)
        dec2 = detector.evaluate(normalized_distance=0.20, current_location=p_drift, timestamp=t)
        # MUST NOT enter START_DRAG because click was already emitted!
        self.assertNotEqual(dec2.decision_type, PinchDecisionType.START_DRAG, "Click must NOT become unintended drag")
        self.assertEqual(dec2.decision_type, PinchDecisionType.ARMED)

    def test_shortcut_cooldown_prevents_repeated_triggers(self):
        detector = FingerShortcutDetector(cooldown_seconds=1.5)

        def make_sample(t, thumb_p, mid_p):
            joints = {
                HandJointName.WRIST: HandJoint(HandJointName.WRIST, Point2D(0.5, 0.8), 0.9, 0.0),
                HandJointName.INDEX_MCP: HandJoint(HandJointName.INDEX_MCP, Point2D(0.5, 0.5), 0.9, 0.0),
                HandJointName.THUMB_TIP: HandJoint(HandJointName.THUMB_TIP, thumb_p, 0.9, 0.0),
                HandJointName.MIDDLE_TIP: HandJoint(HandJointName.MIDDLE_TIP, mid_p, 0.9, 0.0),
            }
            return HandSample(
                host_timestamp=t,
                presentation_time_seconds=t,
                is_presentation_time_estimated=False,
                joints=joints,
                overall_confidence=0.9,
                estimated_handedness="right",
                tracking_id=1
            )

        # Touch thumb and middle finger (distance = 0.05 / scale 0.3 = 0.16 <= contact_threshold)
        s0 = make_sample(1.00, Point2D(0.5, 0.5), Point2D(0.5, 0.55))
        res0 = detector.evaluate(s0)
        self.assertIsNone(res0)  # Needs 80ms confirmation

        s1 = make_sample(1.10, Point2D(0.5, 0.5), Point2D(0.5, 0.55))
        res1 = detector.evaluate(s1)
        self.assertEqual(res1, FingerShortcut.COPY, "First contact should emit COPY")

        # Immediately try again at 1.20s (within 1.5s cooldown)
        s2 = make_sample(1.20, Point2D(0.5, 0.5), Point2D(0.5, 0.55))
        res2 = detector.evaluate(s2)
        self.assertIsNone(res2, "Should NOT trigger repeated shortcut during cooldown")

        # Even after separating and re-touching at 1.40s
        s3 = make_sample(1.30, Point2D(0.5, 0.5), Point2D(0.5, 0.80)) # separate
        detector.evaluate(s3)
        s4 = make_sample(1.40, Point2D(0.5, 0.5), Point2D(0.5, 0.55)) # re-touch
        res4 = detector.evaluate(s4)
        self.assertIsNone(res4, "Should still be in refractory cooldown window")


if __name__ == "__main__":
    unittest.main()
