#coding: utf-8

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


def create_linkable_property(config_graph, class_ont, prop_ont):
    """
    Create linkable properties for given properties in a given config_graph
    """

    class_item = config_graph.subjects(LTW.ontologyClass, URIRef(class_ont)).next()
    for prop_item in config_graph.objects(class_item, LTW.hasPropertyItem):
        for obj in config_graph.objects(prop_item, LTW.ontologyProperty):
            if str(obj) == prop_ont:
                config_graph.add( (prop_item, LTW.isLinkable, Literal(True)) )


def generate_config_file(data_graph, graph=None):
    """
    Analyze a given RDF graph and generates a LTW configuration graph based on its classes and properties
    """

    config_file = Graph()
    config_file.bind('ltw', LTW)

    graph_str = 'GRAPH <%s>' % graph if graph else ''
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

    class_prop_items = {}
    i = 0
    for class_item, prop_item, clickable_prop in data_q_res:
        i += 1
        if class_item in class_prop_items:
            class_prop_items[class_item].append((prop_item, clickable_prop))
        else:
            class_prop_items[class_item] = [(prop_item, clickable_prop)]
    print i

    j = 0
    for class_item, prop_clicks in class_prop_items.items():
        class_name = re.split('/|#', class_item)[-1]
        class_uri = URIRef('#%sMap' % class_name)
        config_file.add( (class_uri, RDF.type, LTW.ClassItem) )
        config_file.add( (class_uri, LTW.ontologyClass, URIRef(class_item)) )

        is_main = False
        for prop_click in prop_clicks:
            j += 1
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

    print j
    return config_file

def generate_config_file_2(data_graph, graph=None):
    config_file = Graph()
    config_file.bind('ltw', LTW)

    graph_str = 'GRAPH <%s>' % graph if graph else ''

    for class_item in set(data_graph.objects(None, RDF.type)):
        is_main = False

        class_name = re.split('/|#', class_item)[-1]
        class_uri = URIRef('#%sMap' % class_name)
        config_file.add( (class_uri, RDF.type, LTW.ClassItem) )
        config_file.add( (class_uri, LTW.ontologyClass, URIRef(class_item)) )

        qres = data_graph.query(
        """
            SELECT DISTINCT ?p_link ?p
                WHERE {
                    %s
                    {
                        ?s a <%s> .
                        {
                            ?s ?p_link ?o .
                            FILTER isURI(?o) .
                            FILTER ( str(?p_link) != 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type' ) .
                        }
                        UNION
                        {
                            ?s ?p_link ?o .
                            FILTER isBlank(?o) .
                        }
                        UNION
                        {
                            ?s ?p ?o .
                            FILTER (!isURI(?o)) .
                        }
                    }
               }
        """ % (graph_str, class_item)
        )
        for prop_item in qres:
            prop_item, is_clickable = (prop_item[0], True) if prop_item[0] else (prop_item[1], False)
            prop_uri = BNode()
            prop_name = re.split('/|#', prop_item)[-1].lower()

            config_file.add( (class_uri, LTW.hasPropertyItem, prop_uri) )
            config_file.add( (prop_uri, LTW.identifier, Literal(prop_name)) )
            config_file.add( (prop_uri, LTW.ontologyProperty, URIRef(prop_item)) )
            config_file.add( (prop_uri, LTW.isClickable, Literal(is_clickable)) )

            if not is_clickable and not is_main and prop_item in COMMON_LABEL_PROPS:
                is_main = True
                config_file.add( (prop_uri, LTW.isMain, Literal(is_main)) )

    return config_file

def get_dbpedia_uri(term, lang):
    """
    Get the corresponding DBpedia URI from a wikipedia term (taking in account the language of the term)
    """

    DBPEDIA_RESOURCE_URI = 'dbpedia.org/resource/'
    if lang == 'en':
        return 'http://%s%s' % (DBPEDIA_RESOURCE_URI, str(term))
    else:
        return 'http://%s.%s%s' % (lang, DBPEDIA_RESOURCE_URI, str(term))


