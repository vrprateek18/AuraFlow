"""
Open-Palm Horizontal Swipe Detector
1:1 port of macOS PalmSwipeDetector.swift
Detects ballistic left/right hand sweeps while rejecting stationary rest, diagonal motion, and return strokes.
"""
import math
from dataclasses import dataclass
from typing import List, Optional
from ..domain.models import Point2D, HandJointName, HandSample, PalmSwipeDirection

@dataclass
class PalmSample:
    position: Point2D
    timestamp: float

class PalmSwipeDetector:
    def __init__(
        self,
        min_displacement: float = 0.070,
        max_duration_seconds: float = 0.45,
        cooldown_duration_seconds: float = 0.35,
        min_velocity: float = 0.20,
        candidate_timeout_seconds: float = 0.20,
        horizontal_dominance_ratio: float = 1.15
    ):
        self.min_displacement = min_displacement
        self.max_duration_seconds = max_duration_seconds
        self.cooldown_duration_seconds = cooldown_duration_seconds
        self.min_velocity = min_velocity
        self.candidate_timeout_seconds = candidate_timeout_seconds
        self.horizontal_dominance_ratio = horizontal_dominance_ratio

        self.history: List[PalmSample] = []
        self.last_swipe_time: float = 0.0
        self.is_armed_for_swipe: bool = True
        self.last_non_palm_time: float = 0.0
        self.last_candidate_active_time: float = 0.0

    @property
    def is_candidate_active(self) -> bool:
        if not self.history:
            return False
        newest = self.history[-1]
        for candidate in self.history:
            dt = newest.timestamp - candidate.timestamp
            if 0.02 <= dt <= 0.35:
                dx = abs(newest.position.x - candidate.position.x)
                dy = abs(newest.position.y - candidate.position.y)
                if dx >= 0.018 and dx > (dy * 0.90):
                    return True
        if 0 < (newest.timestamp - self.last_candidate_active_time) < self.candidate_timeout_seconds:
            return True
        return False

    def reset(self):
        self.history.clear()
        self.last_candidate_active_time = 0.0

    def notify_hand_left_open_palm(self, timestamp: float):
        self.last_non_palm_time = timestamp
        self.is_armed_for_swipe = True
        self.reset()

    @staticmethod
    def extract_palm_center(sample: HandSample) -> Optional[Point2D]:
        conf = 0.18
        middle = sample.joint(HandJointName.MIDDLE_MCP, min_confidence=conf)
        wrist = sample.joint(HandJointName.WRIST, min_confidence=conf)
        if middle is not None and wrist is not None:
            return Point2D(x=(middle.x + wrist.x) * 0.5, y=(middle.y + wrist.y) * 0.5)
        if middle is not None:
            return middle

        mcp_names = [HandJointName.INDEX_MCP, HandJointName.MIDDLE_MCP, HandJointName.RING_MCP, HandJointName.LITTLE_MCP]
        avail = [sample.joint(name, min_confidence=conf) for name in mcp_names]
        avail_pts = [p for p in avail if p is not None]
        if avail_pts:
            avg_x = sum(p.x for p in avail_pts) / len(avail_pts)
            avg_y = sum(p.y for p in avail_pts) / len(avail_pts)
            if wrist is not None:
                return Point2D(x=(avg_x + wrist.x) * 0.5, y=(avg_y + wrist.y) * 0.5)
            return Point2D(x=avg_x, y=avg_y)

        return wrist

    def evaluate(self, sample: Optional[HandSample], is_open_palm: bool, timestamp: float) -> Optional[PalmSwipeDirection]:
        if not is_open_palm or sample is None:
            self.notify_hand_left_open_palm(timestamp=timestamp)
            return None

        palm_center = self.extract_palm_center(sample)
        if palm_center is None:
            self.reset()
            return None

        time_since_swipe = timestamp - self.last_swipe_time
        if time_since_swipe < self.cooldown_duration_seconds:
            return None

        if not self.is_armed_for_swipe:
            elapsed = timestamp - self.last_swipe_time
            if elapsed >= (self.cooldown_duration_seconds + 0.30):
                self.is_armed_for_swipe = True
                self.reset()
            elif self.history:
                first = self.history[0]
                dt = timestamp - first.timestamp
                dist = palm_center.distance_to(first.position)
                velocity = (dist / dt) if dt > 0.001 else 1.0
                if dt >= 0.10 and (velocity < 0.25 or dist < 0.06):
                    self.is_armed_for_swipe = True
                    self.reset()
            self.history.append(PalmSample(position=palm_center, timestamp=timestamp))
            self.history = [s for s in self.history if timestamp - s.timestamp <= self.max_duration_seconds]
            return None

        self.history.append(PalmSample(position=palm_center, timestamp=timestamp))
        self.history = [s for s in self.history if timestamp - s.timestamp <= self.max_duration_seconds]

        if len(self.history) < 2:
            return None

        newest = self.history[-1]
        for candidate in self.history:
            dt = newest.timestamp - candidate.timestamp
            if 0.02 <= dt <= 0.35:
                dx = abs(newest.position.x - candidate.position.x)
                dy = abs(newest.position.y - candidate.position.y)
                if dx >= 0.018 and dx > (dy * 0.90):
                    self.last_candidate_active_time = timestamp
                    break

        for candidate in self.history:
            dt = newest.timestamp - candidate.timestamp
            if not (0.04 <= dt <= self.max_duration_seconds):
                continue

            dx = newest.position.x - candidate.position.x
            dy = newest.position.y - candidate.position.y
            abs_dx = abs(dx)
            abs_dy = abs(dy)
            velocity_x = abs_dx / dt

            if abs_dx >= self.min_displacement and velocity_x >= self.min_velocity and abs_dx >= (abs_dy * self.horizontal_dominance_ratio):
                self.last_swipe_time = timestamp
                self.is_armed_for_swipe = False
                self.reset()
                return PalmSwipeDirection.LEFT if dx < 0 else PalmSwipeDirection.RIGHT

        return None
