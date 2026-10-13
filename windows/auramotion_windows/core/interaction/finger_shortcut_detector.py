"""
One-Shot Thumb-to-Finger Shortcuts (Copy & Paste)
1:1 port of macOS FingerShortcutDetector.swift
"""
import math
from typing import Optional
from ..domain.models import Point2D, HandJointName, HandSample, FingerShortcut, CalibrationProfile

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


class FingerShortcutDetector:
    def __init__(self, contact_threshold: float = 0.28, release_threshold: float = 0.40, cooldown_seconds: float = 1.8):
        self.contact_threshold = contact_threshold
        self.release_threshold = release_threshold
        self.cooldown_seconds = cooldown_seconds

        self.active_shortcut: Optional[FingerShortcut] = None
        self.candidate: Optional[FingerShortcut] = None
        self.contact_confirmation = ContactConfirmation(0.08)
        self.release_confirmation = ContactConfirmation(0.08)
        self.profile: Optional[CalibrationProfile] = None

        self.last_trigger_time: float = -999.0
        self.requires_neutral_release: bool = False

    @property
    def is_holding_contact(self) -> bool:
        return self.active_shortcut is not None or self.candidate is not None

    def update_calibration(self, profile: CalibrationProfile):
        self.profile = profile

    def reset(self):
        self.active_shortcut = None
        self.cancel_candidate()
        self.release_confirmation.reset()
        self.requires_neutral_release = False

    def cancel_candidate(self):
        self.candidate = None
        self.contact_confirmation.reset()
        self.release_confirmation.reset()

    @staticmethod
    def _normalized_dist(p1: Point2D, p2: Optional[Point2D], scale: float) -> Optional[float]:
        if p2 is None:
            return None
        return p1.distance_to(p2) / scale

    def evaluate(self, sample: HandSample) -> Optional[FingerShortcut]:
        thumb = sample.joint(HandJointName.THUMB_TIP, min_confidence=0.35)
        scale = sample.scale_reference
        if thumb is None or scale is None:
            self.cancel_candidate()
            return None

        middle_tip = sample.joint(HandJointName.MIDDLE_TIP, min_confidence=0.35)
        ring_tip = sample.joint(HandJointName.RING_TIP, min_confidence=0.35)

        middle_dist = self._normalized_dist(thumb, middle_tip, scale)
        ring_dist = self._normalized_dist(thumb, ring_tip, scale)

        release_thresh = self.release_threshold
        if self.profile:
            release_thresh = max(self.profile.copy_release_threshold, self.profile.paste_release_threshold)

        # Check if awaiting neutral hand release after a previous trigger
        if self.requires_neutral_release:
            middle_open = middle_dist is None or middle_dist >= release_thresh
            ring_open = ring_dist is None or ring_dist >= release_thresh
            if middle_open and ring_open:
                self.requires_neutral_release = False
            else:
                return None

        # Check refractory cooldown window (prevents rapid repetitive triggers)
        now = sample.host_timestamp
        if (now - self.last_trigger_time) < self.cooldown_seconds:
            return None

        if self.active_shortcut is not None:
            dist = middle_dist if self.active_shortcut == FingerShortcut.COPY else ring_dist
            thresh = (
                (self.profile.copy_release_threshold if self.profile else self.release_threshold)
                if self.active_shortcut == FingerShortcut.COPY
                else (self.profile.paste_release_threshold if self.profile else self.release_threshold)
            )
            matches = (dist if dist is not None else float('-inf')) >= thresh
            if self.release_confirmation.update(matches=matches, timestamp=now):
                self.active_shortcut = None
                self.release_confirmation.reset()
            return None

        detected_candidate: Optional[FingerShortcut] = None
        copy_thresh = self.profile.copy_contact_threshold if self.profile else self.contact_threshold
        paste_thresh = self.profile.paste_contact_threshold if self.profile else self.contact_threshold

        if middle_dist is not None and middle_dist <= copy_thresh:
            detected_candidate = FingerShortcut.COPY
        elif ring_dist is not None and ring_dist <= paste_thresh:
            detected_candidate = FingerShortcut.PASTE

        if detected_candidate != self.candidate:
            self.candidate = detected_candidate
            self.contact_confirmation.reset()

        if self.candidate is not None:
            if self.contact_confirmation.update(matches=True, timestamp=now):
                shortcut = self.candidate
                self.active_shortcut = shortcut
                self.last_trigger_time = now
                self.requires_neutral_release = True
                self.cancel_candidate()
                return shortcut

        return None
