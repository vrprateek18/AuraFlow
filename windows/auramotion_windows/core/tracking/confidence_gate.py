"""
Confidence Gate with Hysteresis & Reacquisition Dwell
1:1 port of macOS ConfidenceGate.swift
"""
from typing import Optional
from ..domain.models import HandSample

class ConfidenceGate:
    def __init__(
        self,
        enter_confidence: float = 0.60,
        exit_confidence: float = 0.35,
        drop_consecutive_frames_threshold: int = 3,
        reacquisition_dwell_seconds: float = 0.08
    ):
        self.enter_confidence = enter_confidence
        self.exit_confidence = exit_confidence
        self.drop_consecutive_frames_threshold = drop_consecutive_frames_threshold
        self.reacquisition_dwell_seconds = reacquisition_dwell_seconds

        self.is_tracking: bool = False
        self.low_confidence_frame_count: int = 0
        self.reacquisition_start_time: Optional[float] = None

    def reset(self):
        self.is_tracking = False
        self.low_confidence_frame_count = 0
        self.reacquisition_start_time = None

    def evaluate(self, sample: Optional[HandSample], timestamp: float) -> bool:
        if sample is None or sample.overall_confidence < self.exit_confidence:
            self.low_confidence_frame_count += 1
            if self.low_confidence_frame_count >= self.drop_consecutive_frames_threshold:
                self.is_tracking = False
                self.reacquisition_start_time = None
            return False

        if self.is_tracking:
            if sample.overall_confidence < self.exit_confidence:
                self.low_confidence_frame_count += 1
                if self.low_confidence_frame_count >= self.drop_consecutive_frames_threshold:
                    self.is_tracking = False
                    self.reacquisition_start_time = None
                    return False
            else:
                self.low_confidence_frame_count = 0
            return True
        else:
            if sample.overall_confidence >= self.enter_confidence:
                if self.reacquisition_dwell_seconds <= 0.0:
                    self.is_tracking = True
                    self.low_confidence_frame_count = 0
                    return True
                if self.reacquisition_start_time is None:
                    self.reacquisition_start_time = timestamp
                    return False
                if (timestamp - self.reacquisition_start_time) >= self.reacquisition_dwell_seconds:
                    self.is_tracking = True
                    self.low_confidence_frame_count = 0
                    self.reacquisition_start_time = None
                    return True
                return False
            else:
                self.reacquisition_start_time = None
                return False
