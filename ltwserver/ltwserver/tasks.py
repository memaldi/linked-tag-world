# coding=utf-8

from ltwserver import app, celery
from ltwserver.utils import get_props_by_class_ont, IMG_PROPS

from celery import current_task
from jinja2 import Environment, PackageLoader

from rdflib import Graph, ConjunctiveGraph, Namespace, BNode, URIRef, Literal
from rdflib.namespace import RDF
from rdflib.store import Store
from rdflib.plugin import get as plugin

from multiprocessing import Pool, Value
from itertools import repeat
from time import sleep
import subprocess

import re
import uuid
import shutil
import os
import sys


# Define RDFlib namespaces
LTW = Namespace('http://helheim.deusto.es/ltw/0.1#')
DC = Namespace('http://purl.org/dc/elements/1.1/')

# Properties that are used usually as labels in RDF data
COMMON_LABEL_PROPS = [URIRef(label) for label in app.config['COMMON_LABEL_PROPS']]

ANDROID_BIN = app.config['ANDROID_BIN']
LTW_ANDROID_LIB_PATH = app.config['LTW_ANDROID_LIB_PATH']
BASE_APP_PATH = app.config['BASE_APP_PATH']
NEW_APPS_PATH = app.config['NEW_APPS_PATH']
NUM_OF_PROCESS_MSGS = 262


@celery.task()
def make_omelette(data_source, rdf_data=None, rdf_format=None, sparql_url=None, sparql_graph=None):
    current_task.update_state(state='PROGRESS', meta={'progress_percent': 20, 'progress_msg': 'Peeling potatoes...'})
    print 'Peeling potatoes...'
    sleep(3)
    current_task.update_state(state='PROGRESS', meta={'progress_percent': 50, 'progress_msg': 'Frying potatoes...'})
    print 'Frying potatoes...'
    sleep(5)
    current_task.update_state(state='PROGRESS', meta={'progress_percent': 55, 'progress_msg': 'Adding onion...'})
    print 'Adding onion...'
    sleep(2)
    current_task.update_state(state='PROGRESS', meta={'progress_percent': 60, 'progress_msg': 'Stirring eggs...'})
    print 'Stirring eggs...'
    sleep(3)
    current_task.update_state(state='PROGRESS', meta={'progress_percent': 75, 'progress_msg': 'Mixing all...'})
    print 'Mixing all...'
    sleep(3)
    current_task.update_state(state='PROGRESS', meta={'progress_percent': 90, 'progress_msg': 'Doing the omelette...'})
    print 'Doing the omelette...'
    sleep(2)

@celery.task()
def generate_config_file(data_source, rdf_data=None, rdf_format=None, sparql_url=None, sparql_graph=None):
    current_task.update_state(state='PROGRESS', meta={'progress_percent': 15, 'progress_msg': 'Reading provided RDF data...'})

    try:
        if data_source == 'rdf':
            data_graph = Graph()
            data_graph.parse(format=rdf_format, data=rdf_data)
        else:
            g = ConjunctiveGraph('SPARQLStore')
            g.open(sparql_url)
            data_graph = g.get_context(sparql_graph) if sparql_graph else g
    except Exception, e:
        raise Exception("An error occurred while trying to read provided data source: %s" % str(e))

    config_file = Graph()
    config_file.bind('ltw', LTW)

    current_task.update_state(state='PROGRESS', meta={'progress_percent': 25, 'progress_msg': 'Analyzing RDF data with SPARQL...'})
    try:
        data_q_res = data_graph.query(
        '''
            SELECT DISTINCT ?type ?p ?linkto where {
                ?s a ?type ;
                    ?p ?o .
                OPTIONAL { ?o a ?linkto }
                FILTER (!sameTerm(?p, rdf:type))
            }
        '''
        )
    except:
        try:
            data_q_res = data_graph.query(
            '''
                SELECT DISTINCT ?type ?p ?linkto where {
                    ?s a ?type ;
                        ?p ?o .
                    OPTIONAL { ?o a ?linkto }
                    FILTER (str(?p) != "http://www.w3.org/1999/02/22-rdf-syntax-ns#type>")
                }
            '''
            )
        except Exception, e:
            raise Exception("An error occurred while trying to get classes and properties of provided dataset with SPARQL: %s" % str(e))

    current_task.update_state(state='PROGRESS', meta={'progress_percent': 60})

    class_prop_items = {}
    num_of_props = 0
    for class_item, prop_item, clickable_prop in data_q_res:
        num_of_props += 1
        if class_item in class_prop_items:
            if prop_item not in class_prop_items[class_item] or not class_prop_items[class_item][prop_item]:
                class_prop_items[class_item][prop_item] = clickable_prop
        else:
            class_prop_items[class_item] = { prop_item: clickable_prop }

    building_msg = 'Building the LTW configuration file...'
    current_task.update_state(state='PROGRESS', meta={'progress_percent': 70, 'progress_msg': building_msg})
    num_of_processed_props = 0
    for class_item in class_prop_items:
        class_name = re.split('/|#', class_item)[-1]
        class_uri = URIRef('#%sMap' % class_name)
        config_file.add( (class_uri, RDF.type, LTW.ClassItem) )
        config_file.add( (class_uri, LTW.ontologyClass, URIRef(class_item)) )
        config_file.add( (class_uri, LTW.identifier, Literal(class_name)) )

        is_main = False
        for prop_item, clickable_prop in class_prop_items[class_item].items():
            prop_uri = BNode()
            prop_name = re.split('/|#', prop_item)[-1].lower()

            config_file.add( (class_uri, LTW.hasPropertyItem, prop_uri) )
            config_file.add( (prop_uri, LTW.identifier, Literal(prop_name)) )
            config_file.add( (prop_uri, LTW.ontologyProperty, URIRef(prop_item)) )

            if clickable_prop and clickable_prop in class_prop_items:
                config_file.add( (prop_uri, LTW.isClickable, Literal(str(True))) )
            else:
                config_file.add( (prop_uri, LTW.isClickable, Literal(str(False))) )

            if not clickable_prop and not is_main and prop_item in COMMON_LABEL_PROPS:
                is_main = True
                config_file.add( (prop_uri, LTW.isMain, Literal(str(is_main))) )
                config_file.add( (prop_uri, LTW.isLinkable, Literal(str(True))) )

            num_of_processed_props += 1
            current_task.update_state(state='PROGRESS', meta={'progress_percent': int(70 + (30 * float(num_of_processed_props) / float(num_of_props))), 'progress_msg': building_msg})

    return config_file.serialize(format='turtle')

