"""
Hand Command Menu Window (3x3 Grid Overlay)
1:1 replica of macOS CommandMenuWindow.swift
"""
import ctypes
from typing import Optional, List

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath
from PySide6.QtWidgets import QWidget

from ..core.domain.models import Point2D, GestureCommand
from ..core.interaction.command_menu import CommandMenuSnapshot, ALL_COMMANDS

COMMAND_INFO = [
    (GestureCommand.RIGHT_CLICK, "Right click", "🖱️"),
    (GestureCommand.DOUBLE_CLICK, "Double click", "🖱️🖱️"),
    (GestureCommand.MISSION_CONTROL, "All windows", "🪟"),
    (GestureCommand.PREVIOUS_APP, "Previous app", "⬅️"),
    (GestureCommand.NEXT_APP, "Next app", "➡️"),
    (GestureCommand.MINIMIZE, "Minimize", "➖"),
    (GestureCommand.FULL_SCREEN, "Full screen", "⛶"),
    (GestureCommand.SNAP_LEFT, "Left half", "◀▌"),
    (GestureCommand.SNAP_RIGHT, "Right half", "▐▶"),
]

class CommandMenuWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(560, 430)

        self.snapshot: Optional[CommandMenuSnapshot] = None
        self._center_on_screen()

    def _center_on_screen(self):
        screen = self.screen().geometry()
        self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)

    def update_snapshot(self, snapshot: Optional[CommandMenuSnapshot]):
        self.snapshot = snapshot
        if snapshot is not None and not self.isVisible():
            self.show()
        elif snapshot is None and self.isVisible():
            self.hide()
        self.update()

    def paintEvent(self, event):
        if self.snapshot is None:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Glass background
        card_rect = QRectF(0, 0, self.width(), self.height())
        path = QPainterPath()
        path.addRoundedRect(card_rect, 16, 16)
        painter.fillPath(path, QColor(7, 17, 31, 240))
        painter.setPen(QPen(QColor(32, 191, 234, 60), 1.2))
        painter.drawPath(path)

        # 2. Header
        painter.setPen(QColor(32, 191, 234, 240))
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.drawText(24, 34, "✋  HAND COMMANDS")

        painter.setPen(QColor(255, 255, 255, 140))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(self.width() - 120, 34, "Point · Pinch")

        # Subtitle
        sub_text = "Raise your index finger to begin" if self.snapshot.awaiting_pointer else "Move your hand to choose. Pinch to confirm."
        painter.setPen(QColor(255, 255, 255, 220))
        painter.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        painter.drawText(24, 62, sub_text)

        # 3. 3x3 Tile Grid
        grid_x = 24.0
        grid_y = 82.0
        grid_w = self.width() - 48.0
        grid_h = self.height() - 106.0

        cols = 3
        rows = 3
        spacing = 10.0
        tile_w = (grid_w - (cols - 1) * spacing) / cols
        tile_h = (grid_h - (rows - 1) * spacing) / rows

        for idx, (cmd, title, icon) in enumerate(COMMAND_INFO):
            c = idx % cols
            r = idx // cols
            tx = grid_x + c * (tile_w + spacing)
            ty = grid_y + r * (tile_h + spacing)
            t_rect = QRectF(tx, ty, tile_w, tile_h)

            is_selected = (self.snapshot.selected == cmd)

            t_path = QPainterPath()
            t_path.addRoundedRect(t_rect, 10, 10)

            if is_selected:
                painter.fillPath(t_path, QColor(0, 255, 200, 45))
                painter.setPen(QPen(QColor(0, 255, 200, 240), 2))
            else:
                painter.fillPath(t_path, QColor(255, 255, 255, 12))
                painter.setPen(QPen(QColor(255, 255, 255, 25), 1))

            painter.drawPath(t_path)

            # Icon
            painter.setFont(QFont("Segoe UI Emoji", 16))
            painter.setPen(QColor(255, 255, 255, 240) if is_selected else QColor(255, 255, 255, 180))
            painter.drawText(QRectF(tx, ty + 18, tile_w, 30), Qt.AlignmentFlag.AlignCenter, icon)

            # Title
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold if is_selected else QFont.Weight.Normal))
            painter.setPen(QColor(0, 255, 200, 255) if is_selected else QColor(255, 255, 255, 200))
            painter.drawText(QRectF(tx, ty + 52, tile_w, 24), Qt.AlignmentFlag.AlignCenter, title)

        # 4. Hand Virtual Pointer Dot
        if not self.snapshot.awaiting_pointer:
            px = grid_x + self.snapshot.pointer.x * grid_w
            py = grid_y + self.snapshot.pointer.y * grid_h

            # Outer glow
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(0, 255, 200, 60)))
            painter.drawEllipse(QPointF(px, py), 12, 12)

            # Inner dot
            painter.setBrush(QBrush(QColor(0, 255, 200, 250)))
            painter.drawEllipse(QPointF(px, py), 5, 5)
