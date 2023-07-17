from collections import defaultdict
import json
import rdflib
import re
from modules.serialize import TurtleSerializer


class DetectMappingImpact:

    def __init__(self, user_id, mapping_details, changes_file):
        print("detecting mapping impact.....")
        self.user_id = user_id
        self.changes_graph = rdflib.ConjunctiveGraph()
        self.changes_graph.parse(f"./static/user_files/change_graphs/{user_id}/{changes_file}", format="trig")
        self.mapping_details = mapping_details
        self.mapping_impact = {
            "structural_changes":  defaultdict(dict),
            "data_reference_changes": defaultdict(dict),
        }
        self.get_data_reference_changes()
        self.get_structural_changes()
        print(json.dumps(self.mapping_impact, sort_keys=True, indent=4))
        self.change_template_colors, self.change_type_banners = self.return_banners()

    @staticmethod
    def return_banners():
        change_template_colors = {
                "insert": "success",
                "delete": "danger",
                "move": "primary",
            }

        change_type_banners = {
                "insert": "Column inserted",
                "delete": "Column deleted",
                "move": "Source data moved",
        }
        return change_template_colors, change_type_banners

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

    @staticmethod
    def sort_blank_nodes(blank_nodes_values):
        # A function to order the blank nodes for preserving mapping layout
        add_identifier = [(blank_node, DetectMappingImpact.find_identifier(blank_node)) for blank_node in blank_nodes_values]
        sorted_blank_node = sorted(add_identifier, key=lambda x: x[1])
        remove_identifier = [blank_node for (blank_node, _) in sorted_blank_node]
        return remove_identifier

    @staticmethod
    def order_triple_maps_triples(triple_references, mapping_graph):
        # will order triples based on the blank node identifier assigned
        for (triple_map, values) in triple_references.items():
            for (predicate, blank_nodes) in values.items():
                if predicate != "not_blank_node":
                    sorted_blank_nodes = DetectMappingImpact.sort_blank_nodes(blank_nodes)
                    triple_references[triple_map][rdflib.term.URIRef(predicate)] = sorted_blank_nodes
        return triple_references

    @staticmethod
    def create_triple_references(mapping_graph):
        triple_map_triples = DetectMappingImpact.assign_triples_to_each_map(mapping_graph)
        triple_references = DetectMappingImpact.order_triple_maps_triples(triple_map_triples, mapping_graph)
        return triple_references

    @staticmethod
    def assign_triples_to_each_map(mapping_graph):
        # returns a dic with the triple map as key and the triples within that triple map as values
        triple_maps_identifier = DetectMappingImpact.get_triple_maps_identifier(mapping_graph)
        # iterate each triple map and find triples which have blank nodes
        triple_map_triples = {}
        for IRI in triple_maps_identifier:
            # empty dictionary assign triples to this triple map
            triple_map_triples[IRI] = {}
            for (s, p, o) in mapping_graph.triples((IRI, None, None)):
                # if object is blank node such as rr:logicalTable relate that property to the blank node
                if isinstance(o, rdflib.term.BNode):
                    if p in triple_map_triples[IRI].keys():
                        triple_map_triples[IRI][p].append(o)
                    else:
                        triple_map_triples[IRI][p] = [o]
                else:
                    # for values not relating to blank nodes such as #ORGANISATIONOFOFFICE rr:predicate foaf:Agent
                    not_blank_node_key = "not_blank_node"
                    if not_blank_node_key in triple_map_triples[IRI].keys():
                        triple_map_triples[IRI][not_blank_node_key].append((p, o))
                    else:
                        triple_map_triples[IRI][not_blank_node_key] = [(p, o)]
        return triple_map_triples

    @staticmethod
    def get_triple_maps_identifier(mapping_graph):
        triple_maps = []
        for (s, p, o) in mapping_graph.triples((None, None, None)):
            if not isinstance(s, rdflib.term.BNode):
                if s not in triple_maps:
                    triple_maps.append(s)
        return triple_maps

    @staticmethod
    def find_identifier(node_value):
        regex = re.search('L(.+?)C', node_value)
        if regex:
            match = regex.group(1)
            return int(match)
        return int(0)

    @staticmethod
    def serialize(mapping_graph, triple_references):
        TurtleSerializer(mapping_graph, triple_references, "refined_mapping.ttl")

    @staticmethod
    def update_impacted_mapping(user_id, request_data, mapping_file_name):
        new_data_reference = request_data.get("new_reference").split("-")[0]
        old_data_reference = request_data.get("new_reference").split("-")[1]
        update_query = """
                PREFIX rr: <http://www.w3.org/ns/r2rml#> 
                PREFIX rml: <http://semweb.mmlab.be/ns/rml#> 
                DELETE { ?subject ?predicate ?object }
                INSERT { ?subject ?predicate '%s' }
                WHERE { 
                SELECT ?subject ?predicate ?object 
                WHERE {
                      ?subject ?predicate ?object .
    
                      FILTER (?predicate IN (rml:reference, rr:column))
                      FILTER ('%s' = LCASE(?object))
                    }
                }
               """ % (new_data_reference, old_data_reference.lower())
        print(update_query)
        mapping_file_path = f"./static/user_files/mappings/{user_id}/{mapping_file_name}"
        current_graph = rdflib.Graph().parse(mapping_file_path, format="ttl")
        triple_references = DetectMappingImpact.create_triple_references(current_graph)
        print("triple references.....", triple_references)
        rdflib.plugins.sparql.processUpdate(current_graph, update_query)
        TurtleSerializer(current_graph, triple_references, mapping_file_path)
        # mapping_graph.serialize(destination=mapping_file_path, format="ttl")


if __name__ == "__main__":
    mapping_graph = "/home/alex/MQI-Framework/static/uploads/mappings/sample_mapping26.ttl"
    changes_graph = "/home/alex/MQI-Framework/static/change_detection_cache/change_graphs/1.trig"
    DetectMappingImpact(mapping_graph, changes_graph)