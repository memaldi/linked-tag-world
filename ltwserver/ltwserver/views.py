# coding=utf-8

"""
    Linked Tag Workld Server
    ------------------------

    A little LTW configuring server written in Flask.

    :copyright: (c) 2013 by Jon Lazaro.
"""

from ltwserver import app
from flask import request, redirect, url_for, render_template
from ltwserver.forms import TermListForm, RDFDataForm, SparqlForm

@app.route("/")
def index():
    return redirect(url_for('configure'))

@app.route("/configure/")
def configure():
    return render_template('step0.html')

@app.route("/configure/rdfsource/", methods=['GET', 'POST'])
def rdfsource():
    rdf_form = RDFDataForm(prefix='rdf')
    sparql_form = SparqlForm(prefix='sparql')
    
    if request.method == 'POST' and len(request.form.keys()) > 0:
        if request.form.keys()[0].startswith('rdf-') and rdf_form.validate_on_submit():
            app.logger.debug('RDF!')
        elif request.form.keys()[0].startswith('sparql-') and sparql_form.validate_on_submit():
            app.logger.debug('SPARQL!')
    
    return render_template('rdf_step1.html', rdf_form=rdf_form, sparql_form=sparql_form)

@app.route("/configure/nonrdfsource/", methods=['GET', 'POST'])
def nonrdfsource():
    form = TermListForm()
    if form.validate_on_submit():
        app.logger.debug('LIST!')
    
    return render_template('nonrdf_step1.html', form=form)