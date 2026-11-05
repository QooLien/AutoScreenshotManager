import json
import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("ASM_DATA_DIR", str(Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "AutoScreenshotManager")))

def save_config(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)

def load_config(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
