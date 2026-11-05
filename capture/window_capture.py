import ctypes
from PIL import Image, ImageStat
from capture.screen_capture import capture_rect
from utils.window_manager import resolve_window

def capture_window(target, allow_fallback=False):
    import win32gui
    import win32ui
    window = resolve_window(target)
    if window.minimized:
        raise RuntimeError("視窗已最小化；請先還原視窗。PrintWindow 無法保證擷取最小化視窗。")
    left, top, right, bottom = window.rect
    width, height = right-left, bottom-top
    hwnd_dc = win32gui.GetWindowDC(window.hwnd)
    source = destination = bitmap = old = None
    try:
        source = win32ui.CreateDCFromHandle(hwnd_dc)
        destination = source.CreateCompatibleDC()
        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(source, width, height)
        old = destination.SelectObject(bitmap)
        print_window = ctypes.windll.user32.PrintWindow
        from ctypes import wintypes
        print_window.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
        print_window.restype = wintypes.BOOL
        ok = print_window(window.hwnd, destination.GetSafeHdc(), 2)
        image = Image.frombuffer("RGB", (width,height), bitmap.GetBitmapBits(True), "raw", "BGRX", 0, 1).copy()
        stats = ImageStat.Stat(image)
        if not ok or max(stats.stddev) < 0.5:
            raise RuntimeError("PrintWindow 失敗或產生單色畫面（也可能是有效的純色內容）。")
        return image
    except Exception as exc:
        if not allow_fallback:
            raise RuntimeError(f"背景視窗擷取失敗：{exc}。硬體加速內容可能無法擷取。") from exc
        return capture_rect(dict(left=left, top=top, width=width, height=height))
    finally:
        if old is not None and destination:
            destination.SelectObject(old)
        if bitmap:
            win32gui.DeleteObject(bitmap.GetHandle())
        if destination:
            destination.DeleteDC()
        if source:
            source.DeleteDC()
        win32gui.ReleaseDC(window.hwnd, hwnd_dc)
