from PIL import ImageStat
from capture.screen_capture import capture_monitor, capture_rect
from capture.window_capture import capture_window

def capture(settings):
    mode = settings["mode"]
    if mode not in ("Full Screen", "Selected Region", "Window Capture", "Application Capture"):
        raise ValueError("此模式尚未實作")
    from utils.desktop import ensure_interactive_desktop
    ensure_interactive_desktop()
    if mode == "Full Screen":
        image = capture_monitor(settings["monitor"])
    elif mode == "Selected Region":
        image = capture_rect(settings["region"])
    else:
        image = capture_window(settings["window"], settings.get("fallback", False))
    if max(ImageStat.Stat(image).stddev) < 0.5:
        raise RuntimeError("截圖為單色或空白：可能擷取失敗，也可能是有效純色內容；請確認目標畫面。")
    return image
