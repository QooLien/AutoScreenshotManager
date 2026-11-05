import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

import pytest

_QT_APP = None

@pytest.fixture(scope="session")
def qt_app():
    global _QT_APP
    from PySide6.QtWidgets import QApplication
    _QT_APP = QApplication.instance() or QApplication([])
    return _QT_APP
