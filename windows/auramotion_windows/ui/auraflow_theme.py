"""
AuraFlow - Premium Design Tokens, Theme Stylesheet & Vector Graphics
Brand Palette:
- Midnight Navy Background: #07111F
- Deep Blue Card Surface:   #0D1C2E / #123149
- Primary Flow Cyan:        #20BFEA
- Ice-Blue Highlights:      #8CEBFF
- Muted Typography:         #8EABC0
- Emergency / Alert Coral:  #FF3B5C
- Success Green:            #00E5A3
"""
import math
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (
    QColor, QLinearGradient, QPainter, QPainterPath, QPen, QBrush, QFont
)

# ── Color Palette ──
COLOR_BG_DARK = "#07111F"
COLOR_BG_CARD = "#0D1C2E"
COLOR_BG_CARD_HOVER = "#12283E"
COLOR_SURFACE = "#123149"
COLOR_PRIMARY_CYAN = "#20BFEA"
COLOR_ICE_BLUE = "#8CEBFF"
COLOR_TEXT_PRIMARY = "#FFFFFF"
COLOR_TEXT_MUTED = "#8EABC0"
COLOR_TEXT_DIM = "#567085"
COLOR_BORDER = "rgba(32, 191, 234, 0.22)"
COLOR_BORDER_HOVER = "rgba(140, 235, 255, 0.55)"
COLOR_ACCENT_CORAL = "#FF3B5C"
COLOR_SUCCESS = "#00E5A3"


def get_auraflow_stylesheet() -> str:
    """Returns the unified AuraFlow Qt stylesheet."""
    return f"""
    QMainWindow, QDialog {{
        background-color: {COLOR_BG_DARK};
        color: {COLOR_TEXT_PRIMARY};
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
    }}
    QWidget {{
        color: {COLOR_TEXT_PRIMARY};
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
    }}
    QGroupBox {{
        font-weight: 700;
        border: 1px solid {COLOR_BORDER};
        border-radius: 10px;
        margin-top: 14px;
        padding: 16px;
        background-color: rgba(13, 28, 46, 0.65);
        color: {COLOR_PRIMARY_CYAN};
        font-size: 12px;
        letter-spacing: 0.5px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 14px;
        padding: 0 6px;
        background-color: {COLOR_BG_DARK};
    }}
    QLabel {{
        font-size: 12px;
        color: {COLOR_TEXT_MUTED};
    }}
    QPushButton {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLOR_PRIMARY_CYAN}, stop:1 #14A3CB);
        color: #050B14;
        font-weight: 700;
        border: 1px solid {COLOR_ICE_BLUE};
        border-radius: 8px;
        padding: 9px 18px;
        font-size: 12px;
    }}
    QPushButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLOR_ICE_BLUE}, stop:1 {COLOR_PRIMARY_CYAN});
        border: 1px solid #FFFFFF;
    }}
    QPushButton:pressed {{
        background-color: #0E8EA8;
    }}
    QPushButton#secondaryBtn {{
        background: rgba(18, 49, 73, 0.6);
        color: {COLOR_ICE_BLUE};
        border: 1px solid {COLOR_BORDER};
    }}
    QPushButton#secondaryBtn:hover {{
        background: rgba(32, 191, 234, 0.18);
        border: 1px solid {COLOR_PRIMARY_CYAN};
        color: #FFFFFF;
    }}
    QPushButton#outlineBtn {{
        background: transparent;
        color: {COLOR_TEXT_MUTED};
        border: 1px solid rgba(142, 171, 192, 0.3);
    }}
    QPushButton#outlineBtn:hover {{
        background: rgba(255, 255, 255, 0.06);
        color: #FFFFFF;
        border: 1px solid {COLOR_TEXT_MUTED};
    }}
    QCheckBox {{
        font-size: 12px;
        color: {COLOR_TEXT_PRIMARY};
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 1px solid {COLOR_BORDER};
        background: {COLOR_BG_CARD};
    }}
    QCheckBox::indicator:checked {{
        background: {COLOR_PRIMARY_CYAN};
        border: 1px solid {COLOR_ICE_BLUE};
        image: none;
    }}
    QSlider::groove:horizontal {{
        height: 5px;
        background: rgba(18, 49, 73, 0.8);
        border-radius: 2px;
    }}
    QSlider::sub-page:horizontal {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLOR_PRIMARY_CYAN}, stop:1 {COLOR_ICE_BLUE});
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: #FFFFFF;
        border: 2px solid {COLOR_PRIMARY_CYAN};
        width: 16px;
        margin: -6px 0;
        border-radius: 8px;
    }}
    QComboBox {{
        background-color: {COLOR_BG_CARD};
        border: 1px solid {COLOR_BORDER};
        border-radius: 6px;
        padding: 6px 12px;
        color: {COLOR_TEXT_PRIMARY};
        font-size: 12px;
    }}
    QComboBox:hover {{
        border: 1px solid {COLOR_PRIMARY_CYAN};
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 24px;
        border-left: 1px solid {COLOR_BORDER};
    }}
    QComboBox QAbstractItemView {{
        background-color: #0B1726;
        color: white;
        selection-background-color: {COLOR_PRIMARY_CYAN};
        selection-color: #050B14;
        border: 1px solid {COLOR_BORDER};
        border-radius: 4px;
        padding: 4px;
    }}
    QProgressBar {{
        background-color: rgba(13, 28, 46, 0.8);
        border: 1px solid {COLOR_BORDER};
        border-radius: 6px;
        height: 8px;
        text-align: center;
    }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLOR_PRIMARY_CYAN}, stop:1 {COLOR_ICE_BLUE});
        border-radius: 5px;
    }}
    QScrollBar:vertical {{
        background: {COLOR_BG_DARK};
        width: 8px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {COLOR_SURFACE};
        min-height: 20px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {COLOR_PRIMARY_CYAN};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    """


