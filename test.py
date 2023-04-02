from rdflib import *
def analyse_mappings():
    graph_filename = "/home/alex/MQI-Framework/static/change_detection_cache/change_graphs/14.trig"
    change_graph = Dataset()
    change_graph.parse(graph_filename, format="trig")
    # change_graph.parse("/home/alex/MQI-Framework/static/uploads/mapping.ttl", format="ttl")
    query = """
        PREFIX oscd: <https://w3id.org/OSCD#>
        PREFIX rml: <http://semweb.mmlab.be/ns/rml#>
        PREFIX rr: <http://www.w3.org/ns/r2rml#>

        SELECT ?graphName
        WHERE {
          GRAPH ?changesGraph {    			 
            ?changeLog a oscd:ChangeLog;
                    oscd:hasChange ?change;
                    oscd:hasCurrentVersion ?currentVersion .
            ?change oscd:hasDataReference ?reference;
                    oscd:hasChangedData ?changedData .
          }
          BIND (REPLACE(STR(?currentVersion), "^.*/([^/]*)$", "$1") as ?source)
          GRAPH ?mappingGraph {    			 
            ?tripleMap rml:logicalSource|rr:logicalTable ?logicalSource;
                    rr:predicateObjectMap ?pom .
            ?logicalSource rml:source|rr:tableName ?source .
            ?pom rr:objectMap ?objectMap .
            ?objectMap rml:reference|rr:column ?reference.
          }
           BIND (REPLACE(STR(?mappingGraph), "^.*/([^/]*)$", "$1") as ?graphName)

        }
        GROUP BY ?graphName
    """
    qres = change_graph.query(query)
    return qres

def analyse_result(qres):
    for row in list(set(qres)).copy():
        print(row)
    exit()

t = analyse_mappings()
print(analyse_result(t))