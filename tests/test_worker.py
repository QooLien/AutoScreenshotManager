import time
from threading import Event
from PIL import Image
from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow


def test_worker_deduplicates_and_preserves_stop(monkeypatch, tmp_path, qt_app):
    # This test does not capture the desktop or write production logs/history.
    monkeypatch.setattr('gui.main_window.setup_logging',lambda: None)
    monkeypatch.setattr('gui.capture_panel.monitors',lambda: [dict(left=0,top=0,width=800,height=600)])
    monkeypatch.setattr('gui.capture_panel.list_windows',lambda: [])
    records = []
    monkeypatch.setattr('gui.main_window.append_history',records.append)
    entered, release = Event(), Event()
    calls = []
    def fake_capture(settings):
        calls.append(settings['name'])
        entered.set()
        assert release.wait(3)
        return Image.new('RGB',(24,24),'red')
    monkeypatch.setattr('gui.main_window.capture',fake_capture)
    app = qt_app
    window = MainWindow()
    try:
        settings = window.settings()
        settings['folder'] = str(tmp_path)
        task_id = window.new_task(settings)
        window.enqueue(task_id)
        assert entered.wait(2)
        window.enqueue(task_id)
        window.update_tasks()
        window.task_list.setCurrentRow(0)
        window.control('stop')
        assert window.tasks[task_id]['status'] == 'Stopped'
        release.set()
        deadline = time.monotonic()+4
        while window.busy and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        assert not window.busy
        assert calls == ['Capture']
        assert window.tasks[task_id]['status'] == 'Stopped'
        assert window.tasks[task_id]['count'] == 1
        assert records[0]['result'] == 'success'
    finally:
        release.set()
        window.pool.shutdown(wait=True)
        app.processEvents()
        window.close()
        window.deleteLater()
        from PySide6.QtCore import QCoreApplication, QEvent
        QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)


def test_capture_failure_is_recorded_and_worker_recovers(monkeypatch, tmp_path, qt_app):
    monkeypatch.setattr('gui.main_window.setup_logging',lambda: None)
    monkeypatch.setattr('gui.capture_panel.monitors',lambda: [dict(left=0,top=0,width=800,height=600)])
    monkeypatch.setattr('gui.capture_panel.list_windows',lambda: [])
    records = []
    monkeypatch.setattr('gui.main_window.append_history',records.append)
    def fake_capture(settings):
        if settings['name'] == 'Closed target':
            raise RuntimeError('Target application closed')
        return Image.new('RGB',(24,24),'red')
    monkeypatch.setattr('gui.main_window.capture',fake_capture)
    window = MainWindow()
    try:
        for name in ('Closed target','Healthy target'):
            settings = window.settings()
            settings.update(name=name,folder=str(tmp_path))
            task_id = window.new_task(settings)
            window.enqueue(task_id)
            deadline = time.monotonic()+4
            while window.busy and time.monotonic() < deadline:
                qt_app.processEvents()
                time.sleep(0.01)
            assert not window.busy
            task = window.tasks[task_id]
            if name == 'Closed target':
                assert task['status'] == 'Error'
                assert task['count'] == 0
                assert 'closed' in task['error']
            else:
                assert task['status'] == 'Complete'
                assert task['count'] == 1
        assert [record['result'] for record in records] == ['error','success']
    finally:
        window.pool.shutdown(wait=True)
        qt_app.processEvents()
        window.close()
        window.deleteLater()
        from PySide6.QtCore import QCoreApplication, QEvent
        QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
