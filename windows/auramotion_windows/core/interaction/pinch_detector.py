"""
Anchor-Locked Pinch and Dwell Detector
1:1 port of macOS PinchDetector.swift
Guarantees clean click emission at anchor location and zero micro-drags.
"""
import math
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Tuple
from ..domain.models import Point2D

class PinchDecisionType(str, Enum):
    NONE = "none"
    ARMED = "armed"
    CLICK = "click"
    START_DRAG = "startDrag"
    DRAGGING = "dragging"
    DRAG_RELEASE = "dragRelease"
    CANCELLED = "cancelled"

@dataclass
class PinchDecision:
    decision_type: PinchDecisionType
    anchor: Optional[Point2D] = None
    current: Optional[Point2D] = None

class PinchDetector:
    def __init__(
        self,
        start_threshold: float = 0.26,
        release_threshold: float = 0.36,
        dwell_threshold_seconds: float = 0.35,
        drag_deadband_points: float = 32.0,
        click_deadband_points: float = 30.0,
        max_click_dwell_seconds: float = 0.80,
        max_pinch_entry_speed: float = 650.0
    ):
        self.start_threshold = start_threshold
        self.release_threshold = release_threshold
        self.dwell_threshold_seconds = dwell_threshold_seconds
        self.drag_deadband_points = drag_deadband_points
        self.click_deadband_points = click_deadband_points
        self.max_click_dwell_seconds = max_click_dwell_seconds
        self.max_pinch_entry_speed = max_pinch_entry_speed

        self.is_pinching = False
        self.click_emitted = False
        self.is_dragging = False
        self.pinch_start_time: Optional[float] = None
        self.anchor_location: Optional[Point2D] = None
        self.candidate_anchor: Optional[Point2D] = None

        self.last_cursor_pos: Optional[Point2D] = None
        self.last_cursor_time: Optional[float] = None

        self.pre_pinch_threshold: float = 0.42
        self.anchor_lock_radius: float = 35.0

    @property
    def is_contact_active(self) -> bool:
        return self.is_pinching

    def reset(self):
        self.is_pinching = False
        self.click_emitted = False
        self.is_dragging = False
        self.pinch_start_time = None
        self.anchor_location = None
        self.candidate_anchor = None

    def update_thresholds(
        self,
        start_threshold: Optional[float] = None,
        release_threshold: Optional[float] = None,
        drag_deadband_points: Optional[float] = None
    ):
        if start_threshold is not None:
            self.start_threshold = start_threshold
        if release_threshold is not None:
            self.release_threshold = release_threshold
        if drag_deadband_points is not None:
            self.drag_deadband_points = drag_deadband_points

    def evaluate(
        self,
        normalized_distance: Optional[float],
        current_location: Point2D,
        timestamp: float
    ) -> PinchDecision:
        if normalized_distance is None:
            if self.is_dragging:
                self.reset()
                return PinchDecision(PinchDecisionType.DRAG_RELEASE)
            self.reset()
            return PinchDecision(PinchDecisionType.CANCELLED)

        dist = normalized_distance

        if not self.is_pinching:
            # Velocity Gating: prevent accidental pinch entry during fast hand sweeps
            if self.last_cursor_pos is not None and self.last_cursor_time is not None:
                dt = timestamp - self.last_cursor_time
                if dt > 0.001:
                    speed = current_location.distance_to(self.last_cursor_pos) / dt
                    if speed > self.max_pinch_entry_speed:
                        self.candidate_anchor = None
                        self.last_cursor_pos = current_location
                        self.last_cursor_time = timestamp
                        return PinchDecision(PinchDecisionType.NONE)

            self.last_cursor_pos = current_location
            self.last_cursor_time = timestamp

            # Track candidate anchor when fingers begin closing towards each other
            if dist <= max(self.pre_pinch_threshold, self.release_threshold):
                if self.candidate_anchor is not None:
                    dist_from_candidate = current_location.distance_to(self.candidate_anchor)
                    if dist_from_candidate > self.anchor_lock_radius:
                        self.candidate_anchor = current_location
                else:
                    self.candidate_anchor = current_location
            else:
                self.candidate_anchor = None

            # Check for pinch entry
            if dist <= self.start_threshold:
                self.click_emitted = False
                self.is_pinching = True
                self.is_dragging = False
                self.pinch_start_time = timestamp
                anchor = self.candidate_anchor if self.candidate_anchor is not None else current_location
                self.anchor_location = anchor
                self.candidate_anchor = None
                return PinchDecision(PinchDecisionType.ARMED, anchor=anchor)

            return PinchDecision(PinchDecisionType.NONE)
        else:
            self.last_cursor_pos = current_location
            self.last_cursor_time = timestamp

            # Already pinching
            if self.pinch_start_time is None or self.anchor_location is None:
                self.reset()
                return PinchDecision(PinchDecisionType.CANCELLED)

            dwell = timestamp - self.pinch_start_time
            displacement = current_location.distance_to(self.anchor_location)

            # Check for pinch release
            if dist >= self.release_threshold:
                anchor = self.anchor_location
                was_dragging = self.is_dragging
                self.is_pinching = False
                self.pinch_start_time = None
                self.anchor_location = None
                self.candidate_anchor = None

                if was_dragging:
                    self.is_dragging = False
                    return PinchDecision(PinchDecisionType.DRAG_RELEASE)
                elif not self.click_emitted and displacement <= self.click_deadband_points and 0.075 <= dwell <= self.max_click_dwell_seconds:
                    return PinchDecision(PinchDecisionType.CLICK, anchor=anchor)
                else:
                    return PinchDecision(PinchDecisionType.CANCELLED)

            # Still pinched: check if click should be emitted
            if not self.is_dragging and not self.click_emitted and 0.075 <= dwell <= self.max_click_dwell_seconds and displacement <= self.drag_deadband_points:
                self.click_emitted = True
                return PinchDecision(PinchDecisionType.CLICK, anchor=self.anchor_location)

            # Unintended drag prevention: If click was already emitted, NEVER start a drag!
            if not self.is_dragging:
                if self.click_emitted:
                    return PinchDecision(PinchDecisionType.ARMED, anchor=self.anchor_location)

                if dwell >= self.dwell_threshold_seconds:
                    if displacement > self.drag_deadband_points:
                        self.is_dragging = True
                        return PinchDecision(PinchDecisionType.START_DRAG, anchor=self.anchor_location)
                    return PinchDecision(PinchDecisionType.ARMED, anchor=self.anchor_location)
                else:
                    # Early jitter rejection: excessive displacement during early dwell cancels pinch
                    if displacement > 38.0:
                        self.reset()
                        return PinchDecision(PinchDecisionType.CANCELLED)
                    return PinchDecision(PinchDecisionType.ARMED, anchor=self.anchor_location)
            else:
                return PinchDecision(PinchDecisionType.DRAGGING, current=current_location)
