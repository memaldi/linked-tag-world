# coding=utf-8

"""
    Linked Tag Workld Server
    ------------------------

    A little LTW configuring server written in Flask.

    :copyright: (c) 2013 by Jon Lazaro.
"""

from ltwserver import app, celery
from flask import request, redirect, url_for, render_template
from ltwserver.forms import TermListForm, RDFDataForm, SparqlForm, ConfigHiddenForm, ConfigEditForm
from ltwserver.tasks import generate_config_file
from celery.result import AsyncResult

import json

@app.route("/")
def index():
    return redirect(url_for('configure'))

@app.route("/configure/")
def configure():
    return render_template('step0.html')

@app.route('/_get_task_status')
def get_task_status():
    task_id = request.args.get('task_id', None, type=str)
    if task_id:
        task = AsyncResult(app=celery, id=task_id)
        data = {'status': task.state, 'result': task.result}
    else:
        data = {'error': 'No task_id in the request'}

    return json.dumps(data)

@app.route("/configure/rdfsource/step1", methods=['GET', 'POST'])
def rdfsource():
    rdf_form = RDFDataForm(prefix='rdf')
    sparql_form = SparqlForm(prefix='sparql')
    
    if request.method == 'POST' and len(request.form.keys()) > 0:
        config_form = ConfigHiddenForm()

        if request.form.keys()[0].startswith('rdf-') and rdf_form.validate_on_submit():
            t = generate_config_file.delay(data_source='rdf', rdf_data=request.files[rdf_form.rdf_file.name].read(), rdf_format=rdf_form.format.data)
            return render_template('rdf_step1_a.html', data_source='rdf', task_id=t.task_id, form=config_form)

        elif request.form.keys()[0].startswith('sparql-') and sparql_form.validate_on_submit():
            t = generate_config_file.delay(data_source='sparql', sparql_url=sparql_form.url.data, sparql_graph=sparql_form.graph.data)
            return render_template('rdf_step1_a.html', data_source='sparql', task_id=t.task_id, form=config_form)
    
    return render_template('rdf_step1.html', rdf_form=rdf_form, sparql_form=sparql_form)

@app.route("/configure/rdfsource/step2", methods=['GET', 'POST'])
def rdfsource_step2():
    config_form = ConfigHiddenForm()

    if config_form.validate_on_submit():
        config_file = config_form.config_file.data

        config_edit_form = ConfigEditForm()

        return render_template('rdf_step2.html', config_file=config_file, form=config_edit_form)

@app.route("/configure/rdfsource/step3", methods=['GET', 'POST'])
def rdfsource_step3():
    config_form = ConfigEditForm()

    config_file = config_form.config_file.data

    if config_form.validate_on_submit():
        return render_template('rdf_step2.html', config_file=config_file, form=config_form)
    else:
        return render_template('rdf_step2.html', config_file=config_file, form=config_form)

@app.route("/configure/nonrdfsource/", methods=['GET', 'POST'])
def nonrdfsource():
    form = TermListForm()
    if form.validate_on_submit():
        app.logger.debug('LIST!')
    
    return render_template('nonrdf_step1.html', form=form)