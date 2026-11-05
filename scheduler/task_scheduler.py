from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

class TaskScheduler:
    def __init__(self, callback):
        self.callback = callback
        self.scheduler = BackgroundScheduler(job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 30})
        self.scheduler.start()

    def add(self, task_id, settings):
        schedule = settings["schedule"]
        if schedule["kind"] not in ("interval", "once"):
            raise ValueError("Unknown schedule kind")
        options = dict(id=task_id, replace_existing=True, args=[task_id])
        if schedule["kind"] == "interval":
            seconds = float(schedule["seconds"])
            if seconds < 1:
                raise ValueError("間隔至少為 1 秒")
            self.scheduler.add_job(self.callback, "interval", seconds=seconds, **options)
        else:
            when = datetime.fromisoformat(schedule["when"])
            if when.timestamp() <= datetime.now().timestamp():
                raise ValueError("單次排程時間必須在未來")
            self.scheduler.add_job(self.callback, "date", run_date=when, **options)

    def pause(self, task_id):
        self.scheduler.pause_job(task_id)

    def resume(self, task_id):
        self.scheduler.resume_job(task_id)

    def remove(self, task_id):
        if self.scheduler.get_job(task_id):
            self.scheduler.remove_job(task_id)

    def next_time(self, task_id):
        job = self.scheduler.get_job(task_id)
        return str(job.next_run_time) if job and job.next_run_time else "—"

    def close(self):
        self.scheduler.shutdown(wait=False)
