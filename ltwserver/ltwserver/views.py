# coding=utf-8

"""
    Linked Tag World Server
    ------------------------

    A little LTW configuring server written in Flask.

    :copyright: (c) 2013 by Jon Lazaro.
"""

from ltwserver import app, celery
from ltwserver.forms import TermListForm, RDFDataForm, SparqlForm, MyHiddenForm, ConfigEditForm
from ltwserver.tasks import generate_config_file, get_all_data
from ltwserver.utils import *

from flask import request, redirect, url_for, render_template, make_response, send_file, Response
from celery.result import AsyncResult
from StringIO import StringIO

from rdflib import Graph, URIRef, Namespace
from rdflib.namespace import RDF

import json
import uuid
import os
import re
import qrcode

LTW = Namespace('http://helheim.deusto.es/ltw/0.1#')

@app.route('/res/<graph_id>/<path:url>')
def rdf_description_of_resource(graph_id, url):
    data_graph = get_ltw_data_graph(graph_id)
    requested_mimetype = request_wants_rdf()
    if requested_mimetype and data_graph != None:
        g = Graph()
        for p, o in data_graph.query('SELECT DISTINCT ?p ?o WHERE { <%s> ?p ?o }' % url):
            g.add( (URIRef(url), p, o) )

        return Response(response=g.serialize(format=SUPPORTED_RDF_HEADERS[requested_mimetype]), mimetype=requested_mimetype)
    return render_template('406_error.html'), 406


@app.route("/qr/<path:url>/<size>")
# Thanks to https://gist.github.com/plausibility/5787586
def qr_route(url, size=10):
    qr = qrcode.QRCode(
        box_size=size,
    )
    qr.add_data(url)
    qr.make()
    img = StringIO()
    qr_img = qr.make_image()
    qr_img.save(img)
    img.seek(0)
    return send_file(img, mimetype="image/png")


@app.route("/")
def index():
    return redirect(url_for('configure'))

@app.route("/configure/")
def configure():
    return render_template('step0.html')

@app.route('/_get_task_status')
def get_task_status(task_id=None, return_result=False):
    if not task_id:
        task_id = request.args.get('task_id', None, type=str)

    if task_id:
        task = AsyncResult(app=celery, id=task_id)
        if task.state == 'SUCCESS' and not return_result:
            data = {'status': task.state}
        else:
            res = task.result if task.state != 'FAILURE' else str(task.result)
            data = {'status': task.state, 'result': res}
    else:
        data = {'status': 'FAILURE', 'result': 'No task_id in the request'}

    return json.dumps(data)


@app.route('/_get_next_page')
def get_next_page():
    class_uri = request.args.get('class_uri', None, type=str)
    page = request.args.get('page', None, type=int)
    class_id = request.args.get('class_id', None, type=str)

    data = get_next_resources(page, class_uri)

    template = app.jinja_env.from_string('''
        {% import "macros.html" as macros %}
        {{ macros.data_tabs(data, class_id) }}
        ''')
    html = template.render(data=data, class_id=class_id)

    return json.dumps({'html': html})


@app.route("/configure/rdfsource/step1", methods=['GET', 'POST'])
def rdfsource():
    rdf_form = RDFDataForm(prefix='rdf')
    sparql_form = SparqlForm(prefix='sparql')

    if request.method == 'POST' and len(request.form.keys()) > 0:
        config_form = MyHiddenForm()

        if request.form.keys()[0].startswith('rdf-') and rdf_form.validate_on_submit():
            rdf_file = request.files[rdf_form.rdf_file.name]
            rdf_data = rdf_file.read()
            # Call Celery task
            t = generate_config_file.delay(data_source='rdf', rdf_data=rdf_data, rdf_format=rdf_form.format.data)

            # Save file in upload folder and some other variables as cookies
            file_path = os.path.join(os.path.abspath(app.config['UPLOAD_FOLDER']), str(uuid.uuid4()))

            f = open(file_path, 'w')
            f.write(rdf_data)
            f.close()

            resp = make_response(render_template('rdf_step1_a.html', data_source='rdf', task_id=t.task_id, form=config_form))
            resp.set_cookie('data_source', 'rdf')
            resp.set_cookie('file_path', file_path)
            resp.set_cookie('file_format', rdf_form.format.data)
            return resp

        elif request.form.keys()[0].startswith('sparql-') and sparql_form.validate_on_submit():
            # Call Celery task
            t = generate_config_file.delay(data_source='sparql', sparql_url=sparql_form.url.data, sparql_graph=sparql_form.graph.data)

            # Save some variables as cookies
            resp = make_response(render_template('rdf_step1_a.html', data_source='sparql', task_id=t.task_id, form=config_form))
            resp.set_cookie('data_source', 'sparql')
            resp.set_cookie('sparql_url', sparql_form.url.data)
            resp.set_cookie('sparql_graph', sparql_form.graph.data)
            return resp

    return render_template('rdf_step1.html', rdf_form=rdf_form, sparql_form=sparql_form)


