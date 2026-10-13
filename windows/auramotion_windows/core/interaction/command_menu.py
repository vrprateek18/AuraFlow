"""
Gesture Command Menu (3x3 Hand Command Grid)
1:1 port of macOS GestureCommandMenu.swift
"""
import math
from dataclasses import dataclass
from typing import Optional, List
from ..domain.models import Point2D, GestureCommand
from ..tracking.one_euro_filter import OneEuroFilter2D

ALL_COMMANDS = [
    GestureCommand.RIGHT_CLICK, GestureCommand.DOUBLE_CLICK, GestureCommand.MISSION_CONTROL,
    GestureCommand.PREVIOUS_APP, GestureCommand.NEXT_APP, GestureCommand.MINIMIZE,
    GestureCommand.FULL_SCREEN, GestureCommand.SNAP_LEFT, GestureCommand.SNAP_RIGHT
]

@dataclass
class CommandMenuSnapshot:
    selected: Optional[GestureCommand]
    pointer: Point2D
    target: Point2D
    awaiting_pointer: bool

class ContactConfirmation:
    def __init__(self, duration: float = 0.08):
        self.duration = duration
        self.first_match_time: Optional[float] = None

    def reset(self):
        self.first_match_time = None

    def update(self, matches: bool, timestamp: float) -> bool:
        if not matches:
            self.first_match_time = None
            return False
        if self.first_match_time is None:
            self.first_match_time = timestamp
            return False
        return (timestamp - self.first_match_time) >= self.duration

class GestureCommandMenu:
    def __init__(self, hold_duration: float = 0.9):
        self.hold_duration = hold_duration
        self.is_open: bool = False
        self.hold_start: Optional[float] = None
        self.palm_anchor: Optional[Point2D] = None
        self.pointer_origin: Optional[Point2D] = None
        self.pointer: Point2D = Point2D(0.5, 0.5)
        self.target: Point2D = Point2D(0.0, 0.0)
        self.selected: Optional[GestureCommand] = None
        self.locked_selection: Optional[GestureCommand] = None
        self.confirmation = ContactConfirmation(duration=0.08)
        self.last_time: Optional[float] = None
        self.suppress_until_release: bool = False
        self.opened_at: float = 0.0
        self.pointer_filter = OneEuroFilter2D(min_cutoff=3.0, beta=4.0)

    @property
    def snapshot(self) -> Optional[CommandMenuSnapshot]:
        if not self.is_open:
            return None
        return CommandMenuSnapshot(
            selected=self.locked_selection or self.selected,
            pointer=self.pointer,
            target=self.target,
            awaiting_pointer=self.pointer_origin is None
        )

    def cancel(self):
        self.is_open = False
        self.hold_start = None
        self.palm_anchor = None
        self.pointer_origin = None
        self.selected = None
        self.locked_selection = None
        self.confirmation.reset()
        self.pointer_filter.reset()

    def reset_hold(self):
        self.hold_start = None
        self.palm_anchor = None

    def observe_palm(self, position: Optional[Point2D], timestamp: float, target: Point2D) -> bool:
        if position is None:
            self.reset_hold()
            return False

        if self.last_time is not None and (timestamp - self.last_time > 0.15):
            self.reset_hold()
        self.last_time = timestamp

        if self.palm_anchor is not None and position.distance_to(self.palm_anchor) > 0.035:
            self.reset_hold()

        if self.hold_start is None:
            self.hold_start = timestamp
            self.palm_anchor = position

        elapsed = timestamp - (self.hold_start if self.hold_start is not None else timestamp)
        if elapsed >= self.hold_duration:
            self.is_open = True
            self.target = target
            self.pointer_origin = None
            self.pointer = Point2D(0.5, 0.5)
            self.selected = None
            self.opened_at = timestamp
            self.reset_hold()
            return True

        return False

    def consume_closing_contact(self, distance: Optional[float], release_threshold: float) -> bool:
        if not self.suppress_until_release:
            return False
        if distance is not None and distance >= release_threshold:
            self.suppress_until_release = False
        return True

    def navigate(
        self,
        index: Optional[Point2D],
        is_pointing: bool,
        pinch_distance: Optional[float],
        contact_threshold: float,
        release_threshold: float,
        timestamp: float
    ) -> Optional[GestureCommand]:
        if not self.is_open:
            return None

        if timestamp - self.opened_at > 12.0:
            self.cancel()
            return None

        if index is None or pinch_distance is None:
            self.confirmation.reset()
            self.locked_selection = None
            return None

        if self.pointer_origin is None:
            if not is_pointing or pinch_distance < release_threshold:
                return None
            self.pointer_origin = index

        if pinch_distance >= release_threshold:
            self.confirmation.reset()
            self.locked_selection = None
            origin = self.pointer_origin if self.pointer_origin is not None else index
            if not is_pointing:
                return None

            raw_x = min(1.0, max(0.0, 0.5 + (index.x - origin.x) / 0.24))
            raw_y = min(1.0, max(0.0, 0.5 + (index.y - origin.y) / 0.24))
            self.pointer = self.pointer_filter.filter(Point2D(raw_x, raw_y), timestamp)

            # Keep selected tile until pointer clears edge by 3%
            if self.selected is not None:
                try:
                    cell_idx = ALL_COMMANDS.index(self.selected)
                    col = cell_idx % 3
                    row = cell_idx // 3
                    min_x = (col / 3.0) - 0.03
                    max_x = ((col + 1) / 3.0) + 0.03
                    min_y = (row / 3.0) - 0.03
                    max_y = ((row + 1) / 3.0) + 0.03
                    if min_x <= self.pointer.x <= max_x and min_y <= self.pointer.y <= max_y:
                        return None
                except ValueError:
                    pass

            self.selected = self.command_at(self.pointer)
        elif pinch_distance <= contact_threshold:
            if self.locked_selection is None:
                self.locked_selection = self.selected
            if self.confirmation.update(matches=self.locked_selection is not None, timestamp=timestamp) and self.locked_selection is not None:
                cmd = self.locked_selection
                self.suppress_until_release = True
                self.cancel()
                return cmd
        else:
            self.confirmation.reset()

        return None

    @staticmethod
    def command_at(point: Point2D) -> Optional[GestureCommand]:
        if not (0.0 <= point.x <= 1.0 and 0.0 <= point.y <= 1.0):
            return None
        col = min(2, int(point.x * 3.0))
        row = min(2, int(point.y * 3.0))
        return ALL_COMMANDS[row * 3 + col]
