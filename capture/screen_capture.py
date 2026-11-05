from PIL import Image
import mss

def monitors():
    with mss.mss() as capture:
        return [dict(m) for m in capture.monitors]

def capture_rect(rect):
    if rect["width"] <= 0 or rect["height"] <= 0:
        raise ValueError("區域寬度及高度必須大於零")
    if rect["width"] * rect["height"] > 100_000_000:
        raise ValueError("截圖區域超過 1 億像素安全上限")
    with mss.mss() as capture:
        desktop = capture.monitors[0]
        if (rect["left"] < desktop["left"] or rect["top"] < desktop["top"] or
            rect["left"] + rect["width"] > desktop["left"] + desktop["width"] or
            rect["top"] + rect["height"] > desktop["top"] + desktop["height"]):
            raise ValueError("指定區域超出目前虛擬桌面範圍，請重新選取")
        shot = capture.grab(rect)
        return Image.frombytes("RGB", shot.size, shot.rgb)

def capture_monitor(index):
    with mss.mss() as capture:
        if not 0 <= index < len(capture.monitors):
            raise ValueError("顯示器已移除，請重新選取")
        shot = capture.grab(capture.monitors[index])
        return Image.frombytes("RGB", shot.size, shot.rgb)
