from dataclasses import asdict
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QFormLayout, QComboBox, QLineEdit, QSpinBox, QCheckBox, QPushButton, QFileDialog, QGridLayout)
from capture.screen_capture import monitors
from utils.window_manager import list_windows
from gui.region_capture import RegionOverlay

class CapturePanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QFormLayout(self)
        self.name = QLineEdit("Capture")
        self.monitor = QComboBox()
        self.monitor.setMinimumContentsLength(25)
        self.monitor.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        for index, m in enumerate(monitors()):
            self.monitor.addItem(f"{index}: {'全部顯示器' if index == 0 else '顯示器'} {m}", index)
        self.windows = QComboBox()
        self.windows.setMinimumContentsLength(35)
        self.windows.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        refresh = QPushButton("重新整理視窗清單")
        refresh.clicked.connect(self.refresh)
        self.keyword = QLineEdit()
        self.keyword.setPlaceholderText("重新辨識時使用；留空使用完整原標題")
        self.fallback = QCheckBox("允許螢幕備援（可能包含遮擋物）")
        self.region = {}
        row = QGridLayout()
        for index, (key, value) in enumerate((("left",0),("top",0),("width",640),("height",480))):
            field = QSpinBox()
            field.setRange(-100000 if key in ("left","top") else 1,100000)
            field.setValue(value)
            field.setPrefix(key + ": ")
            self.region[key] = field
            row.addWidget(field, index // 2, index % 2)
        pick = QPushButton("拖曳選取區域（Esc 取消）")
        pick.clicked.connect(self.select_region)
        self.folder = QLineEdit(str(Path.home()/"Pictures"/"AutoScreenshotManager"))
        browse = QPushButton("選擇儲存資料夾")
        browse.clicked.connect(self.browse)
        self.format = QComboBox()
        self.format.addItems(["PNG","JPG"])
        self.quality = QSpinBox()
        self.quality.setRange(1,100)
        self.quality.setValue(90)
        self.date = QCheckBox("自動建立日期資料夾")
        self.date.setChecked(True)
        for label, widget in [("任務名稱", self.name),("顯示器",self.monitor),("目標視窗",self.windows),("",refresh),("標題關鍵字",self.keyword),("",self.fallback)]:
            layout.addRow(label,widget)
        layout.addRow("實體像素座標",row)
        layout.addRow(pick)
        for label, widget in [("儲存位置",self.folder),("",browse),("格式",self.format),("JPG Quality",self.quality),("",self.date)]:
            layout.addRow(label,widget)
        self.refresh()

    def refresh(self):
        self.windows.clear()
        for w in list_windows():
            l,t,r,b = w.rect
            self.windows.addItem(f"{w.process} | {w.title} | {w.pid} | {w.hwnd} | {r-l}×{b-t} | {'Minimized' if w.minimized else ('Maximized' if w.maximized else 'Normal')}", asdict(w))

    def select_region(self):
        self.overlay = RegionOverlay()
        self.overlay.selected.connect(self.set_region)
        self.overlay.show()
        self.overlay.activateWindow()

    def set_region(self, values):
        for key,value in values.items():
            self.region[key].setValue(value)

    def browse(self):
        folder = QFileDialog.getExistingDirectory(self,"儲存位置",self.folder.text())
        if folder:
            self.folder.setText(folder)

    def settings(self, mode):
        window = self.windows.currentData()
        if mode in ("Window Capture","Application Capture") and not window:
            raise ValueError("請選取目標視窗")
        if window:
            window = dict(window)
            window["keyword"] = self.keyword.text() or window["title"]
        if not self.folder.text().strip():
            raise ValueError("請選擇儲存位置")
        return dict(name=self.name.text() or "Capture", mode=mode, monitor=self.monitor.currentData(), window=window, region={k:v.value() for k,v in self.region.items()}, fallback=self.fallback.isChecked(), folder=self.folder.text(), format=self.format.currentText(), quality=self.quality.value(), date_folder=self.date.isChecked())

    def restore(self, data):
        self.name.setText(data["name"])
        self.folder.setText(data["folder"])
        self.format.setCurrentText(data["format"])
        self.quality.setValue(data.get("quality",90))
        self.date.setChecked(data.get("date_folder",True))
        self.fallback.setChecked(data.get("fallback",False))
        self.set_region(data["region"])
        self.monitor.setCurrentIndex(max(0,self.monitor.findData(data["monitor"])))
        target = data.get("window")
        if target:
            self.windows.addItem(f"已儲存目標：{target['process']} | {target['title']}",target)
            self.windows.setCurrentIndex(self.windows.count()-1)
            self.keyword.setText(target.get("keyword",""))
