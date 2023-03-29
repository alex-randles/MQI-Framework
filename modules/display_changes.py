# class which displays the change detection processes being run by a user
from rdflib import *
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
        self.graph_details = {}
        self.mapping_details = {}
        # error code
        # no error = 0
        self.error_code = 0
        self.generate_display_information()

    # generate information to display graph information
    def generate_display_information(self):
        # try:
        self.iterate_changes_graphs()
        self.iterate_mappings()
        self.analyse_mappings()
        # except Exception as exception:
        #     # general exception
        #     print("CHANGE DETECTION EXCEPTION", exception)
        #     self.error_code = 1

    def get_changes_count(self):
        # query to get notification thresholds
        query = """
            PREFIX oscd: <https://w3id.org/OSCD#>
            
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

        qres = self.current_graph.query(query)
        # count of each change type within graph
        change_count = 0
        for (change_type, count) in qres:
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
            self.current_graph = Dataset()
            self.current_graph.parse(user_graph_file, format="trig")
            self.get_graph_details()
        print(self.graph_details)

    def iterate_mappings(self):
        directory = os.fsencode(self.mappings_directory)
        self.current_graph_version = 1
        for file in os.listdir(directory):
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
            self.current_graph = Graph()
            self.current_graph.parse(user_graph_file, format="ttl")
            self.get_mappings_details()
            self.current_graph_version += 1

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

    # take graph filename and generate a dictionary to display threshold information
    @staticmethod
    def generate_thresholds_html(graph_filename, user_id):
        graph_filename = r2rml.graph_directory + graph_filename
        change_graph = Dataset()
        change_graph.parse(graph_filename, format="trig")
        query = """
            PREFIX oscd: <https://w3id.org/OSCD#>
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
        qres = change_graph.query(query)
        # change type human readable
        oscd_namespace = "https://w3id.org/OSCD#"
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
        for row in qres:
            total_threshold_count += int(row[1])
            notification_thresholds[change_types.get(str(row[0]))] = str(row[1])
        notification_thresholds["Total Count"] = total_threshold_count
        return notification_thresholds

    def get_detection_period(self):
        # get detection time for notification policy to check if still valid
        query = """
        PREFIX oscd: <https://w3id.org/OSCD/#>
        PREFIX rei-policy: <http://www.cs.umbc.edu/~lkagal1/rei/ontologies/ReiPolicy.owl#>
        SELECT ?detectionStart ?detectionEnd 
        WHERE
        {
          # QUERY NOTIFICATION GRAPH
          GRAPH ?g  {
            # GET DETECTION PERIOD END
            ?policy a rei-policy:Policy ;
                    oscd:hasDetectionEnd ?detectionEnd; 
                    oscd:hasDetectionStart ?detectionStart . 
          }
        }

        """
        qres = self.current_graph.query(query)
        for row in qres:
            detection_start = str(row[0]).split(" ")[0]
            detection_end = str(row[1]).split(" ")[0]
            self.graph_details[self.current_graph_version]["detection_start"] = detection_start
            self.graph_details[self.current_graph_version]["detection_end"] = detection_end

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
        qres = self.current_graph.query(query)
        # lists as could be more than 1 triple map
        source_data = []
        for row in qres:
            source_data.append(str(row[0]))
        self.mapping_details[self.current_graph_version]["source_data"] = source_data

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
        qres = self.current_graph.query(query)
        # lists as could be more than 1 triple map
        iterator = []
        for row in qres:
            iterator.append(str(row[0]))
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
        qres = self.current_graph.query(query)
        references = []
        for row in qres:
            reference = row[0]
            references.append(str(reference))
        return references

    def get_mapping_template_references(self):
        # get template values as well
        query = """
            PREFIX rr: <http://www.w3.org/ns/r2rml#> 
            PREFIX rml: <http://semweb.mmlab.be/ns/rml#> 
            SELECT DISTINCT ?dataReference
            WHERE
            {
                      ?subject rr:template ?dataReference
            }
        """
        qres = self.current_graph.query(query)
        references = []
        for row in qres:
            template = row[0]
            str_template = str(template)
            reference = re.findall('{(.+?)}', str_template)
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
        qres = self.current_graph.query(query)
        change_reasons = ["name"]
        change_reasons = {}
        i = 0
        # full and short text for displaying and matching
        for row in qres:
            change_reasons[i] = {
                "match_reason": str(row[0]),
                "reason": str(row[1]),
                "change_type": str(row[2]),

            }
            i += 1
        self.graph_details[self.current_graph_version]["change_reasons"] = change_reasons

    def analyse_mappings(self):
        # function to find which mappings are effected by changes
        # match data references to mapping references
        for graph_id, graph_details in self.graph_details.items():
            self.graph_details[graph_id]["mappings_impacted"] = {
                "references_impacted" : defaultdict(list),
                "sources_impacted" : defaultdict(list),
            }
        # return
        # for graph_id, graph_details in self.graph_details.items():
        #     change_reasons = graph_details["change_reasons"]
        #     for mapping_id, mapping_details in self.mapping_details.items():
        #         # compare sources to file names
        #         if "change_sources" in graph_details.keys():
        #             data_sources = graph_details["change_sources"].values()
        #             # compare change reasons and data references
        #             mapping_data_references = mapping_details["data_references"]
        #             mapping_data_sources = mapping_details["source_data"]
        #             for mapping_source in mapping_data_sources:
        #                 # match regardless of case
        #                 matching_data_sources = [source.lower() for source in data_sources]
        #                 matching_data_sources = [source.lower() for source in data_sources]
        #                 # another loop to capture which sources match
        #                 for data_source in matching_data_sources:
        #                     # check if mapping source e.g student.csv
        #                     # in url of change detection files
        #                     # e.g https://raw.githubusercontent.com/kg-construct/rml-test-cases/master/test-cases/rmltc0002a-csv/student.csv
        #                     if mapping_source in data_source:
        #                         # only append if not already appended
        #                         print("MATCCCH", mapping_source, data_source)
        #                         self.graph_details[graph_id]["mappings_impacted"]["sources_impacted"][mapping_id].append(mapping_source)
        #                         for reason_id, reason in change_reasons.items():
        #                             match_reason = reason["match_reason"]
        #                             for reference in mapping_data_references:
        #                                 if reference.lower() == match_reason.lower():
        #                                     current_matches  = self.graph_details[graph_id]["mappings_impacted"]["references_impacted"][
        #                                         mapping_id]
        #                                     if reason_id not in current_matches:
        #                                         self.graph_details[graph_id]["mappings_impacted"]["references_impacted"][
        #                                             mapping_id].append(reason_id)

        # print(self.graph_details[2])

    # get the location of the change detection source data
    def get_changes_source(self):
        # get the reasons for changes occurring
        query = """
        PREFIX changes-graph: <http://www.example.com/changesGraph/user/>
        PREFIX notification-graph: <http://www.example.com/notificationGraph/user/>
        PREFIX contact-graph: <http://www.example.com/contactDetailsGraph/user/>
        PREFIX oscd: <https://w3id.org/OSCD#>
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
        qres = self.current_graph.query(query)
        change_sources = {}
        # convert to lower case
        for row in qres:
            change_sources["current_version"] = str(row[0])
            change_sources["previous_version"] = str(row[1])
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