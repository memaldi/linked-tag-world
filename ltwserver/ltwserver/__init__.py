# coding=utf-8

from flask import Flask
from celery import Celery

def make_celery(app):
    celery = Celery('hola', broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)

    TaskBase = celery.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery


app = Flask(__name__)
app.config.from_object('ltwserver.settings')
celery = make_celery(app)

import ltwserver.views