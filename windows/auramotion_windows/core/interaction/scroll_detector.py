"""
Two-Finger Scroll Detector with Mutual Exclusion, Smoothing, and Inertia
1:1 port of macOS ScrollDetector.swift and ScrollController.swift
"""
import math
from dataclasses import dataclass
from typing import Optional
from ..domain.models import Point2D

@dataclass
class ScrollDelta:
    delta_x: float
    delta_y: float

class ScrollController:
    def __init__(
        self,
        is_inertia_enabled: bool = True,
        friction_coefficient: float = 0.82,
        speed_multiplier: float = 1.8,
        smoothing_factor: float = 0.32
    ):
        self.is_inertia_enabled = is_inertia_enabled
        self.friction_coefficient = friction_coefficient
        self.speed_multiplier = speed_multiplier
        self.smoothing_factor = smoothing_factor

        self.current_velocity_x: float = 0.0
        self.current_velocity_y: float = 0.0
        self.is_first_step: bool = True

    def reset(self):
        self.current_velocity_x = 0.0
        self.current_velocity_y = 0.0
        self.is_first_step = True

    def update(self, raw_delta_x: float, raw_delta_y: float) -> ScrollDelta:
        scaled_x = raw_delta_x * self.speed_multiplier
        scaled_y = raw_delta_y * self.speed_multiplier

        if self.is_first_step:
            self.current_velocity_x = scaled_x
            self.current_velocity_y = scaled_y
            self.is_first_step = False
        else:
            self.current_velocity_x = self.smoothing_factor * scaled_x + (1.0 - self.smoothing_factor) * self.current_velocity_x
            self.current_velocity_y = self.smoothing_factor * scaled_y + (1.0 - self.smoothing_factor) * self.current_velocity_y

        return ScrollDelta(delta_x=self.current_velocity_x, delta_y=self.current_velocity_y)

    def compute_inertia_step(self) -> Optional[ScrollDelta]:
        if not self.is_inertia_enabled:
            return None

        self.current_velocity_x *= self.friction_coefficient
        self.current_velocity_y *= self.friction_coefficient

        if abs(self.current_velocity_x) < 0.5 and abs(self.current_velocity_y) < 0.5:
            self.reset()
            return None

        return ScrollDelta(delta_x=self.current_velocity_x, delta_y=self.current_velocity_y)


class ScrollDetector:
    def __init__(
        self,
        deadband_points: float = 3.0,
        scroll_speed_multiplier: float = 1.8
    ):
        self.deadband_points = deadband_points
        self.scroll_controller = ScrollController(speed_multiplier=scroll_speed_multiplier)

        self.previous_location: Optional[Point2D] = None
        self.pending_delta_x: float = 0.0
        self.pending_delta_y: float = 0.0
        self.is_scroll_active: bool = False

    @property
    def scroll_speed_multiplier(self) -> float:
        return self.scroll_controller.speed_multiplier

    @scroll_speed_multiplier.setter
    def scroll_speed_multiplier(self, value: float):
        self.scroll_controller.speed_multiplier = value

    def reset(self):
        self.previous_location = None
        self.pending_delta_x = 0.0
        self.pending_delta_y = 0.0
        self.is_scroll_active = False
        self.scroll_controller.reset()

    def update_deadband(self, points: float):
        self.deadband_points = max(0.5, points)

    def evaluate(self, is_two_finger_pose: bool, current_location: Point2D) -> Optional[ScrollDelta]:
        if not is_two_finger_pose:
            return None

        if self.previous_location is None:
            self.previous_location = current_location
            return None

        raw_dx = current_location.x - self.previous_location.x
        raw_dy = current_location.y - self.previous_location.y
        self.previous_location = current_location

        if not self.is_scroll_active:
            self.pending_delta_x += raw_dx
            self.pending_delta_y += raw_dy
            total_dist = math.hypot(self.pending_delta_x, self.pending_delta_y)
            if total_dist >= self.deadband_points:
                self.is_scroll_active = True
                init_x = self.pending_delta_x
                init_y = self.pending_delta_y
                self.pending_delta_x = 0.0
                self.pending_delta_y = 0.0
                return self.scroll_controller.update(raw_delta_x=init_x, raw_delta_y=init_y)
            return None
        else:
            return self.scroll_controller.update(raw_delta_x=raw_dx, raw_delta_y=raw_dy)
