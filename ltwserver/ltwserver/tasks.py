# coding=utf-8

from ltwserver import celery

from celery import current_task
from rdflib import Graph, ConjunctiveGraph, Namespace, BNode
from rdflib.namespace import RDF, RDFS, FOAF, SKOS
from rdflib.term import URIRef, Literal
from rdflib.store import Store
from rdflib.plugin import get as plugin
from multiprocessing import Pool, Value
from itertools import repeat

import re
import wikipedia
import uuid
from time import sleep


# Define RDFlib namespaces
LTW = Namespace('http://helheim.deusto.es/ltw/0.1#')
DC = Namespace(u"http://purl.org/dc/elements/1.1/")

# Properties that are used usually as labels in RDF data
COMMON_LABEL_PROPS = [RDFS.label, DC.name, FOAF.name, SKOS.prefLabel]

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

    if data_source == 'rdf':
        data_graph = Graph()
        data_graph.parse(format=rdf_format, data=rdf_data)
    else:
        g = ConjunctiveGraph('SPARQLStore')
        g.open(sparql_url)
        data_graph = g.get_context(sparql_graph) if sparql_graph else g

    config_file = Graph()
    config_file.bind('ltw', LTW)

    current_task.update_state(state='PROGRESS', meta={'progress_percent': 25, 'progress_msg': 'Analyzing RDF data with SPARQL...'})
    data_q_res = data_graph.query(
    '''
        SELECT DISTINCT ?type ?p ?linkto where {
            ?s a ?type ;
                ?p ?o .
            OPTIONAL { ?o a ?linkto }
            FILTER (!sameTerm(?p, rdf:type))
        }
    '''
    # FILTER (str(?p) != "http://www.w3.org/1999/02/22-rdf-syntax-ns#type>")
    # FILTER (!sameTerm(?p, rdf:type))
    )

    current_task.update_state(state='PROGRESS', meta={'progress_percent': 60})

    class_prop_items = {}
    num_of_props = 0
    for class_item, prop_item, clickable_prop in data_q_res:
        num_of_props += 1
        if class_item in class_prop_items:
            class_prop_items[class_item].append((prop_item, clickable_prop))
        else:
            class_prop_items[class_item] = [(prop_item, clickable_prop)]


    current_task.update_state(state='PROGRESS', meta={'progress_percent': 70, 'progress_msg': 'Building the LTW configuration file...'})
    num_of_processed_props = 0
    for class_item, prop_clicks in class_prop_items.items():
        class_name = re.split('/|#', class_item)[-1]
        class_uri = URIRef('#%sMap' % class_name)
        config_file.add( (class_uri, RDF.type, LTW.ClassItem) )
        config_file.add( (class_uri, LTW.ontologyClass, URIRef(class_item)) )
        config_file.add( (class_uri, LTW.identifier, Literal(class_name)) )

        is_main = False
        for prop_click in prop_clicks:
            prop_item, clickable_prop = prop_click

            prop_uri = BNode()
            prop_name = re.split('/|#', prop_item)[-1].lower()

            config_file.add( (class_uri, LTW.hasPropertyItem, prop_uri) )
            config_file.add( (prop_uri, LTW.identifier, Literal(prop_name)) )
            config_file.add( (prop_uri, LTW.ontologyProperty, URIRef(prop_item)) )

            if clickable_prop and clickable_prop in class_prop_items:
                config_file.add( (prop_uri, LTW.isClickable, Literal(True)) )
            else:
                config_file.add( (prop_uri, LTW.isClickable, Literal(False)) )

            if not clickable_prop and not is_main and prop_item in COMMON_LABEL_PROPS:
                is_main = True
                config_file.add( (prop_uri, LTW.isMain, Literal(is_main)) )

            num_of_processed_props += 1
            current_task.update_state(state='PROGRESS', meta={'progress_percent': int(70 + (30 * float(num_of_processed_props) / float(num_of_props)))})

    return config_file.serialize(format='turtle')

@celery.task()
def get_all_data(data_source, config_file, rdf_data=None, rdf_format=None, sparql_url=None, sparql_graph=None):
    current_task.update_state(state='PROGRESS', meta={'progress_percent': 15, 'progress_msg': 'Reading RDF data...'})

    if data_source == 'rdf':
        data_graph = Graph()
        data_graph.parse(format=rdf_format, data=rdf_data)
    else:
        g = ConjunctiveGraph('SPARQLStore')
        g.open(sparql_url)
        data_graph = g.get_context(sparql_graph) if sparql_graph else g

    config_graph = Graph()
    config_graph.parse(data=config_file, format='turtle')

    # data_dict = {}

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

    ont_class_tot = len(config_q_res)

    Virtuoso = plugin("Virtuoso", Store)
    store = Virtuoso("DSN=VOS;UID=dba;PWD=dba;WideAsUTF16=Y")

    ltw_conj_data_graph = ConjunctiveGraph(store=store)
    graph_id = str(uuid.uuid4())
    ltw_data_graph = ltw_conj_data_graph.get_context(graph_id)

    progress_per_part = 70 / ont_class_tot
    last_progress = 20

    counter = Value('f', float(last_progress))
    max_processes = ont_class_tot if ont_class_tot <= 10 else 10
    pool = Pool(max_processes, p_q_initializer, [counter])

    pool_result = pool.map_async(fetch_and_save_by_class_ont_wrapper, zip([str(a[1]) for a in config_q_res], repeat(config_graph), repeat(data_graph), repeat(ltw_data_graph), repeat(progress_per_part)))
    
    pool.close()
    while not  pool_result.ready():
        current_task.update_state(state='PROGRESS', meta={'progress_percent': int(counter.value)})
        sleep(1)

    #print "yeah!"
    print pool_result.get()


    return graph_id

def p_q_initializer(counter):
    fetch_and_save_by_class_ont_wrapper.counter = counter

def fetch_and_save_by_class_ont_wrapper(tup):
    tup += (fetch_and_save_by_class_ont_wrapper.counter, )
    return fetch_and_save_by_class_ont(*tup)

def fetch_and_save_by_class_ont(class_ont, config_graph, data_graph, ltw_data_graph, progress_per_part, counter):
    #current_task.update_state(state='PROGRESS', meta={'progress_percent': int(last_progress), 'progress_msg': 'Fetching %ss...' % class_id.lower() })

    # data_dict[class_ont] = {}

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

    for stmt in data_q_res:
        counter.value += prog_per_iteration
        #current_task.update_state(state='PROGRESS', meta={'progress_percent': int(last_progress + (progress_per_part * float(j) / float(len_data_q_res))), 'progress_msg': 'Fetching %ss...' % class_id.lower() })
        if str(stmt[1]) in props:
            ltw_data_graph.add(stmt)


def get_props_by_class_ont(class_ont, config_graph):
    props = config_graph.query(
    '''
        SELECT DISTINCT ?prop_ont where {
            ?s <http://helheim.deusto.es/ltw/0.1#ontologyClass> <%s> ;
                <http://helheim.deusto.es/ltw/0.1#hasPropertyItem> ?prop .
            ?prop <http://helheim.deusto.es/ltw/0.1#ontologyProperty> ?prop_ont .
        }
    ''' % class_ont
    )
    ret_list = []
    for prop in props:
        ret_list.append(str(prop[0]))
    return ret_list

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
