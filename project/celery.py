import os
from celery import Celery

# set default Django settings module for 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

celery_app = Celery('project')

# read config from Django settings, using CELERY_ prefix if desired.
celery_app.config_from_object('django.conf:settings', namespace='CELERY')

# automatically discover tasks in installed apps (looks for tasks.py)
celery_app.autodiscover_tasks()

# periodic task schedule (Celery Beat)
celery_app.conf.beat_schedule = {
    'run-sample-task-every-10-seconds': {
        'task': 'app.tasks.sample_task',  # path to the task
        'schedule': 10.0,                 # run every 10 seconds
    },
}

celery_app.conf.timezone = 'Asia/Kolkata'
