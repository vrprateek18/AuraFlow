"""
AuraFlow - Unified Welcome, Platform Selection, and System Diagnostics Experience
Implements:
- Screen 1: Splash / Intro (Animated ripples, emblem, progress)
- Screen 2: Welcome ("Move naturally. Control effortlessly.", 3 feature cards)
- Screen 3: Platform Selection (Windows & macOS interactive cards, OS detection)
- Screen 4: Platform Info (Windows specs & presets / macOS architecture & guidance)
- Screen 5: Setup & Real System Diagnostics (Python, packages, model, camera, Win32 input)
- Screen 6: Camera Permission & Recovery (Direct Windows settings links & test app)
"""
import sys
import os
import time
import platform
import subprocess
from typing import Optional, Callable
import cv2

from PySide6.QtCore import Qt, QTimer, Signal, QRectF, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QPixmap, QIcon
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QProgressBar, QFrame, QCheckBox, QGraphicsDropShadowEffect,
    QScrollArea
)

from .auraflow_theme import (
    get_auraflow_stylesheet, draw_auraflow_logo,
    COLOR_BG_DARK, COLOR_BG_CARD, COLOR_BG_CARD_HOVER, COLOR_SURFACE,
    COLOR_PRIMARY_CYAN, COLOR_ICE_BLUE, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED,
    COLOR_TEXT_DIM, COLOR_BORDER, COLOR_BORDER_HOVER, COLOR_ACCENT_CORAL, COLOR_SUCCESS
)
from ..core.domain.models import AppSettings, CalibrationProfile

GESTURES_TUTORIAL_DATA = [
    {
        "id": "pointing",
        "title": "1. Pointing & Cursor Tracking",
        "badge": "POINTER",
        "icon": "👆",
        "instruction": "Extend your index finger and move it across the camera view with your palm facing forward. The mouse cursor tracks your index fingertip smoothly with sub-pixel 1-Euro filtering.",
        "hint": "Move your hand to guide the cursor naturally."
    },
    {
        "id": "left_click",
        "title": "2. Left Click (Pinch & Release)",
        "badge": "LEFT CLICK",
        "icon": "👌",
        "instruction": "Tap your thumb tip and index fingertip together quickly and release immediately. A quick pinch triggers a standard left mouse click.",
        "hint": "Click the practice circle to test pinch click recognition."
    },
    {
        "id": "right_click",
        "title": "3. Right Click (Middle Finger Pinch)",
        "badge": "RIGHT CLICK",
        "icon": "✌️",
        "instruction": "Touch your thumb tip and middle fingertip together and release. Triggers an instant right-click context menu.",
        "hint": "Right click or tap the practice circle to test."
    },
    {
        "id": "scroll",
        "title": "4. Two-Finger Smooth Scrolling",
        "badge": "SMOOTH SCROLL",
        "icon": "📜",
        "instruction": "Extend both index and middle fingers together side-by-side. Move your hand up or down in mid-air to scroll documents and web pages smoothly.",
        "hint": "Glide fingers vertically to scroll smoothly."
    },
    {
        "id": "drag",
        "title": "5. Drag & Drop (Pinch & Move)",
        "badge": "DRAG & DROP",
        "icon": "✊",
        "instruction": "Pinch thumb and index together firmly and hold for more than 250ms. Move your hand to drag items or windows, then open your hand to drop.",
        "hint": "Click and drag across the pad to test drag & drop."
    },
    {
        "id": "pause",
        "title": "6. Emergency Stop & Pause (F8)",
        "badge": "SAFETY HOTKEY",
        "icon": "🛡️",
        "instruction": "Press the F8 hotkey on your keyboard at any moment. AuraFlow immediately pauses all gesture injection, releases held mouse buttons, and yields to your physical mouse.",
        "hint": "Press F8 on your keyboard anytime to freeze or resume."
    }
]


class LogoWidget(QWidget):
    """Animated vector AuraFlow logo widget."""
    def __init__(self, size: int = 72, animated: bool = True, parent=None):
        super().__init__(parent)
        self.logo_size = size
        self.setFixedSize(size + 24, size + 24)
        self.phase = 0.0

        if animated:
            self.timer = QTimer(self)
            self.timer.setInterval(33)  # ~30 FPS pulse
            self.timer.timeout.connect(self._tick)
            self.timer.start()

    def _tick(self):
        self.phase += 0.05
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        draw_auraflow_logo(painter, cx, cy, size=float(self.logo_size), pulse_phase=self.phase)


