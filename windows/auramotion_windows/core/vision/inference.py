"""
Hand Pose Inference Worker
Decodes 21 hand landmarks into HandSample models matching Apple Vision VNDetectHumanHandPoseRequest.
"""
import os
import time
from typing import Optional, List, Dict
import numpy as np
import cv2

import mediapipe as mp
from ..domain.models import (
    Point2D, HandJoint, HandJointName, HandSample,
    MEDIAPIPE_JOINT_MAP
)

class VisionInferenceWorker:
    def __init__(self, model_path: str = "hand_landmarker.task", flip_horizontal: bool = True):
        self.model_path = model_path
        self.flip_horizontal = flip_horizontal
        self.landmarker = None

        self.last_inference_time_ms: float = 0.0
        self.inference_fps: float = 0.0
        self._fps_counter: int = 0
        self._fps_timer: float = time.time()
        self._recent_latencies: List[float] = []

        self._tracking_id_counter: int = 1

    def initialize(self) -> bool:
        if not os.path.exists(self.model_path):
            return False

        try:
            options = mp.tasks.vision.HandLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=self.model_path),
                running_mode=mp.tasks.vision.RunningMode.IMAGE,
                num_hands=1,
                min_hand_detection_confidence=0.5,
                min_hand_presence_confidence=0.5,
                min_tracking_confidence=0.5
            )
            self.landmarker = mp.tasks.vision.HandLandmarker.create_from_options(options)
            return True
        except Exception as e:
            print("Error initializing HandLandmarker:", e)
            return False

    def close(self):
        if self.landmarker is not None:
            self.landmarker.close()
            self.landmarker = None

    def process_frame(self, frame_bgr: np.ndarray, timestamp: float) -> Optional[HandSample]:
        if self.landmarker is None:
            return None

        t0 = time.time()

        if self.flip_horizontal:
            frame_proc = cv2.flip(frame_bgr, 1)
        else:
            frame_proc = frame_bgr

        frame_rgb = cv2.cvtColor(frame_proc, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

        result = self.landmarker.detect(mp_image)

        dt_ms = (time.time() - t0) * 1000.0
        self.last_inference_time_ms = dt_ms

        self._recent_latencies.append(dt_ms)
        if len(self._recent_latencies) > 60:
            self._recent_latencies.pop(0)

        self._fps_counter += 1
        now = time.time()
        if self._fps_counter == 1 and self.inference_fps == 0.0:
            self._fps_timer = now
        elif now - self._fps_timer >= 1.0:
            self.inference_fps = self._fps_counter / (now - self._fps_timer)
            self._fps_counter = 0
            self._fps_timer = now

        if not result.hand_landmarks or len(result.hand_landmarks) == 0:
            return None

        landmarks = result.hand_landmarks[0]
        handedness_list = result.handedness
        handedness = "right"
        overall_conf = 0.92
        if handedness_list and len(handedness_list) > 0 and len(handedness_list[0]) > 0:
            top_category = handedness_list[0][0]
            handedness = top_category.category_name.lower()

        joints: Dict[HandJointName, HandJoint] = {}
        for idx, lm in enumerate(landmarks):
            if idx < len(MEDIAPIPE_JOINT_MAP):
                joint_name = MEDIAPIPE_JOINT_MAP[idx]
                joints[joint_name] = HandJoint(
                    name=joint_name,
                    position=Point2D(x=float(lm.x), y=float(lm.y)),
                    confidence=overall_conf,
                    z=float(lm.z)
                )

        return HandSample(
            host_timestamp=timestamp,
            presentation_time_seconds=timestamp,
            is_presentation_time_estimated=False,
            joints=joints,
            overall_confidence=overall_conf,
            estimated_handedness=handedness,
            tracking_id=self._tracking_id_counter
        )

    @property
    def p95_latency_ms(self) -> float:
        if not self._recent_latencies:
            return 0.0
        return float(np.percentile(self._recent_latencies, 95))
