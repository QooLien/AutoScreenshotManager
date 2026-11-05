import ctypes
from ctypes import wintypes

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QApplication, QWidget


def physical_cursor():
    point = wintypes.POINT()
    if ctypes.windll.user32.GetCursorPos(ctypes.byref(point)):
        return QPoint(point.x, point.y)
    return None


class RegionOverlay(QWidget):
    selected = Signal(dict)
    closed = Signal()
    SAMPLE_SIZE = 31
    ZOOM = 5

    def __init__(self, desktop=None, origin=None):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)
        geometry = QRect()
        for screen in QApplication.screens():
            geometry = geometry.united(screen.geometry())
        self.setGeometry(geometry)
        self.desktop = desktop
        self.origin = origin if origin is not None else QPoint()
        self.start = self.end = self.native_start = None
        self.cursor = self.native_cursor = None
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)

    def update_cursor(self, event):
        self.cursor = event.position().toPoint()
        self.native_cursor = physical_cursor()
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.update_cursor(event)
            self.start = self.end = self.cursor
            self.native_start = self.native_cursor

    def mouseMoveEvent(self, event):
        self.update_cursor(event)
        if self.start is not None:
            self.end = self.cursor

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton or self.start is None:
            return
        self.update_cursor(event)
        start, end = self.native_start, self.native_cursor
        if start is not None and end is not None:
            width, height = abs(start.x() - end.x()), abs(start.y() - end.y())
            if width and height:
                self.selected.emit(dict(left=min(start.x(), end.x()), top=min(start.y(), end.y()),
                                        width=width, height=height))
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        super().closeEvent(event)
        self.closed.emit()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 75))
        painter.setPen(QColor("white"))
        hint = "拖曳選取區域，按 Esc 取消"
        if self.desktop is None:
            hint += "。目前無法取得放大鏡預覽"
        painter.drawText(16, 26, hint)
        if self.start is not None:
            rect = QRect(self.start, self.end).normalized()
            painter.setPen(QPen(QColor("#44ccff"), 2))
            painter.drawRect(rect)
            if self.native_start is not None and self.native_cursor is not None:
                delta = self.native_cursor - self.native_start
                painter.drawText(rect.topLeft() + QPoint(0, -8),
                                 f"{abs(delta.x())} × {abs(delta.y())} 像素")
        if self.desktop is not None and self.cursor is not None and self.native_cursor is not None:
            self.paint_loupe(painter)

    def paint_loupe(self, painter):
        size = self.SAMPLE_SIZE * self.ZOOM
        offset = 24
        x, y = self.cursor.x() + offset, self.cursor.y() + offset
        screen = QApplication.screenAt(self.mapToGlobal(self.cursor))
        bounds = self.rect() if screen is None else QRect(
            self.mapFromGlobal(screen.geometry().topLeft()), screen.geometry().size())
        if x + size > bounds.right():
            x = self.cursor.x() - size - offset
        if y + size > bounds.bottom():
            y = self.cursor.y() - size - offset
        x = max(bounds.left(), x)
        y = max(bounds.top(), y)
        target = QRect(x, y, size, size)
        source = QRect(self.native_cursor - self.origin - QPoint(self.SAMPLE_SIZE // 2,
                                                                self.SAMPLE_SIZE // 2),
                       QSize(self.SAMPLE_SIZE, self.SAMPLE_SIZE))
        visible = source.intersected(self.desktop.rect())
        painter.fillRect(target, QColor("#202020"))
        if not visible.isEmpty():
            offset_in_sample = (visible.topLeft() - source.topLeft()) * self.ZOOM
            destination = QRect(target.topLeft() + offset_in_sample,
                                visible.size() * self.ZOOM)
            painter.drawImage(destination, self.desktop, visible)
        painter.setPen(QPen(QColor("#44ccff"), 2))
        painter.drawRect(target)
        center = target.center()
        painter.drawLine(center.x(), y, center.x(), center.y() - 4)
        painter.drawLine(center.x(), center.y() + 4, center.x(), target.bottom())
        painter.drawLine(x, center.y(), center.x() - 4, center.y())
        painter.drawLine(center.x() + 4, center.y(), target.right(), center.y())
