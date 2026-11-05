import copy
import logging
import uuid
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from PySide6.QtCore import QObject, Signal, QTimer, Qt
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QPushButton, QLabel, QMessageBox, QFileDialog, QSplitter, QScrollArea)
from capture.service import capture
from gui.capture_panel import CapturePanel
from gui.scheduler_panel import SchedulerPanel
from gui.preview_widget import PreviewWidget
from scheduler.task_scheduler import TaskScheduler
from utils.file_manager import save_image, append_history
from utils.config_manager import save_config, load_config
from utils.logger import setup_logging

class Signals(QObject):
    request = Signal(str)
    complete = Signal(str, str, str, str)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        setup_logging()
        self.setWindowTitle("Auto Screenshot Manager — Phase 1")
        self.resize(1500,850)
        self.tasks = {}
        self.busy = set()
        self.closing = False
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="capture")
        self.signals = Signals()
        self.signals.request.connect(self.enqueue)
        self.signals.complete.connect(self.completed)
        self.scheduler = TaskScheduler(self.signals.request.emit)
        widget = QWidget()
        self.setCentralWidget(widget)
        layout = QVBoxLayout(widget)
        splitter = QSplitter()
        self.modes = QListWidget()
        self.modes.addItems(["Full Screen","Selected Region","Window Capture","Application Capture"])
        self.modes.setCurrentRow(0)
        splitter.addWidget(self.modes)
        center = QWidget()
        center_layout = QVBoxLayout(center)
        self.capture_panel = CapturePanel()
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
        for label, callback in [("Capture Now",self.capture_now),("Start Schedule",self.start_schedule),("Pause",lambda:self.control("pause")),("Resume",lambda:self.control("resume")),("Stop",lambda:self.control("stop")),("Save Profile",self.save_profile),("Load Profile",self.load_profile)]:
            button = QPushButton(label)
            button.clicked.connect(callback)
            controls.addWidget(button)
        layout.addLayout(controls)
        self.status = QLabel("就緒。編輯設定只影響新任務；每次 Start Schedule 建立獨立任務。")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_tasks)
        self.timer.start(1000)

    def settings(self):
        settings = self.capture_panel.settings(self.modes.currentItem().text())
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
        if self.closing and not self.busy:
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
            item = QListWidgetItem(f"{task['settings']['name']} | {task['settings']['mode']} | {task['status']} | Total {task['count']} | Last {task['last']} | Next {self.scheduler.next_time(task_id)} | {task['error']}")
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
                matches = self.modes.findItems(settings["mode"],Qt.MatchExactly)
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
            self.pool.shutdown(wait=False,cancel_futures=False)
        if self.busy:
            event.ignore()
            self.status.setText("等待已排入的截圖完成後關閉…")
        else:
            event.accept()
