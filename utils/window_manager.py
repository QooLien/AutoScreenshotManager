from dataclasses import dataclass
import psutil

@dataclass
class Window:
    hwnd: int
    title: str
    process: str
    pid: int
    rect: tuple
    minimized: bool
    maximized: bool = False

def list_windows():
    import win32gui
    import win32process
    import pywintypes
    result = []
    def callback(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd) or not win32gui.GetWindowText(hwnd):
            return
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid).name()
            rect = win32gui.GetWindowRect(hwnd)
            if rect[2] > rect[0] and rect[3] > rect[1]:
                result.append(Window(hwnd, win32gui.GetWindowText(hwnd), process, pid, rect, bool(win32gui.IsIconic(hwnd)), win32gui.GetWindowPlacement(hwnd)[1] == 3))
        except (psutil.Error, OSError, pywintypes.error):
            pass
    win32gui.EnumWindows(callback, None)
    return result

def resolve_window(target):
    windows = list_windows()
    for window in windows:
        if window.hwnd == target["hwnd"] and window.pid == target["pid"] and window.process.lower() == target["process"].lower():
            return window
    matches = [w for w in windows if w.process.lower() == target["process"].lower() and target.get("keyword", target["title"]).lower() in w.title.lower()]
    if len(matches) != 1:
        raise RuntimeError("目標視窗不存在或重新辨識得到多個結果，請重新選取視窗。")
    return matches[0]
