from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtGui import QPainter, QColor, QPen

class RegionOverlay(QWidget):
    selected = Signal(dict)
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        geometry = QRect()
        for screen in QApplication.screens():
            geometry = geometry.united(screen.geometry())
        self.setGeometry(geometry)
        self.start = self.end = None
        self.setCursor(Qt.CrossCursor)

    def mousePressEvent(self, event):
        self.start = self.end = event.position().toPoint()

    def mouseMoveEvent(self, event):
        if self.start is not None:
            self.end = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        import ctypes
        from ctypes import wintypes
        if self.start is None:
            return
        # Native cursor coordinates are physical pixels under per-monitor DPI awareness.
        point = wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
        end = (point.x, point.y)
        start = self.native_start
        left, top = min(start[0],end[0]), min(start[1],end[1])
        width, height = abs(start[0]-end[0]), abs(start[1]-end[1])
        if width and height:
            self.selected.emit(dict(left=left, top=top, width=width, height=height))
        self.close()

    def event(self, event):
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.MouseButtonPress:
            import ctypes
            from ctypes import wintypes
            point = wintypes.POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
            self.native_start = (point.x, point.y)
        return super().event(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0,0,0,75))
        if self.start is not None:
            rect = QRect(self.start, self.end).normalized()
            painter.setPen(QPen(QColor("#44ccff"), 2))
            painter.drawRect(rect)
            painter.drawText(rect.topLeft() + QPoint(0,-8), f"{rect.width()} × {rect.height()} (邏輯像素；儲存時轉實體座標)")
