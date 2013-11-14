# coding=utf-8

from ltwserver import celery

from celery import current_task
from rdflib import Graph, ConjunctiveGraph, Namespace, BNode
from rdflib.namespace import RDF, RDFS, FOAF, SKOS
from rdflib.term import URIRef, Literal

import re
import wikipedia


# Define RDFlib namespaces
LTW = Namespace('http://helheim.deusto.es/ltw/0.1#')
DC = Namespace(u"http://purl.org/dc/elements/1.1/")

# Properties that are used usually as labels in RDF data
COMMON_LABEL_PROPS = [RDFS.label, DC.name, FOAF.name, SKOS.prefLabel]

@celery.task()
def make_omelette(data_source, rdf_data=None, rdf_format=None, sparql_url=None, sparql_graph=None):
    from time import sleep
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
        data_graph = ConjunctiveGraph('SPARQLStore')
        data_graph.open(sparql_url)

    config_file = Graph()
    config_file.bind('ltw', LTW)

    current_task.update_state(state='PROGRESS', meta={'progress_percent': 25, 'progress_msg': 'Analyzing RDF data with SPARQL...'})
    graph_str = 'GRAPH <%s>' % sparql_graph if sparql_graph else ''
    data_q_res = data_graph.query(
    '''
        SELECT DISTINCT ?type ?p ?linkto where {
            %s
            {
                ?s a ?type ;
                    ?p ?o .
                OPTIONAL { ?o a ?linkto }
                FILTER (!sameTerm(?p, rdf:type))
            }
        }
    ''' % graph_str
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