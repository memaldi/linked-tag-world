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
from ltwserver.utils import get_resource_triples, get_next_resources, get_ltw_data_graph, get_ltw_config_graph, \
    search_dbpedia_trough_wikipedia, request_wants_rdf, call_to_generate_config_file, \
    call_to_get_all_data, get_data_paginators, SUPPORTED_RDF_HEADERS
from ltwserver.models import db, User, App, Endpoint
from ltwserver.tasks import generate_config_file, get_all_data

from flask.ext.login import login_user, logout_user, login_required, current_user

from flask import session, request, redirect, url_for, render_template, make_response, send_file, flash, Response
from celery.result import AsyncResult
from StringIO import StringIO

from rdflib import Graph, URIRef
from rdflib.namespace import RDF

import json
import uuid
import os
import qrcode


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
    apps = []
    for ltwapp in current_user.apps:
        if ltwapp.rdf_file or ltwapp.endpoint:
            ltwapp_dict = {
                'name': ltwapp.name,
                'id': ltwapp.id,
            }
            ltwapp_dict['apk'] = '%s/bin/%s-release.apk' % (ltwapp.app_path, ltwapp.name) if ltwapp.app_path else ''
            apps.append(ltwapp_dict)

    return render_template('dashboard.html', apps=apps)


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

        config_form = MyHiddenForm(prefix='config')

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

        t = call_to_generate_config_file(ltwapp, generate_config_file)
        return render_template('rdf_steps/rdf_step1_a.html', data_source='rdf' if ltwapp.rdf_file else 'sparql', task_id=t.task_id, form=config_form)

    return render_template('rdf_steps/rdf_step1.html', rdf_form=rdf_form, sparql_form=sparql_form)


@app.route('/newapp/rdfsource/step2', methods=['GET', 'POST'])
@login_required
def rdfsource_step2():
    config_form = MyHiddenForm(prefix='config')
    config_edit_form = ConfigEditForm(prefix='editconfig')

    ltwapp = App.query.filter_by(id=session['app']).first()

    if request.method == 'POST' and len(request.form.keys()) > 0:
        if request.form.keys()[0].startswith('config-') and config_form.validate_on_submit():
            config_file = json.loads(get_task_status(task_id=config_form.hidden_field.data, return_result=True))['result']

            config_edit_form.config_file.data = config_file
            ltwapp.config_file = config_file
            db.session.commit()

            return render_template('rdf_steps/rdf_step2.html', form=config_edit_form, app_id=session['app'])

        elif request.form.keys()[0].startswith('editconfig-'):
            if config_edit_form.validate_on_submit():
                config_file = config_edit_form.config_file.data
                ltwapp.config_file = config_file
                db.session.commit()

                if config_edit_form.download_next.data == 'download':
                    return download_config_file(config_file=config_file)
                else:
                    return redirect(url_for('rdfsource_step3', app_id=session['app']))
    return render_template('rdf_steps/rdf_step2.html', form=config_edit_form, app_id=session['app'])


@app.route('/ltwapp/<app_id>/data', methods=['GET', 'POST'])
@login_required
def rdfsource_step3(app_id):
    data_form = MyHiddenForm()
    ltwapp = App.query.filter_by(id=app_id).first()

    if data_form.validate_on_submit():
        # Data fetching task completed
        graph_id = json.loads(get_task_status(task_id=data_form.hidden_field.data, return_result=True))['result']
        ltwapp.graph_id = graph_id
        db.session.commit()

        paginators = get_data_paginators(graph_id)
        return render_template('data_visualization.html', paginators=paginators, app_id=app_id)
    else:
        # Start data fetching task
        t = call_to_get_all_data(ltwapp, get_all_data)
        data_form = MyHiddenForm()
        return render_template('data_fetching.html', task_id=t.task_id, form=data_form, app_id=app_id)


@app.route('/ltwapp/<app_id>/data/edit/<path:url>', methods=['GET'])
@login_required
def edit_resource(app_id, url):
    ltwapp = App.query.filter_by(id=app_id).first()
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

    return render_template('non_rdf_steps/nonrdf_step1.html', form=form)


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
        {{ macros.data_tabs(data, class_id, app_id, pagination) }}
        ''')
    html = template.render(data=data, class_id=class_id, app_id=session['app'], pagination=True)

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
    return render_template('error/406_error.html'), 406


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


@app.route('/ltwapp/<app_id>/delete')
@login_required
def delete_ltw_app(app_id):
    ltwapp = App.query.filter_by(id=app_id).first()
    if ltwapp.user == current_user:
        db.session.delete(ltwapp)
        db.session.commit()
        return redirect(url_for('dashboard'))
    else:
        return render_template('401_error.html'), 401


@app.route('/ltwapp/<app_id>/config/download')
@login_required
def download_config_file(app_id=None, config_file=None):
    if not config_file:
        ltwapp = App.query.filter_by(id=app_id).first()
        if ltwapp.user == current_user:
            config_file = ltwapp.config_file
        else:
            return render_template('401_error.html'), 401

    response = make_response(config_file)
    response.headers['Content-Type'] = 'text/turtle'
    response.headers['Content-Disposition'] = 'attachment; filename=config.ttl'
    return response


@app.route('/ltwapp/<app_id>/data/edit')
@login_required
def edit_data(app_id):
    ltwapp = App.query.filter_by(id=app_id).first()
    if ltwapp.user != current_user:
        return render_template('401_error.html'), 401

    session['app'] = app_id

    print ltwapp
    print ltwapp.graph_id

    if ltwapp.graph_id:
        paginators = get_data_paginators(ltwapp.graph_id)
        return render_template('data_visualization.html', paginators=paginators, app_id=app_id)
    else:
        return redirect(url_for('rdfsource_step3', app_id=app_id))
        # t = call_to_get_all_data(ltwapp, get_all_data)
        # data_form = MyHiddenForm()
        # return render_template('rdf_steps/rdf_step3_a.html', task_id=t.task_id, form=data_form, app_id=app_id)


@app.route('/ltwapp/<app_id>/config/reload')
@login_required
def reload_config_file(app_id):
    ltwapp = App.query.filter_by(id=app_id).first()
    if ltwapp.user != current_user:
        return render_template('401_error.html'), 401

    session['app'] = app_id

    t = call_to_generate_config_file(ltwapp, generate_config_file)

    config_form = MyHiddenForm(prefix='config')
    return render_template('rdf_steps/rdf_step1_a.html', data_source='rdf' if ltwapp.rdf_file else 'sparql', task_id=t.task_id, form=config_form)
