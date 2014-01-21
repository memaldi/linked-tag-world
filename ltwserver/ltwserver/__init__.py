# coding=utf-8

from flask import Flask
from celery import Celery
from flask.ext.login import LoginManager
from simplekv.memory import DictStore
from flaskext.kvsession import KVSessionExtension

def make_celery(app):
    celery = Celery(app.import_name, backend=app.config['CELERY_RESULT_BACKEND'], broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)

    TaskBase = celery.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery

# Load Flask settings
app = Flask(__name__)
app.config.from_object('ltwserver.settings')

# Celery configuration
celery = make_celery(app)

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index'
login_manager.login_message_category = 'info'

# Replace the app's session handling with Flask-KVSession
store = DictStore()
KVSessionExtension(store, app)

# Load models and views
import ltwserver.models
import ltwserver.views
