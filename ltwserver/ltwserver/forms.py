from flask_wtf import Form
from wtforms.fields.html5 import URLField
from wtforms.fields import TextAreaField, TextField, SelectField, HiddenField, PasswordField, BooleanField
from wtforms.validators import DataRequired, url, ValidationError
from flask_wtf.file import FileField
from rdflib import ConjunctiveGraph, Graph

import re

SUPPORTED_RDF_SYNTAXES = {
    'xml': 'RDF/XML',
    'turtle': 'Turtle',
    'n3': 'Notation3 (N3)',
    'nt': 'N-Triple',
    'nquads': 'N-Quads',
    'microdata': 'Microdata',
    'rdfa': 'RDFa',
    'rdfa1.0': 'RDFa 1.0',
    'rdfa1.1': 'RDFa 1.1',
    'trix': 'TriX',
}


def validate_sparql_endpoint(form, field):
    try:
        g = ConjunctiveGraph('SPARQLStore')
        g.open(field.data)
        g.query('SELECT * WHERE { ?s ?p ?o } LIMIT 1')
    except:
        raise ValidationError('This is not a valid SPARQL endpoint.')

def validate_rdf_data(form, field):
    try:
        g = Graph()
        g.parse(data=field.data, format='turtle')
    except:
        raise ValidationError('Not well-formed RDF file.')

def validate_java_package(form, field):
    # Find non-alphanumeric and non-point characters in field
    pattern = re.compile(r'[^\w\.]')
    invalid_chars = list(set(pattern.findall(field.data)))
    if invalid_chars:
        raise ValidationError('Invalid characters for a Java package: %s' % ', '.join(invalid_chars))


class RDFDataForm(Form):
    rdf_file = FileField('RDF file', validators=[DataRequired()])
    format = SelectField(u'Format', choices=[ (key, value) for key, value in SUPPORTED_RDF_SYNTAXES.items() ])

class SparqlForm(Form):
    url = URLField('URL', validators=[url(), DataRequired(), validate_sparql_endpoint])
    graph = TextField('Graph')

class TermListForm(Form):
    term_list = TextAreaField('Terms', validators=[DataRequired()])

class MyHiddenForm(Form):
    hidden_field = HiddenField(validators=[DataRequired()]);

class ConfigEditForm(Form):
    config_file = TextAreaField(validators=[DataRequired(), validate_rdf_data]);
    download_next = HiddenField();

class LoginForm(Form):
    email = TextField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember me')

class RegisterForm(Form):
    name = TextField('Full name', validators=[DataRequired()])
    email = TextField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

class AppNameForm(Form):
    name = TextField('App name', validators=[DataRequired()])
    data_source = HiddenField(validators=[DataRequired()])

class ResourceEditForm(Form):
    pass

class AndroidAppForm(Form):
    app_name = TextField('App name', validators=[DataRequired()])
    package = TextField('Java package', validators=[DataRequired(), validate_java_package])
    launcher_icon = FileField('Launcher icon')
    app_logo = FileField('Application logo')
