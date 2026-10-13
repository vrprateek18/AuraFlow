"""
One Euro Filter Implementation for Windows
Based on Casiez, Roussel, Vogel (CHI 2012):
"1€ Filter: A Simple Speed-based Low-pass Filter for Noisy Input in HCI"
"""
import math
from typing import Optional, Tuple
from ..domain.models import Point2D

class OneEuroFilter1D:
    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.007, d_cutoff: float = 1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff

        self.x_prev: Optional[float] = None
        self.raw_prev: Optional[float] = None
        self.dx_prev: float = 0.0
        self.t_prev: Optional[float] = None

    def reset(self):
        self.x_prev = None
        self.raw_prev = None
        self.dx_prev = 0.0
        self.t_prev = None

    @staticmethod
    def _alpha(rate: float, cutoff: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff)
        te = 1.0 / rate
        return 1.0 / (1.0 + tau / te)

    def filter(self, x: float, timestamp: float) -> float:
        if not math.isfinite(x) or not math.isfinite(timestamp):
            return self.x_prev if self.x_prev is not None else 0.0

        if self.x_prev is None or self.t_prev is None:
            self.x_prev = x
            self.raw_prev = x
            self.t_prev = timestamp
            return x

        if timestamp <= self.t_prev:
            return self.x_prev

        if timestamp - self.t_prev > 0.25:
            self.reset()
            return self.filter(x, timestamp)

        dt = max(timestamp - self.t_prev, 1e-4)
        self.t_prev = timestamp
        rate = 1.0 / dt

        # Estimate derivative (velocity) with low-pass filtering
        raw_prev = self.raw_prev if self.raw_prev is not None else x
        dx = (x - raw_prev) * rate
        self.raw_prev = x

        a_d = self._alpha(rate=rate, cutoff=self.d_cutoff)
        dx_hat = a_d * dx + (1.0 - a_d) * self.dx_prev
        self.dx_prev = dx_hat

        # Dynamic cutoff based on speed
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = self._alpha(rate=rate, cutoff=cutoff)
        x_hat = a * x + (1.0 - a) * self.x_prev
        self.x_prev = x_hat
        return x_hat


class OneEuroFilter2D:
    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.007, d_cutoff: float = 1.0):
        self.x_filter = OneEuroFilter1D(min_cutoff=min_cutoff, beta=beta, d_cutoff=d_cutoff)
        self.y_filter = OneEuroFilter1D(min_cutoff=min_cutoff, beta=beta, d_cutoff=d_cutoff)

    def reset(self):
        self.x_filter.reset()
        self.y_filter.reset()

    def filter(self, point: Point2D, timestamp: float) -> Point2D:
        filtered_x = self.x_filter.filter(point.x, timestamp)
        filtered_y = self.y_filter.filter(point.y, timestamp)
        return Point2D(x=filtered_x, y=filtered_y)
