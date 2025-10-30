# project/celery.py
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

app = Celery("project")
# Use CELERY_ prefixed settings from Django settings
app.config_from_object("django.conf:settings", namespace="CELERY")
# Auto-discover tasks in installed apps (looks for tasks.py)
app.autodiscover_tasks()
