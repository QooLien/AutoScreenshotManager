from PIL import Image, ImageOps, ImageStat
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
        region = settings.get("window_region")
        image = capture_window(settings["window"], settings.get("fallback", False) and not region)
        if region:
            left, top = region["left"], region["top"]
            right, bottom = left + region["width"], top + region["height"]
            if not (0 <= left < right <= image.width and 0 <= top < bottom <= image.height):
                raise ValueError("選區超出目前視窗大小，請重新選取。")
            return image.crop((left, top, right, bottom))
    if max(ImageStat.Stat(image).stddev) < 0.5:
        raise RuntimeError("截圖為單色或空白：可能擷取失敗，也可能是有效純色內容；請確認目標畫面。")
    if mode == "Full Screen" and settings.get("resolution"):
        image = ImageOps.pad(image, tuple(settings["resolution"]), Image.Resampling.LANCZOS, color="black")
    return image
