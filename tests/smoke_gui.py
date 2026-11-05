"""Creates the real GUI and exits; does not take desktop screenshots."""
import sys
import os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ["ASM_DATA_DIR"] = str(Path(__file__).resolve().parent / ".runtime")
from utils.dpi import enable_dpi
enable_dpi()
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow
app = QApplication([])
window = MainWindow()
window.show()
QTimer.singleShot(500,lambda: window.grab().save(str(Path(os.environ["ASM_DATA_DIR"])/"gui-preview.png")))
QTimer.singleShot(1200,window.close)
QTimer.singleShot(2500,app.quit)
result = app.exec()
assert result == 0
print('GUI construction and shutdown passed')
