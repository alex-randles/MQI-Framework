from rdflib import *
from collections import defaultdict
graph_filename = "/home/alex/MQI-Framework/static/change_detection_cache/change_graphs/1.trig"
change_graph = ConjunctiveGraph()
change_graph.parse(graph_filename, format="trig")
def analyse_mappings():
    # change_graph.parse("/home/alex/MQI-Framework/static/uploads/mapping.ttl", format="ttl")
    query = """
    PREFIX oscd: <https://w3id.org/OSCD#>
    PREFIX rml: <http://semweb.mmlab.be/ns/rml#>
    PREFIX rr: <http://www.w3.org/ns/r2rml#>
    SELECT ?mappingGraph ?tripleMap ?source ?change ?reference ?changedData ?changesGraph
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
    matched_graphs[mapping_graph_id] = defaultdict(dict)
    matched_graphs[mapping_graph_id]["data_reference_changes"] = {
        "insert": defaultdict(dict),
        "delete": defaultdict(dict),
    }
    # data reference changes
    current_data_reference_changes = matched_graphs[mapping_graph_id]["data_reference_changes"]
    for row in qres:
        data_reference = row["reference"]
        changed_data = row["changedData"]
        change_identifier = row["change"]
        change_type = "insert"
        if "delete" in change_identifier:
            change_type = "delete"
        if data_reference in current_data_reference_changes[change_type]:
            current_data_reference_changes[change_type][data_reference].append(changed_data)
        else:
            current_data_reference_changes[change_type][data_reference] = [changed_data]
    # add structural changes if theres match
    if current_data_reference_changes:
        find_structural_changes(row["changesGraph"])
    return qres

def find_structural_changes(graph_name):
    print(graph_name)
    query = """
        PREFIX oscd: <https://w3id.org/OSCD#>
        PREFIX rml: <http://semweb.mmlab.be/ns/rml#>
        PREFIX rr: <http://www.w3.org/ns/r2rml#>

        SELECT ?referenceChanged ?dataChanged
        WHERE {
          GRAPH <%s> {    			 
            ?changeLog a oscd:ChangeLog;
                    oscd:hasChange ?change . 
            ?change oscd:hasDataReference ?referenceChanged;
                    oscd:hasChangedData ?dataChanged .

            {
              SELECT ?referenceChanged ?stucturalReference
              WHERE {
                GRAPH <%s> {    			 
                  ?changeLog a oscd:ChangeLog;
                          oscd:hasChange ?change . 
                  ?change oscd:hasStructuralReference ?stucturalReference;
                          oscd:hasChangedData ?referenceChanged .

                }
             }

            }

          }
        }
    """ % (graph_name, graph_name)
    qres = change_graph.query(query)
    print(query)
    for row in qres:
        print(row)

t = analyse_mappings()


