"""
AuraMotion Pro for Windows - Domain Models & Data Structures
1:1 compatible with macOS AuraMotion Core
"""
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Optional, Tuple
import math

class HandJointName(str, Enum):
    WRIST = "wrist"
    # Thumb
    THUMB_CMC = "thumbCMC"
    THUMB_MCP = "thumbMP"
    THUMB_IP = "thumbIP"
    THUMB_TIP = "thumbTip"
    # Index
    INDEX_MCP = "indexMCP"
    INDEX_PIP = "indexPIP"
    INDEX_DIP = "indexDIP"
    INDEX_TIP = "indexTip"
    # Middle
    MIDDLE_MCP = "middleMCP"
    MIDDLE_PIP = "middlePIP"
    MIDDLE_DIP = "middleDIP"
    MIDDLE_TIP = "middleTip"
    # Ring
    RING_MCP = "ringMCP"
    RING_PIP = "ringPIP"
    RING_DIP = "ringDIP"
    RING_TIP = "ringTip"
    # Little (Pinky)
    LITTLE_MCP = "littleMCP"
    LITTLE_PIP = "littlePIP"
    LITTLE_DIP = "littleDIP"
    LITTLE_TIP = "littleTip"

# MediaPipe landmark index mapping (0 to 20)
MEDIAPIPE_JOINT_MAP = [
    HandJointName.WRIST,        # 0
    HandJointName.THUMB_CMC,    # 1
    HandJointName.THUMB_MCP,    # 2
    HandJointName.THUMB_IP,     # 3
    HandJointName.THUMB_TIP,    # 4
    HandJointName.INDEX_MCP,    # 5
    HandJointName.INDEX_PIP,    # 6
    HandJointName.INDEX_DIP,    # 7
    HandJointName.INDEX_TIP,    # 8
    HandJointName.MIDDLE_MCP,   # 9
    HandJointName.MIDDLE_PIP,   # 10
    HandJointName.MIDDLE_DIP,   # 11
    HandJointName.MIDDLE_TIP,   # 12
    HandJointName.RING_MCP,     # 13
    HandJointName.RING_PIP,     # 14
    HandJointName.RING_DIP,     # 15
    HandJointName.RING_TIP,     # 16
    HandJointName.LITTLE_MCP,   # 17
    HandJointName.LITTLE_PIP,   # 18
    HandJointName.LITTLE_DIP,   # 19
    HandJointName.LITTLE_TIP    # 20
]

@dataclass
class Point2D:
    x: float
    y: float

    def distance_to(self, other: "Point2D") -> float:
        dx = self.x - other.x
        dy = self.y - other.y
        return math.hypot(dx, dy)

@dataclass
class HandJoint:
    name: HandJointName
    position: Point2D
    confidence: float
    z: float = 0.0

@dataclass
class HandSample:
    host_timestamp: float
    presentation_time_seconds: float
    is_presentation_time_estimated: bool
    joints: Dict[HandJointName, HandJoint]
    overall_confidence: float
    estimated_handedness: str  # "left" or "right"
    tracking_id: int

    def joint(self, name: HandJointName, min_confidence: float = 0.25) -> Optional[Point2D]:
        j = self.joints.get(name)
        if j is not None and j.confidence >= min_confidence:
            return j.position
        return None

    def joint_object(self, name: HandJointName, min_confidence: float = 0.2) -> Optional[HandJoint]:
        j = self.joints.get(name)
        if j is not None and j.confidence >= min_confidence:
            return j
        return None

    def distance_3d(self, name1: HandJointName, name2: HandJointName, min_confidence: float = 0.18) -> Optional[float]:
        j1 = self.joint_object(name1, min_confidence)
        j2 = self.joint_object(name2, min_confidence)
        if j1 is None or j2 is None:
            return None
        dx = j1.position.x - j2.position.x
        dy = j1.position.y - j2.position.y
        dz = (j1.z - j2.z) * 1.2
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    @property
    def scale_reference(self) -> float:
        wrist = self.joint(HandJointName.WRIST, min_confidence=0.15)
        middle_mcp = self.joint(HandJointName.MIDDLE_MCP, min_confidence=0.15)
        if wrist is not None and middle_mcp is not None:
            dist = wrist.distance_to(middle_mcp)
            if dist > 0.03:
                return dist

        index_mcp = self.joint(HandJointName.INDEX_MCP, min_confidence=0.15)
        if wrist is not None and index_mcp is not None:
            dist = wrist.distance_to(index_mcp)
            if dist > 0.03:
                return dist

        return 0.20