def search_dbpedia_trough_wikipedia(literal, lang):
    """
    Search a literal in Wikipedia (taking in account the language of the literal) and return a list of related DBpedia resources
    """

    ret = {}
    ret[literal] = []
    wikipedia.set_lang(lang)
    for term in wikipedia.search(str(literal)):
        term = term.encode('utf-8').replace(' ', '_')
        ret[literal].append(get_dbpedia_uri(term, lang))
    return ret


def find_linkable_properties(config_graph):
    """
    Crawl the LTW configuration graph searching for linkable properties
    """

    config_q_res = config_graph.query(
        """
            SELECT DISTINCT ?class_ont ?prop_ont
                WHERE {
                    ?s a <http://helheim.deusto.es/ltw/0.1#ClassItem> ;
                        <http://helheim.deusto.es/ltw/0.1#ontologyClass> ?class_ont ;
                        <http://helheim.deusto.es/ltw/0.1#hasPropertyItem> ?prop_item .
                    ?prop_item <http://helheim.deusto.es/ltw/0.1#ontologyProperty> ?prop_ont ;
                        <http://helheim.deusto.es/ltw/0.1#isLinkable> ?linkable .
                    FILTER ( ?linkable )
               }
        """
        )

    return [(class_ont, prop_ont) for class_ont, prop_ont in config_q_res]


def get_linkable_literals(data_graph, linkable_props, default_lang='en', graph=None):
    """
    Get every literal of identified linkable properties in the dataset
    """

    graph_str = 'GRAPH <%s>' % graph if graph else ''
    for class_ont, prop_ont in linkable_props:
        sparql11_query =  """
                SELECT DISTINCT ?s ?literal ?language
                    WHERE {
                        %s
                        {
                            ?s a <%s> ;
                                <%s> ?literal .
                            FILTER isLiteral(?literal) .
                            BIND (lang(?literal) AS ?language )
                        }
                   }
            """

        sparql10_query = """
                SELECT DISTINCT ?s ?literal (lang(?literal) AS ?lang)
                    WHERE {
                        %s
                        {
                            ?s a <%s> ;
                                <%s> ?literal .
                            FILTER isLiteral(?literal) .
                        }
                   }
            """

        print sparql10_query % (graph_str, class_ont, prop_ont)
        data_q_res = data_graph.query(sparql10_query % (graph_str, class_ont, prop_ont))

        for subject, lit, lang in data_q_res:
            lang = lang.encode('utf-8') if lang.encode('utf-8') else default_lang
            lit = lit.encode('utf-8')

            print search_dbpedia_trough_wikipedia(lit, lang)



if __name__ == "__main__":
    g = ConjunctiveGraph('SPARQLStore')
    g.open('http://helheim.deusto.es/hedatuz/sparql')
    #g.open('http://data.semanticweb.org/sparql')
    #g.open('http://helheim.deusto.es/sparql')

    # Generate LTW configuration file for a given dataset
    config = generate_config_file(data_graph=g)#, graph='http://turismo-zaragoza')

    # Add some fake linkable properties to LTW configuration file
    #create_linkable_property(config_graph=config, class_ont='http://xmlns.com/foaf/0.1/Person', prop_ont='http://xmlns.com/foaf/0.1/name')
    #create_linkable_property(config_graph=config, class_ont='http://idi.fundacionctic.org/cruzar/turismo#Edificio-historico', prop_ont='http://www.w3.org/2004/02/skos/core#definition')

    # Print the serialization of the resulting LTW configuration file
    #print config.serialize(format='turtle')

    # Crawl the LTW configuration file searching for linkable properties
    linkable_props = find_linkable_properties(config_graph=config)

    # Get every literal of identified linkable properties in the dataset
    get_linkable_literals(data_graph=g, linkable_props=linkable_props, default_lang='es', graph='http://turismo-zaragoza')
