from rdflib import *
from collections import defaultdict
import os
graph_filename = "/home/alex/MQI-Framework/static/change_detection_cache/change_graphs/1.trig"
complete_graph = ConjunctiveGraph()

def add_change_graphs():
    change_directory = "./static/change_detection_cache/change_graphs/"
    directory = os.fsencode(change_directory)
    for file in os.listdir(directory):
        filename = os.fsdecode(file)
        file_path = change_directory + filename
        current_graph = ConjunctiveGraph()
        current_graph.parse(file_path, format="trig")
        change_graph_identifier = URIRef("http://www.example.com/changesGraph/user-1")
        changes_graph = current_graph.get_context(change_graph_identifier)
        for s, p, o in changes_graph.triples((None, None, None)):
            complete_graph.add((s,p,o, filename))

def add_mapping_graphs():
    mapping_directory = "./static/uploads/"
    directory = os.fsencode(mapping_directory)
    for file in os.listdir(directory):
        filename = os.fsdecode(file)
        file_path = mapping_directory + filename
        mapping_graph = Graph().parse(file_path, format="ttl")
        for s, p, o in mapping_graph.triples((None, None, None)):
            complete_graph.add((s,p,o, filename))
    complete_graph.serialize(destination="test.trig", format="trig")


def analyse_mapping_impact():
    add_change_graphs()
    add_mapping_graphs()
    detect_mapping_impact()