class GestureState(str, Enum):
    IDLE = "idle"
    TRACKING_LOST = "trackingLost"
    PAUSED = "paused"
    POINTING = "pointing"
    PINCH_ARMED = "pinchArmed"
    DRAGGING = "dragging"
    SCROLL_CANDIDATE = "scrollCandidate"
    SCROLLING = "scrolling"
    PALM_REST = "palmRest"
    COMMAND_MENU = "commandMenu"

    @property
    def display_name(self) -> str:
        names = {
            GestureState.IDLE: "READY",
            GestureState.TRACKING_LOST: "SEARCHING",
            GestureState.PAUSED: "PAUSED",
            GestureState.POINTING: "POINTING",
            GestureState.PINCH_ARMED: "PINCH ARMED",
            GestureState.DRAGGING: "DRAGGING",
            GestureState.SCROLL_CANDIDATE: "SCROLL READY",
            GestureState.SCROLLING: "SCROLLING",
            GestureState.PALM_REST: "PALM REST",
            GestureState.COMMAND_MENU: "COMMAND MENU"
        }
        return names.get(self, self.value.upper())

class GestureCommand(str, Enum):
    RIGHT_CLICK = "rightClick"
    DOUBLE_CLICK = "doubleClick"
    MISSION_CONTROL = "missionControl"
    PREVIOUS_APP = "previousApp"
    NEXT_APP = "nextApp"
    MINIMIZE = "minimize"
    FULL_SCREEN = "fullScreen"
    SNAP_LEFT = "snapLeft"
    SNAP_RIGHT = "snapRight"

    @property
    def title(self) -> str:
        titles = {
            GestureCommand.RIGHT_CLICK: "Right click",
            GestureCommand.DOUBLE_CLICK: "Double click",
            GestureCommand.MISSION_CONTROL: "Task View / All Windows",
            GestureCommand.PREVIOUS_APP: "Previous app",
            GestureCommand.NEXT_APP: "Next app",
            GestureCommand.MINIMIZE: "Minimize",
            GestureCommand.FULL_SCREEN: "Full screen",
            GestureCommand.SNAP_LEFT: "Snap Left half",
            GestureCommand.SNAP_RIGHT: "Snap Right half",
        }
        return titles.get(self, self.value)

class FingerShortcut(str, Enum):
    COPY = "copy"
    PASTE = "paste"

class PalmSwipeDirection(str, Enum):
    LEFT = "left"
    RIGHT = "right"

@dataclass
class CalibrationProfile:
    pinch_start_threshold: float = 0.28
    pinch_release_threshold: float = 0.38
    copy_contact_threshold: float = 0.28
    copy_release_threshold: float = 0.40
    paste_contact_threshold: float = 0.28
    paste_release_threshold: float = 0.40
    drag_deadband_points: float = 20.0
    scroll_deadband_points: float = 8.0
    hand_scale_reference: float = 0.18
    is_calibrated: bool = False
    calibrated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "pinch_start_threshold": self.pinch_start_threshold,
            "pinch_release_threshold": self.pinch_release_threshold,
            "copy_contact_threshold": self.copy_contact_threshold,
            "copy_release_threshold": self.copy_release_threshold,
            "paste_contact_threshold": self.paste_contact_threshold,
            "paste_release_threshold": self.paste_release_threshold,
            "drag_deadband_points": self.drag_deadband_points,
            "scroll_deadband_points": self.scroll_deadband_points,
            "hand_scale_reference": self.hand_scale_reference,
            "is_calibrated": self.is_calibrated,
            "calibrated_at": self.calibrated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CalibrationProfile":
        if not isinstance(data, dict):
            return cls()
        return cls(
            pinch_start_threshold=float(data.get("pinch_start_threshold", 0.28)),
            pinch_release_threshold=float(data.get("pinch_release_threshold", 0.38)),
            copy_contact_threshold=float(data.get("copy_contact_threshold", 0.28)),
            copy_release_threshold=float(data.get("copy_release_threshold", 0.40)),
            paste_contact_threshold=float(data.get("paste_contact_threshold", 0.28)),
            paste_release_threshold=float(data.get("paste_release_threshold", 0.40)),
            drag_deadband_points=float(data.get("drag_deadband_points", 20.0)),
            scroll_deadband_points=float(data.get("scroll_deadband_points", 8.0)),
            hand_scale_reference=float(data.get("hand_scale_reference", 0.18)),
            is_calibrated=bool(data.get("is_calibrated", False)),
            calibrated_at=str(data.get("calibrated_at", "")),
        )

