import pandas as pd
import os
import time
import requests
import xml.etree.ElementTree as ET
from rdflib import *
from os import listdir
from os.path import isfile, join
from datetime import datetime
from xmldiff import main, formatting
from collections import defaultdict
from csv_diff import load_csv, compare


# creates tabular form of CSV file
# Then converts tabular form to RDF using R2RML
# user enters details in form
class ChangeDetection:

    def __init__(self, user_id, form_details):
        self.EX = Namespace("http://example.com/")
        self.RR = Namespace("http://www.w3.org/ns/r2rml#")
        self.user_id = user_id
        self.form_details = form_details
        self.notification_directory = "/home/alex/MQI-Framework/change_detection/database_change_detection/user_files/notification_details/"
        self.contact_directory = "/home/alex/MQI-Framework/change_detection/database_change_detection/user_files/contact_details/"
        self.changes_directory = "/home/alex/MQI-Framework/change_detection/database_change_detection/user_files/change_details/"
        self.graph_directory = "/home/alex/MQI-Framework/change_detection/database_change_detection/user_files/graphs"
        self.changes_CSV = "/home/alex/MQI-Framework/change_detection/database_change_detection/user_files/change_details/change_details_user_{}.csv".format(user_id)
        self.XML_diff_output = "diff_output.xml"
        self.R2RML_directory = "/home/alex/MQI-Framework/change_detection/database_change_detection/r2rml/"
        self.config_filename = self.R2RML_directory + "config.properties"
        self.user_graph_file = "/home/alex/MQI-Framework/change_detection/database_change_detection/user_files/graphs/user_{}.trig".format(user_id)
        self.DB_info_directory = "/home/alex/MQI-Framework/change_detection/database_change_detection/user_files/DB_info_directory"
        # error code
        self.error_code = 0
        # 1 is invalid URL
        self.run_change_detection()

    def run_change_detection(self):
        # try catch if error
        try:
            # email address if process run again
            if "email-address" in self.form_details:
                # check source data format type
                if "server-name" in self.form_details.keys():
                    print("DETECTING DB CHANGES")
                    self.email_address = self.form_details["email-address"]
                    self.user_mapping = self.R2RML_directory + "DB_change_detection_mapping_user_{}.ttl".format(
                        self.user_id)
                    self.create_DB_changes()
                # if XML change detection
                elif "XML_file_1" in self.form_details.keys():
                    self.email_address = self.form_details["email-address"]
                    self.user_mapping = self.R2RML_directory + "XML_change_detection_mapping_user_{}.ttl".format(
                        self.user_id)
                    self.create_XML_changes()
                elif "CSV_URL_1" in self.form_details.keys():
                    self.email_address = self.form_details["email-address"]
                    self.user_mapping = self.R2RML_directory + "XML_change_detection_mapping_user_{}.ttl".format(
                        self.user_id)
                    self.create_CSV_changes()
                # get change counts
                self.user_graph = Dataset()
                self.user_graph.parse(self.user_graph_file, format="trig")
                self.change_counts = self.get_changes_count()
            else:
                # process being rerun
                print("RUNNING CHANGE DETECTION AGAIN")

        except requests.exceptions.MissingSchema as exception_1:
            print("EXCEPTION")
            print(exception_1)
            # invalid URL
            self.error_code = 1
        except OSError as exception_2:
            print("EXCEPTION")
            print(exception_2)
            # graph file most likely not generated
            self.error_code = 2
        except Exception as exception_3:
            print("EXCEPTION")
            print(exception_3)
            # incorrect file format
            # except lxml.etree.XMLSyntaxError as E:
            self.error_code = 3


    def get_changes_count(self):
        # query to get notification thresholds
        query = """
        PREFIX changes-graph: <http://www.example.com/changesGraph/user/>
        PREFIX notification-graph: <http://www.example.com/notificationGraph/user/>
        PREFIX contact-graph: <http://www.example.com/contactDetailsGraph/user/>
        PREFIX cdo: <https://change-detection-ontology.adaptcentre.ie/#>
        PREFIX rei-constraint: <http://www.cs.umbc.edu/~lkagal1/rei/ontologies/ReiConstraint.owl#>
        PREFIX rei-policy: <http://www.cs.umbc.edu/~lkagal1/rei/ontologies/ReiPolicy.owl#>
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>


        # GET COUNT FOR EACH CHANGE TYPE
        SELECT ?changeType (count(?change) AS ?count)
        WHERE
        {
          # QUERY USER GRAPH
          GRAPH ?g {
            # GET DIFFERENT CHANGE TYPES
            VALUES ?changeType
            {
                       cdo:InsertSourceData
                       cdo:DeleteSourceData
                       cdo:MoveSourceData
                       cdo:UpdateSourceData
                       cdo:MergeSourceData
                       cdo:DatatypeSourceData
                     }
                    # GET EACH CHANGE FROM LOG
                     ?changeLog a cdo:ChangeLog ;
                                cdo:hasChange ?change.
                     ?change a ?changeType
          }
        }
        GROUP BY ?changeType
        """

        qres = self.user_graph.query(query)
        # count of each change type within graph
        change_type_counts = {}
        for (change_type, count) in qres:
            change_type_counts[change_type] = count.value
        return change_type_counts

    def create_XML_changes(self):
        # create CSV with notification policy details
        self.create_notification_CSV()
        # create CSV for contact details
        self.create_contact_CSV()
        # create CSV with changes that have occured
        self.create_XML_changes_CSV()
        # # add_user_contact(user_id, form_details)
        output_file = self.uplift_information()
        return output_file

    def create_DB_changes(self):
        # create CSV with notification policy details
        self.create_notification_CSV()
        # create CSV for contact details
        self.create_contact_CSV()
        # # create CSV with changes that have occured
        self.create_DB_changes_CSV()
        # # # add_user_contact(user_id, form_details)
        output_file = self.uplift_information()
        return output_file

    def create_CSV_changes(self):
        # create CSV with notification policy details
        self.create_notification_CSV()
        # create CSV for contact details
        self.create_contact_CSV()
        # # create CSV with changes that have occured
        self.create_CSV_changes_CSV()
        # # # add_user_contact(user_id, form_details)
        output_file = self.uplift_information()
        return output_file

    # server info
    def create_DB_changes_CSV(self):
        self.create_DB_info_CSV()
        self.create_notification_CSV()
        self.create_contact_CSV()
        # copy data as DB query not working
        df = pd.read_csv("/home/alex/MQI-Framework/change_detection/database_change_detection/user_files/change_details/change_details_user_1.csv")
        df.to_csv(self.changes_CSV)

    # CSV that contains server info etc
    def create_DB_info_CSV(self):
        server_name = self.form_details["server-name"]
        DB_name = self.form_details["database-name"]
        username = self.form_details["username"]
        password = self.form_details["password"]
        DB_info = {
            "SERVER_NAME": server_name,
            "DB_NAME": DB_name,
            "USERNAME": username,
            "PASSWORD": password,
            }
        df = pd.DataFrame([DB_info])
        print("DATABASE INFORMATION")
        print(df)
        output_file_name = "DB_info_user_{}.csv".format(self.user_id)
        df.to_csv(self.DB_info_directory + "/" + output_file_name)

    def create_XML_changes_CSV(self):
        # check if XML uploaded
        # check if XML or database information being uplifted
        if "XML_file_1" in self.form_details.keys():
            # if XML
            XML_version_1 = self.form_details.get("XML_file_1")
            XML_version_2 = self.form_details.get("XML_file_2")
            self.fetch_XML_data(XML_version_1, XML_version_2)
            self.output_XML_changes()
            print("CHANGES CSV SAVED")
        else:
            self.query_DB_log()

    # query the DB transaction log
    def query_DB_log(self):
        pass

    @staticmethod
    def iterate_user_files(user_id):
        graph_directory = "/home/alex/MQI-Framework/static/change_graphs"
        directory_files = [f for f in listdir(graph_directory) if isfile(join(graph_directory, f))]
        # find files related to user ID
        user_versions = []
        for file in directory_files:
            file_user_id, file_version = ChangeDetection.get_file_details(file)
            if user_id == file_user_id:
                user_versions.append(file_version)
        if user_versions:
            return max(user_versions) + 1
        else:
            return 1


    @staticmethod
    def get_file_details(filename):
        # find if user has files uploaded
        split_index = filename.rfind('_')
        file_details = filename[split_index + 1:].split(".")[0].split("-")
        if len(file_details) > 1:
            file_user_id, file_version = file_details[0], int(file_details[1])
        else:
            file_user_id, file_version = file_details[0], 1
        return file_user_id, file_version

    # fetches the XML data from online
    def fetch_XML_data(self, version_1_URL, version_2_URL):
        version_1_XML = requests.get(version_1_URL)
        version_1_XML.close()
        version_1_XML = version_1_XML.text
        version_2_XML = requests.get(version_2_URL)
        version_2_XML = version_2_XML.text
        self.detect_XML_differences(version_1_XML, version_2_XML)

    # function to detect changes between two XML file versions and store results in XML file
    def detect_XML_differences(self, version_1, version_2):
        # detect differences between XML file versions
        diff = main.diff_texts(
            version_1,
            version_2,
            formatter=formatting.XMLFormatter())
        # output difference to XML file
        diff_text = open(self.XML_diff_output , "w")
        diff_text.write(diff)
        diff_text.close()
        return self.XML_diff_output

    # convert XML output to CSV file with the differences
    def output_XML_changes(self):
        # parse XML file
        # namespace for changes - http://namespaces.shoobx.com/diff
        tree = ET.parse(self.XML_diff_output)
        result = ""
        results = defaultdict(list)
        # create a dictionary with changes
        for elem in tree.iter():
            if elem.tag == "{http://namespaces.shoobx.com/diff}insert":
                results["insert"].append(result)
                result = ""
            elif elem.tag == "{http://namespaces.shoobx.com/diff}delete":
                results["delete"].append(result)
                result = ""
            elif elem.tag == "{http://namespaces.shoobx.com/diff}update-text":
                results[elem.tag].append(result)
                result = ""
            elif elem.text is not None:
                result += elem.tag + ": " + elem.text + " "
            else:
                pass
        # create a dataframe with changes
        changes_df = pd.DataFrame(columns=["ID", "OPERATION", "DETECTION_TIME", "DESCRIPTION", "USER_ID", "VERSION_1", "VERSION_2"])
        change_ID = 1
        detection_time = datetime.now()
        # add each change to dataframe
        for change_type, changes in results.items():
            for value in changes:
                if value:
                    value = value.replace("\n", " ")
                    # store file versions in CSV
                    XML_version_1 = self.form_details.get("XML_file_1")
                    XML_version_2 = self.form_details.get("XML_file_2")
                    changes_df.loc[change_ID] = [change_ID, change_type, detection_time, value, "2", XML_version_1, XML_version_2]
                    change_ID += 1
        # remove row indexes
        changes_df.reset_index(drop=True)
        # output changes into CSV file
        changes_df.to_csv(self.changes_CSV)
        print("CHANGES CSV NEW CREATED")

    # create CSV file to be uplifted to notification policy
    def create_notification_CSV(self):
        # create dictionary with only notification details from form
        # use upper case for R2RML
        notification_details = {
            "USER_ID": self.user_id, "INSERT_THRESHOLD": self.form_details["insert_threshold"],
            "DELETE_THRESHOLD": self.form_details["delete_threshold"],
            "MOVE_THRESHOLD": self.form_details["move_threshold"],
            "DATATYPE_THRESHOLD": self.form_details["datatype_threshold"],
            "MERGE_THRESHOLD": self.form_details["merge_threshold"],
            "UPDATE_THRESHOLD": self.form_details["update_threshold"],
            "DETECTION_START": datetime.now().now(),
            "DETECTION_END": self.form_details["detection-end"] + " 00:00:00.0000"
        }
        df = pd.DataFrame([notification_details])
        output_file_name = "notification_policy_user_{}.csv".format(self.user_id)
        df.to_csv(self.notification_directory + output_file_name)
        print("NOTIFICATION POLICY SAVED TO CSV")
        return df

    def create_contact_CSV(self):
        contact_details = {
            "EMAIL_ADDRESS": self.email_address,
            "USER_ID": self.user_id
        }
        df = pd.DataFrame([contact_details])
        output_file_name = "contact_details_user_{}.csv".format(self.user_id)
        df.to_csv(self.contact_directory + output_file_name)
        print("CONTACT CSV SAVED")
        return df

    # uplift notification details, changes and contact details
    def uplift_information(self):
        # check if XML or database information being uplifted
        print(self.form_details.keys())
        if "XML_file_1" in self.form_details.keys():
            print("UPLIFTING XML INFORMATION")
            self.uplift_XML_information()
        elif "CSV_URL_1" in self.form_details.keys():
            self.uplift_XML_information()
        else:
            print("UPLIFTING DATABASE INFORMATION")
            self.uplift_database_information()
        self.run_mapping()
        return self.user_graph_file

    # uplift information related to database change detection
    def uplift_database_information(self):
        # change mapping table
        current_version = ChangeDetection.iterate_user_files(self.user_id)
        new_version = current_version
        new_file_version = "user_{}-{}".format(self.user_id, new_version)
        config_file_details = """connectionURL =
                mappingFile = /home/alex/MQI-Framework/change_detection/database_change_detection/r2rml/DB_change_detection_mapping_user_{}.ttl
                CSVFiles = /home/alex/MQI-Framework/change_detection/database_change_detection/user_files/notification_details/notification_policy_user_{}.csv;/home/alex/MQI-Framework/change_detection/database_change_detection/user_files/contact_details/contact_details_user_{}.csv;/home/alex/MQI-Framework/change_detection/database_change_detection/user_files/change_details/change_details_user_{}.csv;/home/alex/MQI-Framework/change_detection/database_change_detection/user_files/DB_info_directory/DB_info_user_{}.csv
                outputFile = /home/alex/MQI-Framework/static/change_graphs/{}.trig
                format= TRIG
                    """.format(self.user_id, self.user_id, self.user_id, self.user_id, self.user_id, new_file_version)
        # save config file
        with open(self.config_filename, 'w') as output:
            output.write(config_file_details)
        # change mapping table
        self.change_mapping_table("DB")

    # uplift information related to XML change detection
    def uplift_XML_information(self):
        # change mapping table
        # file version
        current_version = ChangeDetection.iterate_user_files(self.user_id)
        new_version = current_version
        new_file_version = "user_{}-{}".format(self.user_id, new_version)
        config_file_details = """connectionURL =
                mappingFile = /home/alex/MQI-Framework/change_detection/database_change_detection/r2rml/XML_change_detection_mapping_user_{}.ttl
                CSVFiles = /home/alex/MQI-Framework/change_detection/database_change_detection/user_files/notification_details/notification_policy_user_{}.csv;/home/alex/MQI-Framework/change_detection/database_change_detection/user_files/contact_details/contact_details_user_{}.csv;/home/alex/MQI-Framework/change_detection/database_change_detection/user_files/change_details/change_details_user_{}.csv
                outputFile = /home/alex/MQI-Framework/static/change_graphs/{}.trig
                format= TRIG
                    """.format(self.user_id, self.user_id, self.user_id, self.user_id, new_file_version)
        # save config file
        with open(self.config_filename, 'w') as output:
            output.write(config_file_details)
        # run mapping
        self.change_mapping_table("XML")

    def run_mapping(self):
        os.system(self.R2RML_directory + "run.sh '{}'".format(self.config_filename))

    # changes the mapping input table to user specific
    def change_mapping_table(self, mapping_type):
        if mapping_type == "XML":
            notification_mapping = Graph().parse(self.R2RML_directory + "XML_change_detection_mapping.ttl".format(self.user_id), format="ttl")
        else:
            notification_mapping = Graph().parse(self.R2RML_directory + "DB_change_detection_mapping.ttl".format(self.user_id), format="ttl")
        notification_table = "notification_policy_user_{}".format(self.user_id)
        contact_table = "contact_details_user_{}".format(self.user_id)
        changes_table = "change_details_user_{}".format(self.user_id)
        for s, p, o in notification_mapping.triples((None, self.RR.tableName, None)):
            if str(o) == "NOTIFICATION_DETAILS":
                notification_mapping.remove((s,p,o))
                notification_mapping.add((s, p, Literal(notification_table)))
            if str(o) == "CONTACT_DETAILS":
                notification_mapping.remove((s,p,o))
                notification_mapping.add((s, p, Literal(contact_table)))
            if str(o) == "TRANSACTION_LOG":
                notification_mapping.remove((s,p,o))
                notification_mapping.add((s, p, Literal(changes_table)))
        notification_table = "notification_policy_user_{}".format(self.user_id)
        contact_table = "contact_details_user_{}".format(self.user_id)
        changes_table = "change_details_user_{}".format(self.user_id)
        for s, p, o in notification_mapping.triples((None, self.RR.tableName, None)):
            if str(o) == "NOTIFICATION_DETAILS":
                notification_mapping.remove((s,p,o))
                notification_mapping.add((s, p, Literal(notification_table)))
            if str(o) == "CONTACT_DETAILS":
                notification_mapping.remove((s,p,o))
                notification_mapping.add((s, p, Literal(contact_table)))
            if str(o) == "TRANSACTION_LOG":
                notification_mapping.remove((s,p,o))
                notification_mapping.add((s, p, Literal(changes_table)))
        # change SQL query to reference new table
        for s, p, o in notification_mapping.triples((None, self.RR.sqlQuery, None)):
            query = str(o)
            new_query = query.replace("transaction_log", changes_table)
            notification_mapping.remove((s,p,o))
            notification_mapping.add((s, p, Literal(new_query)))
        print("UPDATING MAPPING TABLES", self.user_mapping)
        notification_mapping.serialize(destination=self.user_mapping, format="ttl")

    def create_CSV_changes_CSV(self):
        CSV_URL_1 = self.form_details.get("CSV_URL_1")
        print("FETCHING CSV FILES")
        CSV_text_1 = requests.get(CSV_URL_1)
        CSV_text_1.close()
        CSV_text_1 = CSV_text_1.text.strip()
        CSV_URL_2 = self.form_details.get("CSV_URL_2")
        CSV_text_2 = requests.get(CSV_URL_2)
        CSV_text_2.close()
        CSV_text_2 = CSV_text_2.text.strip()
        self.detect_CSV_difference(CSV_text_1, CSV_text_2)

    def detect_CSV_difference(self, CSV_text_1, CSV_text_2):
        print("DETECTING CSV CHANGES")
        print(CSV_text_1, CSV_text_2)
        # write CSV data to files
        CSV_filename_1 = "CSV_file_1.csv"
        CSV_filename_2 = "CSV_file_2.csv"
        open(CSV_filename_1, "w").write(CSV_text_1)
        open(CSV_filename_2, "w").write(CSV_text_2)
        # compare CSV files
        diff = compare(
            load_csv(open(CSV_filename_1)),
            load_csv(open(CSV_filename_2))
        )
        print("CSV File difference")
        print(diff)
        self.output_CSV_changes(diff)

    # SAMPLE OUTPUT
    # {'added': [{'ID': '10', 'Sport': '100', 'Name': 'Venus Williams'},
    #            {'ID': '20', 'Sport': '', 'Name': 'Demi Moore'}],
    #  'removed': [{'ID': '10', 'Name': 'Venus'}], 'changed': [],
    #  'columns_added': ['Sport'], 'columns_removed': []}

    def output_CSV_changes(self, CSV_changes):
        # takes diff in JSON format and outputs to the CSV file for uplifting
        # create dict with changes and reasons first
        changes = defaultdict(list)
        change_mappings = {
            "added": "insert",
            "removed": "delete",
            "columns_added": "insert",
            "columns_removed": "delete",
            "changed": "update",
        }
        for change_type, related_changes in CSV_changes.items():
            if change_type in change_mappings.keys():
                current_change_type = change_mappings[change_type]
                # check if value string, list or dict
                related_changes_type = type(related_changes)
                # if columns added or remove add extra text
                if change_type == "columns_added":
                    reason_prefix = "Column Added: "
                elif change_type == "columns_removed":
                    reason_prefix = "Column Deleted: "
                else:
                    reason_prefix = ""
                # iterate changes
                if related_changes_type == str:
                    # could be empty value
                    if related_changes:
                        changes[current_change_type].append(reason_prefix + str(related_changes))
                    else:
                        changes[current_change_type].append(reason_prefix + " Null Value")
                elif related_changes_type == list:
                    for value in related_changes:
                        if type(value) == dict:
                            for key, current_value in value.items():
                                if current_value:
                                    change_reason = "{}: {}".format(key, current_value)
                                else:
                                    change_reason = "{}: Null Value".format(key)
                                changes[current_change_type].append(change_reason)
                        else:
                            if related_changes:
                                changes[current_change_type].append(reason_prefix + str(value))
                            else:
                                changes[current_change_type].append(reason_prefix + " Null Value")
                else:
                    pass
        changes_df = pd.DataFrame(
            columns=["ID", "OPERATION", "DETECTION_TIME", "DESCRIPTION", "USER_ID", "VERSION_1", "VERSION_2"])
        change_ID = 1
        detection_time = datetime.now()
        # add each change to dataframe
        for change_type, changes in changes.items():
            for value in changes:
                if value:
                    value = value.replace("\n", " ")
                    # store file versions in CSV
                    XML_version_1 = self.form_details.get("CSV_URL_1")
                    XML_version_2 = self.form_details.get("CSV_URL_2")
                    changes_df.loc[change_ID] = [change_ID, change_type, detection_time, value, "2", XML_version_1,
                                                 XML_version_2]
                    change_ID += 1
        # remove row indexes
        changes_df.reset_index(drop=True)
        # output changes into CSV file
        changes_df.to_csv(self.changes_CSV)