@celery.task()
def get_all_data(data_source, config_file, rdf_data=None, rdf_format=None, sparql_url=None, sparql_graph=None):
    current_task.update_state(state='PROGRESS', meta={'progress_percent': 15, 'progress_msg': 'Reading RDF data...'})

    try:
        if data_source == 'rdf':
            data_graph = Graph()
            data_graph.parse(format=rdf_format, data=rdf_data)
        else:
            g = ConjunctiveGraph('SPARQLStore')
            g.open(sparql_url)
            data_graph = g.get_context(sparql_graph) if sparql_graph else g
    except Exception, e:
        raise Exception("An error occurred while trying to read provided data source: %s" % str(e))

    config_graph = Graph()
    config_graph.parse(data=config_file, format='turtle')

    config_q_res = config_graph.query(
        """
            SELECT DISTINCT ?id ?class_ont
                WHERE {
                    ?s a <http://helheim.deusto.es/ltw/0.1#ClassItem> ;
                        <http://helheim.deusto.es/ltw/0.1#ontologyClass> ?class_ont ;
                        <http://helheim.deusto.es/ltw/0.1#identifier> ?id .
               }
        """
    )

    current_task.update_state(state='PROGRESS', meta={'progress_percent': 20, 'progress_msg': 'Fetching your data...'})

    ont_id_list = [ str(a[0]).lower() + 's' for a in config_q_res ]
    ont_class_list = [ str(a[1]) for a in config_q_res ]

    try:
        Virtuoso = plugin("Virtuoso", Store)
        store = Virtuoso(celery.conf.VIRTUOSO_ODBC)
        ltw_conj_data_graph = ConjunctiveGraph(store=store)
        graph_id = str(uuid.uuid4())
        ltw_data_graph = ltw_conj_data_graph.get_context(graph_id)
    except Exception, e:
        raise Exception("Unable to connect to LTW data source: %s" % str(e))

    progress_per_part = 70 / len(ont_class_list)

    counter = Value('f', float(20))
    max_processes = len(ont_class_list) if len(ont_class_list) <= celery.conf.MAX_MULTIPROCESSING else celery.conf.MAX_MULTIPROCESSING
    pool = Pool(max_processes, p_q_initializer, [counter])

    if len(ont_id_list) > 1:
        fetch_msg = 'Fetching %s' % ', '.join(ont_id_list[:-1])
        fetch_msg += ' and %s...' % ont_id_list[-1]
    else:
        fetch_msg = 'Fetching %s...' % ont_id_list[0]

    pool_result = pool.map_async(fetch_and_save_by_class_ont_wrapper, zip(ont_class_list, repeat(config_graph), repeat(data_graph), repeat(ltw_data_graph), repeat(progress_per_part)))

    pool.close()

    try:
        while not pool_result.ready():
            current_task.update_state(state='PROGRESS', meta={'progress_percent': int(counter.value), 'progress_msg': fetch_msg})
            sleep(1)
        pool_result.wait()
    except Exception, e:
        raise Exception("Error fetching data: %s" % str(e))

    current_task.update_state(state='PROGRESS', meta={'progress_percent': 90, 'progress_msg': 'Saving config file...'})
    try:
        ltw_config_data_graph = ltw_conj_data_graph.get_context(graph_id + '_config')
        for stmt in config_graph:
            ltw_config_data_graph.add(stmt)
    except Exception, e:
        raise Exception("Error saving config file: %s" % str(e))

    return graph_id

