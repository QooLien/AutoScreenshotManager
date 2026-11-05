import asyncio
import copy
import logging
import uuid
from datetime import datetime
from threading import Event
from concurrent.futures import ThreadPoolExecutor
from PySide6.QtCore import QObject, Signal, QTimer, Qt
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem, QPushButton, QLabel, QMessageBox, QFileDialog, QSplitter, QScrollArea)
from PySide6.QtGui import QImage
from capture.service import capture
from capture.web_capture import validate_web_url
from capture.web_picker import pick_web_element
from gui.capture_panel import CapturePanel
from gui.scheduler_panel import SchedulerPanel
from gui.preview_widget import PreviewWidget
from scheduler.task_scheduler import TaskScheduler
from utils.file_manager import save_image, append_history
from utils.config_manager import save_config, load_config
from utils.logger import setup_logging

MODE_LABELS = {
    "Full Screen": "全螢幕擷取",
    "Selected Region": "指定區域",
    "Window Capture": "指定視窗",
    "Application Capture": "指定應用程式",
    "Web Chart": "網頁圖表",
}
STATUS_LABELS = {
    "Ready": "就緒", "Scheduled": "已排程", "Running": "擷取中",
    "Stopped": "已停止", "Paused": "已暫停", "Complete": "已完成", "Error": "失敗",
}


