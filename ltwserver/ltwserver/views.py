# coding=utf-8

"""
    Linked Tag Workld Server
    ------------------------

    A little LTW configuring server written in Flask.

    :copyright: (c) 2013 by Jon Lazaro.
"""

from ltwserver import app, celery
from flask import request, redirect, url_for, render_template, make_response
from ltwserver.forms import TermListForm, RDFDataForm, SparqlForm, MyHiddenForm, ConfigEditForm
from ltwserver.tasks import generate_config_file, get_all_data
from celery.result import AsyncResult

from rdflib import ConjunctiveGraph, URIRef, Namespace
from rdflib.store import Store
from rdflib.plugin import get as plugin
from rdflib.namespace import RDF

import json
import uuid
import os
import re

LTW = Namespace('http://helheim.deusto.es/ltw/0.1#')
PER_PAGE = app.config['PAGINATION_PER_PAGE']

def count_all_by_class(class_uri, graph_id=None):
    g = get_ltw_data_graph(graph_id)
    return len(list(g.subjects(RDF.type, URIRef(class_uri))))


def get_linkable_props_by_class_ont(class_ont, config_graph):
    linkable_props = config_graph.query(
    '''
        SELECT DISTINCT ?prop_ont where {
            ?s <http://helheim.deusto.es/ltw/0.1#ontologyClass> <%s> ;
                <http://helheim.deusto.es/ltw/0.1#hasPropertyItem> ?prop .
            ?prop <http://helheim.deusto.es/ltw/0.1#ontologyProperty> ?prop_ont ;
                <http://helheim.deusto.es/ltw/0.1#isLinkable> ?linkable .
            FILTER (?linkable)
        }
    ''' % class_ont
    )
    ret_list = []
    for prop in linkable_props:
        ret_list.append(str(prop[0]))
    return ret_list


def get_main_props_by_class_ont(class_ont, config_graph):
    main_props = config_graph.query(
    '''
        SELECT DISTINCT ?prop_ont where {
            ?s <http://helheim.deusto.es/ltw/0.1#ontologyClass> <%s> ;
                <http://helheim.deusto.es/ltw/0.1#hasPropertyItem> ?prop .
            ?prop <http://helheim.deusto.es/ltw/0.1#ontologyProperty> ?prop_ont ;
                <http://helheim.deusto.es/ltw/0.1#isMain> ?main .
            FILTER (?main)
        }
    ''' % class_ont
    )
    ret_list = []
    for prop in main_props:
        ret_list.append(str(prop[0]))
    return ret_list


def get_next_resources(page, class_uri, graph_id=None):
    g = get_ltw_data_graph(graph_id)

    offset = (page - 1) * PER_PAGE
    q_res = g.query(
    '''
        SELECT DISTINCT ?s where {
            ?s a <%s> .
        }
        ORDER BY ?s
        LIMIT %s
        OFFSET %s
    ''' % (class_uri, PER_PAGE, offset)
    )

    config_graph = get_ltw_config_graph(graph_id)
    main_props = get_main_props_by_class_ont(class_uri, config_graph)
    linkable_props = get_linkable_props_by_class_ont(class_uri, config_graph)

    res_dict = {}
    for s in q_res:
        main = None
        data_list = []
        for p, o in g.predicate_objects(s[0]):
            if p in main_props:
                main = o
            link = p in linkable_props

            data_list.append((p, o, link))

        res_dict[s[0]] = {'triples': data_list, 'main': main }

    return res_dict


def get_ltw_data_graph(graph_id=None):
    if not graph_id:
        graph_id = request.cookies.get('graph_id')
    if graph_id:
        Virtuoso = plugin("Virtuoso", Store)
        store = Virtuoso(app.config['VIRTUOSO_ODBC'])
        ltw_data_graph = ConjunctiveGraph(store=store)
        g = ltw_data_graph.get_context(graph_id)

        # Initialization step needed to make Virtuoso library work
        g.add((URIRef('initializationstuff'), URIRef('initializationstuff'), URIRef('initializationstuff')))
        g.remove((URIRef('initializationstuff'), URIRef('initializationstuff'), URIRef('initializationstuff')))

        return g
    else:
        return None

def get_ltw_config_graph(graph_id=None):
    if not graph_id:
        graph_id = request.cookies.get('graph_id')
    if graph_id:
        Virtuoso = plugin("Virtuoso", Store)
        store = Virtuoso(app.config['VIRTUOSO_ODBC'])
        ltw_data_graph = ConjunctiveGraph(store=store)
        g = ltw_data_graph.get_context(graph_id + '_config')

        # Initialization step needed to make Virtuoso library work
        g.add((URIRef('initializationstuff'), URIRef('initializationstuff'), URIRef('initializationstuff')))
        g.remove((URIRef('initializationstuff'), URIRef('initializationstuff'), URIRef('initializationstuff')))

        return g
    else:
        return None


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

    data = get_next_resources(page, class_uri)

    return json.dumps(data)

@app.route("/configure/rdfsource/step1", methods=['GET', 'POST'])
def rdfsource():
    rdf_form = RDFDataForm(prefix='rdf')
    sparql_form = SparqlForm(prefix='sparql')

    if request.method == 'POST' and len(request.form.keys()) > 0:
        config_form = MyHiddenForm()

        if request.form.keys()[0].startswith('rdf-') and rdf_form.validate_on_submit():
            rdf_file = request.files[rdf_form.rdf_file.name]
            # Call Celery task
            t = generate_config_file.delay(data_source='rdf', rdf_data=rdf_file.read(), rdf_format=rdf_form.format.data)

            # Save file in upload folder and some other variables as cookies
            file_path = os.path.join(os.path.abspath(app.config['UPLOAD_FOLDER']), str(uuid.uuid4()))
            rdf_file.save(file_path)

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
        # Call Celery task
        rdf_data = None
        if request.cookies.get('data_source') == 'rdf':
            f = open(request.cookies.get('file_path'), 'r')
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

                paginators[class_uri] = { 'id': class_uri_id, 'total': ( count_all_by_class(class_uri, graph_id) / PER_PAGE ) + 1, 'data': get_next_resources(1, class_uri, graph_id) }

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

@app.route("/configure/nonrdfsource/", methods=['GET', 'POST'])
def nonrdfsource():
    form = TermListForm()
    if form.validate_on_submit():
        app.logger.debug('LIST!')

    return render_template('nonrdf_step1.html', form=form)
