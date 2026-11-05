import sys
from utils.dpi import enable_dpi

def main():
    enable_dpi()
    from PySide6.QtWidgets import QApplication
    from gui.main_window import MainWindow
    app = QApplication(sys.argv)
    app.setApplicationName("Auto Screenshot Manager")
    window = MainWindow()
    window.show()
    if "--smoke-test" in sys.argv:
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500, window.close)
        QTimer.singleShot(3000, app.quit)
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
