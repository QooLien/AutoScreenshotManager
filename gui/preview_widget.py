from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy, QPushButton
from PySide6.QtCore import QEvent, Qt, QUrl
from PySide6.QtGui import QPixmap, QDesktopServices

class PreviewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.path = None
        self.pixmap = QPixmap()
        layout = QVBoxLayout(self)
        self.info = QLabel("尚無截圖")
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.label.installEventFilter(self)
        button = QPushButton("開啟原始圖片")
        button.clicked.connect(self.open_image)
        layout.addWidget(self.info)
        layout.addWidget(self.label, 1)
        layout.addWidget(button)

    def show_image(self, path, timestamp):
        self.path = path
        self.pixmap = QPixmap(path)
        self.info.setText(f"{timestamp}\n{self.pixmap.width()} × {self.pixmap.height()}")
        self.render()

    def eventFilter(self, watched, event):
        if watched is self.label and event.type() == QEvent.Resize:
            self.render()
        return super().eventFilter(watched, event)

    def render(self):
        if not self.pixmap.isNull():
            self.label.setPixmap(self.pixmap.scaled(
                self.label.contentsRect().size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))

    def open_image(self):
        if self.path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.path))
