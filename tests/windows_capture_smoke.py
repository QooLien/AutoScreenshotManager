"""Real Windows capture integration using a temporary test window.
Does not cover other applications, secondary monitors or background GPU windows.
"""
import sys
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ["ASM_DATA_DIR"] = str(Path(__file__).resolve().parent / ".runtime")
from utils.dpi import enable_dpi
enable_dpi()
from PySide6.QtCore import QTimer, QObject, Signal
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import QApplication, QWidget
from capture.service import capture
from utils.window_manager import list_windows
from utils.file_manager import save_image

class Pattern(QWidget):
    def paintEvent(self,event):
        painter = QPainter(self)
        painter.fillRect(self.rect(),QColor("white"))
        painter.fillRect(40,40,120,120,QColor("red"))
        painter.fillRect(180,40,120,120,QColor("blue"))
        painter.setPen(QColor("black"))
        painter.drawText(40,210,"Auto Screenshot Manager integration test")

class Bridge(QObject):
    done = Signal(str)

app = QApplication([])
window = Pattern()
window.setWindowTitle("ASM Synthetic Capture Test")
window.resize(500,300)
window.show()
bridge = Bridge()
executor = ThreadPoolExecutor(max_workers=1)
errors = []

def work():
    try:
        from dataclasses import asdict
        target = next(w for w in list_windows() if w.title == "ASM Synthetic Capture Test")
        left,top,right,bottom = target.rect
        output = Path(__file__).resolve().parent / ".runtime" / "captures"
        failures = []
        for mode in ("Selected Region","Window Capture"):
            settings = dict(name=mode,folder=str(output),format="PNG",date_folder=False,mode=mode,region=dict(left=left,top=top,width=right-left,height=bottom-top),window=asdict(target),fallback=False)
            try:
                image = capture(settings)
                assert image.size == (right-left,bottom-top)
                path = save_image(image,settings)
                assert Path(path).is_file()
                print(f"{mode}: {image.size}, saved {Path(path).name}")
            except Exception as exc:
                failures.append(f"{mode}: {exc}")
        bridge.done.emit("; ".join(failures))
    except Exception as exc:
        bridge.done.emit(str(exc))

def finished(error):
    if error:
        errors.append(error)
    window.close()
    app.quit()

bridge.done.connect(finished)
QTimer.singleShot(700,lambda: executor.submit(work))
app.exec()
executor.shutdown()
if errors:
    raise RuntimeError(errors[0])
print("Real region and PrintWindow synthetic-window capture passed")
