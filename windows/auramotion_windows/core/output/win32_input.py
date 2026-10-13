"""
Native Windows Win32 Input Injection via user32.dll SendInput
Tagged with kAuraMotionEventMagicTag = 0x41555241 ("AURAMOTN")
"""
import ctypes
from ctypes import wintypes
import time
from typing import Optional, Tuple
from ..domain.models import Point2D, GestureCommand, FingerShortcut, PalmSwipeDirection

kAuraMotionEventMagicTag = 0x41555241

# Win32 Constants
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x00010
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x01000
MOUSEEVENTF_VIRTUALDESK = 0x4000
MOUSEEVENTF_ABSOLUTE = 0x8000

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002

VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12  # ALT
VK_TAB = 0x09
VK_LWIN = 0x5B
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
VK_C = 0x43
VK_V = 0x56

ULONG_PTR = wintypes.WPARAM

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("u", _INPUT_UNION),
    ]

user32 = ctypes.windll.user32
SendInput = user32.SendInput
SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
SendInput.restype = wintypes.UINT

GetSystemMetrics = user32.GetSystemMetrics
SM_CXSCREEN = 0
SM_CYSCREEN = 1
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79
SM_CMONITORS = 80

class Win32EventSynthesizer:
    def __init__(self):
        self.is_left_down = False
        self.refresh_screen_metrics()

    def refresh_screen_metrics(self):
        self.screen_width = max(1, GetSystemMetrics(SM_CXSCREEN))
        self.screen_height = max(1, GetSystemMetrics(SM_CYSCREEN))
        self.vx = GetSystemMetrics(SM_XVIRTUALSCREEN)
        self.vy = GetSystemMetrics(SM_YVIRTUALSCREEN)
        self.vw = max(self.screen_width, GetSystemMetrics(SM_CXVIRTUALSCREEN))
        self.vh = max(self.screen_height, GetSystemMetrics(SM_CYVIRTUALSCREEN))
        self.num_monitors = max(1, GetSystemMetrics(SM_CMONITORS))

    def get_virtual_desktop_bounds(self) -> Tuple[int, int, int, int]:
        """Returns (vx, vy, vw, vh) virtual desktop bounding box spanning all connected displays."""
        return self.vx, self.vy, self.vw, self.vh

    def _send_mouse(self, flags: int, dx: int = 0, dy: int = 0, data: int = 0):
        inp = INPUT()
        inp.type = INPUT_MOUSE
        inp.u.mi.dx = dx
        inp.u.mi.dy = dy
        inp.u.mi.mouseData = data
        inp.u.mi.dwFlags = flags
        inp.u.mi.time = 0
        inp.u.mi.dwExtraInfo = kAuraMotionEventMagicTag
        SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def _send_key(self, vk: int, key_up: bool = False, extended: bool = False):
        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.u.ki.wVk = vk
        inp.u.ki.wScan = 0
        flags = (KEYEVENTF_KEYUP if key_up else 0) | (KEYEVENTF_EXTENDEDKEY if extended else 0)
        inp.u.ki.dwFlags = flags
        inp.u.ki.time = 0
        inp.u.ki.dwExtraInfo = kAuraMotionEventMagicTag
        SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def move_to(self, x: float, y: float, span_virtual_desktop: bool = False):
        if span_virtual_desktop and self.num_monitors > 1:
            # Map across all virtual desktop monitors
            norm_x = int(max(0.0, min(1.0, (x - self.vx) / max(1.0, float(self.vw)))) * 65535)
            norm_y = int(max(0.0, min(1.0, (y - self.vy) / max(1.0, float(self.vh)))) * 65535)
            self._send_mouse(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK, dx=norm_x, dy=norm_y)
        else:
            # Map to primary display
            norm_x = int(max(0.0, min(1.0, x / self.screen_width)) * 65535)
            norm_y = int(max(0.0, min(1.0, y / self.screen_height)) * 65535)
            self._send_mouse(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, dx=norm_x, dy=norm_y)

    def mouse_down(self):
        if not self.is_left_down:
            self._send_mouse(MOUSEEVENTF_LEFTDOWN)
            self.is_left_down = True

    def mouse_up(self):
        if self.is_left_down:
            self._send_mouse(MOUSEEVENTF_LEFTUP)
            self.is_left_down = False

    def click(self, x: Optional[float] = None, y: Optional[float] = None, span_virtual_desktop: bool = False):
        if x is not None and y is not None:
            self.move_to(x, y, span_virtual_desktop=span_virtual_desktop)
        self._send_mouse(MOUSEEVENTF_LEFTDOWN)
        time.sleep(0.015)
        self._send_mouse(MOUSEEVENTF_LEFTUP)
        self.is_left_down = False

    def right_click(self, x: Optional[float] = None, y: Optional[float] = None):
        if x is not None and y is not None:
            self.move_to(x, y)
        self._send_mouse(MOUSEEVENTF_RIGHTDOWN)
        time.sleep(0.015)
        self._send_mouse(MOUSEEVENTF_RIGHTUP)

    def double_click(self, x: Optional[float] = None, y: Optional[float] = None):
        self.click(x, y)
        time.sleep(0.05)
        self.click(x, y)

    def scroll(self, delta_x: float, delta_y: float):
        # On Windows, positive WHEEL delta scrolls up, negative scrolls down.
        # AuraMotion uses positive delta for scrolling content down (finger down).
        # We multiply by 8 for natural scroll wheel clicks.
        if abs(delta_y) > 0.1:
            wheel_amount = int(delta_y * 8)
            self._send_mouse(MOUSEEVENTF_WHEEL, data=wheel_amount)
        if abs(delta_x) > 0.1:
            hwheel_amount = int(delta_x * 8)
            self._send_mouse(MOUSEEVENTF_HWHEEL, data=hwheel_amount)

    def release_all_mouse_buttons(self):
        """Forces immediate release of left, right, and middle mouse buttons."""
        try:
            self._send_mouse(MOUSEEVENTF_LEFTUP)
            self._send_mouse(MOUSEEVENTF_RIGHTUP)
            self.is_left_down = False
        except Exception:
            pass

    def release_all_modifiers(self):
        """Forces release of all keyboard modifier keys (Ctrl, Alt, Shift, Win)."""
        try:
            for vk in (VK_CONTROL, VK_MENU, VK_SHIFT, VK_LWIN):
                self._send_key(vk, key_up=True)
        except Exception:
            pass

    def trigger_emergency_release(self):
        """Bulletproof emergency stop: releases all mouse buttons and keyboard modifiers."""
        self.release_all_mouse_buttons()
        self.release_all_modifiers()

    def post_shortcut(self, shortcut: FingerShortcut):
        if shortcut == FingerShortcut.COPY:
            # Ctrl + C
            self._send_key(VK_CONTROL, key_up=False)
            self._send_key(VK_C, key_up=False)
            time.sleep(0.01)
            self._send_key(VK_C, key_up=True)
            self._send_key(VK_CONTROL, key_up=True)
        elif shortcut == FingerShortcut.PASTE:
            # Ctrl + V
            self._send_key(VK_CONTROL, key_up=False)
            self._send_key(VK_V, key_up=False)
            time.sleep(0.01)
            self._send_key(VK_V, key_up=True)
            self._send_key(VK_CONTROL, key_up=True)

    def post_swipe(self, direction: PalmSwipeDirection):
        if direction == PalmSwipeDirection.RIGHT:
            # Next app: Alt + Tab
            self._send_key(VK_MENU, key_up=False)
            self._send_key(VK_TAB, key_up=False)
            time.sleep(0.01)
            self._send_key(VK_TAB, key_up=True)
            self._send_key(VK_MENU, key_up=True)
        else:
            # Previous app: Alt + Shift + Tab
            self._send_key(VK_MENU, key_up=False)
            self._send_key(VK_SHIFT, key_up=False)
            self._send_key(VK_TAB, key_up=False)
            time.sleep(0.01)
            self._send_key(VK_TAB, key_up=True)
            self._send_key(VK_SHIFT, key_up=True)
            self._send_key(VK_MENU, key_up=True)

    def post_command(self, command: GestureCommand, target: Point2D):
        if command == GestureCommand.RIGHT_CLICK:
            self.right_click(target.x, target.y)
        elif command == GestureCommand.DOUBLE_CLICK:
            self.double_click(target.x, target.y)
        elif command == GestureCommand.PREVIOUS_APP:
            self.post_swipe(PalmSwipeDirection.LEFT)
        elif command == GestureCommand.NEXT_APP:
            self.post_swipe(PalmSwipeDirection.RIGHT)
        elif command == GestureCommand.MISSION_CONTROL:
            # Task View: Win + Tab
            self._send_key(VK_LWIN, key_up=False)
            self._send_key(VK_TAB, key_up=False)
            time.sleep(0.01)
            self._send_key(VK_TAB, key_up=True)
            self._send_key(VK_LWIN, key_up=True)
        elif command == GestureCommand.MINIMIZE:
            # Win + Down
            self._send_key(VK_LWIN, key_up=False)
            self._send_key(VK_DOWN, key_up=False)
            time.sleep(0.01)
            self._send_key(VK_DOWN, key_up=True)
            self._send_key(VK_LWIN, key_up=True)
        elif command == GestureCommand.FULL_SCREEN:
            # Win + Up
            self._send_key(VK_LWIN, key_up=False)
            self._send_key(VK_UP, key_up=False)
            time.sleep(0.01)
            self._send_key(VK_UP, key_up=True)
            self._send_key(VK_LWIN, key_up=True)
        elif command == GestureCommand.SNAP_LEFT:
            # Win + Left
            self._send_key(VK_LWIN, key_up=False)
            self._send_key(VK_LEFT, key_up=False)
            time.sleep(0.01)
            self._send_key(VK_LEFT, key_up=True)
            self._send_key(VK_LWIN, key_up=True)
        elif command == GestureCommand.SNAP_RIGHT:
            # Win + Right
            self._send_key(VK_LWIN, key_up=False)
            self._send_key(VK_RIGHT, key_up=False)
            time.sleep(0.01)
            self._send_key(VK_RIGHT, key_up=True)
            self._send_key(VK_LWIN, key_up=True)
