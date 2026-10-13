"""
Global Windows Hotkey Manager for Emergency Gesture Stop & Pause
Registers system-wide hotkeys (F8 and Ctrl+Alt+P) using user32.dll RegisterHotKey.
Integrates with Qt native event filtering for instant, zero-latency toggling from any application.
"""
import ctypes
from ctypes import wintypes
import winsound
from typing import Callable, Optional

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Signal
from PySide6.QtWidgets import QApplication

# Win32 Constants
WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

VK_F8 = 0x77
VK_P = 0x50

HOTKEY_ID_F8 = 1001
HOTKEY_ID_CTRL_ALT_P = 1002

user32 = ctypes.windll.user32
RegisterHotKey = user32.RegisterHotKey
RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
RegisterHotKey.restype = wintypes.BOOL

UnregisterHotKey = user32.UnregisterHotKey
UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
UnregisterHotKey.restype = wintypes.BOOL


class _NativeHotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self, on_hotkey: Callable[[], None]):
        super().__init__()
        self.on_hotkey = on_hotkey

    def nativeEventFilter(self, event_type, message):
        if event_type in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
            try:
                addr = int(message)
                msg = wintypes.MSG.from_address(addr)
                if msg.message == WM_HOTKEY:
                    if msg.wParam in (HOTKEY_ID_F8, HOTKEY_ID_CTRL_ALT_P):
                        self.on_hotkey()
                        return True, 0
            except Exception:
                pass
        return False, 0


class GlobalEmergencyHotkey(QObject):
    """
    Manages global F8 and Ctrl+Alt+P hotkeys for immediate emergency stop / pause.
    Safe on Windows 11 x64, handles registration and clean teardown.
    """
    hotkey_triggered = Signal()

    def __init__(self, on_toggle: Optional[Callable[[], None]] = None, parent=None):
        super().__init__(parent)
        self.on_toggle = on_toggle
        self._filter: Optional[_NativeHotkeyFilter] = None
        self._is_registered = False

    def start(self) -> bool:
        if self._is_registered:
            return True

        app = QApplication.instance()
        if not app:
            return False

        # Install native Qt event filter
        self._filter = _NativeHotkeyFilter(self._handle_hotkey)
        app.installNativeEventFilter(self._filter)

        # Register F8 (NoRepeat)
        f8_ok = RegisterHotKey(None, HOTKEY_ID_F8, MOD_NOREPEAT, VK_F8)

        # Register Ctrl+Alt+P (NoRepeat)
        ctrl_alt_p_ok = RegisterHotKey(None, HOTKEY_ID_CTRL_ALT_P, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_P)

        self._is_registered = f8_ok or ctrl_alt_p_ok
        return self._is_registered

    def stop(self):
        if not self._is_registered:
            return

        try:
            UnregisterHotKey(None, HOTKEY_ID_F8)
            UnregisterHotKey(None, HOTKEY_ID_CTRL_ALT_P)
        except Exception:
            pass

        app = QApplication.instance()
        if app and self._filter:
            try:
                app.removeNativeEventFilter(self._filter)
            except Exception:
                pass

        self._filter = None
        self._is_registered = False

    def _handle_hotkey(self):
        # Audible confirmation cue
        try:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            pass

        self.hotkey_triggered.emit()
        if self.on_toggle:
            self.on_toggle()
