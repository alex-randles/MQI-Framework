# import modules.r2rml
from rdflib import *
from collections import defaultdict
import json
import rdflib


class DetectMappingImpact:

    def __init__(self, mapping_details, changes_file):
        print("detecting mapping impact.....")
        self.changes_graph = rdflib.ConjunctiveGraph()
        self.changes_graph.parse("./static/change_detection_cache/change_graphs/" + changes_file, format="trig")
        self.mapping_details = mapping_details
        self.mapping_impact = {
            "structural_changes":  defaultdict(dict),
            "data_reference_changes": defaultdict(dict),
        }
        self.get_data_reference_changes()
        self.get_structural_changes()
        print(json.dumps(self.mapping_impact, sort_keys = True, indent = 4))

    def get_data_reference_changes(self):
        mapping_references = ", ".join(["'{}'".format(reference) for reference in self.mapping_details.get("data_references")])
        query = """
            PREFIX oscd: <https://www.w3id.org/OSCD#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

            SELECT DISTINCT ?changesGraph ?source ?change ?reference ?changedData ?data
            WHERE {
              GRAPH ?changesGraph {    			 
                ?changeLog a oscd:ChangeLog;
                        oscd:hasChange ?change;
                        oscd:hasCurrentSource ?currentSource .
                ?change oscd:hasDataReference ?reference;
                        oscd:hasChangedData ?changedData .
                ?changedData rdfs:comment ?data . 
                FILTER (?reference IN (%s))
              }
            }
        """ % mapping_references
        query_results = self.changes_graph.query(query)
        mapping_impact_key = "data_reference_changes"
        self.mapping_impact[mapping_impact_key]["insert"] = defaultdict(dict)
        self.mapping_impact[mapping_impact_key]["delete"] = defaultdict(dict)
        for row in query_results:
            change_identifier = str(row.get("change"))
            data_reference = str(row.get("reference"))
            changed_data = str(row.get("data"))
            change_type = "insert" if "insert" in change_identifier else "delete"
            if data_reference not in self.mapping_impact[mapping_impact_key][change_type]:
                self.mapping_impact[mapping_impact_key][change_type][data_reference] = [changed_data]
            else:
                self.mapping_impact[mapping_impact_key][change_type][data_reference].append(changed_data)

    def get_structural_changes(self):
        query = """
            PREFIX oscd: <https://www.w3id.org/OSCD#> 
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?change ?data ?changedValue
            WHERE {
              
                  GRAPH ?changesGraph {    			 
                     ?changeLog1 a oscd:ChangeLog;
                             oscd:hasChange ?change1 .
                     ?change1 oscd:hasDataReference ?data ;
                              oscd:hasChangedData ?changedData1 .
                     ?changedData1 rdfs:comment ?changedValue . 
                            
                  {
                  SELECT ?data ?change
                  WHERE {
                          ?changeLog a oscd:ChangeLog;
                                     oscd:hasChange ?change;
                                     oscd:hasCurrentSource ?currentSource .
                          ?change oscd:hasStructuralReference ?reference;
                                  oscd:hasChangedData ?changedData .
                          ?changedData rdfs:comment ?data . 
                        }
                
                }
               }
            }
        """
        query_results = self.changes_graph.query(query)
        mapping_impact_key = "structural_changes"
        self.mapping_impact[mapping_impact_key] = {
            "insert": defaultdict(dict),
            "delete": defaultdict(dict),
        }
        for row in query_results:
            change_identifier = str(row.get("change"))
            data_reference = str(row.get("data"))
            changed_data = str(row.get("changedValue"))
            change_type = "insert" if "insert" in change_identifier else "delete"
            if data_reference not in self.mapping_impact[mapping_impact_key][change_type]:
                self.mapping_impact[mapping_impact_key][change_type][data_reference] = [changed_data]
            else:
                self.mapping_impact[mapping_impact_key][change_type][data_reference].append(changed_data)
        self.detect_move_change()

    def detect_move_change(self):
        query = """
            PREFIX oscd: <https://www.w3id.org/OSCD#> 
            SELECT ?newLocation
            WHERE {
              GRAPH ?changesGraph {
                ?changeLog a oscd:ChangeLog;
                           oscd:hasChange ?change .
                ?change a oscd:MoveSourceData ;
                        oscd:hasChangedData ?changedData .
                ?changedData oscd:hasNewLocation ?newLocation . 
              }
            }     
        """
        mapping_impact_key = "structural_changes"
        self.mapping_impact[mapping_impact_key]["move"] = defaultdict(dict)
        query_results = self.changes_graph.query(query)
        for row in query_results:
            new_location = str(row.get("newLocation"))
            self.mapping_impact[mapping_impact_key]["move"]["Moved to a new location"] = [new_location]

if __name__ == "__main__":
    mapping_graph = "/home/alex/MQI-Framework/static/uploads/mappings/sample_mapping26.ttl"
    changes_graph = "/home/alex/MQI-Framework/static/change_detection_cache/change_graphs/1.trig"
    DetectMappingImpact(mapping_graph, changes_graph)