#
if __name__ == "__main__":
    # form_details = {
    #     "XML_file_1": "https://raw.githubusercontent.com/alex-randles/Change-Detection-System-Examples/main/characters_V1.xml" ,
    #     "XML_file_2" : "https://raw.githubusercontent.com/alex-randles/Change-Detection-System-Examples/main/characters_V2.xml",
    #     "email-address": "alex@gmail.com"
    # }
    # form_details = {'XML_file_1': 'https://raw.githubusercontent.com/alex-randles/Change-Detection-System-Examples/main/students_V1.xml', 'XML_file_2': 'https://raw.githubusercontent.com/alex-randles/Change-Detection-System-Examples/main/students_V2.xml', 'insert_threshold': '10', 'delete_threshold': '0', 'move_threshold': '0', 'datatype_threshold': '0', 'merge_threshold': '0', 'update_threshold': '0', 'detection-end': '2022-07-10', 'email-address': 'alexrandles0@gmail.com'}
    CSV_file_1 = "https://raw.githubusercontent.com/kg-construct/rml-test-cases/master/test-cases/RMLTC0002a-CSV/student.csv"
    CSV_file_2 = "https://raw.githubusercontent.com/kg-construct/rml-test-cases/master/test-cases/RMLTC0009a-CSV/student.csv"
    form_details = {'CSV_URL_1': CSV_file_1,
                    'CSV_URL_2': CSV_file_2,
                    'insert_threshold': '10', 'delete_threshold': '0',
                    'move_threshold': '0', 'datatype_threshold': '0',
                    'merge_threshold': '0', 'update_threshold': '0',
                    'detection-end': '2022-07-10',
                    'email-address': 'alexrandles0@gmail.com'}
    cd = ChangeDetection("1", form_details)

