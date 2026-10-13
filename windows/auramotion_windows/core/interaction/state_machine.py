"""
Gesture State Machine
Hierarchical finite-state machine governing pointer, click, drag, scroll, shortcuts, palm swipe, and menu.
1:1 port of macOS GestureStateMachine.swift
"""
import time
from typing import Optional, Protocol, Callable
from ..domain.models import (
    Point2D, GestureState, GestureCommand, FingerShortcut,
    PalmSwipeDirection, HandSample, CalibrationProfile, HandJointName
)
from ..tracking.confidence_gate import ConfidenceGate
from .engagement_clutch import EngagementClutch
from .pinch_detector import PinchDetector, PinchDecisionType
from .finger_shortcut_detector import FingerShortcutDetector, ContactConfirmation
from .scroll_detector import ScrollDetector, ScrollDelta
from .palm_swipe_detector import PalmSwipeDetector
from .command_menu import GestureCommandMenu
from .pose_classifier import PoseClassifier

class GestureStateMachineListener:
    def on_transition(self, state: GestureState): pass
    def on_move(self, location: Point2D): pass
    def on_click(self, anchor: Point2D): pass
    def on_drag_start(self, anchor: Point2D): pass
    def on_drag_move(self, location: Point2D): pass
    def on_drag_end(self, location: Point2D): pass
    def on_scroll(self, delta: ScrollDelta): pass
    def on_swipe(self, direction: PalmSwipeDirection): pass
    def on_shortcut(self, shortcut: FingerShortcut): pass
    def on_command(self, command: GestureCommand, target: Point2D): pass
    def on_emergency_release(self): pass