@app.route("/configure/rdfsource/step2", methods=['GET', 'POST'])
def rdfsource_step2():
    config_form = MyHiddenForm()

    if config_form.validate_on_submit():
        config_file = json.loads(get_task_status(task_id=config_form.hidden_field.data, return_result=True))['result']

        config_edit_form = ConfigEditForm()
        config_edit_form.config_file.data = config_file

        return render_template('rdf_step2.html', form=config_edit_form)


@app.route("/configure/rdfsource/step3", methods=['GET', 'POST'])
def rdfsource_step3():
    config_form = ConfigEditForm()

    config_file = config_form.config_file.data

    if config_form.validate_on_submit():
        if config_form.download_next.data == 'download':
            response = make_response(config_file)
            response.headers['Content-Type'] = 'text/turtle'
            response.headers['Content-Disposition'] = 'attachment; filename=config.ttl'
            return response
        else:
            # Call Celery task
            rdf_data = None
            if request.cookies.get('data_source') == 'rdf':
                f = open(request.cookies.get('file_path'))
                rdf_data = f.read()

            t = get_all_data.delay(request.cookies.get('data_source'), config_file, rdf_data=rdf_data, rdf_format=request.cookies.get('file_format'),
                sparql_url=request.cookies.get('sparql_url'), sparql_graph=request.cookies.get('sparql_graph'))

            data_form = MyHiddenForm()
            return render_template('rdf_step3_a.html', task_id=t.task_id, form=data_form)
    elif not config_file:
        # Data fetching task completed
        data_form = MyHiddenForm()
        if data_form.validate_on_submit():
            graph_id = json.loads(get_task_status(task_id=data_form.hidden_field.data, return_result=True))['result']

            paginators = {}
            config_graph = get_ltw_config_graph(graph_id)
            for s, class_uri in config_graph.subject_objects(LTW.ontologyClass):
                try:
                    class_uri_id = list(config_graph.objects(URIRef(s), LTW.identifier))[0]
                except:
                    class_uri_id = re.split('/|#', class_uri)[-1]

                count_class = count_all_by_class(class_uri, graph_id)
                paginators[class_uri] = { 'id': class_uri_id, 'total': count_class, 'pages': ( count_class / PER_PAGE ) + 1, 'data': get_next_resources(1, class_uri, graph_id) }

            print graph_id

            resp = make_response(render_template('rdf_step3.html', paginators=paginators))
            resp.set_cookie('graph_id', graph_id)
            return resp

            # resp.set_cookie('data_source', '', expires=0)
            # resp.set_cookie('file_path', '', expires=0)
            # resp.set_cookie('file_format', '', expires=0)
            # resp.set_cookie('data_source', '', expires=0)
            # resp.set_cookie('sparql_url', '', expires=0)
            # resp.set_cookie('sparql_graph', '', expires=0)
    else:
        return render_template('rdf_step2.html', config_file=config_file, form=config_form)


@app.route("/configure/rdfsource/step3/edit/<path:url>", methods=['GET'])
def edit_resource(url):
    graph_id = request.cookies.get('graph_id')
    if graph_id:
        data_graph = get_ltw_data_graph(graph_id)
        config_graph = get_ltw_config_graph(graph_id)
        class_uri = list(data_graph.objects(URIRef(url), RDF.type))[0]

        res_data = get_resource_triples(data_graph, config_graph, str(class_uri), url)

        for link in res_data['linkable']:
            for o in data_graph.objects(URIRef(url), URIRef(link)):
                print search_dbpedia_trough_wikipedia(str(o.encode('utf-8')), 'eu')

        return render_template('edit_resource.html', data=res_data, url=url)


@app.route("/configure/nonrdfsource/", methods=['GET', 'POST'])
def nonrdfsource():
    form = TermListForm()
    if form.validate_on_submit():
        app.logger.debug('LIST!')

    return render_template('nonrdf_step1.html', form=form)