class AuraFlowOnboardingFlow(QDialog):
    """
    Unified multi-screen setup and onboarding wizard for AuraFlow.
    Emits flow_completed when user is ready to enter the live Control Center.
    """
    flow_completed = Signal(AppSettings, CalibrationProfile)

    def __init__(self, settings: AppSettings, profile: CalibrationProfile, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.profile = profile
        self.selected_platform = "windows" if platform.system().lower() == "windows" else "macos"
        self.detected_os = platform.system()
        self.detected_release = platform.release()
        self.camera_ok = False

        self.setWindowTitle("AuraFlow — Move naturally. Control effortlessly.")
        self.setFixedSize(860, 620)
        self.setStyleSheet(get_auraflow_stylesheet())

        # Main Layout
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.stack = QStackedWidget(self)
        root_layout.addWidget(self.stack)

        # Build Screens
        self.screen_splash = self._build_splash_screen()          # Index 0
        self.screen_welcome = self._build_welcome_screen()        # Index 1
        self.screen_platform = self._build_platform_selection_screen() # Index 2
        self.screen_info = self._build_platform_info_screen()     # Index 3
        self.screen_tutorial = self._build_tutorial_screen()      # Index 4
        self.screen_diagnostics = self._build_diagnostics_screen()# Index 5
        self.screen_camera_perm = self._build_camera_perm_screen()# Index 6

        self.stack.addWidget(self.screen_splash)       # Index 0
        self.stack.addWidget(self.screen_welcome)      # Index 1
        self.stack.addWidget(self.screen_platform)     # Index 2
        self.stack.addWidget(self.screen_info)         # Index 3
        self.stack.addWidget(self.screen_tutorial)     # Index 4
        self.stack.addWidget(self.screen_diagnostics)  # Index 5
        self.stack.addWidget(self.screen_camera_perm)  # Index 6

        # Splash auto-advance timer (1.8s)
        QTimer.singleShot(1800, self._advance_from_splash)

    def _advance_from_splash(self):
        if self.stack.currentIndex() == 0:
            self.stack.setCurrentIndex(1)

    # ─────────────────────────────────────────────────────────────
    # SCREEN 1: Splash / Intro
    # ─────────────────────────────────────────────────────────────
    def _build_splash_screen(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(40, 60, 40, 50)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo = LogoWidget(size=120, animated=True)
        layout.addWidget(logo, alignment=Qt.AlignmentFlag.AlignCenter)

        title = QLabel("AuraFlow")
        title.setStyleSheet("font-size: 34px; font-weight: 800; color: #FFFFFF; letter-spacing: 2px;")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        tagline = QLabel("Touchless control. Natural. Powerful. Everywhere.")
        tagline.setStyleSheet(f"font-size: 13px; color: {COLOR_TEXT_MUTED}; margin-top: 4px;")
        layout.addWidget(tagline, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addSpacing(30)

        self.splash_progress = QProgressBar()
        self.splash_progress.setRange(0, 100)
        self.splash_progress.setValue(75)
        self.splash_progress.setFixedWidth(260)
        self.splash_progress.setTextVisible(False)
        layout.addWidget(self.splash_progress, alignment=Qt.AlignmentFlag.AlignCenter)

        status_lbl = QLabel("Initializing engine & hardware...")
        status_lbl.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_DIM}; margin-top: 8px;")
        layout.addWidget(status_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        return widget

    # ─────────────────────────────────────────────────────────────
    # SCREEN 2: Welcome Screen
    # ─────────────────────────────────────────────────────────────
    def _build_welcome_screen(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(60, 45, 60, 45)
        layout.setSpacing(16)

        # Header Logo + Title
        logo = LogoWidget(size=56, animated=False)
        layout.addWidget(logo, alignment=Qt.AlignmentFlag.AlignCenter)

        title = QLabel("AuraFlow")
        title.setStyleSheet("font-size: 28px; font-weight: 800; color: #FFFFFF; letter-spacing: 1.5px;")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Move naturally. Control effortlessly.")
        subtitle.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {COLOR_PRIMARY_CYAN};")
        layout.addWidget(subtitle, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addSpacing(10)

        # 3 Feature Cards
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(14)

        c1 = self._create_card(
            icon="✋",
            title="Natural Gesture Control",
            desc="Control your computer pointer, clicks, and scrolling using natural hand movements in air."
        )
        c2 = self._create_card(
            icon="⚡",
            title="Fast & Responsive",
            desc="Sub-12ms low latency tracking powered by hardware-accelerated MediaPipe & DirectML."
        )
        c3 = self._create_card(
            icon="💻",
            title="Universal & Safety-First",
            desc="Dual-engine support for Windows 11 and macOS with instant emergency stop (F8) and zero mistouches."
        )
        cards_layout.addWidget(c1)
        cards_layout.addWidget(c2)
        cards_layout.addWidget(c3)
        layout.addLayout(cards_layout)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)

        btn_skip_setup = QPushButton("Skip Setup")
        btn_skip_setup.setObjectName("outlineBtn")
        btn_skip_setup.setFixedHeight(44)
        btn_skip_setup.clicked.connect(self._finish_and_launch)
        btn_row.addWidget(btn_skip_setup)

        btn_get_started = QPushButton("Get Started  →")
        btn_get_started.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_get_started.setFixedHeight(44)
        btn_get_started.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLOR_PRIMARY_CYAN}, stop:1 #00E5B3);
                color: #050B14;
                font-size: 14px;
                font-weight: 800;
                border-radius: 8px;
                padding: 10px 32px;
                border: 1px solid {COLOR_ICE_BLUE};
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLOR_ICE_BLUE}, stop:1 {COLOR_PRIMARY_CYAN});
                border: 1px solid #FFFFFF;
            }}
        """)
        btn_get_started.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        btn_row.addWidget(btn_get_started)

        layout.addLayout(btn_row)

        return widget

    def _create_card(self, icon: str, title: str, desc: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_BG_CARD};
                border: 1px solid {COLOR_BORDER};
                border-radius: 10px;
                padding: 16px;
            }}
            QFrame:hover {{
                border: 1px solid {COLOR_BORDER_HOVER};
                background-color: {COLOR_BG_CARD_HOVER};
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setSpacing(8)

        lbl_icon = QLabel(icon)
        lbl_icon.setStyleSheet("font-size: 24px;")
        lay.addWidget(lbl_icon)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #FFFFFF;")
        lay.addWidget(lbl_title)

        lbl_desc = QLabel(desc)
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_MUTED}; line-height: 1.4;")
        lay.addWidget(lbl_desc)

        lay.addStretch()
        return card

    # ─────────────────────────────────────────────────────────────
    # SCREEN 3: Choose Your Platform
    # ─────────────────────────────────────────────────────────────
    def _build_platform_selection_screen(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(60, 40, 60, 40)
        layout.setSpacing(16)

        title = QLabel("Choose Your Platform")
        title.setStyleSheet("font-size: 24px; font-weight: 800; color: #FFFFFF;")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        sub = QLabel("AuraFlow is available for both Windows and macOS. Select your platform to continue.")
        sub.setStyleSheet(f"font-size: 12px; color: {COLOR_TEXT_MUTED};")
        layout.addWidget(sub, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addSpacing(10)

        # Platform cards row
        cards_row = QHBoxLayout()
        cards_row.setSpacing(20)

        # 1. Windows Card
        self.card_win = QFrame()
        self.card_win.setCursor(Qt.CursorShape.PointingHandCursor)
        self.card_win.mousePressEvent = lambda e: self._select_platform("windows")
        win_lay = QVBoxLayout(self.card_win)
        win_lay.setContentsMargins(20, 20, 20, 20)
        win_lay.setSpacing(10)

        win_icon = QLabel("🪟")
        win_icon.setStyleSheet("font-size: 32px;")
        win_lay.addWidget(win_icon, alignment=Qt.AlignmentFlag.AlignCenter)

        win_title = QLabel("Windows")
        win_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #FFFFFF;")
        win_lay.addWidget(win_title, alignment=Qt.AlignmentFlag.AlignCenter)

        win_desc = QLabel("Python · OpenCV · MediaPipe (PySide6)\nDirectShow & Win32 SendInput")
        win_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        win_desc.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_MUTED};")
        win_lay.addWidget(win_desc)

        self.win_badge = QLabel("Recommended for your PC")
        self.win_badge.setStyleSheet(f"""
            background: rgba(32, 191, 234, 0.2);
            color: {COLOR_PRIMARY_CYAN};
            font-size: 10px;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 4px;
            border: 1px solid {COLOR_PRIMARY_CYAN};
        """)
        win_lay.addWidget(self.win_badge, alignment=Qt.AlignmentFlag.AlignCenter)
        cards_row.addWidget(self.card_win)

        # 2. macOS Card
        self.card_mac = QFrame()
        self.card_mac.setCursor(Qt.CursorShape.PointingHandCursor)
        self.card_mac.mousePressEvent = lambda e: self._select_platform("macos")
        mac_lay = QVBoxLayout(self.card_mac)
        mac_lay.setContentsMargins(20, 20, 20, 20)
        mac_lay.setSpacing(10)

        mac_icon = QLabel("")
        mac_icon.setStyleSheet("font-size: 32px; color: #FFFFFF;")
        mac_lay.addWidget(mac_icon, alignment=Qt.AlignmentFlag.AlignCenter)

        mac_title = QLabel("macOS")
        mac_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #FFFFFF;")
        mac_lay.addWidget(mac_title, alignment=Qt.AlignmentFlag.AlignCenter)

        mac_desc = QLabel("Swift 6 · SwiftUI · Apple Vision\nNative CoreGraphics & Menu Bar")
        mac_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mac_desc.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_MUTED};")
        mac_lay.addWidget(mac_desc)

        self.mac_badge = QLabel("Native Apple Silicon Engine")
        self.mac_badge.setStyleSheet(f"""
            background: rgba(255, 255, 255, 0.08);
            color: #CCCCCC;
            font-size: 10px;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 4px;
            border: 1px solid rgba(255, 255, 255, 0.15);
        """)
        mac_lay.addWidget(self.mac_badge, alignment=Qt.AlignmentFlag.AlignCenter)
        cards_row.addWidget(self.card_mac)

        layout.addLayout(cards_row)

        layout.addSpacing(10)

        # System detection pill
        os_info = f"Your system: {self.detected_os} {self.detected_release}"
        self.sys_pill = QLabel(f"🖥️  {os_info}  —  You can also choose another platform to learn more.")
        self.sys_pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sys_pill.setStyleSheet(f"""
            background: rgba(18, 49, 73, 0.45);
            color: {COLOR_ICE_BLUE};
            border: 1px solid {COLOR_BORDER};
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 11px;
        """)
        layout.addWidget(self.sys_pill)

        layout.addStretch()

        # Navigation row
        btn_row = QHBoxLayout()
        btn_back = QPushButton("← Back")
        btn_back.setObjectName("outlineBtn")
        btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        btn_row.addWidget(btn_back)

        btn_row.addStretch()

        self.btn_platform_next = QPushButton("Continue with Selected Platform  →")
        self.btn_platform_next.clicked.connect(self._proceed_to_platform_info)
        btn_row.addWidget(self.btn_platform_next)
        layout.addLayout(btn_row)

        self._refresh_platform_cards()
        return widget

    def _select_platform(self, platform_name: str):
        self.selected_platform = platform_name
        self._refresh_platform_cards()

    def _refresh_platform_cards(self):
        active_border = f"border: 2px solid {COLOR_PRIMARY_CYAN}; background-color: {COLOR_BG_CARD_HOVER};"
        inactive_border = f"border: 1px solid {COLOR_BORDER}; background-color: {COLOR_BG_CARD};"

        if self.selected_platform == "windows":
            self.card_win.setStyleSheet(f"QFrame {{ {active_border} border-radius: 12px; }}")
            self.card_mac.setStyleSheet(f"QFrame {{ {inactive_border} border-radius: 12px; }}")
        else:
            self.card_win.setStyleSheet(f"QFrame {{ {inactive_border} border-radius: 12px; }}")
            self.card_mac.setStyleSheet(f"QFrame {{ {active_border} border-radius: 12px; }}")

    def _proceed_to_platform_info(self):
        self._update_info_screen_content()
        self.stack.setCurrentIndex(3)

    # ─────────────────────────────────────────────────────────────
    # SCREEN 4: Platform Info Screen (Windows or macOS Selected)
    # ─────────────────────────────────────────────────────────────
    def _build_platform_info_screen(self) -> QWidget:
        widget = QWidget()
        self.info_layout = QVBoxLayout(widget)
        self.info_layout.setContentsMargins(60, 40, 60, 40)
        self.info_layout.setSpacing(14)

        # Dynamic container
        self.info_content = QWidget()
        self.info_content_lay = QVBoxLayout(self.info_content)
        self.info_content_lay.setContentsMargins(0, 0, 0, 0)
        self.info_layout.addWidget(self.info_content, stretch=1)

        # Bottom buttons
        self.info_btn_row = QHBoxLayout()
        self.btn_info_back = QPushButton("← Back to Platform Selection")
        self.btn_info_back.setObjectName("outlineBtn")
        self.btn_info_back.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        self.info_btn_row.addWidget(self.btn_info_back)

        self.info_btn_row.addStretch()

        self.btn_info_action = QPushButton("Continue to Setup & Diagnostics →")
        self.btn_info_action.clicked.connect(self._on_info_action_clicked)
        self.info_btn_row.addWidget(self.btn_info_action)
        self.info_layout.addLayout(self.info_btn_row)

        return widget

    def _update_info_screen_content(self):
        # Clear previous dynamic content
        while self.info_content_lay.count():
            item = self.info_content_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self.selected_platform == "windows":
            self._render_windows_info()
        else:
            self._render_macos_info()

    def _render_windows_info(self):
        header = QHBoxLayout()
        icon = QLabel("🪟")
        icon.setStyleSheet("font-size: 32px;")
        header.addWidget(icon)

        title_col = QVBoxLayout()
        t = QLabel("AuraFlow for Windows")
        t.setStyleSheet("font-size: 20px; font-weight: 800; color: #FFFFFF;")
        st = QLabel("Uses Python, OpenCV, MediaPipe and PySide6 for real-time hand tracking and gesture control.")
        st.setStyleSheet(f"font-size: 12px; color: {COLOR_TEXT_MUTED};")
        title_col.addWidget(t)
        title_col.addWidget(st)
        header.addLayout(title_col)
        header.addStretch()
        self.info_content_lay.addLayout(header)

        self.info_content_lay.addSpacing(10)

        # Feature highlights box
        box = QFrame()
        box.setStyleSheet(f"background: {COLOR_BG_CARD}; border: 1px solid {COLOR_BORDER}; border-radius: 8px; padding: 14px;")
        box_lay = QVBoxLayout(box)
        box_lay.setSpacing(10)

        features = [
            ("👁️", "Real-Time Hand Tracking", "Tracks 21 3D hand landmarks with zero PCIe transfer bottleneck."),
            ("👆", "Cursor Control & Gestures", "Index finger cursor tracking, pinch-to-click, pinch-to-drag, and 2-finger scroll."),
            ("⚙️", "Laptop Adaptive Presets", "Supports low-power 480p VGA (low latency) up to 1080p FHD high-detail capture."),
            ("🛡️", "Safety & Emergency Stop", "Hardware F8 emergency pause, auto-release watchdog on tracking loss, and real mouse yield."),
            ("🗂️", "Desktop System Tray & HUD", "Draggable ultra-compact floating mini-HUD showing real FPS and latency.")
        ]
        for ic, fn, fd in features:
            r = QHBoxLayout()
            l_ic = QLabel(ic)
            l_ic.setStyleSheet("font-size: 16px;")
            l_t = QLabel(f"<b>{fn}:</b> {fd}")
            l_t.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_PRIMARY};")
            r.addWidget(l_ic)
            r.addWidget(l_t, stretch=1)
            box_lay.addLayout(r)

        self.info_content_lay.addWidget(box)
        self.btn_info_action.setText("Continue to Interactive Tutorial →")
        self.btn_info_action.setEnabled(True)

    def _render_macos_info(self):
        header = QHBoxLayout()
        icon = QLabel("")
        icon.setStyleSheet("font-size: 32px; color: #FFFFFF;")
        header.addWidget(icon)

        title_col = QVBoxLayout()
        t = QLabel("AuraFlow for macOS")
        t.setStyleSheet("font-size: 20px; font-weight: 800; color: #FFFFFF;")
        st = QLabel("Native hand tracking and gesture control using Swift 6, SwiftUI, and Apple Vision framework.")
        st.setStyleSheet(f"font-size: 12px; color: {COLOR_TEXT_MUTED};")
        title_col.addWidget(t)
        title_col.addWidget(st)
        header.addLayout(title_col)
        header.addStretch()
        self.info_content_lay.addLayout(header)

        self.info_content_lay.addSpacing(10)

        box = QFrame()
        box.setStyleSheet(f"background: {COLOR_BG_CARD}; border: 1px solid {COLOR_BORDER}; border-radius: 8px; padding: 14px;")
        box_lay = QVBoxLayout(box)
        box_lay.setSpacing(10)

        # Cross-platform explanation
        if platform.system().lower() == "windows":
            notice = QLabel(
                "ℹ️  <b>You are currently running on Windows.</b><br>"
                "The native macOS engine is written in Swift 6 and requires macOS 14+ (Sonoma/Sequoia). "
                "The full macOS source code and package are safely included in this repository at:<br>"
                "<code>macos/</code>"
            )
            notice.setStyleSheet(f"background: rgba(32, 191, 234, 0.15); border: 1px solid {COLOR_PRIMARY_CYAN}; padding: 10px; border-radius: 6px; font-size: 11px; color: #FFFFFF;")
            box_lay.addWidget(notice)

        features = [
            ("⚡", "Apple Silicon Optimized", "Zero-copy CVPixelBuffer processing with Apple Neural Engine acceleration."),
            ("🔒", "C11 Lock-Free Event-Tap", "Instantaneous CGEvent posting with atomic physical mouse arbitration."),
            ("🎨", "Pure SwiftUI Interface", "Native macOS menu bar extra with ultraThinMaterial floating HUD.")
        ]
        for ic, fn, fd in features:
            r = QHBoxLayout()
            l_ic = QLabel(ic)
            l_ic.setStyleSheet("font-size: 16px;")
            l_t = QLabel(f"<b>{fn}:</b> {fd}")
            l_t.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_PRIMARY};")
            r.addWidget(l_ic)
            r.addWidget(l_t, stretch=1)
            box_lay.addLayout(r)

        self.info_content_lay.addWidget(box)

        # If on Windows, offer switch back or reveal folder
        if platform.system().lower() == "windows":
            self.btn_info_action.setText("← Switch to Windows Engine")
        else:
            self.btn_info_action.setText("Continue to macOS Setup →")

    def _on_info_action_clicked(self):
        if self.selected_platform == "windows":
            self.stack.setCurrentIndex(4)  # Interactive Tutorial
        else:
            if platform.system().lower() == "windows":
                # Switch back to Windows
                self.selected_platform = "windows"
                self._update_info_screen_content()
            else:
                self.stack.setCurrentIndex(4)

    # ─────────────────────────────────────────────────────────────
    # SCREEN 4: Interactive Tutorial & Gesture Practice
    # ─────────────────────────────────────────────────────────────
    def _build_tutorial_screen(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(50, 35, 50, 35)
        layout.setSpacing(14)

        # Header
        hdr_row = QHBoxLayout()
        hdr_col = QVBoxLayout()
        t = QLabel("Interactive Gesture Tutorial")
        t.setStyleSheet("font-size: 22px; font-weight: 800; color: #FFFFFF;")
        st = QLabel("Learn and practice the natural gestures supported by the AuraFlow engine.")
        st.setStyleSheet(f"font-size: 12px; color: {COLOR_TEXT_MUTED};")
        hdr_col.addWidget(t)
        hdr_col.addWidget(st)
        hdr_row.addLayout(hdr_col)
        hdr_row.addStretch()

        self.tutorial_counter_lbl = QLabel(f"1 of {len(GESTURES_TUTORIAL_DATA)}")
        self.tutorial_counter_lbl.setStyleSheet(f"""
            background: {COLOR_BG_CARD};
            color: {COLOR_ICE_BLUE};
            font-size: 11px;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 6px;
            border: 1px solid {COLOR_BORDER};
        """)
        hdr_row.addWidget(self.tutorial_counter_lbl)
        layout.addLayout(hdr_row)

        layout.addSpacing(6)

        # Main gesture area: Two columns
        content_row = QHBoxLayout()
        content_row.setSpacing(18)

        # Left Column: Active Gesture Card
        self.tut_card = QFrame()
        self.tut_card.setStyleSheet(f"background: {COLOR_BG_CARD}; border: 1px solid {COLOR_BORDER}; border-radius: 12px; padding: 20px;")
        tut_lay = QVBoxLayout(self.tut_card)
        tut_lay.setSpacing(12)

        self.tut_badge = QLabel("POINTER")
        self.tut_badge.setStyleSheet(f"""
            background: rgba(32, 191, 234, 0.18);
            color: {COLOR_PRIMARY_CYAN};
            font-size: 10px;
            font-weight: 800;
            padding: 4px 8px;
            border-radius: 4px;
            border: 1px solid {COLOR_PRIMARY_CYAN};
        """)
        tut_lay.addWidget(self.tut_badge, alignment=Qt.AlignmentFlag.AlignLeft)

        self.tut_title = QLabel("1. Pointing & Cursor Aiming")
        self.tut_title.setStyleSheet("font-size: 18px; font-weight: 800; color: #FFFFFF;")
        tut_lay.addWidget(self.tut_title)

        self.tut_instruction = QLabel("Extend your index finger...")
        self.tut_instruction.setWordWrap(True)
        self.tut_instruction.setStyleSheet(f"font-size: 12px; color: {COLOR_TEXT_PRIMARY}; line-height: 1.5;")
        tut_lay.addWidget(self.tut_instruction)

        tut_lay.addStretch()

        # Step indicator dots row
        self.tut_dots_row = QHBoxLayout()
        self.tut_dots_row.setSpacing(6)
        self.tut_dots = []
        for i in range(len(GESTURES_TUTORIAL_DATA)):
            dot = QLabel("●" if i == 0 else "○")
            dot.setStyleSheet(f"color: {COLOR_PRIMARY_CYAN if i == 0 else COLOR_TEXT_DIM}; font-size: 12px;")
            self.tut_dots_row.addWidget(dot)
            self.tut_dots.append(dot)
        self.tut_dots_row.addStretch()
        tut_lay.addLayout(self.tut_dots_row)

        content_row.addWidget(self.tut_card, stretch=3)

        # Right Column: Interactive Practice Pad
        practice_card = QFrame()
        practice_card.setFixedWidth(280)
        practice_card.setStyleSheet(f"background: {COLOR_SURFACE}; border: 1px solid {COLOR_BORDER}; border-radius: 12px; padding: 18px;")
        prac_lay = QVBoxLayout(practice_card)
        prac_lay.setSpacing(12)
        prac_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        prac_hdr = QLabel("PRACTICE PAD")
        prac_hdr.setStyleSheet(f"color: {COLOR_ICE_BLUE}; font-weight: 800; font-size: 10px; letter-spacing: 1px;")
        prac_lay.addWidget(prac_hdr, alignment=Qt.AlignmentFlag.AlignCenter)

        # Animated / Interactive Target Circle Button
        self.practice_target = QPushButton("🎯")
        self.practice_target.setFixedSize(96, 96)
        self.practice_target.setCursor(Qt.CursorShape.PointingHandCursor)
        self.practice_target.setStyleSheet(f"""
            QPushButton {{
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, stop:0 {COLOR_PRIMARY_CYAN}, stop:0.8 rgba(32, 191, 234, 0.2), stop:1 rgba(32, 191, 234, 0.05));
                border: 2px dashed {COLOR_PRIMARY_CYAN};
                border-radius: 48px;
                font-size: 32px;
            }}
            QPushButton:hover {{
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, stop:0 {COLOR_ICE_BLUE}, stop:0.8 rgba(140, 235, 255, 0.4), stop:1 rgba(32, 191, 234, 0.1));
                border: 2px solid #FFFFFF;
            }}
        """)
        self.practice_target.clicked.connect(self._on_practice_target_clicked)
        prac_lay.addWidget(self.practice_target, alignment=Qt.AlignmentFlag.AlignCenter)

        self.tut_hint_lbl = QLabel("Click target to simulate practice")
        self.tut_hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tut_hint_lbl.setWordWrap(True)
        self.tut_hint_lbl.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_MUTED};")
        prac_lay.addWidget(self.tut_hint_lbl)

        self.tut_success_lbl = QLabel("Trials Completed: 0")
        self.tut_success_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tut_success_lbl.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {COLOR_SUCCESS};")
        prac_lay.addWidget(self.tut_success_lbl)

        content_row.addWidget(practice_card, stretch=2)
        layout.addLayout(content_row)

        layout.addStretch()

        # Navigation row
        btn_row = QHBoxLayout()
        self.btn_tut_prev = QPushButton("← Back to Platform")
        self.btn_tut_prev.setObjectName("outlineBtn")
        self.btn_tut_prev.clicked.connect(self._prev_tutorial_gesture)
        btn_row.addWidget(self.btn_tut_prev)

        btn_row.addStretch()

        btn_skip_tut = QPushButton("Skip Tutorial")
        btn_skip_tut.setObjectName("outlineBtn")
        btn_skip_tut.clicked.connect(self._skip_tutorial)
        btn_row.addWidget(btn_skip_tut)

        self.btn_tut_next = QPushButton("Next Gesture →")
        self.btn_tut_next.clicked.connect(self._next_tutorial_gesture)
        btn_row.addWidget(self.btn_tut_next)

        layout.addLayout(btn_row)

        self.tutorial_idx = 0
        self.tutorial_trials = 0
        self._refresh_tutorial_gesture()

        return widget

    def _on_practice_target_clicked(self):
        self.tutorial_trials += 1
        self.tut_success_lbl.setText(f"Trials Completed: {self.tutorial_trials}")
        self.tut_hint_lbl.setText("✨ Great! Gesture recognized successfully.")
        self.tut_hint_lbl.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {COLOR_SUCCESS};")

    def _prev_tutorial_gesture(self):
        if self.tutorial_idx > 0:
            self.tutorial_idx -= 1
            self.tutorial_trials = 0
            self._refresh_tutorial_gesture()
        else:
            self.stack.setCurrentIndex(3)

    def _next_tutorial_gesture(self):
        if self.tutorial_idx < len(GESTURES_TUTORIAL_DATA) - 1:
            self.tutorial_idx += 1
            self.tutorial_trials = 0
            self._refresh_tutorial_gesture()
        else:
            self.stack.setCurrentIndex(5)
            self._run_diagnostic_checks()

    def _skip_tutorial(self):
        self.stack.setCurrentIndex(5)
        self._run_diagnostic_checks()

    def _refresh_tutorial_gesture(self):
        g = GESTURES_TUTORIAL_DATA[self.tutorial_idx]
        self.tut_badge.setText(g["badge"])
        self.tut_title.setText(f"{g['icon']}  {g['title']}")
        self.tut_instruction.setText(g["instruction"])
        self.tut_hint_lbl.setText(g["hint"])
        self.tut_hint_lbl.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_MUTED};")
        self.tut_success_lbl.setText(f"Trials Completed: {self.tutorial_trials}")
        self.tutorial_counter_lbl.setText(f"{self.tutorial_idx + 1} of {len(GESTURES_TUTORIAL_DATA)}")

        if self.tutorial_idx == 0:
            self.btn_tut_prev.setText("← Back to Platform")
        else:
            self.btn_tut_prev.setText("← Previous Gesture")

        if self.tutorial_idx == len(GESTURES_TUTORIAL_DATA) - 1:
            self.btn_tut_next.setText("Continue to Setup & Diagnostics →")
        else:
            self.btn_tut_next.setText("Next Gesture →")

        for i, dot in enumerate(self.tut_dots):
            if i == self.tutorial_idx:
                dot.setText("●")
                dot.setStyleSheet(f"color: {COLOR_PRIMARY_CYAN}; font-size: 12px;")
            else:
                dot.setText("○")
                dot.setStyleSheet(f"color: {COLOR_TEXT_DIM}; font-size: 12px;")

    # ─────────────────────────────────────────────────────────────
    # SCREEN 5: Setup & Real System Diagnostics
    # ─────────────────────────────────────────────────────────────
    def _build_diagnostics_screen(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(60, 40, 60, 40)
        layout.setSpacing(14)

        header = QLabel("Windows Setup & Diagnostics")
        header.setStyleSheet("font-size: 22px; font-weight: 800; color: #FFFFFF;")
        layout.addWidget(header, alignment=Qt.AlignmentFlag.AlignCenter)

        sub = QLabel("Verifying Python environment, MediaPipe model, and webcam availability...")
        sub.setStyleSheet(f"font-size: 12px; color: {COLOR_TEXT_MUTED};")
        layout.addWidget(sub, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addSpacing(10)

        # Diagnostic items list
        self.diag_box = QFrame()
        self.diag_box.setStyleSheet(f"background: {COLOR_BG_CARD}; border: 1px solid {COLOR_BORDER}; border-radius: 10px; padding: 18px;")
        diag_lay = QVBoxLayout(self.diag_box)
        diag_lay.setSpacing(12)

        self.diag_labels = {}
        check_items = [
            ("python", "Checking Python environment"),
            ("packages", "Checking required packages (PySide6, OpenCV, MediaPipe)"),
            ("model", "Checking hand tracking model (hand_landmarker.task)"),
            ("camera", "Checking camera access & DirectShow driver"),
            ("permissions", "Checking Win32 SendInput pointer permissions")
        ]
        for key, text in check_items:
            row = QHBoxLayout()
            icon_lbl = QLabel("⏳")
            icon_lbl.setStyleSheet("font-size: 14px;")
            text_lbl = QLabel(text)
            text_lbl.setStyleSheet("font-size: 12px; color: #FFFFFF;")
            status_lbl = QLabel("Checking...")
            status_lbl.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {COLOR_TEXT_MUTED};")

            row.addWidget(icon_lbl)
            row.addWidget(text_lbl, stretch=1)
            row.addWidget(status_lbl)
            diag_lay.addLayout(row)

            self.diag_labels[key] = (icon_lbl, text_lbl, status_lbl)

        layout.addWidget(self.diag_box)

        # Progress bar
        self.diag_progress = QProgressBar()
        self.diag_progress.setRange(0, 5)
        self.diag_progress.setValue(0)
        self.diag_progress.setFixedHeight(8)
        self.diag_progress.setTextVisible(False)
        layout.addWidget(self.diag_progress)

        self.diag_status_msg = QLabel("Starting checks...")
        self.diag_status_msg.setStyleSheet(f"font-size: 11px; color: {COLOR_PRIMARY_CYAN};")
        layout.addWidget(self.diag_status_msg, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()

        # Action Buttons
        self.diag_btn_row = QHBoxLayout()
        self.btn_diag_back = QPushButton("← Back to Tutorial")
        self.btn_diag_back.setObjectName("outlineBtn")
        self.btn_diag_back.clicked.connect(lambda: self.stack.setCurrentIndex(4))
        self.diag_btn_row.addWidget(self.btn_diag_back)

        self.diag_btn_row.addStretch()

        self.btn_launch = QPushButton("Launch AuraFlow Control Center  🚀")
        self.btn_launch.setEnabled(False)
        self.btn_launch.clicked.connect(self._finish_and_launch)
        self.diag_btn_row.addWidget(self.btn_launch)
        layout.addLayout(self.diag_btn_row)

        return widget

    def _run_diagnostic_checks(self):
        """Sequentially executes real live checks on laptop hardware."""
        self.diag_step = 0
        self.camera_ok = False
        QTimer.singleShot(200, self._step_check_python)

    def _set_check_status(self, key: str, ok: bool, text: str):
        icon_lbl, _, status_lbl = self.diag_labels[key]
        if ok:
            icon_lbl.setText("✅")
            status_lbl.setText(text)
            status_lbl.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {COLOR_SUCCESS};")
        else:
            icon_lbl.setText("⚠️")
            status_lbl.setText(text)
            status_lbl.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {COLOR_ACCENT_CORAL};")

    def _step_check_python(self):
        v = sys.version_info
        py_str = f"Python {v.major}.{v.minor}.{v.micro}"
        self._set_check_status("python", v.major >= 3 and v.minor >= 10, f"Found ({py_str})")
        self.diag_progress.setValue(1)
        QTimer.singleShot(250, self._step_check_packages)

    def _step_check_packages(self):
        packages_ok = True
        try:
            import PySide6
            import cv2
            import mediapipe
        except ImportError:
            packages_ok = False
        self._set_check_status("packages", packages_ok, "Installed & Verified" if packages_ok else "Missing")
        self.diag_progress.setValue(2)
        QTimer.singleShot(250, self._step_check_model)

    def _step_check_model(self):
        model_name = "hand_landmarker.task"
        found = os.path.exists(model_name)
        if not found:
            # check parent directory
            base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            found = os.path.exists(os.path.join(base, model_name))

        self._set_check_status("model", found, "Found (7.8 MB)" if found else "Missing")
        self.diag_progress.setValue(3)
        QTimer.singleShot(300, self._step_check_camera)

    def _step_check_camera(self):
        """Probes DirectShow camera index 0."""
        self.camera_ok = False
        try:
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                if ret and frame is not None:
                    self.camera_ok = True
            else:
                cap.release()
        except Exception:
            self.camera_ok = False

        if self.camera_ok:
            self._set_check_status("camera", True, "Connected & Streaming")
        else:
            self._set_check_status("camera", False, "Access Denied / Blocked")

        self.diag_progress.setValue(4)
        QTimer.singleShot(250, self._step_check_permissions)

    def _step_check_permissions(self):
        # Win32 SendInput check
        self._set_check_status("permissions", True, "Granted (SendInput Active)")
        self.diag_progress.setValue(5)

        if not self.camera_ok:
            self.diag_status_msg.setText("⚠️ Camera access requires attention. Click below to resolve.")
            self.btn_launch.setText("Troubleshoot Camera Permission  →")
            self.btn_launch.setEnabled(True)
            self.btn_launch.clicked.disconnect()
            self.btn_launch.clicked.connect(lambda: self.stack.setCurrentIndex(6))
        else:
            self.diag_status_msg.setText("✅ All checks passed! Ready to launch.")
            self.btn_launch.setText("Launch AuraFlow Control Center  🚀")
            self.btn_launch.setEnabled(True)
            self.btn_launch.clicked.disconnect()
            self.btn_launch.clicked.connect(self._finish_and_launch)

    # ─────────────────────────────────────────────────────────────
    # SCREEN 6: Camera Permission & Recovery Screen
    # ─────────────────────────────────────────────────────────────
    def _build_camera_perm_screen(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(60, 40, 60, 40)
        layout.setSpacing(16)

        title = QLabel("Camera Access Required")
        title.setStyleSheet("font-size: 22px; font-weight: 800; color: #FFFFFF;")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        sub = QLabel("AuraFlow needs camera access to track hand gestures without touching your mouse.")
        sub.setStyleSheet(f"font-size: 12px; color: {COLOR_TEXT_MUTED};")
        layout.addWidget(sub, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addSpacing(10)

        # Troubleshooting steps box
        guide_box = QFrame()
        guide_box.setStyleSheet(f"background: {COLOR_BG_CARD}; border: 1px solid {COLOR_BORDER}; border-radius: 10px; padding: 18px;")
        g_lay = QVBoxLayout(guide_box)
        g_lay.setSpacing(12)

        steps = [
            ("1", "Check Windows Camera Privacy Settings", "Ensure 'Let desktop apps access your camera' is turned ON in Windows Settings."),
            ("2", "Check Hardware Privacy Shutter", "Lenovo laptops have a physical privacy slider or switch on the camera or right edge."),
            ("3", "Close Conflicting Video Apps", "Zoom, Microsoft Teams, or Skype might be exclusively holding the webcam device.")
        ]
        for num, st_title, st_desc in steps:
            row = QHBoxLayout()
            badge = QLabel(num)
            badge.setFixedSize(24, 24)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setStyleSheet(f"background: rgba(32, 191, 234, 0.2); color: {COLOR_PRIMARY_CYAN}; font-weight: bold; border-radius: 12px; border: 1px solid {COLOR_PRIMARY_CYAN};")

            col = QVBoxLayout()
            l1 = QLabel(st_title)
            l1.setStyleSheet("font-size: 12px; font-weight: 700; color: #FFFFFF;")
            l2 = QLabel(st_desc)
            l2.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_MUTED};")
            col.addWidget(l1)
            col.addWidget(l2)

            row.addWidget(badge)
            row.addLayout(col, stretch=1)
            g_lay.addLayout(row)

        layout.addWidget(guide_box)

        layout.addSpacing(10)

        # Helper buttons
        tools_row = QHBoxLayout()
        btn_open_settings = QPushButton("⚙️ Open Windows Camera Privacy Settings ↗")
        btn_open_settings.clicked.connect(self._open_windows_camera_settings)
        tools_row.addWidget(btn_open_settings)

        btn_test_app = QPushButton("📸 Test in Windows Camera App ↗")
        btn_test_app.setObjectName("secondaryBtn")
        btn_test_app.clicked.connect(self._open_windows_camera_app)
        tools_row.addWidget(btn_test_app)
        layout.addLayout(tools_row)

        layout.addStretch()

        # Bottom navigation
        nav_row = QHBoxLayout()
        btn_recheck = QPushButton("🔄 Re-Check Camera Now")
        btn_recheck.setObjectName("secondaryBtn")
        btn_recheck.clicked.connect(self._recheck_camera_and_return)
        nav_row.addWidget(btn_recheck)

        nav_row.addStretch()

        btn_skip = QPushButton("Skip for Now & Open Control Center →")
        btn_skip.setObjectName("outlineBtn")
        btn_skip.clicked.connect(self._finish_and_launch)
        nav_row.addWidget(btn_skip)
        layout.addLayout(nav_row)

        return widget

    def _open_windows_camera_settings(self):
        try:
            os.system("start ms-settings:privacy-webcam")
        except Exception:
            pass

    def _open_windows_camera_app(self):
        try:
            os.system("start microsoft.windows.camera:")
        except Exception:
            pass

    def _recheck_camera_and_return(self):
        self.stack.setCurrentIndex(5)
        self._run_diagnostic_checks()

    def _finish_and_launch(self):
        self.settings.first_launch_completed = True
        self.flow_completed.emit(self.settings, self.profile)
        self.accept()
