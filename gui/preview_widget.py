from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QSlider, QPushButton
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QPixmap, QDesktopServices

class PreviewWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.info = QLabel("尚無截圖")
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        scroll = QScrollArea()
        scroll.setWidget(self.label)
        self.zoom = QSlider(Qt.Horizontal)
        self.zoom.setRange(10, 150)
        self.zoom.setValue(40)
        self.zoom.valueChanged.connect(self.render)
        button = QPushButton("開啟原始圖片")
        button.clicked.connect(self.open_image)
        for item in (self.info, scroll, self.zoom, button):
            layout.addWidget(item)
        self.path = None
        self.pixmap = QPixmap()

    def show_image(self, path, timestamp):
        self.path = path
        self.pixmap = QPixmap(path)
        self.info.setText(f"{timestamp}\n{self.pixmap.width()} × {self.pixmap.height()}")
        self.render()

    def render(self):
        if not self.pixmap.isNull():
            size = self.pixmap.size() * (self.zoom.value()/100)
            self.label.setPixmap(self.pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.label.resize(size)

    def open_image(self):
        if self.path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.path))
