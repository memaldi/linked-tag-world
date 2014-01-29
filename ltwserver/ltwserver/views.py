# coding=utf-8

'''
    Linked Tag World Server
    ------------------------

    A little LTW configuring server written in Flask.

    :copyright: (c) 2013 by Jon Lazaro.
'''

from ltwserver import app, celery, login_manager
from ltwserver.forms import TermListForm, RDFDataForm, SparqlForm, MyHiddenForm, ConfigEditForm, LoginForm, \
    RegisterForm, AppNameForm, ResourceEditForm, AndroidAppForm
from ltwserver.tasks import generate_new_android_app
from ltwserver.utils import get_resource_triples, get_next_resources, get_ltw_data_graph, get_ltw_config_graph, \
    search_dbpedia_trough_wikipedia, request_wants_rdf, call_to_generate_config_file, \
    call_to_get_all_data, get_data_paginators, get_literal_and_lang, get_dbpedia_resource_triples, \
    zip_dir, get_ltw_uri, SUPPORTED_RDF_HEADERS
from ltwserver.models import db, User, App, Endpoint
from ltwserver.tasks import generate_config_file, get_all_data

from flask.ext.login import login_user, logout_user, login_required, current_user
from flask import session, request, redirect, url_for, render_template, make_response, send_file, flash, Response, send_from_directory

from wtforms.fields import TextField
from celery.result import AsyncResult
from StringIO import StringIO

from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF

from subprocess import call

import urllib
import json
import uuid
import os
import qrcode
import zipfile
import shutil


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
                elif config_edit_form.download_next.data == 'android':
                    return redirect(url_for('generate_android_app',  app_id=session['app']))
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


@app.route('/ltwapp/<app_id>/data/edit/<path:url>', methods=['GET', 'POST'])
@login_required
def edit_resource(app_id, url):
    ltwapp = App.query.filter_by(id=app_id).first()
    graph_id = ltwapp.graph_id

    data_graph = get_ltw_data_graph(graph_id)
    config_graph = get_ltw_config_graph(graph_id)
    class_uri = list(data_graph.objects(URIRef(url), RDF.type))[0]

    res_data = get_resource_triples(data_graph, config_graph, str(class_uri), url)

    i = -1

    for i, triple in enumerate(sorted(res_data['triples'])):
        if isinstance(triple[1], Literal) and triple[1].language:
            default_txt = u'%s @ %s' % (unicode(triple[1]), triple[1].language)
        else:
            default_txt = triple[1]
        setattr(ResourceEditForm, 'field' + str(i), TextField(triple[2], default=default_txt, description=triple[0]))

    number_of_fields = i + 1 # +1 because i starts on 0
    form = ResourceEditForm()

    if form.validate_on_submit():
        for i, triple in enumerate(sorted(res_data['triples'])):
            data_graph.remove( (URIRef(url), triple[0], triple[1]) )

            field_data, lang = get_literal_and_lang(getattr(form, 'field' + str(i)).data)

            if field_data:
                data_graph.add( (URIRef(url), triple[0], Literal(field_data, lang=lang)) )

        if len(request.form.keys()) - 1 > number_of_fields: # -1 because CSRF token is included in form keys
            number_of_new_fields = (len(request.form.keys()) - 1 - number_of_fields) / 2
            for i in range(number_of_fields + 1, number_of_fields + 1 + number_of_new_fields):
                p = request.form['field%s_p' % str(i)]
                o = request.form['field%s_o' % str(i)]
                if p and o:
                    if o.startswith('http://'):
                        data_graph.add( (URIRef(url), URIRef(p), URIRef(o)) )
                    else:
                        o, lang = get_literal_and_lang(o)
                        data_graph.add( (URIRef(url), URIRef(p), Literal(o, lang=lang)) )

        return redirect(url_for('edit_resource', app_id=app_id, url=url))
    else:
        linked_resources = []
        resources = {}

        for link in res_data['linkable']:
            for o in data_graph.objects(URIRef(url), URIRef(link)):
                if str(o.encode('utf-8')) not in linked_resources:
                    linked_resources.append(str(o.encode('utf-8')))
                    lang = o.language if o.language else 'en'
                    if lang not in resources:
                        resources[lang] = []
                    for resource in search_dbpedia_trough_wikipedia(str(o.encode('utf-8')), lang):
                        resources[lang].append(resource)

        return render_template('edit_resource.html', data=res_data, app_id=app_id, url=url, resources=resources,
            form=form, number_of_fields=number_of_fields)


