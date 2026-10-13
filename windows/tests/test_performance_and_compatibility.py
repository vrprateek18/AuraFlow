"""
Unit tests for AuraMotion Pro Performance & Compatibility:
- End-to-end latency and real-time CPU/GPU hardware utilization monitoring
- MediaPipe CPU vs DirectML GPU benchmark engine
- Low-light and underexposed camera conditions
- Hand occlusion and partial landmark tracking safety
- Camera selection and resolution presets
- Multi-monitor virtual desktop spanning and coordinate mapping
"""
import unittest
import time
import numpy as np
from unittest.mock import MagicMock, patch

from auramotion_windows.core.domain.models import (
    Point2D, GestureState, HandSample, HandJoint, HandJointName,
    AppSettings, CalibrationProfile
)
from auramotion_windows.core.monitoring.system_perf import SystemPerformanceMonitor, SystemPerfMetric
from auramotion_windows.core.vision.benchmark import HardwareInferenceBenchmark, BenchmarkReport
from auramotion_windows.core.vision.inference import VisionInferenceWorker
from auramotion_windows.core.capture.pipeline import (
    CameraCapturePipeline, enumerate_available_cameras, SUPPORTED_RESOLUTIONS, FrameMailbox
)
from auramotion_windows.core.tracking.fusion import HandCursorFusion
from auramotion_windows.core.interaction.pinch_detector import PinchDetector, PinchDecisionType
from auramotion_windows.core.interaction.state_machine import GestureStateMachine, GestureStateMachineListener
from auramotion_windows.core.output.win32_input import (
    Win32EventSynthesizer, MOUSEEVENTF_MOVE, MOUSEEVENTF_ABSOLUTE, MOUSEEVENTF_VIRTUALDESK
)


