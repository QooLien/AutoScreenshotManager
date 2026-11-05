from datetime import datetime
from pathlib import Path
import re
import uuid

def save_image(image, settings):
    folder = Path(settings["folder"]).expanduser()
    now = datetime.now().astimezone()
    if settings.get("date_folder", True):
        folder /= now.strftime("%Y-%m-%d")
    folder.mkdir(parents=True, exist_ok=True)
    prefix = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", settings.get("name", "Capture")).strip(" .")[:80] or "Capture"
    ext = settings.get("format", "PNG").lower()
    if ext not in ("png", "jpg"):
        raise ValueError("Unsupported image format")
    name = f"{prefix}_{now:%Y%m%d_%H%M%S}_{now.microsecond//1000:03d}_{uuid.uuid4().hex[:12]}.{ext}"
    target = folder / name
    created = False
    try:
        with target.open("xb") as output:
            created = True
            image.convert("RGB").save(output, format="JPEG" if ext == "jpg" else "PNG", quality=int(settings.get("quality", 90)))
    except Exception:
        if created:
            target.unlink(missing_ok=True)
        raise
    return str(target)

def append_history(record):
    import json
    from utils.config_manager import DATA_DIR
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with (DATA_DIR / "history.jsonl").open("a", encoding="utf-8") as output:
        output.write(json.dumps(record, ensure_ascii=False) + "\n")
