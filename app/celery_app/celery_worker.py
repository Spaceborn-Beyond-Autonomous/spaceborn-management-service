# app/celery_app/celery_worker.py
from celery import Celery

celery_app = Celery(
    "spaceborn",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1"
)

celery_app.conf.task_default_queue = "default"
celery_app.autodiscover_tasks(["app.celery_app"])
