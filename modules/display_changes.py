# class which displays the change detection processes being run by a user
from rdflib import *
import rdflib
import os
import re
from collections import defaultdict
from modules.r2rml import *
import modules.r2rml as r2rml
class DisplayChanges:

    def __init__(self, user_id, testing=False):
        # user graph files naming convention
        # user_1-2.trig
        self.user_id = 1
        self.graph_directory = graph_directory
        self.mappings_directory = upload_directory
        # stores graph currently being queried
        self.current_graph = None
        # stores version of graph being queried
        self.current_graph_version = None
        self.graph_details = defaultdict(dict)
        self.mapping_details = defaultdict(dict)
        self.complete_graph = rdflib.ConjunctiveGraph()
        # error code
        # no error = 0
        self.error_code = 0
        self.generate_display_information()
        self.analyse_mapping_impact()

    def analyse_mapping_impact(self):
        for change_graph, changed_values in self.graph_details.items():
            # split which fails?
            if changed_values:
                source_versions = changed_values.get("change_sources")
                if source_versions:
                    change_graph_sources = [changed_values.get("change_sources").get("previous_version").split("/")[-1], changed_values.get("change_sources").get("current_version").split("/")[-1]]
                    for change_source in change_graph_sources:
                        for mapping_graph, mapping_values in self.mapping_details.items():
                            mapping_sources = mapping_values.get("source_data")
                            if change_source in mapping_sources:
                                if "impacts_mapping" not in self.graph_details[change_graph].keys():
                                    self.graph_details[change_graph]["impacts_mapping"] = [mapping_graph]
                                else:
                                    self.graph_details[change_graph]["impacts_mapping"].append(mapping_graph)

    def get_mapping_identifier(self, mapping_filename):
        mapping_identifier = [key for key, values in self.mapping_details.items() if values["filename"] == mapping_filename.strip()]
        # print(mapping_filename, mapping_identifier, self.mapping_details)
        return mapping_identifier

    # generate information to display graph information
    def generate_display_information(self):
        # try:
        self.iterate_mappings()
        self.iterate_changes_graphs()
        # self.analyse_mappings()
        # except Exception as exception:
        #     # general exception
        #     print("CHANGE DETECTION EXCEPTION", exception)
        #     self.error_code = 1

    def get_changes_count(self):
        # query to get notification thresholds
        query = """
            PREFIX oscd: <https://www.w3id.org/OSCD#>
            
            # GET COUNT FOR EACH CHANGE TYPE
            SELECT ?changeType (COUNT(?change) AS ?count)
            WHERE
            {
              # QUERY USER GRAPH
              GRAPH ?g {
                # GET EACH CHANGE FROM LOG
                ?changeLog a oscd:ChangeLog ;
                           oscd:hasChange ?change.
                ?change a ?changeType . 
              }
            }
            GROUP BY ?changeType
        """
        query_results = self.current_graph.query(query)
        # count of each change type within graph
        change_count = 0
        for (change_type, count) in query_results:
            change_count += count.value
        self.graph_details[self.current_graph_version]["change_count"] = change_count
        return change_count

    def iterate_changes_graphs(self):
        directory = os.fsencode(self.graph_directory)
        for file in os.listdir(directory):
            filename = os.fsdecode(file)
            self.current_graph_version = int(filename.split(".")[0])
            self.graph_details[self.current_graph_version] = {}
            self.graph_details[self.current_graph_version]["filename"] = filename
            # user_graph_file
            print(filename)
            user_graph_file = self.graph_directory + filename
            # set current graph
            self.current_graph = rdflib.Dataset()
            self.current_graph.parse(user_graph_file, format="trig")
            self.get_graph_details()
        print(self.graph_details)

    def iterate_mappings(self):
        directory = os.fsencode(self.mappings_directory)
        self.current_graph_version = 1
        for file in os.listdir(directory):
            try:
                filename = os.fsdecode(file)
                # get user ID from file
                # graph version e.g version 1 user_1-1.trig
                # graph_version = filename.split("_")[-1].split("-")[1].split(".")[0]
                self.mapping_details[self.current_graph_version] = {}
                # create dictionary to store version details
                self.mapping_details[self.current_graph_version]["filename"] = filename
                self.mapping_details[self.current_graph_version]["display_filename"] = filename
                user_graph_file = self.mappings_directory + filename
                # set current graph
                self.current_graph = rdflib.Graph()
                self.current_graph.parse(user_graph_file, format="ttl")
                self.get_mappings_details()
                self.current_graph_version += 1
            except rdflib.plugins.parsers.notation3.BadSyntax as e:
                pass

    def get_graph_details(self):
        # get details from change graphs
        self.get_detection_period()
        self.get_changes_count()
        self.get_change_reasons()
        self.get_changes_source()
        self.get_data_format()

    def get_mappings_details(self):
        # get details from mappings
        self.get_table_name()
        self.get_iterator()
        self.get_mapping_references()
        print(self.mapping_details)

    # take graph filename and generate a dictionary to display threshold information
    @staticmethod
    def generate_thresholds_html(graph_filename, user_id):
        graph_filename = r2rml.graph_directory + graph_filename
        change_graph = rdflib.Dataset()
        change_graph.parse(graph_filename, format="trig")
        query = """
            PREFIX oscd: <https://www.w3id.org/OSCD#>
            PREFIX rei-constraint: <http://www.cs.umbc.edu/~lkagal1/rei/ontologies/ReiConstraint.owl#>
            SELECT ?changeType ?threshold 
            WHERE
            {
              # QUERY NOTIFICATION GRAPH
              GRAPH ?g  {
                ?constraint a rei-constraint:SimpleConstraint; 
                            rei-constraint:subject ?changeType; 
                            rei-constraint:object ?threshold . 
              }
            }
            """
        query_results = change_graph.query(query)
        # change type human readable
        oscd_namespace = "https://www.w3id.org/OSCD#"
        change_types = {
            oscd_namespace + 'DatatypeSourceData': "Datatype Change",
            oscd_namespace + 'MoveSourceData': "Move Change",
            oscd_namespace + 'DeleteSourceData': "Delete Change",
            oscd_namespace + 'UpdateSourceData': "Update Change",
            oscd_namespace + 'MergeSourceData': "Merge Change",
            oscd_namespace + 'InsertSourceData': "Insert Change",
        }
        # dictionary that maps change type to notification threshold
        notification_thresholds = {}
        total_threshold_count = 0
        for row in query_results:
            total_threshold_count += int(row[1])
            notification_thresholds[change_types.get(str(row[0]))] = str(row[1])
        notification_thresholds["Total Count"] = total_threshold_count
        return notification_thresholds

    def get_detection_period(self):
        # get detection time for notification policy to check if still valid
        query = """
        PREFIX oscd: <https://www.w3id.org/OSCD#>
        PREFIX rei-policy: <http://www.cs.umbc.edu/~lkagal1/rei/ontologies/ReiPolicy.owl#>
        SELECT ?detectionStart ?detectionEnd
        WHERE
        {
          GRAPH ?g  {
            ?policy a rei-policy:Policy ;
                    oscd:hasDetectionEnd ?detectionEnd; 
                    oscd:hasDetectionStart ?detectionStart .
          }
        }
        """
        query_results = self.current_graph.query(query)
        for row in query_results:
            detection_start = str(row.get("detectionStart")).split(" ")[0]
            detection_end = str(row.get("detectionEnd")).split(" ")[0]
            self.graph_details[self.current_graph_version]["detection_start"] = detection_start
            self.graph_details[self.current_graph_version]["detection_end"] = detection_end
        self.graph_details[self.current_graph_version]["mappings_impacted"] = {"references_impacted": {}}

    def get_table_name(self):
        # get detection time for notification policy to check if still valid
        query = """
            PREFIX rr: <http://www.w3.org/ns/r2rml#> 
            PREFIX rml: <http://semweb.mmlab.be/ns/rml#> 
            SELECT DISTINCT ?sourceData
            WHERE
            {
                ?subject rr:tableName|rml:source ?sourceData
            }
        """
        query_results = self.current_graph.query(query)
        # lists as could be more than 1 triple map
        source_data = []
        for row in query_results:
            source_data.append(str(row.get("sourceData")))
        if source_data:
            self.mapping_details[self.current_graph_version]["source_data"] = source_data
        else:
            self.extract_sql_query()

    def extract_sql_query(self):
        query = """
            PREFIX rr: <http://www.w3.org/ns/r2rml#> 
            PREFIX rml: <http://semweb.mmlab.be/ns/rml#> 
            SELECT DISTINCT ?sourceData
            WHERE
            {
                ?subject rr:sqlQuery ?sourceData
            }
        """
        query_results = self.current_graph.query(query)
        source_data = []
        for row in query_results:
            sql_query = str(row.get("sourceData")).split()
            if "FROM" in sql_query:
                source_data.append(sql_query[sql_query.index("FROM") + 1])
        self.mapping_details[self.current_graph_version]["source_data"] = list(set(source_data))

    def get_iterator(self):
        # get detection time for notification policy to check if still valid
        query = """
            PREFIX rr: <http://www.w3.org/ns/r2rml#> 
            PREFIX rml: <http://semweb.mmlab.be/ns/rml#> 
            SELECT DISTINCT ?iterator
            WHERE
            {
              ?subject rml:iterator ?iterator
            }
        """
        query_results = self.current_graph.query(query)
        # lists as could be more than 1 triple map
        iterator = []
        for row in query_results:
            iterator.append(str(row.get("iterator")))
        if iterator:
            self.mapping_details[self.current_graph_version]["iterators"] = iterator

    def get_mapping_references(self):
        # template values or direct references
        direct_references = self.get_mapping_direct_references()
        template_references = self.get_mapping_template_references()
        # add references from both
        combined_references = direct_references + template_references
        # remove duplicates
        combined_references = list(set(combined_references))
        self.mapping_details[self.current_graph_version]["data_references"] = combined_references

    def get_mapping_direct_references(self):
        # get references from column or attribute names
        query = """
            PREFIX rr: <http://www.w3.org/ns/r2rml#> 
            PREFIX rml: <http://semweb.mmlab.be/ns/rml#> 
            SELECT DISTINCT ?dataReference
            WHERE
            {
                ?subject rml:reference|rr:column ?dataReference
            }
        """
        query_results = self.current_graph.query(query)
        references = []
        for row in query_results:
            reference = row.get("dataReference")
            references.append(str(reference))
        return references

    def get_mapping_template_references(self):
        # get template values as well
        query = """
            PREFIX rr: <http://www.w3.org/ns/r2rml#> 
            PREFIX rml: <http://semweb.mmlab.be/ns/rml#> 
            SELECT DISTINCT ?template
            WHERE
            {
                 ?subject rr:template ?template
            }
        """
        query_results = self.current_graph.query(query)
        references = []
        for row in query_results:
            template = str(row.get("template"))
            reference = re.findall('{(.+?)}', template)
            # findall returns list so need to use extend
            references.extend(reference)
        return references

    def get_change_reasons(self):
        # get the reasons for changes occurring
        query = """
            PREFIX oscd: <https://w3id.org/OSCD/#>
            # GET REASON FOR CHANGE OCCURING AND REMOVE UNNEEDED INFORMATION
            SELECT (strbefore(?changeReason,':') as ?reason) ?changeReason ?changeType 
            WHERE
            {
              # QUERY USER GRAPH
              GRAPH ?g {
                ?changeLog a oscd:ChangeLog;
                           oscd:hasChange ?change .
                ?change oscd:hasChangedData ?changeReason;
                        a ?changeType .
              }
            }
        """
        query_results = self.current_graph.query(query)
        change_reasons = {}
        counter = 0
        # full and short text for displaying and matching
        for row in query_results:
            change_reasons[counter] = {
                "match_reason": str(row.get("reason")),
                "reason": str(row.get("changeReason")),
                "change_type": str(row.get("changeType")),

            }
            counter += 1
        self.graph_details[self.current_graph_version]["change_reasons"] = change_reasons

    def get_changes_source(self):
        # get the reasons for changes occurring
        query = """
        PREFIX changes-graph: <http://www.example.com/changesGraph/user/>
        PREFIX notification-graph: <http://www.example.com/notificationGraph/user/>
        PREFIX contact-graph: <http://www.example.com/contactDetailsGraph/user/>
        PREFIX oscd: <https://www.w3id.org/OSCD#>
        PREFIX rei-constraint: <http://www.cs.umbc.edu/~lkagal1/rei/ontologies/ReiConstraint.owl#>
        PREFIX rei-policy: <http://www.cs.umbc.edu/~lkagal1/rei/ontologies/ReiPolicy.owl#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX rr: <http://www.w3.org/ns/r2rml#> 
        PREFIX rml: <http://semweb.mmlab.be/ns/rml#> 
        # GET XML FILE DETAILS FROM CHANGE GRAPH 
        SELECT ?currentVersion ?previousVersion
        WHERE
        {
          # QUERY USER GRAPH
          GRAPH ?g {
            ?changeLog a oscd:ChangeLog; 
                       oscd:hasCurrentVersion ?currentVersion ;
                       oscd:hasPreviousVersion ?previousVersion . 
          }
        }
        """
        query_results = self.current_graph.query(query)
        change_sources = {}
        # convert to lower case
        for row in query_results:
            change_sources["current_version"] = str(row.get("currentVersion"))
            change_sources["previous_version"] = str(row.get("previousVersion"))
        if change_sources:
            self.graph_details[self.current_graph_version]["change_sources"] = change_sources

    def get_data_format(self):
        # get format of data e.g CSV, XML
        change_sources = self.graph_details[self.current_graph_version].get("change_sources")
        if change_sources:
            first_source = list(change_sources.values())[0]
            data_format = first_source.split(".")[-1]
            self.graph_details[self.current_graph_version]["data_format"] = data_format


if __name__ == "__main__":
    # DisplayChanges.generate_thresholds_html("user_1-1.trig")
    DisplayChanges("1", testing=True)