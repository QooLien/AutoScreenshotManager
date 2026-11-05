from datetime import datetime, timedelta
from threading import Event
from pathlib import Path
from unittest.mock import patch
import pytest
from PIL import Image
from utils.file_manager import save_image
from utils.config_manager import save_config, load_config
from scheduler.task_scheduler import TaskScheduler
from capture.service import capture


def test_unique_files_and_jpeg(tmp_path):
    settings = dict(folder=str(tmp_path), name='a:b/c', format='JPG', date_folder=True, quality=85)
    image = Image.new('RGBA',(32,24),'red')
    paths = [save_image(image,settings) for _ in range(4)]
    assert len(set(paths)) == 4
    for path in paths:
        with Image.open(path) as saved:
            assert saved.size == (32,24)
            assert saved.format == 'JPEG'
        assert Path(path).parent != tmp_path


def test_no_overwrite_on_name_collision(tmp_path):
    settings = dict(folder=str(tmp_path), name='capture', format='PNG', date_folder=False)
    with patch('utils.file_manager.uuid.uuid4') as unique, patch('utils.file_manager.datetime') as clock:
        unique.return_value.hex = 'a'*32
        clock.now.return_value = datetime(2026,11,5,12,0).astimezone()
        path = save_image(Image.new('RGB',(4,4),'red'),settings)
        before = Path(path).read_bytes()
        with pytest.raises(FileExistsError):
            save_image(Image.new('RGB',(4,4),'blue'),settings)
        assert Path(path).read_bytes() == before


def test_failed_save_removes_partial_file(tmp_path):
    with patch.object(Image.Image,'save',side_effect=OSError('disk full')):
        with pytest.raises(OSError):
            save_image(Image.new('RGB',(4,4)),dict(folder=str(tmp_path),format='PNG',date_folder=False))
    assert not list(tmp_path.iterdir())


def test_config_round_trip(tmp_path):
    path = tmp_path/'nested'/'profile.json'
    settings = dict(name='測試',region=dict(left=-100,top=0,width=100,height=100))
    save_config(path,settings)
    assert load_config(path) == settings


def test_invalid_mode():
    with pytest.raises(ValueError):
        capture(dict(mode='unknown'))


def test_scheduler_once_integration():
    fired = Event()
    scheduler = TaskScheduler(lambda task_id: fired.set())
    try:
        scheduler.add('test',dict(schedule=dict(kind='once',when=(datetime.now().astimezone()+timedelta(seconds=0.3)).isoformat())))
        assert fired.wait(4)
        assert scheduler.next_time('test') == '—'
    finally:
        scheduler.close()


def test_scheduler_pause_resume_stop():
    scheduler = TaskScheduler(lambda task_id: None)
    try:
        scheduler.add('test',dict(schedule=dict(kind='interval',seconds=60)))
        assert scheduler.next_time('test') != '—'
        scheduler.pause('test')
        assert scheduler.next_time('test') == '—'
        scheduler.resume('test')
        assert scheduler.next_time('test') != '—'
        scheduler.remove('test')
        assert scheduler.next_time('test') == '—'
        with pytest.raises(ValueError):
            scheduler.add('bad',dict(schedule=dict(kind='interval',seconds=0)))
        with pytest.raises(ValueError):
            scheduler.add('past',dict(schedule=dict(kind='once',when=(datetime.now().astimezone()-timedelta(seconds=60)).isoformat())))
    finally:
        scheduler.close()


def test_window_reacquire_and_ambiguity():
    from utils.window_manager import Window, resolve_window
    target = dict(hwnd=1,pid=2,process='EXCEL.EXE',title='Original',keyword='Report')
    replacement = Window(3,'Report - Excel','EXCEL.EXE',4,(0,0,100,100),False)
    with patch('utils.window_manager.list_windows',return_value=[replacement]):
        assert resolve_window(target).hwnd == 3
    with patch('utils.window_manager.list_windows',return_value=[replacement,replacement]):
        with pytest.raises(RuntimeError):
            resolve_window(target)
    with patch('utils.window_manager.list_windows',return_value=[]):
        with pytest.raises(RuntimeError):
            resolve_window(target)
