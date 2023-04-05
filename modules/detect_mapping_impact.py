# import modules.r2rml
from rdflib import *
from collections import defaultdict
import json

class DetectMappingImpact:

    def __init__(self, mapping_details, changes_file):
        self.changes_graph = ConjunctiveGraph()
        self.changes_graph.parse("./static/change_detection_cache/change_graphs/" + changes_file, format="trig")
        self.mapping_details = mapping_details
        mapping_file = mapping_details.get("filename")
        mapping_graph_identifier = URIRef("http://www.example.com/mappingGraph/" + mapping_file)
        mapping_graph = Graph().parse("./static/uploads/mappings/" + mapping_file, format="ttl")
        for s, p, o in mapping_graph.triples((None, None, None)):
            self.changes_graph.add((s,p,o, mapping_graph_identifier))
        self.changes_graph.serialize(destination="test.trig", format="trig")
        self.mapping_impact = defaultdict(dict)
        self.get_data_reference_changes()
        self.get_structural_changes()
        print(json.dumps(self.mapping_impact, sort_keys = True, indent = 4))

    def get_data_reference_changes(self):
        mapping_references = ["'item_id'", "'name'", "'price'"]
        query = """
            PREFIX oscd: <https://w3id.org/OSCD#>
            PREFIX rml: <http://semweb.mmlab.be/ns/rml#>
            PREFIX rr: <http://www.w3.org/ns/r2rml#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

            SELECT DISTINCT ?changesGraph ?source ?change ?reference ?changedData ?data
            WHERE {
              GRAPH ?changesGraph {    			 
                ?changeLog a oscd:ChangeLog;
                        oscd:hasChange ?change;
                        oscd:hasCurrentVersion ?currentVersion .
                ?change oscd:hasDataReference ?reference;
                        oscd:hasChangedData ?changedData .
                ?changedData rdfs:comment ?data . 
                FILTER (?reference IN (%s))
              }
            }
        """ % ", ".join(mapping_references)
        qres = self.changes_graph.query(query)
        mapping_impact_key = "data_reference_changes"
        self.mapping_impact[mapping_impact_key] = defaultdict(dict)
        self.mapping_impact[mapping_impact_key]["insert"] = defaultdict(dict)
        self.mapping_impact[mapping_impact_key]["delete"] = defaultdict(dict)
        for row in qres:
            change_identifier = str(row.get("change"))
            data_reference = str(row.get("reference"))
            changed_data = str(row.get("data"))
            change_type = self.get_change_type(change_identifier)
            if data_reference not in self.mapping_impact[mapping_impact_key][change_type]:
                self.mapping_impact[mapping_impact_key][change_type][data_reference] = [changed_data]
            else:
                self.mapping_impact[mapping_impact_key][change_type][data_reference].append(changed_data)

    def get_structural_changes(self):
        mapping_references = ["'item_id'", "'name'", "'price'"]
        query = """
            PREFIX oscd: <https://w3id.org/OSCD#>
            PREFIX rml: <http://semweb.mmlab.be/ns/rml#>
            PREFIX rr: <http://www.w3.org/ns/r2rml#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

            SELECT DISTINCT ?changesGraph ?source ?change ?reference ?changedData ?data
            WHERE {
              GRAPH ?changesGraph {    			 
                ?changeLog a oscd:ChangeLog;
                        oscd:hasChange ?change;
                        oscd:hasCurrentVersion ?currentVersion .
                ?change oscd:hasDataReference ?reference;
                        oscd:hasChangedData ?changedData .
                ?changedData rdfs:comment ?data . 
                FILTER (?reference NOT IN (%s))
              }
            }
        """ % ", ".join(mapping_references)
        qres = self.changes_graph.query(query)
        mapping_impact_key = "structural_changes"
        self.mapping_impact[mapping_impact_key] = defaultdict(dict)
        self.mapping_impact[mapping_impact_key]["insert"] = defaultdict(dict)
        self.mapping_impact[mapping_impact_key]["delete"] = defaultdict(dict)
        for row in qres:
            change_identifier = str(row.get("change"))
            data_reference = str(row.get("reference"))
            changed_data = str(row.get("data"))
            change_type = self.get_change_type(change_identifier)
            if data_reference not in self.mapping_impact[mapping_impact_key][change_type]:
                self.mapping_impact[mapping_impact_key][change_type][data_reference] = [changed_data]
            else:
                self.mapping_impact[mapping_impact_key][change_type][data_reference].append(changed_data)

    def get_change_type(self, change_identifier):
        if "insert" in change_identifier:
            return "insert"
        else:
            return "delete"


if __name__ == "__main__":
    mapping_graph = "/home/alex/MQI-Framework/static/uploads/mappings/sample_mapping26.ttl"
    changes_graph = "/home/alex/MQI-Framework/static/change_detection_cache/change_graphs/1.trig"
    DetectMappingImpact(mapping_graph, changes_graph)