class Signals(QObject):
    request = Signal(str)
    complete = Signal(str, str, str, str)
    preview_ready = Signal(object, object, str)
    web_pick_ready = Signal(str, object, str)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        setup_logging()
        self.setWindowTitle("Auto Screenshot Manager — Phase 1")
        self.resize(1500,850)
        self.tasks = {}
        self.busy = set()
        self.closing = False
        self.preview_pending = False
        self.web_pick_cancel = None
        self.web_picker_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="web-picker")
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="capture")
        self.signals = Signals()
        self.signals.request.connect(self.enqueue)
        self.signals.complete.connect(self.completed)
        self.signals.preview_ready.connect(self.window_preview_ready)
        self.signals.web_pick_ready.connect(self.web_picker_ready)
        self.scheduler = TaskScheduler(self.signals.request.emit)
        widget = QWidget()
        self.setCentralWidget(widget)
        layout = QVBoxLayout(widget)
        splitter = QSplitter()
        self.modes = QListWidget()
        for mode, label in MODE_LABELS.items():
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, mode)
            self.modes.addItem(item)
        self.modes.setCurrentRow(0)
        splitter.addWidget(self.modes)
        center = QWidget()
        center_layout = QVBoxLayout(center)
        self.capture_panel = CapturePanel()
        self.capture_panel.preview_requested.connect(self.request_window_preview)
        self.capture_panel.web_pick.clicked.connect(self.toggle_web_picker)
        self.capture_panel.set_mode(self.modes.currentItem().data(Qt.UserRole))
        self.modes.currentItemChanged.connect(
            lambda current, previous: self.capture_panel.set_mode(current.data(Qt.UserRole))
        )
        self.schedule_panel = SchedulerPanel()
        center_layout.addWidget(self.capture_panel)
        center_layout.addWidget(self.schedule_panel)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(center)
        splitter.addWidget(scroll)
        self.preview = PreviewWidget()
        splitter.addWidget(self.preview)
        splitter.setSizes([170,760,570])
        layout.addWidget(splitter, 3)
        self.task_list = QListWidget()
        layout.addWidget(self.task_list,1)
        controls = QHBoxLayout()
        for label, callback in [("立即截圖",self.capture_now),("啟動排程",self.start_schedule),("暫停",lambda:self.control("pause")),("繼續",lambda:self.control("resume")),("停止",lambda:self.control("stop")),("儲存設定檔",self.save_profile),("載入設定檔",self.load_profile)]:
            button = QPushButton(label)
            button.clicked.connect(callback)
            controls.addWidget(button)
        layout.addLayout(controls)
        self.status = QLabel("就緒。編輯設定只影響新任務；每次啟動排程都會建立獨立任務。")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_tasks)
        self.timer.start(1000)

    def toggle_web_picker(self):
        if self.closing:
            return
        if self.web_pick_cancel is not None:
            self.web_pick_cancel.set()
            self.capture_panel.web_pick.setEnabled(False)
            return
        url = self.capture_panel.web_url.text().strip()
        try:
            validate_web_url(url)
        except ValueError as exc:
            QMessageBox.warning(self, "請檢查網址", str(exc))
            return
        self.web_pick_cancel = Event()
        self.capture_panel.web_pick.setText("取消網頁元素選取")
        self.status.setText("在 Edge 視窗內將滑鼠移到圖表，再點一下。關閉 Edge 可取消。")
        self.web_picker_pool.submit(self.run_web_picker, url, self.web_pick_cancel)

    def run_web_picker(self, url, cancelled):
        selector = None
        error = ""
        try:
            selector = asyncio.run(pick_web_element(url, cancelled))
        except Exception as exc:
            if not cancelled.is_set():
                logging.exception("Web element picker failed")
                error = str(exc)
        self.signals.web_pick_ready.emit(url, selector if not cancelled.is_set() else None, error)

    def web_picker_ready(self, url, selector, error):
        cancelled = self.web_pick_cancel.is_set()
        self.web_pick_cancel = None
        self.capture_panel.web_pick.setText("在網頁上點選元素")
        self.capture_panel.web_pick.setEnabled(True)
        if self.closing:
            if not self.busy and not self.preview_pending:
                self.close()
            return
        if cancelled:
            self.status.setText("已取消選取")
        elif error:
            self.status.setText(error)
            QMessageBox.warning(self, "無法選取網頁元素", error)
        elif selector and url == self.capture_panel.web_url.text().strip():
            self.capture_panel.web_selector.setText(selector)
            self.status.setText("已填入 CSS 選擇器。可先按「立即截圖」確認範圍。")
        else:
            self.status.setText("已取消選取或網址已變更")

    def request_window_preview(self, target):
        if self.closing or self.preview_pending:
            return
        self.preview_pending = True
        self.capture_panel.pick.setEnabled(False)
        self.status.setText("正在取得目標視窗的背景預覽…")
        self.pool.submit(self.capture_window_preview, target)

    def capture_window_preview(self, target):
        image = None
        error = ""
        try:
            frame = capture(dict(mode="Window Capture", window=target, fallback=False))
            image = QImage(frame.tobytes(), frame.width, frame.height, frame.width * 3,
                           QImage.Format_RGB888).copy()
        except Exception as exc:
            logging.exception("Window preview failed")
            error = str(exc)
        self.signals.preview_ready.emit(image, (target["hwnd"], target["pid"]), error)

    def window_preview_ready(self, image, key, error):
        self.preview_pending = False
        self.capture_panel.pick.setEnabled(True)
        if self.closing:
            if not self.busy and self.web_pick_cancel is None:
                self.close()
            return
        self.status.setText(error or "背景預覽已就緒")
        if error:
            QMessageBox.warning(self, "無法取得背景預覽", error)
        else:
            self.capture_panel.apply_window_preview(image, key)

    def settings(self):
        settings = self.capture_panel.settings(self.modes.currentItem().data(Qt.UserRole))
        settings["schedule"] = self.schedule_panel.settings()
        return settings

    def report(self, exc):
        logging.exception("Operation failed")
        self.status.setText(str(exc))
        QMessageBox.warning(self,"操作失敗",str(exc))

    def new_task(self, settings):
        task_id = uuid.uuid4().hex
        self.tasks[task_id] = dict(settings=copy.deepcopy(settings), status="Ready", count=0, last="—", error="")
        return task_id

    def capture_now(self):
        try:
            self.enqueue(self.new_task(self.settings()))
        except Exception as exc:
            self.report(exc)

    def start_schedule(self):
        task_id = None
        try:
            task_id = self.new_task(self.settings())
            self.scheduler.add(task_id,self.tasks[task_id]["settings"])
            self.tasks[task_id]["status"] = "Scheduled"
            self.update_tasks()
        except Exception as exc:
            if task_id:
                self.tasks.pop(task_id,None)
            self.report(exc)

    def enqueue(self, task_id):
        if self.closing or task_id not in self.tasks or self.tasks[task_id]["status"] in ("Stopped","Paused"):
            return
        if task_id in self.busy:
            logging.warning("Skipped overlapping capture %s",task_id)
            return
        self.busy.add(task_id)
        settings = copy.deepcopy(self.tasks[task_id]["settings"])
        self.tasks[task_id]["status"] = "Running"
        self.pool.submit(self.work,task_id,settings)

    def work(self, task_id, settings):
        path = error = ""
        timestamp = datetime.now().astimezone().isoformat(timespec="milliseconds")
        try:
            path = save_image(capture(settings),settings)
        except Exception as exc:
            error = str(exc)
            logging.exception("Capture failed: %s", task_id)
        try:
            append_history(dict(time=timestamp, task=settings["name"],mode=settings["mode"],path=path,result="error" if error else "success",error=error))
        except Exception as exc:
            logging.exception("History write failed")
            error = (error + "; " if error else "") + f"歷史紀錄寫入失敗：{exc}"
        self.signals.complete.emit(task_id,path,error,timestamp)

    def completed(self, task_id, path, error, timestamp):
        self.busy.discard(task_id)
        task = self.tasks[task_id]
        task["error"] = error
        if path:
            task["count"] += 1
            task["last"] = timestamp
            self.preview.show_image(path,timestamp)
        if task["status"] not in ("Stopped","Paused"):
            task["status"] = "Error" if error else ("Scheduled" if self.scheduler.scheduler.get_job(task_id) else "Complete")
        self.status.setText(error or f"已儲存：{path}")
        self.update_tasks()
        if self.closing and not self.busy and not self.preview_pending and self.web_pick_cancel is None:
            self.close()

    def selected_id(self):
        from PySide6.QtCore import Qt
        item = self.task_list.currentItem()
        if not item:
            raise ValueError("請先選取任務")
        return item.data(Qt.UserRole)

    def control(self, action):
        try:
            task_id = self.selected_id()
            task = self.tasks[task_id]
            if action == "stop":
                self.scheduler.remove(task_id)
                task["status"] = "Stopped"
            elif action == "pause":
                self.scheduler.pause(task_id)
                task["status"] = "Paused"
            else:
                self.scheduler.resume(task_id)
                task["status"] = "Scheduled"
            self.status.setText("控制已套用；已開始的截圖會完成，後續排程依新狀態執行。")
            self.update_tasks()
        except Exception as exc:
            self.report(exc)

    def update_tasks(self):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QListWidgetItem
        selected = self.task_list.currentItem()
        selected_id = selected.data(Qt.UserRole) if selected else None
        self.task_list.clear()
        for task_id, task in self.tasks.items():
            item = QListWidgetItem(f"{task['settings']['name']} | {MODE_LABELS[task['settings']['mode']]} | {STATUS_LABELS[task['status']]} | 張數 {task['count']} | 上次 {task['last']} | 下次 {self.scheduler.next_time(task_id)} | {task['error']}")
            item.setData(Qt.UserRole,task_id)
            self.task_list.addItem(item)
            if task_id == selected_id:
                self.task_list.setCurrentItem(item)

    def save_profile(self):
        try:
            settings = self.settings()
            path,_ = QFileDialog.getSaveFileName(self,"儲存設定檔","profile.json","JSON (*.json)")
            if path:
                save_config(path,dict(version=1,settings=settings))
        except Exception as exc:
            self.report(exc)

    def load_profile(self):
        try:
            path,_ = QFileDialog.getOpenFileName(self,"載入設定檔","","JSON (*.json)")
            if path:
                data = load_config(path)
                if data.get("version") != 1:
                    raise ValueError("不支援的設定檔版本")
                settings = data["settings"]
                matches = self.modes.findItems(MODE_LABELS.get(settings["mode"], ""), Qt.MatchExactly)
                if not matches:
                    raise ValueError("不支援的截圖模式")
                self.capture_panel.restore(settings)
                self.schedule_panel.restore(settings["schedule"])
                self.modes.setCurrentItem(matches[0])
        except Exception as exc:
            self.report(exc)

    def closeEvent(self,event):
        if not self.closing:
            self.closing = True
            self.scheduler.close()
            if self.web_pick_cancel is not None:
                self.web_pick_cancel.set()
            self.web_picker_pool.shutdown(wait=False)
            self.pool.shutdown(wait=False,cancel_futures=False)
        if self.busy or self.preview_pending or self.web_pick_cancel is not None:
            event.ignore()
            self.status.setText("等待已排入的截圖完成後關閉…")
        else:
            event.accept()