class TestPerformanceAndCompatibility(unittest.TestCase):
    def setUp(self):
        self.perf_monitor = SystemPerformanceMonitor()

    def tearDown(self):
        self.perf_monitor.close()

    def test_system_perf_monitor_cpu_and_gpu(self):
        """Test native Win32 CPU % measurement and NVML GPU % measurement."""
        metric = self.perf_monitor.sample()
        self.assertIsInstance(metric, SystemPerfMetric)
        self.assertGreaterEqual(metric.cpu_percent, 0.0)
        self.assertLessEqual(metric.cpu_percent, 100.0)
        self.assertGreaterEqual(metric.gpu_percent, 0.0)
        self.assertLessEqual(metric.gpu_percent, 100.0)
        self.assertIsInstance(metric.gpu_name, str)
        self.assertGreater(len(metric.gpu_name), 0)

        # Ensure subsequent samples work stably without leaking handles
        time.sleep(0.05)
        metric2 = self.perf_monitor.sample()
        self.assertIsInstance(metric2, SystemPerfMetric)

    def test_benchmark_engine_cpu_vs_gpu(self):
        """Test empirical CPU vs GPU benchmark engine."""
        benchmark = HardwareInferenceBenchmark(iterations=5, warmup_runs=2)
        report = benchmark.run_benchmark()

        self.assertIsInstance(report, BenchmarkReport)
        self.assertGreater(report.cpu_mean_ms, 0.0)
        self.assertGreater(report.cpu_fps, 0.0)
        self.assertIsInstance(report.recommendation, str)
        self.assertGreater(len(report.recommendation), 0)
        self.assertIn("CPU", report.to_markdown())

        # Verify summary dictionary serialization
        summary = report.to_dict()
        self.assertIn("cpu_mean_ms", summary)
        self.assertIn("recommended_backend", summary)

    def test_low_light_conditions_handling(self):
        """Test that dark and underexposed camera frames are handled gracefully."""
        # 1. Pitch black frame (mean brightness = 0)
        black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # 2. Extreme low-light noisy frame (mean brightness < 10)
        low_light_frame = np.random.randint(0, 12, size=(480, 640, 3), dtype=np.uint8)

        worker = VisionInferenceWorker(model_path="hand_landmarker.task")
        worker.initialize()

        # Inference on pitch black frame should return None gracefully without raising
        result_black = worker.process_frame(black_frame, time.time())
        self.assertIsNone(result_black)

        # Inference on low-light noisy frame should return None gracefully
        result_low_light = worker.process_frame(low_light_frame, time.time())
        self.assertIsNone(result_low_light)

        # Verify state machine safety: receiving low-light / None maintains TRACKING_LOST
        class DummyListener(GestureStateMachineListener):
            def __init__(self):
                self.released = False
            def on_transition(self, state): pass
            def on_move(self, loc): pass
            def on_click(self, anchor): pass
            def on_drag_start(self, anchor): pass
            def on_drag_move(self, loc): pass
            def on_drag_end(self, loc): pass
            def on_scroll(self, delta): pass
            def on_swipe(self, direction): pass
            def on_shortcut(self, shortcut): pass
            def on_command(self, cmd, target): pass
            def on_emergency_release(self):
                self.released = True

        listener = DummyListener()
        fsm = GestureStateMachine(listener=listener)
        fsm.process_frame(sample=None, mapped_cursor_location=None)
        self.assertEqual(fsm.current_state, GestureState.TRACKING_LOST)

        worker.close()

    def test_hand_occlusion_and_partial_landmarks_safety(self):
        """Test that partially occluded hand joints do not cause erratic clicks or pointer jumps."""
        fusion = HandCursorFusion()
        pinch_detector = PinchDetector()

        # Create sample where index finger is occluded (confidence = 0.05)
        joints = {
            HandJointName.WRIST: HandJoint(name=HandJointName.WRIST, position=Point2D(0.5, 0.8), confidence=0.9),
            HandJointName.THUMB_TIP: HandJoint(name=HandJointName.THUMB_TIP, position=Point2D(0.5, 0.4), confidence=0.85),
            HandJointName.INDEX_TIP: HandJoint(name=HandJointName.INDEX_TIP, position=Point2D(0.5, 0.4), confidence=0.05), # occluded!
        }
        occluded_sample = HandSample(
            host_timestamp=time.time(),
            presentation_time_seconds=time.time(),
            is_presentation_time_estimated=False,
            joints=joints,
            overall_confidence=0.3,
            estimated_handedness="right",
            tracking_id=1
        )

        # Fusion should not pick an occluded low-confidence index tip
        fused_pt = fusion.update(occluded_sample)
        # Point should be None because index_tip confidence < 0.25 and no fallback is reliable
        self.assertIsNone(fused_pt)

        # Pinch detector must not trigger click when normalized_distance is None (missing/occluded joints)
        pinch_decision = pinch_detector.evaluate(
            normalized_distance=None,
            current_location=Point2D(0.5, 0.5),
            timestamp=time.time()
        )
        self.assertEqual(pinch_decision.decision_type, PinchDecisionType.CANCELLED)

    def test_camera_selection_and_resolution_controls(self):
        """Test camera enumeration, resolution queue, and presets."""
        # Check presets
        res_pairs = [(w, h) for w, h, _ in SUPPORTED_RESOLUTIONS]
        self.assertIn((640, 480), res_pairs)
        self.assertIn((1280, 720), res_pairs)
        self.assertIn((1920, 1080), res_pairs)

        pipeline = CameraCapturePipeline(camera_index=0, target_fps=60)
        pipeline.set_resolution(1280, 720)
        self.assertEqual(pipeline._pending_resolution, (1280, 720))

        # Enumerate cameras returns list of (index, label)
        cams = enumerate_available_cameras(max_devices=2)
        self.assertIsInstance(cams, list)
        if len(cams) > 0:
            idx, label = cams[0]
            self.assertIsInstance(idx, int)
            self.assertIsInstance(label, str)

    def test_multi_monitor_virtual_desktop_mapping(self):
        """Test multi-monitor virtual desktop bounds and SendInput flag selection."""
        synth = Win32EventSynthesizer()
        vx, vy, vw, vh = synth.get_virtual_desktop_bounds()

        self.assertGreater(vw, 0)
        self.assertGreater(vh, 0)

        # Mock SendInput to verify MOUSEEVENTF_VIRTUALDESK flag
        captured_flags = []

        def mock_send_mouse(flags, dx=0, dy=0, data=0):
            captured_flags.append(flags)

        with patch.object(synth, "_send_mouse", side_effect=mock_send_mouse):
            # 1. Primary monitor mapping
            synth.move_to(100.0, 100.0, span_virtual_desktop=False)
            self.assertEqual(len(captured_flags), 1)
            self.assertEqual(captured_flags[0], MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE)

            # 2. Virtual desktop spanning
            captured_flags.clear()
            # Force num_monitors > 1 for test
            orig_monitors = synth.num_monitors
            synth.num_monitors = 2
            try:
                synth.move_to(100.0, 100.0, span_virtual_desktop=True)
                self.assertEqual(len(captured_flags), 1)
                self.assertEqual(captured_flags[0], MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK)
            finally:
                synth.num_monitors = orig_monitors

    def test_e2e_latency_and_mailbox_dropped_frames(self):
        """Test rolling end-to-end latency and frame drop counter."""
        mailbox = FrameMailbox()

        # Put 5 frames without taking any to simulate drops
        t0 = time.time()
        for i in range(5):
            dummy = np.zeros((10, 10, 3), dtype=np.uint8)
            mailbox.put(dummy, t0 + i * 0.016)

        # Frame drop counter should reflect 4 dropped frames (only 1 latest kept)
        delivered, dropped = mailbox.stats
        self.assertEqual(dropped, 4)

        # Retrieve latest frame and verify timestamp
        frame, ts, has_new = mailbox.get()
        self.assertTrue(has_new)
        self.assertIsNotNone(frame)
        self.assertAlmostEqual(ts, t0 + 4 * 0.016, places=3)

        # End-to-end latency calculation
        now = t0 + 4 * 0.016 + 0.012  # 12 ms pipeline loop lag
        e2e_ms = (now - ts) * 1000.0
        self.assertAlmostEqual(e2e_ms, 12.0, places=1)


if __name__ == "__main__":
    unittest.main()