def detect_mapping_impact():
    query = """
        PREFIX oscd: <https://w3id.org/OSCD#>
        PREFIX rml: <http://semweb.mmlab.be/ns/rml#>
        PREFIX rr: <http://www.w3.org/ns/r2rml#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?mappingGraph ?changesGraph ?source ?change ?reference ?changedData ?data
        WHERE {
          GRAPH ?changesGraph {    			 
            ?changeLog a oscd:ChangeLog;
                    oscd:hasChange ?change;
                    oscd:hasCurrentVersion ?currentVersion .
            ?change oscd:hasDataReference ?reference;
                    oscd:hasChangedData ?changedData .
            ?changedData rdfs:comment ?data . 
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
    qres = complete_graph.query(query)
    matched_graphs = defaultdict(dict)
    for row in qres:
        mapping_graph = str(row["mappingGraph"])
        change_graph = str(row["changesGraph"])
        mapping_identifier = get_mapping_identifier(mapping_graph)
        if mapping_identifier:
            mapping_identifier = mapping_identifier[0]
            data_reference = str(row["reference"])
            if change_graph not in matched_graphs:
                matched_graphs[change_graph] = defaultdict(dict)
            matched_graphs[change_graph][mapping_identifier] = {
                "insert": defaultdict(dict),
            }
            matched_graphs[change_graph][mapping_identifier][data_reference] = str(row["data"])
    print(matched_graphs)
    return matched_graphs

def get_mapping_identifier(mapping_filename):
    mappings = {1: {'filename': 'sample_mapping.ttl', 'display_filename': 'sample_mapping.ttl', 'source_data': ['EMP'],
         'data_references': ['ENAME', 'EMPNO']},
     2: {'filename': 'sample_mapping10.ttl', 'display_filename': 'sample_mapping10.ttl', 'source_data': ['student.csv'],
         'data_references': ['ID', 'Name']},
     3: {'filename': 'refined-mapping28.ttl', 'display_filename': 'refined-mapping28.ttl',
         'source_data': ['student.csv'], 'data_references': ['ID', 'Name']},
     4: {'filename': 'sample_mapping8.ttl', 'display_filename': 'sample_mapping8.ttl', 'source_data': ['EMP'],
         'data_references': ['ENAME', 'EMPNO']},
     5: {'filename': 'mapping.ttl', 'display_filename': 'mapping.ttl', 'source_data': ['EMP'],
         'data_references': ['ENAME', 'EMPNO']},
     6: {'filename': 'sample_mapping9.ttl', 'display_filename': 'sample_mapping9.ttl', 'source_data': ['EMP'],
         'data_references': ['ENAME', 'EMPNO']},
     7: {'filename': 'document_mapping.ttl', 'display_filename': 'document_mapping.ttl', 'source_data': ['student.csv'],
         'data_references': ['ID', 'Name']}}

    mapping_identifier = [key for key, values in mappings.items() if values["filename"] == mapping_filename.strip()]
    return mapping_identifier


analyse_mapping_impact()














#     # change_graph.parse("/home/alex/MQI-Framework/static/uploads/mapping.ttl", format="ttl")
#     query = """
#     PREFIX oscd: <https://w3id.org/OSCD#>
#     PREFIX rml: <http://semweb.mmlab.be/ns/rml#>
#     PREFIX rr: <http://www.w3.org/ns/r2rml#>
#     SELECT ?mappingGraph ?tripleMap ?source ?change ?reference ?changedData ?changesGraph
#     WHERE {
#       GRAPH ?changesGraph {
#         ?changeLog a oscd:ChangeLog;
#                 oscd:hasChange ?change;
#                 oscd:hasCurrentVersion ?currentVersion .
#         ?change oscd:hasDataReference ?reference;
#                 oscd:hasChangedData ?changedData .
#         BIND (REPLACE(STR(?currentVersion), "^.*/([^/]*)$", "$1") as ?source)
#       }
#       GRAPH ?mappingGraph {
#         ?tripleMap rml:logicalSource|rr:logicalTable ?logicalSource;
#                 rr:predicateObjectMap ?pom .
#         ?logicalSource rml:source|rr:tableName ?source .
#         ?pom rr:objectMap ?objectMap .
#         ?objectMap rml:reference|rr:column ?reference.
#       }
#     }
#     """
#     mapping_graph_id = 1
#     graph_name = URIRef("http://example.org/mapping-" + str(mapping_graph_id))
#     mapping_file = "/home/alex/MQI-Framework/static/uploads/sample_mapping10.ttl"
#     g = Graph().parse(mapping_file, format="ttl")
#     for s,p,o in g.triples((None, None, None)):
#         change_graph.add((s,p,o,graph_name))
#     change_graph.serialize(destination="test.trig", format="trig")
#     qres = change_graph.query(query)
#     matched_graphs = defaultdict(dict)
#     matched_graphs[mapping_graph_id] = defaultdict(dict)
#     matched_graphs[mapping_graph_id]["data_reference_changes"] = {
#         "insert": defaultdict(dict),
#         "delete": defaultdict(dict),
#     }
#     # data reference changes
#     current_data_reference_changes = matched_graphs[mapping_graph_id]["data_reference_changes"]
#     for row in qres:
#         data_reference = row["reference"]
#         changed_data = row["changedData"]
#         change_identifier = row["change"]
#         change_type = "insert"
#         if "delete" in change_identifier:
#             change_type = "delete"
#         if data_reference in current_data_reference_changes[change_type]:
#             current_data_reference_changes[change_type][data_reference].append(changed_data)
#         else:
#             current_data_reference_changes[change_type][data_reference] = [changed_data]
#     # add structural changes if theres match
#     # if current_data_reference_changes:
#     #     find_structural_changes(row["changesGraph"])
#     return qres
#
# def find_structural_changes(graph_name):
#     print(graph_name)
#     query = """
#         PREFIX oscd: <https://w3id.org/OSCD#>
#         PREFIX rml: <http://semweb.mmlab.be/ns/rml#>
#         PREFIX rr: <http://www.w3.org/ns/r2rml#>
#
#         SELECT ?referenceChanged ?dataChanged
#         WHERE {
#           GRAPH <%s> {
#             ?changeLog a oscd:ChangeLog;
#                     oscd:hasChange ?change .
#             ?change oscd:hasDataReference ?referenceChanged;
#                     oscd:hasChangedData ?dataChanged .
#
#             {
#               SELECT ?referenceChanged ?stucturalReference
#               WHERE {
#                 GRAPH <%s> {
#                   ?changeLog a oscd:ChangeLog;
#                           oscd:hasChange ?change .
#                   ?change oscd:hasStructuralReference ?stucturalReference;
#                           oscd:hasChangedData ?referenceChanged .
#
#                 }
#              }
#
#             }
#
#           }
#         }
#     """ % (graph_name, graph_name)
#     qres = change_graph.query(query)
#     print(query)
#     for row in qres:
#         print(row, "shshs")
#
# t = analyse_mappings()
#

