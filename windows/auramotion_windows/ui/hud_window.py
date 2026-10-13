"""
AuraMotion Pro - Translucent Floating HUD Window
1:1 visual replica of macOS HUDView.swift
Frameless, non-activating, click-through, glassmorphic styling.
"""
import ctypes
from ctypes import wintypes
from typing import Optional, Dict

from PySide6.QtCore import Qt, QRectF, QPointF, QTimer, Signal
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPainterPath,
    QLinearGradient, QFontDatabase
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsDropShadowEffect
)

from ..core.domain.models import HandSample, GestureState, HandJointName

# Win32 click-through flags
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000

class HandSkeletonWidget(QWidget):
    """Draws live hand skeleton with anti-aliased glowing bones and joint nodes."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.sample: Optional[HandSample] = None
        self.setFixedHeight(140)
        self.setCursor(Qt.CursorShape.SizeAllCursor)

    def mousePressEvent(self, event):
        p = self.window()
        if p and hasattr(p, "mousePressEvent"):
            p.mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        p = self.window()
        if p and hasattr(p, "mouseMoveEvent"):
            p.mouseMoveEvent(event)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        p = self.window()
        if p and hasattr(p, "mouseReleaseEvent"):
            p.mouseReleaseEvent(event)
        else:
            super().mouseReleaseEvent(event)

    def set_sample(self, sample: Optional[HandSample]):
        self.sample = sample
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Dark translucent canvas background
        bg_rect = QRectF(0, 0, self.width(), self.height())
        path = QPainterPath()
        path.addRoundedRect(bg_rect, 8, 8)
        painter.fillPath(path, QColor(0, 0, 0, 140))
        painter.setPen(QPen(QColor(255, 255, 255, 20), 1))
        painter.drawPath(path)

        if self.sample is None or not self.sample.joints:
            # "No Hand Detected" placeholder
            painter.setPen(QColor(255, 255, 255, 90))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
            painter.drawText(bg_rect, Qt.AlignmentFlag.AlignCenter, "✋  No Hand Detected")
            return

        # Bone connections
        bones = [
            # Thumb
            (HandJointName.WRIST, HandJointName.THUMB_CMC),
            (HandJointName.THUMB_CMC, HandJointName.THUMB_MCP),
            (HandJointName.THUMB_MCP, HandJointName.THUMB_IP),
            (HandJointName.THUMB_IP, HandJointName.THUMB_TIP),
            # Index
            (HandJointName.WRIST, HandJointName.INDEX_MCP),
            (HandJointName.INDEX_MCP, HandJointName.INDEX_PIP),
            (HandJointName.INDEX_PIP, HandJointName.INDEX_DIP),
            (HandJointName.INDEX_DIP, HandJointName.INDEX_TIP),
            # Middle
            (HandJointName.WRIST, HandJointName.MIDDLE_MCP),
            (HandJointName.MIDDLE_MCP, HandJointName.MIDDLE_PIP),
            (HandJointName.MIDDLE_PIP, HandJointName.MIDDLE_DIP),
            (HandJointName.MIDDLE_DIP, HandJointName.MIDDLE_TIP),
            # Ring
            (HandJointName.WRIST, HandJointName.RING_MCP),
            (HandJointName.RING_MCP, HandJointName.RING_PIP),
            (HandJointName.RING_PIP, HandJointName.RING_DIP),
            (HandJointName.RING_DIP, HandJointName.RING_TIP),
            # Little
            (HandJointName.WRIST, HandJointName.LITTLE_MCP),
            (HandJointName.LITTLE_MCP, HandJointName.LITTLE_PIP),
            (HandJointName.LITTLE_PIP, HandJointName.LITTLE_DIP),
            (HandJointName.LITTLE_DIP, HandJointName.LITTLE_TIP),
            # Knuckle bridge
            (HandJointName.INDEX_MCP, HandJointName.MIDDLE_MCP),
            (HandJointName.MIDDLE_MCP, HandJointName.RING_MCP),
            (HandJointName.RING_MCP, HandJointName.LITTLE_MCP),
        ]

        w = self.width() - 20
        h = self.height() - 20
        off_x = 10
        off_y = 10

        # Draw bones
        pen_bone = QPen(QColor(0, 220, 255, 180), 2)
        painter.setPen(pen_bone)

        for j1_name, j2_name in bones:
            p1 = self.sample.joint(j1_name, min_confidence=0.1)
            p2 = self.sample.joint(j2_name, min_confidence=0.1)
            if p1 and p2:
                x1 = off_x + p1.x * w
                y1 = off_y + p1.y * h
                x2 = off_x + p2.x * w
                y2 = off_y + p2.y * h
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # Draw joints
        painter.setPen(Qt.PenStyle.NoPen)
        for name, joint in self.sample.joints.items():
            jx = off_x + joint.position.x * w
            jy = off_y + joint.position.y * h
            if name in (HandJointName.INDEX_TIP, HandJointName.THUMB_TIP):
                painter.setBrush(QBrush(QColor(0, 255, 200, 240)))
                painter.drawEllipse(QPointF(jx, jy), 3.5, 3.5)
            else:
                painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
                painter.drawEllipse(QPointF(jx, jy), 2.2, 2.2)


class FloatingHUDWindow(QWidget):
    visibility_changed = Signal(bool)

    def __init__(self):
        super().__init__()
        self.is_compact = False
        self._drag_pos = None
        self._dock_index = 0  # 0: Top-Right, 1: Bottom-Right, 2: Bottom-Left, 3: Top-Left

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(230)
        self.setCursor(Qt.CursorShape.SizeAllCursor)

        self._init_ui()
        self._position_top_right()
        # Default to interactive/movable so user can position it anywhere on desktop
        self._enable_click_through(False)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        event.accept()

    def _init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 10, 12, 10)
        self.layout.setSpacing(8)

        # 1. Header Bar with Drag Grips and Window Controls
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(5)

        # Move grip icon
        self.grip_lbl = QLabel("⠿")
        self.grip_lbl.setStyleSheet("color: rgba(32, 191, 234, 0.85); font-size: 13px; font-weight: bold;")
        self.grip_lbl.setToolTip("Click and drag anywhere to move HUD")
        header.addWidget(self.grip_lbl)

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #20BFEA; font-size: 11px;")
        header.addWidget(self.status_dot)

        self.title_lbl = QLabel("AuraFlow")
        self.title_lbl.setStyleSheet("color: rgba(255,255,255,0.95); font-weight: 800; font-size: 11px; font-family: 'Segoe UI', 'Consolas', sans-serif; letter-spacing: 0.5px;")
        self.title_lbl.setToolTip("Click and drag to reposition HUD")
        header.addWidget(self.title_lbl)

        header.addStretch()

        # Snap to corner button
        self.dock_btn = QPushButton("⬚")
        self.dock_btn.setFixedSize(18, 18)
        self.dock_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dock_btn.setToolTip("Snap HUD to next screen corner")
        self.dock_btn.setStyleSheet("""
            QPushButton { background: transparent; color: rgba(255,255,255,0.6); border: none; font-size: 11px; font-weight: bold; }
            QPushButton:hover { color: #20BFEA; background: rgba(32, 191, 234, 0.15); border-radius: 3px; }
        """)
        self.dock_btn.clicked.connect(self._cycle_dock_corner)
        header.addWidget(self.dock_btn)

        # Compact toggle button
        self.compact_btn = QPushButton("▲")
        self.compact_btn.setFixedSize(18, 18)
        self.compact_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.compact_btn.setToolTip("Minimize / expand HUD")
        self.compact_btn.setStyleSheet("""
            QPushButton { background: transparent; color: rgba(255,255,255,0.6); border: none; font-size: 8px; }
            QPushButton:hover { color: white; background: rgba(255,255,255,0.1); border-radius: 3px; }
        """)
        self.compact_btn.clicked.connect(self._toggle_compact)
        header.addWidget(self.compact_btn)

        # Close / Hide button
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(18, 18)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setToolTip("Hide floating HUD (can reopen from Control Center)")
        self.close_btn.setStyleSheet("""
            QPushButton { background: transparent; color: rgba(255,100,100,0.7); border: none; font-size: 9px; font-weight: bold; }
            QPushButton:hover { color: #FF334B; background: rgba(255,255,255,0.1); border-radius: 3px; }
        """)
        self.close_btn.clicked.connect(self.hide)
        header.addWidget(self.close_btn)

        self.layout.addLayout(header)

        # 2. Status Pill & Latency
        pill_layout = QHBoxLayout()
        pill_layout.setContentsMargins(0, 0, 0, 0)

        self.status_pill = QLabel("READY")
        self.status_pill.setStyleSheet("""
            background: rgba(0, 255, 200, 0.15);
            color: #00FFC8;
            font-size: 10px;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 5px;
        """)
        pill_layout.addWidget(self.status_pill)
        pill_layout.addStretch()

        self.latency_lbl = QLabel("0.0 ms")
        self.latency_lbl.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 9px; font-family: 'Consolas', monospace;")
        pill_layout.addWidget(self.latency_lbl)
        self.layout.addLayout(pill_layout)

        # 3. Skeleton Canvas
        self.skeleton_widget = HandSkeletonWidget(self)
        self.layout.addWidget(self.skeleton_widget)

        # 4. Telemetry Footer
        self.footer = QHBoxLayout()
        self.footer.setContentsMargins(0, 0, 0, 0)
        self.footer.setSpacing(10)

        self.cap_lbl = QLabel("CAP 60")
        self.cap_lbl.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 8px; font-weight: 600;")
        self.inf_lbl = QLabel("INF 60")
        self.inf_lbl.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 8px; font-weight: 600;")
        self.cpu_lbl = QLabel("CPU 0%")
        self.cpu_lbl.setStyleSheet("color: rgba(0,255,200,0.7); font-size: 8px; font-weight: 600;")
        self.gpu_lbl = QLabel("GPU 0%")
        self.gpu_lbl.setStyleSheet("color: rgba(0,191,255,0.7); font-size: 8px; font-weight: 600;")
        self.drop_lbl = QLabel("DROP 0")
        self.drop_lbl.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 8px; font-weight: 600;")

        self.footer.addWidget(self.cap_lbl)
        self.footer.addWidget(self.inf_lbl)
        self.footer.addWidget(self.cpu_lbl)
        self.footer.addWidget(self.gpu_lbl)
        self.footer.addWidget(self.drop_lbl)
        self.footer.addStretch()
        self.layout.addLayout(self.footer)

    def _toggle_compact(self):
        self.is_compact = not self.is_compact
        self.skeleton_widget.setVisible(not self.is_compact)
        self.cap_lbl.setVisible(not self.is_compact)
        self.inf_lbl.setVisible(not self.is_compact)
        self.cpu_lbl.setVisible(not self.is_compact)
        self.gpu_lbl.setVisible(not self.is_compact)
        self.drop_lbl.setVisible(not self.is_compact)
        self.compact_btn.setText("▼" if self.is_compact else "▲")
        self.adjustSize()

    def _cycle_dock_corner(self):
        """Snaps the HUD sequentially between the 4 corners of the screen."""
        screen = self.screen().geometry()
        w = self.width()
        h = self.height()
        corners = [
            (screen.width() - w - 25, 45),                       # Top-Right
            (screen.width() - w - 25, screen.height() - h - 65), # Bottom-Right
            (25, screen.height() - h - 65),                      # Bottom-Left
            (25, 45)                                             # Top-Left
        ]
        self._dock_index = (self._dock_index + 1) % len(corners)
        x, y = corners[self._dock_index]
        self.move(x, y)

    def _position_top_right(self):
        screen = self.screen().geometry()
        self.move(screen.width() - self.width() - 25, 45)

    def _enable_click_through(self, enable: bool):
        """Toggle click-through transparent hit-testing via Win32 extended window styles."""
        try:
            hwnd = int(self.winId())
            user32 = ctypes.windll.user32
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if enable:
                style |= (WS_EX_TRANSPARENT | WS_EX_LAYERED)
            else:
                style &= ~WS_EX_TRANSPARENT
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        except Exception:
            pass

    def hide(self):
        super().hide()
        self.visibility_changed.emit(False)

    def show(self):
        super().show()
        self.visibility_changed.emit(True)

    def update_telemetry(
        self,
        state: GestureState,
        sample: Optional[HandSample],
        cap_fps: float,
        inf_fps: float,
        p95_ms: float,
        dropped: int = 0,
        e2e_ms: float = 0.0,
        cpu_pct: float = 0.0,
        gpu_pct: float = 0.0
    ):
        # Update status pill and color
        status_text = "PAUSED (F8)" if state == GestureState.PAUSED else state.display_name
        self.status_pill.setText(status_text)
        color = "#00FFC8"
        bg_alpha = "0.15"

        if state in (GestureState.PINCH_ARMED, GestureState.POINTING):
            color = "#00FFC8"
        elif state == GestureState.DRAGGING:
            color = "#FFA500"
            bg_alpha = "0.25"
        elif state == GestureState.SCROLLING:
            color = "#00BFFF"
        elif state in (GestureState.PALM_REST, GestureState.COMMAND_MENU):
            color = "#BB86FC"
        elif state == GestureState.PAUSED:
            color = "#FF4D6D"
            bg_alpha = "0.30"
        elif state == GestureState.TRACKING_LOST:
            color = "#FFB703"
            bg_alpha = "0.20"

        self.status_dot.setStyleSheet(f"color: {color}; font-size: 11px;")
        self.status_pill.setStyleSheet(f"""
            background: rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, {bg_alpha});
            color: {color};
            font-size: 10px;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 5px;
        """)

        lat_display = f"E2E {e2e_ms:.1f}ms" if e2e_ms > 0 else f"{p95_ms:.1f} ms"
        self.latency_lbl.setText(lat_display)
        self.cap_lbl.setText(f"CAP {int(cap_fps)}")
        self.inf_lbl.setText(f"INF {int(inf_fps)}")
        self.cpu_lbl.setText(f"CPU {int(cpu_pct)}%")
        self.gpu_lbl.setText(f"GPU {int(gpu_pct)}%")
        self.drop_lbl.setText(f"DROP {dropped}")

        self.skeleton_widget.set_sample(sample)

    def paintEvent(self, event):
        # Glassmorphic rounded background matching SwiftUI .ultraThinMaterial
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(0, 0, self.width(), self.height())
        path = QPainterPath()
        path.addRoundedRect(rect, 12, 12)

        # Frosted glass dark fill
        painter.fillPath(path, QColor(20, 22, 28, 215))

        # Subtle translucent border
        pen = QPen(QColor(255, 255, 255, 30), 1)
        painter.setPen(pen)
        painter.drawPath(path)
