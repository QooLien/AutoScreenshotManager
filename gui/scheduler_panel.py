from PySide6.QtWidgets import QWidget, QFormLayout, QComboBox, QDoubleSpinBox, QDateTimeEdit
from PySide6.QtCore import QDateTime

class SchedulerPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QFormLayout(self)
        self.kind = QComboBox()
        self.kind.addItems(["interval","once"])
        self.seconds = QDoubleSpinBox()
        self.seconds.setRange(1,86400*365)
        self.seconds.setValue(10)
        self.when = QDateTimeEdit(QDateTime.currentDateTime().addSecs(60))
        self.when.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.when.setCalendarPopup(True)
        layout.addRow("排程類型",self.kind)
        layout.addRow("間隔（秒）",self.seconds)
        layout.addRow("單次時間（系統本地時區）",self.when)

    def settings(self):
        return dict(kind=self.kind.currentText(),seconds=self.seconds.value(),when=self.when.dateTime().toPython().astimezone().isoformat())

    def restore(self, data):
        self.kind.setCurrentText(data["kind"])
        self.seconds.setValue(data["seconds"])
        from datetime import datetime
        self.when.setDateTime(QDateTime(datetime.fromisoformat(data["when"]).astimezone()))
