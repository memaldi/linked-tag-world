from flask_wtf import Form
from wtforms.fields.html5 import URLField
from wtforms.fields import TextAreaField
from wtforms.validators import DataRequired, url
from flask_wtf.file import FileField


class RDFDataForm(Form):
    rdf_file = FileField('RDF file')

class SparqlForm(Form):
    url = URLField('Endpoint', validators=[url()])

class TermListForm(Form):
	term_list = TextAreaField('Terms', validators=[DataRequired()])