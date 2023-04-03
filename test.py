from rdflib import *
def analyse_mappings():
    graph_filename = "/home/alex/MQI-Framework/static/change_detection_cache/change_graphs/1.trig"
    change_graph = ConjunctiveGraph()
    change_graph.parse(graph_filename, format="trig")
    # change_graph.parse("/home/alex/MQI-Framework/static/uploads/mapping.ttl", format="ttl")
    query = """
    PREFIX oscd: <https://w3id.org/OSCD#>
    PREFIX rml: <http://semweb.mmlab.be/ns/rml#>
    PREFIX rr: <http://www.w3.org/ns/r2rml#>
    SELECT ?mappingGraph ?tripleMap ?source ?change ?reference ?changedData
    WHERE {
      GRAPH ?changesGraph {    			 
        ?changeLog a oscd:ChangeLog;
                oscd:hasChange ?change;
                oscd:hasCurrentVersion ?currentVersion .
        ?change oscd:hasDataReference ?reference;
                oscd:hasChangedData ?changedData .
        BIND (REPLACE(STR(?currentVersion), "^.*/([^/]*)$", "$1") as ?source)
      }
      GRAPH ?mappingGraph {    			 
        ?tripleMap rml:logicalSource|rr:logicalTable ?logicalSource;
                rr:predicateObjectMap ?pom .
        ?logicalSource rml:source|rr:tableName ?source .
        ?pom rr:objectMap ?objectMap .
        ?objectMap rml:reference|rr:column ?reference.
      }
    }
    """
    mapping_graph_id = 1
    graph_name = URIRef("http://example.org/mapping-" + str(mapping_graph_id))
    mapping_file = "/home/alex/MQI-Framework/static/uploads/sample_mapping10.ttl"
    g = Graph().parse(mapping_file, format="ttl")
    for s,p,o in g.triples((None, None, None)):
        change_graph.add((s,p,o,graph_name))
    change_graph.serialize(destination="test.trig", format="trig")
    qres = change_graph.query(query)
    matched_graphs = defaultdict(dict)
    for row in qres:
        matched_graphs[mapping_graph_id] = {

        }
        print(row)
    return qres

t = analyse_mappings()
