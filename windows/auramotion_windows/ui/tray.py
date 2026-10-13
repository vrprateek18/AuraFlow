"""
System Tray Icon & Menu Controller for Windows
1:1 replica of macOS StatusItemController.swift
"""
from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu

class TrayController(QObject):
    open_control_center_signal = Signal()
    toggle_pause_signal = Signal(bool)
    toggle_hud_signal = Signal(bool)
    open_settings_signal = Signal()
    open_calibration_signal = Signal()
    open_tutorial_signal = Signal()
    open_onboarding_signal = Signal()
    quit_signal = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tray_icon = QSystemTrayIcon(parent)
        self._icon_pixmap = self._generate_tray_icon(is_active=True)
        self.tray_icon.setIcon(QIcon(self._icon_pixmap))
        self.tray_icon.setToolTip("AuraFlow — Move naturally. Control effortlessly.")
        self.tray_icon.activated.connect(self._on_tray_activated)

        self.menu = QMenu()
        self.menu.setStyleSheet("""
            QMenu {
                background-color: #07111F;
                color: #FFFFFF;
                border: 1px solid rgba(32, 191, 234, 0.3);
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #20BFEA;
                color: #07111F;
                font-weight: bold;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255,255,255,0.1);
                margin: 4px 8px;
            }
        """)

        # Actions
        self.act_open = QAction("Open AuraFlow Control Center", self.menu)
        self.act_open.triggered.connect(self.open_control_center_signal.emit)
        self.menu.addAction(self.act_open)

        self.menu.addSeparator()

        self.act_pause = QAction("Pause Gesture Control", self.menu)
        self.act_pause.setCheckable(True)
        self.act_pause.toggled.connect(self._on_pause_toggled)
        self.menu.addAction(self.act_pause)

        self.act_hud = QAction("Show Floating Mini-HUD", self.menu)
        self.act_hud.setCheckable(True)
        self.act_hud.setChecked(True)
        self.act_hud.toggled.connect(self._on_hud_toggled)
        self.menu.addAction(self.act_hud)

        self.act_tutorial = QAction("🎓 Gesture Tutorial & Practice...", self.menu)
        self.act_tutorial.triggered.connect(self.open_tutorial_signal.emit)
        self.menu.addAction(self.act_tutorial)

        self.act_cal = QAction("✋ Calibrate Hand...", self.menu)
        self.act_cal.triggered.connect(self.open_calibration_signal.emit)
        self.menu.addAction(self.act_cal)

        self.act_onboarding = QAction("🚀 First-Launch Setup Tour...", self.menu)
        self.act_onboarding.triggered.connect(self.open_onboarding_signal.emit)
        self.menu.addAction(self.act_onboarding)

        self.menu.addSeparator()

        self.act_settings = QAction("⚙️ Preferences & Tuning...", self.menu)
        self.act_settings.triggered.connect(self.open_settings_signal.emit)
        self.menu.addAction(self.act_settings)

        self.menu.addSeparator()

        self.act_quit = QAction("Quit AuraFlow", self.menu)
        self.act_quit.triggered.connect(self.quit_signal.emit)
        self.menu.addAction(self.act_quit)

        self.tray_icon.setContextMenu(self.menu)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_control_center_signal.emit()

    def show(self):
        self.tray_icon.show()

    def set_paused_state(self, is_paused: bool):
        self.act_pause.setChecked(is_paused)
        pix = self._generate_tray_icon(is_active=not is_paused)
        self.tray_icon.setIcon(QIcon(pix))

    def _on_pause_toggled(self, checked: bool):
        self.toggle_pause_signal.emit(checked)
        pix = self._generate_tray_icon(is_active=not checked)
        self.tray_icon.setIcon(QIcon(pix))

    def _on_hud_toggled(self, checked: bool):
        self.toggle_hud_signal.emit(checked)

    @staticmethod
    def _generate_tray_icon(is_active: bool = True) -> QPixmap:
        pix = QPixmap(32, 32)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color = QColor(0, 255, 200) if is_active else QColor(160, 160, 160)

        # Outer ring
        painter.setPen(color)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(4, 4, 24, 24)

        # Inner aura core
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(10, 10, 12, 12)

        painter.end()
        return pix