@dataclass
class AppSettings:
    first_launch_completed: bool = False
    camera_index: int = 0
    flip_horizontal: bool = True
    activation_delay_seconds: float = 0.05
    one_euro_min_cutoff: float = 1.0
    one_euro_beta: float = 0.007
    one_euro_d_cutoff: float = 1.0
    cursor_sensitivity: float = 1.0
    scroll_speed_multiplier: float = 1.0
    is_clutch_enabled: bool = True
    is_palm_swipe_enabled: bool = True
    show_hud: bool = True
    show_skeleton: bool = True
    show_click_feedback: bool = True
    yield_to_physical_mouse: bool = True
    camera_width: int = 640
    camera_height: int = 480
    span_multi_monitors: bool = False
    inference_backend: str = "cpu"

    def to_dict(self) -> dict:
        return {
            "first_launch_completed": self.first_launch_completed,
            "camera_index": self.camera_index,
            "flip_horizontal": self.flip_horizontal,
            "activation_delay_seconds": self.activation_delay_seconds,
            "one_euro_min_cutoff": self.one_euro_min_cutoff,
            "one_euro_beta": self.one_euro_beta,
            "one_euro_d_cutoff": self.one_euro_d_cutoff,
            "cursor_sensitivity": self.cursor_sensitivity,
            "scroll_speed_multiplier": self.scroll_speed_multiplier,
            "is_clutch_enabled": self.is_clutch_enabled,
            "is_palm_swipe_enabled": self.is_palm_swipe_enabled,
            "show_hud": self.show_hud,
            "show_skeleton": self.show_skeleton,
            "show_click_feedback": self.show_click_feedback,
            "yield_to_physical_mouse": self.yield_to_physical_mouse,
            "camera_width": self.camera_width,
            "camera_height": self.camera_height,
            "span_multi_monitors": self.span_multi_monitors,
            "inference_backend": self.inference_backend,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AppSettings":
        if not isinstance(data, dict):
            return cls()
        return cls(
            first_launch_completed=bool(data.get("first_launch_completed", False)),
            camera_index=int(data.get("camera_index", 0)),
            flip_horizontal=bool(data.get("flip_horizontal", True)),
            activation_delay_seconds=float(data.get("activation_delay_seconds", 0.05)),
            one_euro_min_cutoff=float(data.get("one_euro_min_cutoff", 1.0)),
            one_euro_beta=float(data.get("one_euro_beta", 0.007)),
            one_euro_d_cutoff=float(data.get("one_euro_d_cutoff", 1.0)),
            cursor_sensitivity=float(data.get("cursor_sensitivity", 1.0)),
            scroll_speed_multiplier=float(data.get("scroll_speed_multiplier", 1.0)),
            is_clutch_enabled=bool(data.get("is_clutch_enabled", True)),
            is_palm_swipe_enabled=bool(data.get("is_palm_swipe_enabled", True)),
            show_hud=bool(data.get("show_hud", True)),
            show_skeleton=bool(data.get("show_skeleton", True)),
            show_click_feedback=bool(data.get("show_click_feedback", True)),
            yield_to_physical_mouse=bool(data.get("yield_to_physical_mouse", True)),
            camera_width=int(data.get("camera_width", 640)),
            camera_height=int(data.get("camera_height", 480)),
            span_multi_monitors=bool(data.get("span_multi_monitors", False)),
            inference_backend=str(data.get("inference_backend", "cpu")),
        )
