from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import UserMixin
from ltwserver import app

db = SQLAlchemy(app)

class BaseModel():
    """
    An abstract base class model that provides self-updating
    'created' and 'modified'
    """
    log_created = db.Column(db.DateTime, default=db.func.now())
    log_modified = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

    class Meta:
        abstract = True


class User(db.Model, BaseModel, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000))
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(120))

    def __init__(self, name, email, password):
        self.name = name
        self.email = email
        self.password = password

    def get_id(self):
        return unicode(self.email)

    def __repr__(self):
        return '<User %r>' % self.name


class App(db.Model, BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000))
    graph_id = db.Column(db.String(1000))
    rdf_file = db.Column(db.String(1000))
    rdf_file_format = db.Column(db.String(100))
    config_file = db.Column(db.String(1000))
    app_path = db.Column(db.String(1000))
    app_name = db.Column(db.String(1000))
    app_package = db.Column(db.String(1000))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('apps', lazy='dynamic'))

    endpoint_id = db.Column(db.Integer, db.ForeignKey('endpoint.id'))
    endpoint = db.relationship('Endpoint', backref=db.backref('apps', lazy='dynamic'))

    def __init__(self, name, user, rdf_file=None, endpoint=None, config_file=None, graph_id=None, app_path=None, app_name=None, app_package=None):
        self.name = name
        self.graph_id = graph_id
        self.rdf_file = rdf_file
        self.config_file = config_file
        self.app_path = app_path
        self.user = user
        self.endpoint = endpoint
        self.app_name = app_name
        self.app_package = app_package

    def __repr__(self):
        return '<App %r>' % self.name


class Endpoint(db.Model, BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(1000))
    graph = db.Column(db.String(1000))

    def __init__(self, url, graph=None):
        self.url = url
        self.graph = graph

    def __repr__(self):
        return '<User %r>' % self.username
