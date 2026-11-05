import sys

def main():
    from utils.dpi import enable_dpi
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
    try:
        exit_code = main()
    except Exception as error:
        import traceback

        details = traceback.format_exc()
        if sys.stderr is not None:
            print(details, file=sys.stderr)
        if sys.platform == "win32" and "--smoke-test" not in sys.argv:
            import ctypes
            import tempfile
            from pathlib import Path

            log_path = Path(tempfile.gettempdir()) / "AutoScreenshotManager-startup.log"
            try:
                log_path.write_text(details, encoding="utf-8")
                log_message = f"\n\nDetails: {log_path}"
            except OSError:
                log_message = ""
            ctypes.windll.user32.MessageBoxW(
                None,
                f"Auto Screenshot Manager could not start.\n\n{error}"
                f"\n\nIf running from source, double-click Start.bat."
                f"{log_message}",
                "Auto Screenshot Manager",
                0x10,
            )
        exit_code = 1
    sys.exit(exit_code)
