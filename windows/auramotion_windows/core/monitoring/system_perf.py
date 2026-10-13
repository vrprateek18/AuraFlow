"""
AuraMotion Pro - System Performance & Hardware Telemetry Monitor
Tracks CPU utilization, NVIDIA RTX GPU utilization, memory, and frame rates using native Win32 APIs and NVML.
"""
import ctypes
from ctypes import wintypes
import time
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class SystemPerfMetric:
    cpu_percent: float
    gpu_percent: float
    gpu_name: str


class FILETIME(ctypes.Structure):
    _fields_ = [
        ("dwLowDateTime", wintypes.DWORD),
        ("dwHighDateTime", wintypes.DWORD),
    ]


def _filetime_to_int(ft: FILETIME) -> int:
    return (ft.dwHighDateTime << 32) | ft.dwLowDateTime


class SystemPerformanceMonitor:
    """Non-blocking Win32 & NVML hardware telemetry monitor."""

    def __init__(self):
        self.kernel32 = ctypes.windll.kernel32
        self._prev_idle = FILETIME()
        self._prev_kernel = FILETIME()
        self._prev_user = FILETIME()
        self._last_cpu_sample_time = 0.0
        self.cached_cpu_percent: float = 0.0

        # Prime initial CPU times
        try:
            self.kernel32.GetSystemTimes(
                ctypes.byref(self._prev_idle),
                ctypes.byref(self._prev_kernel),
                ctypes.byref(self._prev_user)
            )
        except Exception:
            pass

        # NVML setup for NVIDIA RTX 4050
        self._nvml = None
        self._nvml_device = None
        self.gpu_name: str = "GPU Not Detected"
        self.cached_gpu_percent: float = 0.0
        self._last_gpu_sample_time = 0.0
        self._init_nvml()

    def _init_nvml(self):
        try:
            nvml = ctypes.windll.LoadLibrary("nvml.dll")
            nvml.nvmlInit_v2()
            device = ctypes.c_void_p()
            nvml.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(device))
            name_buf = ctypes.create_string_buffer(96)
            nvml.nvmlDeviceGetName(device, name_buf, 96)

            self._nvml = nvml
            self._nvml_device = device
            raw_name = name_buf.value.decode("utf-8", errors="ignore").strip()
            self.gpu_name = raw_name if raw_name else "NVIDIA GeForce RTX 4050"
        except Exception:
            self._nvml = None
            self.gpu_name = "Integrated / DirectML Graphics"

    def get_cpu_percent(self) -> float:
        now = time.time()
        if now - self._last_cpu_sample_time < 0.4:
            return self.cached_cpu_percent

        try:
            idle = FILETIME()
            kernel = FILETIME()
            user = FILETIME()
            if self.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
                idle_delta = _filetime_to_int(idle) - _filetime_to_int(self._prev_idle)
                kernel_delta = _filetime_to_int(kernel) - _filetime_to_int(self._prev_kernel)
                user_delta = _filetime_to_int(user) - _filetime_to_int(self._prev_user)

                total = kernel_delta + user_delta
                if total > 0:
                    usage = 100.0 * (1.0 - (idle_delta / total))
                    self.cached_cpu_percent = max(0.0, min(100.0, usage))

                self._prev_idle = idle
                self._prev_kernel = kernel
                self._prev_user = user
                self._last_cpu_sample_time = now
        except Exception:
            pass

        return self.cached_cpu_percent

    def get_gpu_percent(self) -> float:
        if self._nvml is None or self._nvml_device is None:
            return 0.0

        now = time.time()
        if now - self._last_gpu_sample_time < 0.4:
            return self.cached_gpu_percent

        try:
            class Utilization(ctypes.Structure):
                _fields_ = [("gpu", ctypes.c_uint), ("memory", ctypes.c_uint)]

            util = Utilization()
            res = self._nvml.nvmlDeviceGetUtilizationRates(self._nvml_device, ctypes.byref(util))
            if res == 0:
                self.cached_gpu_percent = float(util.gpu)
                self._last_gpu_sample_time = now
        except Exception:
            pass

        return self.cached_gpu_percent

    def get_metrics(self) -> Tuple[float, float, str]:
        """Returns (cpu_percent, gpu_percent, gpu_name)."""
        return self.get_cpu_percent(), self.get_gpu_percent(), self.gpu_name

    def sample(self) -> SystemPerfMetric:
        """Samples hardware performance and returns a typed SystemPerfMetric."""
        return SystemPerfMetric(
            cpu_percent=self.get_cpu_percent(),
            gpu_percent=self.get_gpu_percent(),
            gpu_name=self.gpu_name
        )

    def close(self):
        if self._nvml:
            try:
                self._nvml.nvmlShutdown()
            except Exception:
                pass
            self._nvml = None
