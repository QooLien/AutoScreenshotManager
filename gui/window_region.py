from math import ceil, floor

from PySide6.QtCore import QEvent, QRect, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QRubberBand, QVBoxLayout


class WindowRegionDialog(QDialog):
    def __init__(self, image, parent):
        super().__init__(parent)
        self.setWindowTitle("選取視窗內的截圖範圍")
        self.region = None
        self.start = None
        self.image_size = image.size()
        bounds = self.screen().availableGeometry().size() * 0.8
        pixmap = QPixmap.fromImage(image)
        if pixmap.width() > bounds.width() or pixmap.height() > bounds.height():
            pixmap = pixmap.scaled(bounds, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("在預覽上拖曳選取範圍。放開滑鼠套用，按 Esc 取消。"))
        self.preview = QLabel()
        self.preview.setPixmap(pixmap)
        self.preview.setFixedSize(pixmap.size())
        self.preview.setCursor(Qt.CrossCursor)
        self.preview.installEventFilter(self)
        layout.addWidget(self.preview, alignment=Qt.AlignHCenter)
        self.band = QRubberBand(QRubberBand.Rectangle, self.preview)

    def eventFilter(self, watched, event):
        if watched is self.preview:
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self.start = event.position().toPoint()
                self.band.setGeometry(QRect(self.start, self.start))
                self.band.show()
                return True
            if self.start is not None and event.type() == QEvent.MouseMove:
                self.band.setGeometry(QRect(self.start, event.position().toPoint()).normalized()
                                      .intersected(self.preview.rect()))
                return True
            if self.start is not None and event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                rect = QRect(self.start, event.position().toPoint()).normalized().intersected(self.preview.rect())
                self.start = None
                self.band.hide()
                if rect.width() > 1 and rect.height() > 1:
                    scale_x = self.image_size.width() / self.preview.width()
                    scale_y = self.image_size.height() / self.preview.height()
                    left, top = floor(rect.left() * scale_x), floor(rect.top() * scale_y)
                    right = min(self.image_size.width(), ceil((rect.right() + 1) * scale_x))
                    bottom = min(self.image_size.height(), ceil((rect.bottom() + 1) * scale_y))
                    self.region = dict(left=left, top=top, width=right-left, height=bottom-top)
                    self.accept()
                return True
        return super().eventFilter(watched, event)
