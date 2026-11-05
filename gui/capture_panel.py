from dataclasses import asdict
from itertools import groupby
import logging
from PySide6.QtCore import QPoint, QTimer, Qt, Signal
from PySide6.QtGui import QImage
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QFormLayout, QComboBox, QLineEdit, QSpinBox, QCheckBox, QPushButton, QFileDialog, QGridLayout, QLabel, QMessageBox)
from capture.screen_capture import capture_rect, monitors
from utils.window_manager import list_windows
from gui.region_capture import RegionOverlay
from gui.window_region import WindowRegionDialog

WINDOW_MODES = ("Window Capture", "Application Capture")


class CapturePanel(QWidget):
    preview_requested = Signal(dict)

    def __init__(self):
        super().__init__()
        layout = QFormLayout(self)
        self.name = QLineEdit("Capture")
        self.monitor = QComboBox()
        self.monitor.setMinimumContentsLength(25)
        self.monitor.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        for index, m in enumerate(monitors()):
            self.monitor.addItem(f"{index}: {'全部顯示器' if index == 0 else '顯示器'} {m}", index)
        self.resolution = QComboBox()
        self.resolution.addItem("原始尺寸", None)
        for width, height in [(1280, 720), (1366, 768), (1600, 900), (1920, 1080),
                              (1920, 1200), (2560, 1440), (3440, 1440), (3840, 2160)]:
            self.resolution.addItem(f"{width} × {height}", [width, height])
        self.resolution.setCurrentIndex(self.resolution.findData([1920, 1080]))
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
            field.setPrefix({"left": "左：", "top": "上：", "width": "寬：", "height": "高："}[key])
            self.region[key] = field
            row.addWidget(field, index // 2, index % 2)
        self.mode = "Full Screen"
        self.window_region = None
        self.region_target = None
        self.pick = QPushButton("拖曳選取區域（Esc 取消）")
        self.pick.clicked.connect(self.select_region)
        self.crop_label = QLabel()
        self.clear_crop = QPushButton("清除視窗選區")
        self.clear_crop.clicked.connect(self.clear_window_region)
        self.windows.currentIndexChanged.connect(self.update_crop_label)
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
        for label, widget in [("任務名稱", self.name),("顯示器",self.monitor),("全螢幕輸出解析度",self.resolution),("目標視窗",self.windows),("",refresh),("標題關鍵字",self.keyword),("",self.fallback)]:
            layout.addRow(label,widget)
        layout.addRow("實體像素座標",row)
        layout.addRow(self.pick)
        layout.addRow(self.crop_label)
        layout.addRow(self.clear_crop)
        for label, widget in [("儲存位置",self.folder),("",browse),("格式",self.format),("JPG 品質",self.quality),("",self.date)]:
            layout.addRow(label,widget)
        self.refresh()
        self.set_mode(self.mode)

    def refresh(self):
        selected = self.windows.currentData()
        windows = sorted(list_windows(), key=lambda w: (w.process.casefold(), w.title.casefold()))
        self.windows.clear()
        first = selected_index = -1
        for process, group in groupby(windows, key=lambda w: w.process.casefold()):
            self.windows.addItem(process.upper())
            header = self.windows.model().item(self.windows.count() - 1)
            header.setFlags(Qt.NoItemFlags)
            for w in group:
                left, top, right, bottom = w.rect
                state = "最小化" if w.minimized else ("最大化" if w.maximized else "一般")
                index = self.windows.count()
                self.windows.addItem(
                    f"    {w.title} | {right-left}×{bottom-top} | {state} | PID {w.pid}",
                    asdict(w),
                )
                if first == -1:
                    first = index
                if selected and (w.hwnd, w.pid) == (selected["hwnd"], selected["pid"]):
                    selected_index = index
        self.windows.setCurrentIndex(selected_index if selected_index != -1 else first)

    def set_mode(self, mode):
        self.mode = mode
        self.pick.setText("在視窗預覽上拖曳選區" if mode in WINDOW_MODES else "拖曳選取區域（Esc 取消）")
        self.update_crop_label()

    def window_key(self):
        target = self.windows.currentData()
        return (target["hwnd"], target["pid"]) if target else None

    def active_window_region(self):
        if self.mode in WINDOW_MODES and self.region_target == self.window_key():
            return self.window_region
        return None

    def update_crop_label(self):
        region = self.active_window_region()
        self.crop_label.setVisible(self.mode in WINDOW_MODES)
        self.clear_crop.setVisible(region is not None)
        if region:
            self.crop_label.setText(
                f"視窗內選區：左 {region['left']}，上 {region['top']}，"
                f"{region['width']} × {region['height']} 像素"
            )
        else:
            self.crop_label.setText("目前擷取整個目標視窗")

    def clear_window_region(self):
        self.window_region = None
        self.region_target = None
        self.update_crop_label()

    def apply_window_preview(self, image, key):
        if self.mode not in WINDOW_MODES or key != self.window_key():
            return
        dialog = WindowRegionDialog(image, self)
        if dialog.exec():
            self.window_region = dialog.region
            self.region_target = key
            self.update_crop_label()
        dialog.deleteLater()

    def select_region(self):
        if self.mode in WINDOW_MODES:
            target = self.windows.currentData()
            if not target:
                QMessageBox.warning(self, "請選取目標", "請先從清單選擇要截圖的視窗。")
                return
            target = dict(target)
            target["keyword"] = self.keyword.text() or target["title"]
            self.preview_requested.emit(target)
            return
        main_window = self.window()
        main_window.hide()
        # Let Windows remove the main window from the desktop before sampling.
        QTimer.singleShot(150, self, self.show_region_overlay)

    def show_region_overlay(self):
        main_window = self.window()
        desktop = origin = None
        try:
            bounds = monitors()[0]
            image = capture_rect(bounds)
            desktop = QImage(image.tobytes(), image.width, image.height,
                             image.width * 3, QImage.Format_RGB888).copy()
            origin = QPoint(bounds["left"], bounds["top"])
        except Exception:
            logging.exception("Unable to capture the desktop for the region magnifier")

        def restore_window():
            self.overlay = None
            main_window.show()
            main_window.raise_()
            main_window.activateWindow()

        try:
            self.overlay = RegionOverlay(desktop, origin)
            self.overlay.selected.connect(self.set_region)
            self.overlay.closed.connect(restore_window)
            self.overlay.show()
            self.overlay.raise_()
            self.overlay.activateWindow()
            self.overlay.setFocus()
        except Exception:
            restore_window()
            raise

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
        return dict(name=self.name.text() or "Capture", mode=mode, monitor=self.monitor.currentData(), resolution=self.resolution.currentData(), window=window, window_region=self.active_window_region(), region={k:v.value() for k,v in self.region.items()}, fallback=self.fallback.isChecked(), folder=self.folder.text(), format=self.format.currentText(), quality=self.quality.value(), date_folder=self.date.isChecked())

    def restore(self, data):
        self.clear_window_region()
        self.name.setText(data["name"])
        self.folder.setText(data["folder"])
        self.format.setCurrentText(data["format"])
        self.quality.setValue(data.get("quality",90))
        self.date.setChecked(data.get("date_folder",True))
        self.fallback.setChecked(data.get("fallback",False))
        self.set_region(data["region"])
        self.monitor.setCurrentIndex(max(0,self.monitor.findData(data["monitor"])))
        self.resolution.setCurrentIndex(max(0, self.resolution.findData(data.get("resolution"))))
        target = data.get("window")
        if target:
            self.windows.addItem(f"已儲存目標：{target['process']} | {target['title']}",target)
            self.windows.setCurrentIndex(self.windows.count()-1)
            self.keyword.setText(target.get("keyword",""))
            self.window_region = data.get("window_region")
            self.region_target = self.window_key()
            self.update_crop_label()
