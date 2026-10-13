"""
Physical Input Arbitrator for Windows
Monitors physical mouse events using WH_MOUSE_LL low-level mouse hook.
Ignores AuraMotion's own events via kAuraMotionEventMagicTag.
Yields gesture control when user operates physical mouse.
"""
import ctypes
from ctypes import wintypes
import threading
import time
from typing import Callable, Optional

kAuraMotionEventMagicTag = 0x41555241

WH_MOUSE_LL = 14
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_RBUTTONDOWN = 0x0204
WM_MBUTTONDOWN = 0x0207

ULONG_PTR = wintypes.WPARAM

class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", wintypes.POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]

LRESULT = ctypes.c_ssize_t

HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

user32 = ctypes.windll.user32
SetWindowsHookEx = user32.SetWindowsHookExW
SetWindowsHookEx.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
SetWindowsHookEx.restype = wintypes.HHOOK

UnhookWindowsHookEx = user32.UnhookWindowsHookEx
UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
UnhookWindowsHookEx.restype = wintypes.BOOL

CallNextHookEx = user32.CallNextHookEx
CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
CallNextHookEx.restype = LRESULT

GetMessage = user32.GetMessageW
TranslateMessage = user32.TranslateMessage
DispatchMessage = user32.DispatchMessageW
PostThreadMessage = user32.PostThreadMessageW
PostThreadMessage.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
PostThreadMessage.restype = wintypes.BOOL
WM_QUIT = 0x0012

class PhysicalInputArbitrator:
    def __init__(self, on_physical_input: Optional[Callable[[], None]] = None, cooldown_seconds: float = 1.0):
        self.on_physical_input = on_physical_input
        self.cooldown_seconds = cooldown_seconds
        self.last_physical_time: float = 0.0
        self._hook = None
        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None
        self._hook_proc = None
        self._stop_requested = False

    @property
    def is_yielding(self) -> bool:
        return (time.time() - self.last_physical_time) < self.cooldown_seconds

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_requested = False
        self._thread = threading.Thread(target=self._run_hook_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_requested = True
        if self._thread_id is not None:
            PostThreadMessage(self._thread_id, WM_QUIT, 0, 0)
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

    def _run_hook_loop(self):
        self._thread_id = threading.get_native_id()

        def hook_callback(nCode, wParam, lParam):
            if nCode >= 0 and lParam:
                hook_data = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                # Check magic tag
                if hook_data.dwExtraInfo != kAuraMotionEventMagicTag:
                    # External physical event detected
                    if wParam in (WM_LBUTTONDOWN, WM_RBUTTONDOWN, WM_MBUTTONDOWN):
                        self.last_physical_time = time.time()
                        if self.on_physical_input:
                            self.on_physical_input()
            return CallNextHookEx(self._hook, nCode, wParam, lParam)

        self._hook_proc = HOOKPROC(hook_callback)
        self._hook = SetWindowsHookEx(WH_MOUSE_LL, self._hook_proc, None, 0)

        msg = wintypes.MSG()
        while not self._stop_requested and GetMessage(ctypes.byref(msg), 0, 0, 0) > 0:
            TranslateMessage(ctypes.byref(msg))
            DispatchMessage(ctypes.byref(msg))

        if self._hook:
            UnhookWindowsHookEx(self._hook)
            self._hook = None
