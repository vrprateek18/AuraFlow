"""
Click and Drag Feedback Overlay Window
1:1 visual replica of macOS ClickFeedbackWindow.swift
Draws a subtle animated expanding ripple circle on clicks and a drag halo.
"""
import ctypes
import time
from typing import Optional, List

from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush
from PySide6.QtWidgets import QWidget

from ..core.domain.models import Point2D

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000

class Ripple:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.start_time = time.time()
        self.duration = 0.25  # 250 ms

    @property
    def progress(self) -> float:
        return min(1.0, (time.time() - self.start_time) / self.duration)

    @property
    def is_finished(self) -> bool:
        return (time.time() - self.start_time) >= self.duration


class ClickFeedbackOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Full screen coverage
        screen = self.screen().geometry()
        self.setGeometry(screen)

        self.ripples: List[Ripple] = []
        self.drag_current: Optional[Point2D] = None
        self.drag_anchor: Optional[Point2D] = None

        self._enable_click_through()

        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(16)  # ~60 fps
        self.anim_timer.timeout.connect(self._on_tick)

    def _enable_click_through(self):
        hwnd = int(self.winId())
        user32 = ctypes.windll.user32
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style |= (WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_NOACTIVATE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

    def trigger_click(self, x: float, y: float):
        self.ripples.append(Ripple(x, y))
        if not self.anim_timer.isActive():
            self.anim_timer.start()
        self.update()

    def update_drag(self, current: Optional[Point2D], anchor: Optional[Point2D] = None):
        self.drag_current = current
        self.drag_anchor = anchor
        if current is not None and not self.anim_timer.isActive():
            self.anim_timer.start()
        self.update()

    def _on_tick(self):
        self.ripples = [r for r in self.ripples if not r.is_finished]
        if not self.ripples and self.drag_current is None:
            self.anim_timer.stop()
        self.update()

    def paintEvent(self, event):
        if not self.ripples and self.drag_current is None:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw expanding ripples
        for ripple in self.ripples:
            p = ripple.progress
            radius = 6.0 + p * 24.0
            alpha = int((1.0 - p) * 220)
            pen = QPen(QColor(32, 191, 234, alpha), 2.5)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(ripple.x, ripple.y), radius, radius)

        # Draw drag indicators
        if self.drag_current is not None:
            if self.drag_anchor is not None:
                # Drag connector line
                pen_line = QPen(QColor(255, 165, 0, 100), 1.5, Qt.PenStyle.DashLine)
                painter.setPen(pen_line)
                painter.drawLine(QPointF(self.drag_anchor.x, self.drag_anchor.y), QPointF(self.drag_current.x, self.drag_current.y))

                # Anchor ring
                painter.setPen(QPen(QColor(255, 165, 0, 160), 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(QPointF(self.drag_anchor.x, self.drag_anchor.y), 8, 8)

            # Current drag dot
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(255, 165, 0, 200)))
            painter.drawEllipse(QPointF(self.drag_current.x, self.drag_current.y), 5, 5)