def draw_auraflow_logo(painter: QPainter, center_x: float, center_y: float, size: float = 64.0, pulse_phase: float = 0.0):
    """
    Renders the abstract AuraFlow symbol:
    Continuous fluid motion arcs + radiating gesture waves + high-precision cursor trajectory.
    100% scalable vector rendering.
    """
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # 1. Concentric energy ripples (subtle glowing arcs)
    for i in range(3):
        r = size * (0.35 + i * 0.16) + math.sin(pulse_phase + i * 1.2) * (size * 0.03)
        alpha = int(max(0, min(140, 90 - i * 28 + math.sin(pulse_phase + i) * 20)))
        pen_ripple = QPen(QColor(32, 191, 234, alpha), 1.6)
        painter.setPen(pen_ripple)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(center_x, center_y), r, r * 0.92)

    # 2. Continuous Fluid Flow Ribbon (Abstract Infinity / Gesture loop)
    path = QPainterPath()
    r = size * 0.38
    # Start top-left loop
    path.moveTo(center_x - r * 0.6, center_y - r * 0.3)
    path.cubicTo(
        center_x - r * 1.1, center_y - r * 0.8,
        center_x - r * 0.8, center_y + r * 0.7,
        center_x, center_y
    )
    # Flow to top-right and loop around
    path.cubicTo(
        center_x + r * 0.8, center_y - r * 0.7,
        center_x + r * 1.1, center_y + r * 0.8,
        center_x + r * 0.4, center_y + r * 0.4
    )

    grad = QLinearGradient(center_x - r, center_y - r, center_x + r, center_y + r)
    grad.setColorAt(0.0, QColor(140, 235, 255, 255))
    grad.setColorAt(0.5, QColor(32, 191, 234, 240))
    grad.setColorAt(1.0, QColor(18, 49, 73, 200))

    pen_ribbon = QPen(QBrush(grad), max(3.0, size * 0.08), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen_ribbon)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(path)

    # 3. Dynamic Cursor Pointer Node
    ptr_x = center_x + r * 0.35
    ptr_y = center_y - r * 0.35
    ptr_size = size * 0.16

    pointer_path = QPainterPath()
    pointer_path.moveTo(ptr_x, ptr_y - ptr_size * 0.7)
    pointer_path.lineTo(ptr_x + ptr_size * 0.6, ptr_y + ptr_size * 0.6)
    pointer_path.lineTo(ptr_x, ptr_y + ptr_size * 0.3)
    pointer_path.lineTo(ptr_x - ptr_size * 0.6, ptr_y + ptr_size * 0.6)
    pointer_path.closeSubpath()

    painter.setPen(QPen(QColor(255, 255, 255, 240), 1.5))
    painter.setBrush(QBrush(QColor(140, 235, 255, 255)))
    painter.drawPath(pointer_path)

    # 4. Core Hand Touch Point (Glowing Center Node)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor(32, 191, 234, 220)))
    painter.drawEllipse(QPointF(center_x, center_y), size * 0.08, size * 0.08)
    painter.setBrush(QBrush(QColor(255, 255, 255, 255)))
    painter.drawEllipse(QPointF(center_x, center_y), size * 0.04, size * 0.04)

    painter.restore()
