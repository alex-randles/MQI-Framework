from rdflib import *
from collections import defaultdict
import os
import copy

class DetectChangeRelations:

    def __init__(self, user_id, change_graph_id, mapping_graph_name, session_id=None):
        mapping_graph_name = "document_mapping"
        self.session_id = session_id
        self.changed_columns = []
        self.user_id = user_id
        self.mapping_graph_name = mapping_graph_name
        self.change_graph_id = change_graph_id
        self.change_graph = Dataset()
        self.change_graph_file = "/home/alex/Desktop/Mapping-Quality-Framework/static/change_detection_cache/1/change_graphs/{}.trig".format(change_graph_id)
        self.change_graph_directory = "/home/alex/Desktop/Mapping-Quality-Framework/static/change_detection_cache/{}/change_graphs/".format(user_id)
        self.mapping_directory = "/home/alex/Desktop/Mapping-Quality-Framework/static/uploads/{}/".format(self.user_id)
        self.change_relations = defaultdict(dict)
        self.load_mapping_graphs()
        self.mapping_relations = self.get_change_relations()
        self.structural_relations = self.get_structure_changes()
        self.new_structure_values = self.get_new_structure_values()

    def get_structure_changes(self):
        g = ConjunctiveGraph()
        g.parse("test.trig", format="trig")
        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rml: <http://semweb.mmlab.be/ns/rml#>
        PREFIX r2rml: <http://www.w3.org/ns/r2rml#>
        PREFIX cdo: <https://change-detection-ontology.adaptcentre.ie/#>
        PREFIX ex: <http://www.example.com/>
        PREFIX ex-changes: <http://www.example.com/changesGraph/user/>
        PREFIX ex-intent: <https://data.example.com/intent/>
        PREFIX ex-action: <https://data.example.com/action/>
        PREFIX ex-action-effect: <https://data.example.com/actionEffect/>
        PREFIX ex-goal: <https://data.example.com/goal/>
        PREFIX ex-metric: <https://data.example.com/metric/>
        PREFIX ex-metric-query: <https://data.example.com/metricQuery/>
        PREFIX ex-result-set: <https://data.example.com/resultSet/>
        PREFIX ex-result: <https://data.example.com/result/>
        PREFIX : <https://ibclo.ericsson.com/#>
        PREFIX rr: <http://www.w3.org/ns/r2rml#>
        PREFIX rml: <http://semweb.mmlab.be/ns/rml#>
        PREFIX r2rml: <http://www.w3.org/ns/r2rml#>
        PREFIX cdo: <https://change-detection-ontology.adaptcentre.ie/#>
        PREFIX ex: <http://www.example.com/>
        PREFIX ex-changes: <http://www.example.com/changesGraph/user/>
        
        SELECT ?source ?reason ?changeType ?changeContent
        WHERE {
        
           GRAPH ?changeGraph
         {
            ?changeLog a cdo:ChangeLog;
            cdo:hasChange ?change;
            cdo:hasCurrentVersion ?currentVersion .
            ?change a ?changeType;
            cdo:hasReason ?reason.
        
         }
         GRAPH ex:%s
         { 
            ?tripleMap rml:logicalSource|rr:logicalTable ?logicalSource. 
            ?logicalSource rml:source|rr:tableName ?source .
         }
          BIND (REPLACE(STR(?currentVersion), "^.*/([^/]*)$", "$1") as ?changesFileName)
          FILTER(?source = ?changesFileName)
          BIND (STRBEFORE(?reason, ":") AS ?changeReference)
          BIND (STRAFTER(?reason, ":") AS ?changeContent)
          FILTER(STRSTARTS(?changeReference, "Column"))
        }   
        """ % self.mapping_graph_name
        qres = g.query(query)
        change_relations = defaultdict(dict)
        for row in qres:
            source = str(row["source"])
            change_type = str(row["changeType"])
            reason = str(row["changeContent"]).strip()
            change_names = {
                "https://change-detection-ontology.adaptcentre.ie/#InsertSourceData" : "insert",
                "https://change-detection-ontology.adaptcentre.ie/#DeleteSourceData" : "delete",
            }
            name = change_names.get(str(change_type))
            self.changed_columns.append(str(row["changeContent"]).strip())
            if source not in change_relations.keys():
                change_relations[source] = defaultdict(dict)
            if name not in change_relations[source].keys():
                change_relations[source][name] = defaultdict(dict)
                change_relations[source][name][reason] = []
            else:
                change_relations[source][name][reason] = []
        # self.changed_columns = list(set(self.changed_columns))
        return change_relations

        # find the relationship between changes references and mappings
    def get_new_structure_values(self):
        print("Getting change relations")
        g = ConjunctiveGraph()
        g.parse("test.trig", format="trig")
        query = """
            PREFIX cdo: <https://change-detection-ontology.adaptcentre.ie/#>
            
            SELECT ?changeReference ?changeContent ?changeType
            WHERE {
              GRAPH ?changeGraph {
                ?changeLog a cdo:ChangeLog;
                           cdo:hasChange ?change .
                ?change a ?changeType; 
                        cdo:hasReason ?reason .
              }
              BIND (STRAFTER(?reason, ":") AS ?changeContent)
              BIND (STRBEFORE(?reason, ":") AS ?changeReference)
              FILTER(?changeReference IN %s)
            }
        """ % str(tuple(self.changed_columns))
        qres = g.query(query)
        for row in qres:
            column = str(row["changeReference"])
            new_column_data = str(row["changeContent"]).strip()
            if column in self.structural_relations["student.csv"]["insert"].keys():
                self.structural_relations["student.csv"]["insert"][column].append(new_column_data)
            else:
                self.structural_relations["student.csv"]["delete"][column].append(new_column_data)
            # if column.strip() in self.structural_relations
        print(self.structural_relations)
        return self.structural_relations

    # find the relationship between changes references and mappings
    def get_change_relations(self):
        print("Getting change relations")
        g = ConjunctiveGraph()
        g.parse("test.trig", format="trig")
        query = """
			PREFIX rml: <http://semweb.mmlab.be/ns/rml#>
			PREFIX r2rml: <http://www.w3.org/ns/r2rml#>
			PREFIX cdo: <https://change-detection-ontology.adaptcentre.ie/#>
			PREFIX ex: <http://www.example.com/>
			PREFIX ex-changes: <http://www.example.com/changesGraph/user/>
			PREFIX ex-intent: <https://data.example.com/intent/>
			PREFIX ex-action: <https://data.example.com/action/>
			PREFIX ex-action-effect: <https://data.example.com/actionEffect/>
			PREFIX ex-goal: <https://data.example.com/goal/>
			PREFIX ex-metric: <https://data.example.com/metric/>
			PREFIX ex-metric-query: <https://data.example.com/metricQuery/>
			PREFIX ex-result-set: <https://data.example.com/resultSet/>
			PREFIX ex-result: <https://data.example.com/result/>
			PREFIX : <https://ibclo.ericsson.com/#>
			PREFIX rr: <http://www.w3.org/ns/r2rml#>
			PREFIX rml: <http://semweb.mmlab.be/ns/rml#>
			PREFIX r2rml: <http://www.w3.org/ns/r2rml#>
			PREFIX cdo: <https://change-detection-ontology.adaptcentre.ie/#>
			PREFIX ex: <http://www.example.com/>
			PREFIX ex-changes: <http://www.example.com/changesGraph/user/>

			SELECT ?mappingGraph ?source ?changeType ?changeReference ?changeContent
			WHERE {

			  GRAPH ?changeGraph
			  {
				?changeLog a cdo:ChangeLog;
						   cdo:hasChange ?change;
						   cdo:hasCurrentVersion ?currentVersion .
				?change a ?changeType;
						cdo:hasReason ?reason.

			  }
			  BIND (STRBEFORE(?reason, ":") AS ?changeReference)
			  BIND (STRAFTER(?reason, ":") AS ?changeContent)
			  GRAPH ex:%s
			  {
				?tripleMap rml:logicalSource|rr:logicalTable ?logicalSource;
											rr:predicateObjectMap ?pom .
				?logicalSource 	rml:source|rr:tableName ?source .
				?pom rr:objectMap ?objectMap .
				?objectMap  rml:reference|rr:column ?changeReference.
			  }
			}
		""" % self.mapping_graph_name
        qres = g.query(query)
        # output to html template
        change_relations = defaultdict(dict)
        for row in qres:
            print(row)
            source = str(row["source"])
            change_type = str(row["changeType"])
            change_names = {
                "https://change-detection-ontology.adaptcentre.ie/#InsertSourceData" : "insert",
                "https://change-detection-ontology.adaptcentre.ie/#DeleteSourceData" : "delete",
            }
            name = change_names.get(str(change_type))
            data_reference = str(row["changeReference"])
            reason = str(row["changeContent"])
            if data_reference not in change_relations[source].keys():
                change_relations[source][data_reference] = defaultdict(dict)
            if name not in change_relations[source][data_reference].keys():
                    change_relations[source][data_reference][name] = [reason]
            else:
                    change_relations[source][data_reference][name].append(reason)
        return change_relations

    # creates a graph including changes and mappings as named graphs
    def load_mapping_graphs(self):
        mapping_directory = os.fsencode(self.mapping_directory)
        change_graph_directory = os.fsencode(self.change_graph_directory)
        # for change_graph_file in os.listdir(change_graph_directory):
        #     # create named graphs from the change graph file
        #     filename = os.fsdecode(change_graph_file)
        #     graph_name = filename.split(".")[0]
        #     graph_full_path = self.change_graph_directory + filename
        #     g = self.change_graph.graph(URIRef('http://www.example.com/' + graph_name))
        #     g.parse(graph_full_path, format="trig")
        #     print(graph_full_path)
        #     # iterate each mapping the user has u`ploaded
        self.change_graph.parse(self.change_graph_file, format="trig")
        for mapping_file in os.listdir(mapping_directory):
                filename = os.fsdecode(mapping_file)
                # mapping_graph = Graph()
                graph_name = filename.split(".")[0]
                graph_full_path = self.mapping_directory + filename
                g = self.change_graph.graph(URIRef('http://www.example.com/' + graph_name))
                g.parse(graph_full_path, format="ttl")
        # self.change_graph.serialize(destination="test.trig", format="trig")

if __name__ == "__main__":
    user_id = 1
    graph_id = 1
    DetectChangeRelations(user_id, graph_id, "document_mapping")