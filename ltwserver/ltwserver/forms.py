from flask_wtf import Form
from wtforms.fields.html5 import URLField
from wtforms.fields import TextAreaField, TextField, SelectField
from wtforms.validators import DataRequired, url
from flask_wtf.file import FileField

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

class RDFDataForm(Form):
    rdf_file = FileField('RDF file', validators=[DataRequired()])
    format = SelectField(u'Format', choices=[ (key, value) for key, value in SUPPORTED_RDF_SYNTAXES.items() ])

class SparqlForm(Form):
    url = URLField('URL', validators=[url(), DataRequired()])
    graph = TextField('Graph')

class TermListForm(Form):
	term_list = TextAreaField('Terms', validators=[DataRequired()])