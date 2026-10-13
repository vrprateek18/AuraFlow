"""
Whole-hand Landmark Fusion
Palm translation carries fast motion; a slowly varying fingertip offset keeps
absolute index aiming while attenuating independent finger wobble.
"""
import math
from typing import List, Optional
from ..domain.models import Point2D, HandJointName, HandSample

class HandCursorFusion:
    def __init__(self):
        self.previous_time: Optional[float] = None
        self.identity: Optional[int] = None
        self.offset: Optional[Point2D] = None
        self.palm_joints: List[HandJointName] = []

    def reset(self):
        self.previous_time = None
        self.identity = None
        self.offset = None
        self.palm_joints = []

    def update(self, sample: HandSample, is_pinch_or_two_finger: bool = False) -> Optional[Point2D]:
        if not math.isfinite(sample.host_timestamp):
            return None

        tip = sample.joint(HandJointName.INDEX_TIP, min_confidence=0.45)
        if tip is None or not (math.isfinite(tip.x) and math.isfinite(tip.y)):
            return None

        if self.previous_time is not None and sample.host_timestamp <= self.previous_time:
            return None

        if self.identity != sample.tracking_id or (self.previous_time is not None and sample.host_timestamp - self.previous_time > 0.25):
            self.reset()

        dt = min(0.1, max(0.001, sample.host_timestamp - (self.previous_time if self.previous_time is not None else sample.host_timestamp)))
        self.previous_time = sample.host_timestamp
        self.identity = sample.tracking_id

        names = [
            HandJointName.WRIST,
            HandJointName.INDEX_MCP,
            HandJointName.MIDDLE_MCP,
            HandJointName.RING_MCP,
            HandJointName.LITTLE_MCP
        ]
        available = []
        for name in names:
            p = sample.joint(name, min_confidence=0.55)
            if p is not None and math.isfinite(p.x) and math.isfinite(p.y):
                available.append((name, p))

        # Use fixed landmark set per uninterrupted observation span.
        if len(available) < 3:
            self.offset = None
            self.palm_joints = []
            return tip

        palm_points = [p for (_, p) in available]
        palm_x = sum(p.x for p in palm_points) / len(palm_points)
        palm_y = sum(p.y for p in palm_points) / len(palm_points)
        palm = Point2D(x=palm_x, y=palm_y)

        measured = Point2D(x=tip.x - palm.x, y=tip.y - palm.y)
        avail_names = [n for (n, _) in available]

        if self.offset is None or avail_names != self.palm_joints:
            self.offset = measured
            self.palm_joints = avail_names

        previous = self.offset if self.offset is not None else measured

        if is_pinch_or_two_finger:
            # Finger articulation for clicking or scrolling is not translation.
            # Keep the last pointing offset and let palm motion carry the action.
            return Point2D(x=palm.x + previous.x, y=palm.y + previous.y)

        alpha = 1.0 - math.exp(-dt / 0.085)
        learned = Point2D(
            x=previous.x + alpha * (measured.x - previous.x),
            y=previous.y + alpha * (measured.y - previous.y)
        )
        self.offset = learned
        return Point2D(x=palm.x + learned.x, y=palm.y + learned.y)