def p_q_initializer(counter):
    fetch_and_save_by_class_ont_wrapper.counter = counter

def fetch_and_save_by_class_ont_wrapper(tup):
    tup += (fetch_and_save_by_class_ont_wrapper.counter, )
    return fetch_and_save_by_class_ont(*tup)

def fetch_and_save_by_class_ont(class_ont, config_graph, data_graph, ltw_data_graph, progress_per_part, counter):
    data_q_res = data_graph.query(
    '''
        SELECT DISTINCT ?s ?p ?o where {
            ?s a <%s> ;
                ?p ?o .
        }
    ''' % class_ont
    )

    # main_props = get_main_props_by_class_ont(class_ont, config_graph)
    # linkable_props = get_linkable_props_by_class_ont(class_ont, config_graph)

    len_data_q_res = len(data_q_res)
    prog_per_iteration = float(progress_per_part) / float(len_data_q_res)

    props = get_props_by_class_ont(class_ont, config_graph)
    props.append(str(RDF.type))

    for stmt in data_q_res:
        counter.value += prog_per_iteration
        if str(stmt[1]) in props:
            try:
                ltw_data_graph.add(stmt)
            except:
                pass


@celery.task()
def generate_new_android_app(app_name, package, config_file, graph_id=None, logo=None, icon=None):
    current_task.update_state(state='PROGRESS', meta={'progress_percent': 5, 'progress_msg': 'Creating app structure...'})

    config_graph = Graph()
    config_graph.parse(format='turtle', data=config_file)

    if not graph_id:
        graph_id = uuid.uuid4()

    lib_path = LTW_ANDROID_LIB_PATH if LTW_ANDROID_LIB_PATH.endswith('/') else LTW_ANDROID_LIB_PATH + '/'

    # Copy base app to new app path
    app_path = '%s%s/%s/' if NEW_APPS_PATH.endswith('/') else '%s/%s/%s/'
    app_path = app_path % ( NEW_APPS_PATH, graph_id, app_name.replace(' ', '_').lower())
    try:
        shutil.copytree(BASE_APP_PATH, app_path)
    except OSError:
        shutil.rmtree(app_path)
        shutil.copytree(BASE_APP_PATH, app_path)

    # Create source folders (based on package)
    shutil.move(app_path + 'src/package/', '%ssrc/%s/' % ( app_path, package.replace('.', '/') ))

    # Remove unnecesary files
    os.remove(app_path + 'src/%s/model/model_template.java' % package.replace('.', '/'))
    os.remove(app_path + 'res/layout/model_layout.xml')

    # Create Jinja environment
    env = Environment(loader=PackageLoader('ltwserver', 'android_app_base'))

    # Edit AndroidManifest.xml
    template = env.get_template('AndroidManifest.xml')
    with open(app_path + 'AndroidManifest.xml', 'w') as f:
        f.write(template.render(package=package))

    # Edit res/values/strings.xml
    template = env.get_template('res/values/strings.xml')
    with open(app_path + 'res/values/strings.xml', 'w') as f:
        f.write(template.render(app_name=app_name).encode('utf-8'))

    # Edit res/layout/activity_main.xml
    template = env.get_template('res/layout/activity_main.xml')
    with open(app_path + 'res/layout/activity_main.xml', 'w') as f:
        f.write(template.render(logo=logo).encode('utf-8'))

    # Edit src/pkg/BarcodeActivity.java
    template = env.get_template('src/package/BarcodeActivity.java')
    with open(app_path + 'src/%s/BarcodeActivity.java' % package.replace('.', '/'), 'w') as f:
        f.write(template.render(package=package).encode('utf-8'))

    # Edit src/pkg/DataActivity.java
    template = env.get_template('src/package/DataActivity.java')
    with open(app_path + 'src/%s/DataActivity.java' % package.replace('.', '/'), 'w') as f:
        f.write(template.render(package=package).encode('utf-8'))

    # Edit src/pkg/MainActivity.java
    template = env.get_template('src/package/MainActivity.java')
    with open(app_path + 'src/%s/MainActivity.java' % package.replace('.', '/'), 'w') as f:
        f.write(template.render(package=package).encode('utf-8'))

    # Generate model/property dictionary from LTW configuration
    # Dictionary structure:
    #     {
    #         model: {
    #             'main': prop2,
    #             'properties': [
    #                 { 'id': prop1, 'is_list': False, 'is_img': True },
    #                 { 'id': prop2, 'is_list': True, 'is_img': False },
    #                 ...
    #             ]
    #         },
    #         model2: { ... }
    #     }

    model_prop_dict = {}
    model_props = config_graph.query(
    '''
        PREFIX ltw: <http://helheim.deusto.es/ltw/0.1#>
        SELECT DISTINCT ?s ?model ?property ?prop_ont ?is_main where {
            ?s a ltw:ClassItem ;
                ltw:identifier ?model ;
                ltw:hasPropertyItem ?prop .
            ?prop ltw:ontologyProperty ?prop_ont ;
                ltw:identifier ?property .
            OPTIONAL { ?prop ltw:isMain ?is_main }
        }
    '''
    )

    for s, model, prop, prop_ont, is_main in model_props:
        if model.lower() not in model_prop_dict:
            model_prop_dict[model.lower()] = {}
            model_prop_dict[model.lower()]['subject'] = s
            model_prop_dict[model.lower()]['properties'] = []

        if is_main:
            model_prop_dict[model.lower()]['main'] = prop.lower()

        model_prop_dict[model.lower()]['properties'].append(
            { 'id': prop, 'is_list': check_if_list(graph_id, prop_ont), 'is_image': str(prop_ont) in IMG_PROPS, 'is_main': is_main }
        )

    # Generate Java classes and Android layouts for each model
    model_template = env.get_template('src/package/model/model_template.java')
    layout_template = env.get_template('res/layout/model_layout.xml')

    for model_id, model in model_prop_dict.items():
        # Update config file to add javaClass
        config_graph.add( (URIRef(s), LTW.javaClass, Literal(package + ".model." + model_id.title())) )
        # Generate model
        with open(app_path + 'src/%s/model/%s.java' % ( package.replace('.', '/'), model_id.title() ), 'w') as f:
            f.write(model_template.render(package=package, model=model_id, properties=model['properties']).encode('utf-8'))
        # Generate layout
        with open(app_path + 'res/layout/%s.xml' % model_id, 'w') as f:
            f.write(layout_template.render(package=package, model=model_id, properties=model['properties']).encode('utf-8'))

    # Save LTW config file in it's corresponding place
    config_graph.bind('ltw', LTW)

    with open(app_path + 'res/raw/config.ttl', 'w') as f:
        f.write(config_graph.serialize(format='turtle').encode('utf-8'))

    relative_lib_path = ''
    for i in range(len(lib_path.split('/'))):
        relative_lib_path += '../'
    relative_lib_path = relative_lib_path[:-1] + lib_path

    current_task.update_state(state='PROGRESS', meta={'progress_percent': 15, 'progress_msg': 'Creating app structure...'})
    subprocess.call([ANDROID_BIN, 'update', 'project', '--path', app_path, '--target', 'android-18', '--name', app_name, '--library', relative_lib_path])

    current_task.update_state(state='PROGRESS', meta={'progress_percent': 25, 'progress_msg': 'Building app...'})

    i = 0
    process = subprocess.Popen(['ant', '-f', lib_path + 'build.xml', 'clean'], stdout=subprocess.PIPE)
    for line in iter(process.stdout.readline, ''):
        sys.stdout.write(line)
        i += 1
        current_task.update_state(state='PROGRESS', meta={'progress_percent': int(25 + (65 * float(i) / float(NUM_OF_PROCESS_MSGS))), 'progress_msg': 'Building app...'})

    process = subprocess.Popen(['ant', '-f', app_path + 'build.xml', 'release'], stdout=subprocess.PIPE)
    for line in iter(process.stdout.readline, ''):
        sys.stdout.write(line)
        i += 1
        current_task.update_state(state='PROGRESS', meta={'progress_percent': int(25 + (65 * float(i) / float(NUM_OF_PROCESS_MSGS))), 'progress_msg': 'Building app...'})

    current_task.update_state(state='PROGRESS', meta={'progress_percent': 95, 'progress_msg': 'Signing app...'})

    return app_path


def check_if_list(graph_id, prop_ont):
    return False
