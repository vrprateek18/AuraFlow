"""
Engagement Clutch with Dwell Delay and Hysteresis Grace
1:1 port of macOS EngagementClutch.swift
"""
from typing import Optional

class EngagementClutch:
    def __init__(self, dwell_duration: float = 0.05, disengage_grace_duration: float = 0.25):
        self.dwell_duration = dwell_duration
        self.disengage_grace_duration = disengage_grace_duration

        self.clutch_start_time: Optional[float] = None
        self.disengage_start_time: Optional[float] = None
        self._is_engaged_state: bool = False

    @property
    def is_engaged(self) -> bool:
        return self._is_engaged_state

    def reset(self):
        self.clutch_start_time = None
        self.disengage_start_time = None
        self._is_engaged_state = False

    def evaluate(self, is_ready_pose: bool, timestamp: float) -> bool:
        if self._is_engaged_state:
            if is_ready_pose:
                self.disengage_start_time = None
                return True
            else:
                if self.disengage_start_time is not None:
                    if (timestamp - self.disengage_start_time) >= self.disengage_grace_duration:
                        self._is_engaged_state = False
                        self.disengage_start_time = None
                        self.clutch_start_time = None
                        return False
                    return True
                else:
                    self.disengage_start_time = timestamp
                    return True

        self.disengage_start_time = None
        if not is_ready_pose:
            self.clutch_start_time = None
            return False

        if self.clutch_start_time is not None:
            if (timestamp - self.clutch_start_time) >= self.dwell_duration:
                self._is_engaged_state = True
                self.clutch_start_time = None
                return True
            return False
        else:
            self.clutch_start_time = timestamp
            return False
