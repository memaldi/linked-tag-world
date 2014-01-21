# coding=utf-8

'''
    Linked Tag World Server
    ------------------------

    A little LTW configuring server written in Flask.

    :copyright: (c) 2013 by Jon Lazaro.
'''

from ltwserver import app, celery, login_manager
from ltwserver.forms import TermListForm, RDFDataForm, SparqlForm, MyHiddenForm, ConfigEditForm, LoginForm, \
    RegisterForm, AppNameForm
from ltwserver.tasks import generate_config_file, get_all_data
from ltwserver.utils import count_all_by_class, get_resource_triples, get_next_resources, get_ltw_data_graph, \
    get_ltw_config_graph, search_dbpedia_trough_wikipedia, request_wants_rdf, PER_PAGE, SUPPORTED_RDF_HEADERS
from ltwserver.models import db, User, App, Endpoint
from flask.ext.login import login_user, logout_user, login_required, current_user

from flask import session, request, redirect, url_for, render_template, make_response, send_file, flash, Response
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


@login_manager.user_loader
def load_user(userid):
    return User.query.filter_by(email=userid).first()


@app.route('/login', methods=['POST'])
def login():
    if not current_user.is_anonymous():
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.password == form.password.data:
            login_user(user, remember=form.remember_me)
            flash('Successfully logged in.', 'success')
        else:
            flash('Incorrect user or password.', 'danger')
        return redirect(request.args.get('next') or url_for('index'))

    return redirect(url_for('index', login_form=form))


@app.route('/register', methods=['POST'])
def register():
    if not current_user.is_anonymous():
        return redirect(url_for('index'))

    form = RegisterForm()
    if form.validate_on_submit():
        if not User.query.filter_by(email=form.email.data).first():
            user = User(name=form.name.data, email=form.email.data, password=form.password.data)
            db.session.add(user)
            db.session.commit()
            login_user(user, remember=True)
            flash('Successfully registered. Welcome to LTW!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Already registered email.', 'danger')

    return redirect(url_for('index', register_form=form))


@login_manager.unauthorized_handler
def unauthorized():
    flash('Unauthorized. Please login or register.', 'warning')
    return redirect(url_for('index'))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/')
def index(login_form=None, register_form=None):
    if current_user.is_anonymous():
        login_form = LoginForm() if not login_form else login_form
        register_form = RegisterForm() if not register_form else register_form
        return render_template('index.html', login_form=login_form, register_form=register_form)
    else:
         return redirect(url_for('dashboard'))


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


@app.route('/newapp', methods=['GET', 'POST'])
@login_required
def configure():
    form = AppNameForm()
    if form.validate_on_submit():
        ltwapp = App(name=form.name.data, user=current_user)
        db.session.add(ltwapp)
        db.session.commit()

        session['app'] = ltwapp.id

        if form.data_source.data == 'rdfsource':
            return redirect(url_for('rdfsource'))
        elif form.data_source.data == 'nonrdfsource':
            return redirect(url_for('nonrdfsource'))

    return render_template('step0.html', form=form)


@app.route('/newapp/rdfsource/step1', methods=['GET', 'POST'])
@login_required
def rdfsource():
    rdf_form = RDFDataForm(prefix='rdf')
    sparql_form = SparqlForm(prefix='sparql')

    if request.method == 'POST' and len(request.form.keys()) > 0:
        ltwapp = App.query.filter_by(id=session['app']).first()

        config_form = MyHiddenForm()

        if request.form.keys()[0].startswith('rdf-') and rdf_form.validate_on_submit():
            rdf_file = request.files[rdf_form.rdf_file.name]
            rdf_data = rdf_file.read()

            # Save file in upload folder
            file_path = os.path.join(os.path.abspath(app.config['UPLOAD_FOLDER']), str(uuid.uuid4()))
            f = open(file_path, 'w')
            f.write(rdf_data)
            f.close()

            ltwapp.rdf_file = file_path
            ltwapp.rdf_file_format = rdf_form.format.data
            ltwapp.endpoint = None
            db.session.commit()

        elif request.form.keys()[0].startswith('sparql-') and sparql_form.validate_on_submit():
            ltwapp.rdf_file = None
            ltwapp.rdf_file_format = None
            endpoint = Endpoint(sparql_form.url.data, sparql_form.graph.data)
            db.session.add(endpoint)
            ltwapp.endpoint = endpoint
            db.session.commit()

        rdf_data = None
        if ltwapp.rdf_file:
            with open(ltwapp.rdf_file) as f:
                rdf_data = f.read()

        # Call Celery task
        t = generate_config_file.delay(
            data_source='rdf' if rdf_data else 'sparql',
            rdf_data=rdf_data,
            rdf_format=ltwapp.rdf_file_format,
            sparql_url=ltwapp.endpoint.url,
            sparql_graph=ltwapp.endpoint.graph
        )
        return render_template('rdf_step1_a.html', data_source='rdf' if ltwapp.rdf_file else 'sparql', task_id=t.task_id, form=config_form)

    return render_template('rdf_step1.html', rdf_form=rdf_form, sparql_form=sparql_form)


