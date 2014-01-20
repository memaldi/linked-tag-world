# coding=utf-8

from ltwserver import app
from flask import request

from rdflib import ConjunctiveGraph, URIRef
from rdflib.store import Store
from rdflib.plugin import get as plugin
from rdflib.namespace import RDF

import wikipedia

PER_PAGE = app.config['PAGINATION_PER_PAGE']
IMG_PROPS = ['http://xmlns.com/foaf/0.1/depiction']
SUPPORTED_RDF_HEADERS = {
    'application/rdf+xml': 'xml',
    'text/turtle': 'turtle',
    'text/n3': 'n3',
    'text/plain': 'nt',
    'application/n-quads': 'nquads',
}


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


def get_property_labels(config_graph):
    main_props = config_graph.query(
    '''
        SELECT DISTINCT ?prop_ont, ?prop_id where {
            ?s <http://helheim.deusto.es/ltw/0.1#hasPropertyItem> ?prop .
            ?prop <http://helheim.deusto.es/ltw/0.1#identifier> ?prop_id ;
                <http://helheim.deusto.es/ltw/0.1#ontologyProperty> ?prop_ont .
        }
    '''
    )
    ret_dict = {}
    for prop, prop_id in main_props:
        ret_dict[str(prop)] = str(prop_id)
    return ret_dict


def get_resource_triples(data_graph, config_graph, class_uri, s, graph_id=None):
    main_props = [str(prop) for prop in get_main_props_by_class_ont(class_uri, config_graph)]
    linkable_props = [str(prop) for prop in get_linkable_props_by_class_ont(class_uri, config_graph)]
    property_labels = get_property_labels(config_graph)

    main = None

    img = None

    data_list = []
    linkable = []
    for p, o in data_graph.predicate_objects(URIRef(s)):
        if str(p) != str(RDF.type):
            label = property_labels[str(p)] if str(p) in property_labels else str(p)
            if str(p) in main_props:
                main = o
            elif str(p) in IMG_PROPS:
                img = o
            if str(p) in linkable_props:
                linkable.append(str(p))

            data_list.append((p, o, label.title()))

    graph_id = graph_id if graph_id else request.cookies.get('graph_id')
    return {'triples': data_list, 'main': main, 'img': img, 'linkable': linkable, 'ltwuri': get_ltw_uri(s, graph_id)}


def get_next_resources(page, class_uri, graph_id=None):
    g = get_ltw_data_graph(graph_id)
    config_graph = get_ltw_config_graph(graph_id)

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

    res_dict = {}
    for s in q_res:
        res_dict[str(s[0])] = get_resource_triples(g, config_graph, class_uri, str(s[0]))

    return res_dict


def get_ltw_uri(uri, graph_id):
    url_root = request.url_root[:-1] if request.url_root.endswith('/') else request.url_root
    return '%s/res/%s/%s' % ( url_root, graph_id, uri )


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


def get_dbpedia_uri(term, lang):
    """
    Get the corresponding DBpedia URI from a wikipedia term (taking in account the language of the term)
    """

    DBPEDIA_RESOURCE_URI = 'dbpedia.org/resource/'
    if lang == 'en':
        return 'http://%s%s' % (DBPEDIA_RESOURCE_URI, str(term))
    else:
        return 'http://%s.%s%s' % (lang, DBPEDIA_RESOURCE_URI, str(term))


def search_dbpedia_trough_wikipedia(literal, lang='en'):
    """
    Search a literal in Wikipedia (taking in account the language of the literal) and return a list of related DBpedia resources
    """

    ret = {}
    ret[literal] = []
    wikipedia.set_lang(lang)
    for term in wikipedia.search(str(literal)):
        summary = wikipedia.summary(term, sentences=1)
        #imgs = wikipedia.page(term).images
        term = term.encode('utf-8').replace(' ', '_')
        ret[literal].append( (get_dbpedia_uri(term, lang), summary) )
    return ret


def request_wants_rdf():
# Based on http://flask.pocoo.org/snippets/45/. Thanks!
    accepted_headers = [ header for header in SUPPORTED_RDF_HEADERS ]
    accepted_headers.append('text/html')
    best = request.accept_mimetypes.best_match(accepted_headers)
    if best in SUPPORTED_RDF_HEADERS and request.accept_mimetypes[best] > request.accept_mimetypes['text/html']:
        return best
    return None
