"""
Pose Classifier & Geometric Feature Extraction
1:1 port of macOS PoseClassifier.swift
"""
import math
from dataclasses import dataclass
from typing import Optional
from ..domain.models import Point2D, HandJointName, HandSample

@dataclass
class HandPoseFeatures:
    normalized_pinch_distance: Optional[float]
    is_index_extended: bool
    is_middle_extended: bool
    is_ring_curled: bool
    is_little_curled: bool
    is_open_palm: bool
    is_two_finger_pointing: bool
    is_pinch_approach: bool
    extended_finger_count: int

class PoseClassifier:
    @staticmethod
    def classify(sample: HandSample, pinch_release_threshold: float = 0.38) -> HandPoseFeatures:
        scale = sample.scale_reference or 0.20

        # 1. Pinch Distance (True 3D Euclidean distance)
        pinch_dist: Optional[float] = None
        thumb_tip = sample.joint(HandJointName.THUMB_TIP, min_confidence=0.18)
        index_tip = sample.joint(HandJointName.INDEX_TIP, min_confidence=0.18)

        dist_3d = sample.distance_3d(HandJointName.THUMB_TIP, HandJointName.INDEX_TIP, min_confidence=0.18)
        if dist_3d is not None:
            pinch_dist = dist_3d / scale
        elif thumb_tip is not None and index_tip is not None:
            pinch_dist = thumb_tip.distance_to(index_tip) / scale

        is_pinch_approach = (pinch_dist if pinch_dist is not None else 1.0) < max(0.42, pinch_release_threshold)
        is_pinching = (pinch_dist if pinch_dist is not None else 1.0) < pinch_release_threshold

        # 2. Finger Extension (scale-adaptive)
        index_ext = PoseClassifier._finger_extension(sample, HandJointName.INDEX_MCP, HandJointName.INDEX_PIP, HandJointName.INDEX_TIP, scale)
        middle_ext = PoseClassifier._finger_extension(sample, HandJointName.MIDDLE_MCP, HandJointName.MIDDLE_PIP, HandJointName.MIDDLE_TIP, scale)
        ring_ext = PoseClassifier._finger_extension(sample, HandJointName.RING_MCP, HandJointName.RING_PIP, HandJointName.RING_TIP, scale)
        little_ext = PoseClassifier._finger_extension(sample, HandJointName.LITTLE_MCP, HandJointName.LITTLE_PIP, HandJointName.LITTLE_TIP, scale)

        is_index_strong = index_ext >= 0.85
        is_middle_strong = middle_ext >= 0.85
        is_ring_extended = ring_ext >= 0.50
        is_little_extended = little_ext >= 0.50
        is_index_extended = index_ext >= 0.50
        is_middle_extended = middle_ext >= 0.50

        # Thumb extension
        is_thumb_ext = False
        if thumb_tip is not None:
            index_mcp = sample.joint(HandJointName.INDEX_MCP, min_confidence=0.15)
            if index_mcp is not None and thumb_tip.distance_to(index_mcp) > (scale * 0.65):
                is_thumb_ext = True
            wrist = sample.joint(HandJointName.WRIST, min_confidence=0.15)
            if wrist is not None and wrist.distance_to(thumb_tip) > (scale * 0.75):
                is_thumb_ext = True

        ext_count = (1 if is_thumb_ext else 0) + (1 if is_index_extended else 0) + (1 if is_middle_extended else 0) + (1 if is_ring_extended else 0) + (1 if is_little_extended else 0)

        # OPEN PALM: 3+ non-thumb digits extended and not actively pinching
        extended_non_thumb = (1 if is_index_extended else 0) + (1 if is_middle_extended else 0) + (1 if is_ring_extended else 0) + (1 if is_little_extended else 0)
        is_open = (extended_non_thumb >= 3) and not is_pinching

        # TWO-FINGER SCROLL (V-sign)
        is_two_finger = is_index_strong and is_middle_strong and not is_ring_extended and not is_little_extended and not is_open

        return HandPoseFeatures(
            normalized_pinch_distance=pinch_dist,
            is_index_extended=is_index_extended,
            is_middle_extended=is_middle_extended,
            is_ring_curled=not is_ring_extended,
            is_little_curled=not is_little_extended,
            is_open_palm=is_open,
            is_two_finger_pointing=is_two_finger,
            is_pinch_approach=is_pinch_approach,
            extended_finger_count=ext_count
        )

    @staticmethod
    def _finger_extension(sample: HandSample, mcp: HandJointName, pip: HandJointName, tip: HandJointName, scale: float) -> float:
        mcp_pt = sample.joint(mcp, min_confidence=0.15)
        tip_pt = sample.joint(tip, min_confidence=0.15)
        if mcp_pt is None or tip_pt is None:
            return 0.0

        d_mcp_to_tip = mcp_pt.distance_to(tip_pt)
        wrist = sample.joint(HandJointName.WRIST, min_confidence=0.15)
        if wrist is not None and wrist.distance_to(tip_pt) < wrist.distance_to(mcp_pt) * 0.95:
            return 0.0

        pip_pt = sample.joint(pip, min_confidence=0.15)
        if pip_pt is not None and d_mcp_to_tip < mcp_pt.distance_to(pip_pt) * 1.05:
            return 0.0

        if d_mcp_to_tip < scale * 0.15:
            return 0.0

        full_length = scale * 0.45
        ratio = min(d_mcp_to_tip / max(full_length, 0.01), 1.0)

        if wrist is not None:
            d_wrist_to_tip = wrist.distance_to(tip_pt)
            d_wrist_to_mcp = wrist.distance_to(mcp_pt)
            if d_wrist_to_mcp > 0.01:
                wrist_ratio = d_wrist_to_tip / d_wrist_to_mcp
                if wrist_ratio > 1.15:
                    return max(ratio, 0.85)

        if pip_pt is not None:
            d_mcp_to_pip = mcp_pt.distance_to(pip_pt)
            if d_mcp_to_pip > 0.01:
                pip_ratio = d_mcp_to_tip / d_mcp_to_pip
                if pip_ratio < 1.05:
                    return 0.0
                if pip_ratio > 1.15:
                    return max(ratio, 0.85)

        return ratio