@app.route('/newapp/rdfsource/step2', methods=['GET', 'POST'])
@login_required
def rdfsource_step2():
    config_form = MyHiddenForm()

    if config_form.validate_on_submit():
        config_file = json.loads(get_task_status(task_id=config_form.hidden_field.data, return_result=True))['result']

        config_edit_form = ConfigEditForm()
        config_edit_form.config_file.data = config_file

        ltwapp = App.query.filter_by(id=session['app']).first()
        ltwapp.config_file = config_file
        db.session.commit()

        return render_template('rdf_step2.html', form=config_edit_form)


@app.route('/newapp/rdfsource/step3', methods=['GET', 'POST'])
@login_required
def rdfsource_step3():
    config_form = ConfigEditForm()
    config_file = config_form.config_file.data

    ltwapp = App.query.filter_by(id=session['app']).first()

    if config_form.validate_on_submit():
        ltwapp.config_file = config_file
        db.session.commit()

        if config_form.download_next.data == 'download':
            response = make_response(config_file)
            response.headers['Content-Type'] = 'text/turtle'
            response.headers['Content-Disposition'] = 'attachment; filename=config.ttl'
            return response
        else:
            # Call Celery task
            rdf_data = None
            if ltwapp.rdf_file:
                with open(ltwapp.rdf_file) as f:
                    rdf_data = f.read()

            t = get_all_data.delay(
                data_source='rdf' if rdf_data else 'sparql',
                config_file=ltwapp.config_file,
                rdf_data=rdf_data,
                rdf_format=ltwapp.rdf_file_format,
                sparql_url=ltwapp.endpoint.url,
                sparql_graph=ltwapp.endpoint.graph
            )

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

            ltwapp.graph_id = graph_id
            db.session.commit()
            return render_template('rdf_step3.html', paginators=paginators)
    else:
        return render_template('rdf_step2.html', config_file=config_file, form=config_form)


@app.route('/newapp/rdfsource/step3/edit/<path:url>', methods=['GET'])
@login_required
def edit_resource(url):
    ltwapp = App.query.filter_by(id=session['app']).first()
    graph_id = ltwapp.graph_id

    if graph_id:
        data_graph = get_ltw_data_graph(graph_id)
        config_graph = get_ltw_config_graph(graph_id)
        class_uri = list(data_graph.objects(URIRef(url), RDF.type))[0]

        res_data = get_resource_triples(data_graph, config_graph, str(class_uri), url)

        for link in res_data['linkable']:
            for o in data_graph.objects(URIRef(url), URIRef(link)):
                print search_dbpedia_trough_wikipedia(str(o.encode('utf-8')), 'eu')

        return render_template('edit_resource.html', data=res_data, url=url)


@app.route('/newapp/nonrdfsource/', methods=['GET', 'POST'])
@login_required
def nonrdfsource():
    form = TermListForm()
    if form.validate_on_submit():
        app.logger.debug('LIST!')

    return render_template('nonrdf_step1.html', form=form)


@app.route('/_get_task_status')
@login_required
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
@login_required
def get_next_page():
    class_uri = request.args.get('class_uri', None, type=str)
    page = request.args.get('page', None, type=int)
    class_id = request.args.get('class_id', None, type=str)

    data = get_next_resources(page, class_uri)

    template = app.jinja_env.from_string('''
        {% import 'macros.html' as macros %}
        {{ macros.data_tabs(data, class_id) }}
        ''')
    html = template.render(data=data, class_id=class_id)

    return json.dumps({'html': html})


@app.route('/res/<graph_id>/<path:url>')
@login_required
def rdf_description_of_resource(graph_id, url):
    data_graph = get_ltw_data_graph(graph_id)
    requested_mimetype = request_wants_rdf()
    if requested_mimetype and data_graph != None:
        g = Graph()
        for p, o in data_graph.query('SELECT DISTINCT ?p ?o WHERE { <%s> ?p ?o }' % url):
            g.add( (URIRef(url), p, o) )

        return Response(response=g.serialize(format=SUPPORTED_RDF_HEADERS[requested_mimetype]), mimetype=requested_mimetype)
    return render_template('406_error.html'), 406


@app.route('/qr/<path:url>/<size>')
@login_required
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
    return send_file(img, mimetype='image/png')