class GestureStateMachine:
    def __init__(self, listener: Optional[GestureStateMachineListener] = None):
        self.listener = listener or GestureStateMachineListener()

        self.current_state: GestureState = GestureState.IDLE
        self.confidence_gate = ConfidenceGate()
        self.clutch = EngagementClutch(dwell_duration=0.02, disengage_grace_duration=0.20)
        self.pinch_detector = PinchDetector()
        self.shortcut_detector = FingerShortcutDetector()
        self.scroll_detector = ScrollDetector()
        self.palm_swipe_detector = PalmSwipeDetector()
        self.command_menu = GestureCommandMenu()

        self.last_pointer_target: Optional[Point2D] = None
        self.scroll_pose_confirmation = ContactConfirmation(duration=0.04)
        self.scroll_pose_confirmed = False
        self.last_scroll_pose_time: Optional[float] = None

        self.is_clutch_enabled: bool = True
        self.is_manual_paused: bool = False
        self.is_palm_swipe_enabled: bool = True
        self.open_palm_grace_duration: float = 0.12
        self.last_open_palm_timestamp: float = 0.0

    def update_calibration(self, profile: CalibrationProfile):
        self.pinch_detector.update_thresholds(
            start_threshold=profile.pinch_start_threshold,
            release_threshold=profile.pinch_release_threshold,
            drag_deadband_points=profile.drag_deadband_points
        )
        self.scroll_detector.update_deadband(profile.scroll_deadband_points)
        self.shortcut_detector.update_calibration(profile)

    def reset(self):
        self.scroll_pose_confirmation.reset()
        self.scroll_pose_confirmed = False
        self.last_scroll_pose_time = None
        self.current_state = GestureState.IDLE
        self.command_menu.cancel()
        self.confidence_gate.reset()
        self.clutch.reset()
        self.pinch_detector.reset()
        self.shortcut_detector.reset()
        self.scroll_detector.reset()
        self.palm_swipe_detector.reset()
        self.last_open_palm_timestamp = 0.0

    def transition(self, new_state: GestureState):
        if new_state not in (GestureState.SCROLLING, GestureState.SCROLL_CANDIDATE):
            self.scroll_pose_confirmation.reset()
            self.scroll_pose_confirmed = False
            self.last_scroll_pose_time = None

        if new_state in (GestureState.PAUSED, GestureState.TRACKING_LOST):
            self.command_menu.cancel()

        if self.current_state != new_state:
            self.current_state = new_state
            self.listener.on_transition(new_state)

    def process_frame(
        self,
        sample: Optional[HandSample],
        mapped_cursor_location: Optional[Point2D],
        is_injection_allowed: bool = True
    ):
        timestamp = sample.host_timestamp if sample is not None else time.time()

        # 1. Manual Pause
        if self.is_manual_paused:
            self.command_menu.cancel()
            if self.current_state != GestureState.PAUSED:
                self.transition(GestureState.PAUSED)
                self.palm_swipe_detector.reset()
                self.listener.on_emergency_release()
            return

        # 2. Confidence Gate
        has_valid_confidence = self.confidence_gate.evaluate(sample, timestamp)
        if not has_valid_confidence or sample is None or mapped_cursor_location is None:
            self.command_menu.cancel()
            if self.current_state != GestureState.TRACKING_LOST:
                self.transition(GestureState.TRACKING_LOST)
                self.pinch_detector.reset()
                self.shortcut_detector.cancel_candidate()
                self.scroll_detector.reset()
                self.palm_swipe_detector.reset()
                self.clutch.reset()
                self.last_open_palm_timestamp = 0.0
                self.listener.on_emergency_release()
            return

        # 3. Classify Pose
        if not is_injection_allowed:
            self.command_menu.cancel()
            if self.current_state != GestureState.PAUSED:
                self.pinch_detector.reset()
                self.scroll_detector.reset()
                self.palm_swipe_detector.reset()
                self.clutch.reset()
                self.transition(GestureState.PAUSED)
                self.listener.on_emergency_release()
            return

        features = PoseClassifier.classify(sample, pinch_release_threshold=self.pinch_detector.release_threshold)

        if self.command_menu.consume_closing_contact(features.normalized_pinch_distance, self.pinch_detector.release_threshold):
            return

        menu_snapshot = self.command_menu.snapshot
        if menu_snapshot is not None:
            if not features.is_open_palm and not features.is_index_extended and not features.is_two_finger_pointing and not features.is_pinch_approach:
                self.command_menu.cancel()
                return

            cmd = self.command_menu.navigate(
                index=sample.joint(HandJointName.INDEX_TIP, min_confidence=0.5),
                is_pointing=features.is_index_extended and not features.is_middle_extended,
                pinch_distance=features.normalized_pinch_distance,
                contact_threshold=self.pinch_detector.start_threshold,
                release_threshold=self.pinch_detector.release_threshold,
                timestamp=timestamp
            )
            if cmd is not None:
                self.listener.on_command(cmd, menu_snapshot.target)
            return

        if not features.is_open_palm:
            self.command_menu.reset_hold()

        # Shortcut contacts (Copy / Paste)
        if self.current_state not in (GestureState.PINCH_ARMED, GestureState.DRAGGING):
            was_holding = self.shortcut_detector.is_holding_contact
            shortcut = self.shortcut_detector.evaluate(sample)
            if was_holding or self.shortcut_detector.is_holding_contact:
                self.pinch_detector.reset()
                self.scroll_detector.reset()
                self.palm_swipe_detector.reset()
                self.transition(GestureState.IDLE)
                if shortcut is not None:
                    self.listener.on_shortcut(shortcut)
                return

        is_explicit_pointer_pose = features.is_index_extended and not features.is_middle_extended and not features.is_open_palm
        is_explicit_non_palm_pose = is_explicit_pointer_pose or features.is_two_finger_pointing or features.is_pinch_approach

        # 4. Open Palm with grace period
        if is_explicit_non_palm_pose:
            is_effective_open_palm = False
            self.last_open_palm_timestamp = 0.0
        elif features.is_open_palm:
            self.last_open_palm_timestamp = timestamp
            is_effective_open_palm = True
        elif self.current_state == GestureState.PALM_REST and (timestamp - self.last_open_palm_timestamp) < self.open_palm_grace_duration and self.last_open_palm_timestamp > 0:
            is_effective_open_palm = True
        else:
            is_effective_open_palm = False

        # 5. Palm Swipe / Palm Rest
        if is_effective_open_palm:
            in_pinch_or_drag_or_scroll = self.current_state in (GestureState.PINCH_ARMED, GestureState.DRAGGING, GestureState.SCROLLING, GestureState.SCROLL_CANDIDATE)
            if not in_pinch_or_drag_or_scroll:
                self.pinch_detector.reset()
                self.scroll_detector.reset()

                if self.is_palm_swipe_enabled:
                    swipe_dir = self.palm_swipe_detector.evaluate(sample, is_open_palm=True, timestamp=timestamp)
                    if swipe_dir is not None:
                        self.transition(GestureState.PALM_REST)
                        self.clutch.reset()
                        self.command_menu.reset_hold()
                        self.listener.on_swipe(swipe_dir)
                        return

                palm_center = PalmSwipeDetector.extract_palm_center(sample)
                target_loc = self.last_pointer_target or mapped_cursor_location
                if self.command_menu.observe_palm(palm_center, timestamp, target_loc):
                    self.pinch_detector.reset()
                    self.scroll_detector.reset()
                    self.shortcut_detector.reset()
                    self.transition(GestureState.COMMAND_MENU)
                    return

                if self.current_state != GestureState.PALM_REST:
                    self.transition(GestureState.PALM_REST)
                    self.clutch.reset()
                    self.listener.on_emergency_release()
                return
        else:
            self.palm_swipe_detector.notify_hand_left_open_palm(timestamp=timestamp)
            if self.current_state == GestureState.PALM_REST:
                self.transition(GestureState.IDLE)

        # 6. Pinch Detection
        is_pinch_active = self.current_state in (GestureState.PINCH_ARMED, GestureState.DRAGGING)
        if is_pinch_active or features.is_pinch_approach:
            pinch_decision = self.pinch_detector.evaluate(
                normalized_distance=features.normalized_pinch_distance,
                current_location=mapped_cursor_location,
                timestamp=timestamp
            )

            if pinch_decision.decision_type == PinchDecisionType.ARMED and pinch_decision.anchor:
                self.scroll_detector.reset()
                self.transition(GestureState.PINCH_ARMED)
                self.listener.on_move(pinch_decision.anchor)
                return
            elif pinch_decision.decision_type == PinchDecisionType.CLICK and pinch_decision.anchor:
                next_state = GestureState.PINCH_ARMED if self.pinch_detector.is_contact_active else GestureState.POINTING
                self.transition(next_state)
                self.listener.on_click(pinch_decision.anchor)
                return
            elif pinch_decision.decision_type == PinchDecisionType.START_DRAG and pinch_decision.anchor:
                self.scroll_detector.reset()
                self.transition(GestureState.DRAGGING)
                self.listener.on_drag_start(pinch_decision.anchor)
                return
            elif pinch_decision.decision_type == PinchDecisionType.DRAGGING and pinch_decision.current:
                self.scroll_detector.reset()
                self.transition(GestureState.DRAGGING)
                self.listener.on_drag_move(pinch_decision.current)
                return
            elif pinch_decision.decision_type == PinchDecisionType.DRAG_RELEASE:
                self.transition(GestureState.POINTING)
                self.listener.on_drag_end(mapped_cursor_location)
                return
            elif pinch_decision.decision_type == PinchDecisionType.NONE and is_pinch_active:
                return

        # 7. Engagement Clutch
        if self.is_clutch_enabled:
            is_active_gesture = features.is_index_extended or features.is_two_finger_pointing
            engaged = self.clutch.evaluate(is_ready_pose=is_active_gesture, timestamp=timestamp)
            if not engaged:
                self.transition(GestureState.IDLE)
                return

        # 8. Two-Finger Scroll
        if features.is_two_finger_pointing:
            self.last_scroll_pose_time = timestamp
            if not self.scroll_pose_confirmed:
                self.scroll_pose_confirmed = self.scroll_pose_confirmation.update(matches=True, timestamp=timestamp)
                if not self.scroll_pose_confirmed:
                    self.scroll_detector.reset()
                    self.transition(GestureState.SCROLL_CANDIDATE)
                    return

            delta = self.scroll_detector.evaluate(is_two_finger_pose=True, current_location=mapped_cursor_location)
            if delta is not None:
                self.transition(GestureState.SCROLLING)
                self.listener.on_scroll(delta)
            else:
                self.transition(GestureState.SCROLL_CANDIDATE)
            return

        # 9. Scroll Inertia Decay
        if not is_explicit_pointer_pose and not features.is_open_palm and not features.is_pinch_approach:
            if self.last_scroll_pose_time is not None and (timestamp - self.last_scroll_pose_time < 0.08):
                return

        if not is_explicit_pointer_pose and not features.is_open_palm:
            inertia_delta = self.scroll_detector.scroll_controller.compute_inertia_step()
            if inertia_delta is not None:
                self.transition(GestureState.SCROLLING)
                self.listener.on_scroll(inertia_delta)
                return

        self.scroll_detector.reset()

        if not is_explicit_pointer_pose:
            self.transition(GestureState.IDLE)
            return

        # 10. Default: Pointer
        if not is_pinch_active:
            passive_decision = self.pinch_detector.evaluate(
                normalized_distance=features.normalized_pinch_distance,
                current_location=mapped_cursor_location,
                timestamp=timestamp
            )
            if passive_decision.decision_type == PinchDecisionType.ARMED and passive_decision.anchor:
                self.scroll_detector.reset()
                self.transition(GestureState.PINCH_ARMED)
                self.listener.on_move(passive_decision.anchor)
                return

        self.transition(GestureState.POINTING)
        self.last_pointer_target = mapped_cursor_location
        self.listener.on_move(mapped_cursor_location)