@app.route('/ltwapp/<app_id>/android', methods=['GET', 'POST'])
@login_required
def generate_android_app(app_id):
    ltwapp = App.query.filter_by(id=app_id).first()
    app_details_form = AndroidAppForm(prefix='details')
    app_path_form = MyHiddenForm(prefix='path')

    if request.method == 'POST' and len(request.form.keys()) > 0:
        if request.form.keys()[0].startswith('details-') and app_details_form.validate_on_submit():
            ltwapp.app_name = app_details_form.app_name.data
            ltwapp.app_package = app_details_form.package.data
            db.session.commit()

            t = generate_new_android_app.delay(app_details_form.app_name.data, app_details_form.package.data, ltwapp.config_file, ltwapp.graph_id)
            return render_template('app_generation_1.html', form=app_path_form, app_id=app_id, task_id=t.task_id)
        elif request.form.keys()[0].startswith('path-') and app_path_form.validate_on_submit():
            app_path = json.loads(get_task_status(task_id=app_path_form.hidden_field.data, return_result=True))['result']
            ltwapp.app_path = app_path
            db.session.commit()

            shutil.copyfile(app_path + 'bin/' + ltwapp.app_name + '-release.apk', app_path + '/' + ltwapp.app_name + '-release.apk')

            call(['ant', '-f', app_path + 'build.xml', 'clean'])

            zf = zipfile.ZipFile(app_path + 'androidapp-' + str(app_id) + '.zip', 'w')
            zip_dir(app_path, zf, ['ant.properties', 'local.properties', 'project.properties', 'androidapp-' + str(app_id) + '.zip'])
            zf.close()

            flash('There you have your Android app. In the root of the ZIP file there is an APK ready to use. Enjoy!', 'success')

            return send_from_directory(app_path, 'androidapp-' + str(app_id) + '.zip')
    else:
        app_details_form.app_name.data = ltwapp.name
        app_details_form.package.data = 'eu.deustotech.internet.ltw.%s' % ltwapp.name.replace(' ', '_').lower()

    return render_template('app_generation.html', form=app_details_form, app_id=app_id)


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


@app.route('/_get_uri_triples')
@login_required
def get_uri_triples():
    uri = request.args.get('uri', None, type=str)
    dbpedia_uri = request.args.get('dbpedia_uri', None, type=str)
    lang = request.args.get('lang', None, type=str)

    template = app.jinja_env.from_string('''
        {% import 'macros.html' as macros %}
        {{ macros.triples_table(uri, triples) }}
        ''')
    html = template.render(uri=urllib.unquote(uri), triples=get_dbpedia_resource_triples(urllib.unquote(dbpedia_uri), lang))

    return json.dumps({'html': html})


@app.route('/_add_external_triples')
@login_required
def add_external_triples():
    s = request.args.get('s', None, type=str)
    p = request.args.get('p', None, type=str)
    o = request.args.get('o', None, type=str)

    o, lang = get_literal_and_lang(urllib.unquote(o))

    ltwapp = App.query.filter_by(id=session['app']).first()
    data_graph = get_ltw_data_graph(ltwapp.graph_id)
    data_graph.add( (URIRef(urllib.unquote(s)), URIRef(urllib.unquote(p)), Literal(o, lang=lang)) )

    return json.dumps({})


@app.route('/res/<graph_id>/<path:url>')
def rdf_description_of_resource(graph_id, url):
    data_graph = get_ltw_data_graph(graph_id)
    requested_mimetype = request_wants_rdf()
    if requested_mimetype and data_graph != None:
        g = Graph()
        for p, o in data_graph.query('SELECT DISTINCT ?p ?o WHERE { <%s> ?p ?o }' % url):
            if isinstance(o, URIRef):
                g.add( (URIRef(url), p, URIRef(get_ltw_uri(str(o), graph_id))) )
            else:
                g.add( (URIRef(url), p, o) )

        return Response(response=g.serialize(format=SUPPORTED_RDF_HEADERS[requested_mimetype]), mimetype=requested_mimetype)
    return render_template('error/406_error.html'), 406


@app.route('/qr/<path:url>/<size>')
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
