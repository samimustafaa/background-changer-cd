"""Non-invasive Win32 foreground-window wallpaper overlay.

No injection, hooks, memory access, game-file changes, or anti-cheat bypass.
Only supports windowed / borderless desktop composition on Windows.
"""
from __future__ import annotations

import ctypes
import os
import time
import tkinter as tk
from ctypes import wintypes

import psutil
from PIL import Image, ImageTk, ImageGrab
from lobby_regions import chroma_frame

CHROMA = '#010203'
POLL_MS = 350
GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020


def request_dpi_awareness() -> None:
    """Call BEFORE creating the first Tk root for accurate Win32 pixel sizing."""
    if os.name != 'nt':
        return
    try:
        # Per Monitor v2: exact desktop pixels, even on 125%/150% DPI screens.
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (AttributeError, OSError):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            pass


class LiveLobbyOverlay:
    """Displays a clickable-through wallpaper clipped to the lobby sky area.

    Display follows the foreground game client window. It never touches game
    processes other than reading the foreground PID/name and client rectangle.
    """
    def __init__(self, root: tk.Tk, status_callback=None):
        if os.name != 'nt':
            raise RuntimeError('Live game overlay requires Windows 10/11.')
        self.root = root
        self.status_callback = status_callback or (lambda text: None)
        self.user32 = ctypes.windll.user32
        # Explicit signatures: HWND is pointer-sized on 64-bit Windows.
        self.user32.GetParent.argtypes = [wintypes.HWND]
        self.user32.GetParent.restype = wintypes.HWND
        self.user32.GetForegroundWindow.argtypes = []
        self.user32.GetForegroundWindow.restype = wintypes.HWND
        self.user32.GetWindowThreadProcessId.argtypes = [
            wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        self.user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        self.user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        self.user32.GetClientRect.restype = wintypes.BOOL
        self.user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
        self.user32.ClientToScreen.restype = wintypes.BOOL
        self.user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
        self.user32.SetWindowLongW.argtypes = [
            wintypes.HWND, ctypes.c_int, wintypes.LONG]
        self.user32.SetWindowPos.argtypes = [
            wintypes.HWND, wintypes.HWND,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
        self.window = tk.Toplevel(root)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.configure(bg=CHROMA)
        self.window.attributes('-transparentcolor', CHROMA)
        self.window.attributes('-topmost', True)
        self.canvas = tk.Canvas(self.window, bg=CHROMA, highlightthickness=0, bd=0)
        self.canvas.pack(fill='both', expand=True)
        self.window.update_idletasks()
        self._enable_clickthrough()
        self.armed = False
        self.wallpaper = None
        self.protection = None
        self.process_name = 'client.exe'
        self.last_rect = None
        self.guard_lobby = True
        self.last_lobby_check = 0.0
        self.last_lobby_ok = False
        self.photo = None
        self.last_state = None
        self._scheduled = None
        self._schedule()

    def _enable_clickthrough(self):
        """Use a layered topmost non-activating window; clicks pass to game."""
        hwnd = self.user32.GetParent(self.window.winfo_id()) or self.window.winfo_id()
        style = self.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        self.user32.SetWindowLongW(hwnd, GWL_EXSTYLE,
            style | WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)
        self.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0,
            SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE | SWP_FRAMECHANGED)

    def _status(self, message):
        if message != self.last_state:
            self.last_state = message
            self.status_callback(message)

    def arm(self, wallpaper: Image.Image, protection: Image.Image | None,
            game_exe: str = 'client.exe', guard_lobby: bool = True) -> None:
        name = os.path.basename(game_exe.strip()).lower()
        if not name.endswith('.exe'):
            raise ValueError('Enter a Windows executable filename, e.g. client.exe')
        self.process_name = name
        self.guard_lobby = guard_lobby
        self.last_lobby_check = 0
        self.last_lobby_ok = False
        self.wallpaper = wallpaper.convert('RGB').copy()
        self.protection = protection.copy() if protection is not None else None
        self.last_rect = None
        self.armed = True
        self._status('ARMED — switch to the game lobby (windowed/borderless).')

    def remove(self) -> None:
        self.armed = False
        self.last_rect = None
        self._hide()
        self._status('REMOVED — lobby background overlay disabled.')

    def close(self):
        self.remove()
        if self._scheduled is not None:
            try:
                self.root.after_cancel(self._scheduled)
            except tk.TclError:
                pass
            self._scheduled = None
        try:
            self.window.destroy()
        except tk.TclError:
            pass

    def _schedule(self):
        self._scheduled = self.root.after(POLL_MS, self._tick)

    def _hide(self):
        try:
            if self.window.state() != 'withdrawn':
                self.window.withdraw()
        except tk.TclError:
            pass

    def _game_rect(self):
        """Use only the active game window. Return (x,y,w,h) or None."""
        hwnd = self.user32.GetForegroundWindow()
        if not hwnd:
            return None
        pid = wintypes.DWORD()
        self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        try:
            if psutil.Process(pid.value).name().lower() != self.process_name:
                return None
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            return None
        if self.user32.IsIconic(hwnd):
            return None
        rect = wintypes.RECT()
        if not self.user32.GetClientRect(hwnd, ctypes.byref(rect)):
            return None
        pt = wintypes.POINT(0, 0)
        if not self.user32.ClientToScreen(hwnd, ctypes.byref(pt)):
            return None
        w, h = rect.right - rect.left, rect.bottom - rect.top
        if w < 700 or h < 400:
            return None
        # This mask was designed for the supplied 16:9 lobby.
        if abs(w / h - 16/9) > 0.17:
            self._status('WAITING — use a 16:9 borderless/windowed game resolution.')
            return None
        return pt.x, pt.y, w, h

    def _lobby_start_visible(self, rect):
        """Optional safety guard: sample only the bottom-right Start button.

        If the lobby Start button is absent (e.g. gameplay), the overlay is
        automatically hidden. This heuristic can be disabled in the editor.
        """
        x, y, w, h = rect
        box = (x + int(.79*w), y + int(.89*h),
               x + int(.96*w), y + int(.95*h))
        sample = ImageGrab.grab(bbox=box).convert('RGB').resize((32, 12))
        colors = list(sample.getdata())
        yellow = sum(1 for r,g,b in colors if r > 185 and g > 135 and b < 145)
        return yellow > len(colors) * .30

    def _paint_rect(self, rect):
        x, y, w, h = rect
        # PIL images are computed only on image selection / window size changes,
        # never on every game frame.
        frame = chroma_frame(self.wallpaper, (w, h), self.protection)
        self.photo = ImageTk.PhotoImage(frame, master=self.window)
        self.window.geometry(f'{w}x{h}{x:+d}{y:+d}')
        self.canvas.configure(width=w, height=h)
        self.canvas.delete('all')
        self.canvas.create_image(0, 0, image=self.photo, anchor='nw')
        self.last_rect = rect

    def _tick(self):
        try:
            if not self.armed:
                self._hide()
                return
            rect = self._game_rect()
            if rect is None:
                self._hide()
                self._status('ARMED — waiting for focused ' + self.process_name)
                return
            if self.guard_lobby:
                now = time.monotonic()
                if now - self.last_lobby_check >= .9 or rect != self.last_rect:
                    self.last_lobby_check = now
                    self.last_lobby_ok = self._lobby_start_visible(rect)
                if not self.last_lobby_ok:
                    self._hide()
                    self._status('ARMED — game found, waiting for lobby Start button.')
                    return
            if rect != self.last_rect:
                self._paint_rect(rect)
            if self.window.state() == 'withdrawn':
                self.window.deiconify()
                self._enable_clickthrough()
            # Foreground game remains active because this overlay is no-activate.
            self._status('APPLIED — live lobby overlay on ' + self.process_name)
        except Exception as exc:
            self._hide()
            self._status('OVERLAY ERROR — ' + str(exc)[:130])
        finally:
            self._schedule()
