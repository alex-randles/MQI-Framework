import pandas as pd
import os
import requests
from xmldiff import main, formatting
from datetime import datetime
from os import listdir
from os.path import isfile, join
import xml.etree.ElementTree as ET
import os
import time
import requests
from rdflib import *
from os import listdir
from os.path import isfile, join
from datetime import datetime
from xmldiff import main, formatting
from collections import defaultdict
from csv_diff import load_csv, compare

class DetectChanges:

    def __init__(self, user_id, form_details):
        self.form_details = form_details
        self.user_id = user_id
        self.filenames = FileNames(self.user_id)
        self.error_code = 0
        self.user_directory = self.filenames.filename_dict.get("user_graph_directory")
        self.graph_directory = self.filenames.filename_dict.get("graph_directory")
        self.xml_diff_file = self.filenames.filename_dict.get("xml_diff_file")
        self.mapping_file = self.filenames.filename_dict.get("mapping_file")
        self.r2rml_input_files = self.filenames.filename_dict.get("r2rml_input_files")
        self.r2rml_output_file = self.filenames.filename_dict.get("r2rml_output_file")
        self.r2rml_config_file = self.filenames.filename_dict.get("r2rml_config_file")
        self.r2rml_run_file = self.filenames.filename_dict.get("r2rml_run_file")
        self.notification_details_csv = self.filenames.filename_dict.get("notification_details_csv")
        self.execute_change_detection()
        self.create_notification_csv()
        self.update_r2rml_config()
        self.execute_r2rml()

    def execute_change_detection(self):
        file_format = self.retrieve_file_format()
        if file_format == "csv":
            self.fetch_csv_data()
        elif file_format == "xml":
            self.fetch_xml_data()
        else:
            pass

    def retrieve_file_format(self):
        # maps the key for the form file input to the format
        file_format = {
            "CSV_URL_1" : "csv",
            "XML_file_1" : "xml",
        }
        for form_name, file_format in file_format.items():
            if form_name in self.form_details.keys():
                return file_format
        return None

    def fetch_csv_data(self):
        # retrieve csv data from
        version_1_url = self.form_details.get("CSV_URL_1")
        version_2_url = self.form_details.get("CSV_URL_2")
        version_1_csv = requests.get(version_1_url).text
        version_2_csv = requests.get(version_2_url).text
        open("one.csv", "w+").write(version_1_csv)
        open("two.csv", "w+").write(version_2_csv)
        version_1_csv = version_2_csv = None
        csv_diff = self.detect_csv_changes(version_1_csv, version_2_csv)
        output_changes = self.format_csv_changes(csv_diff)
        self.output_changes(output_changes)

    @staticmethod
    def detect_csv_changes(version_1_csv, version_2_csv):
        csv_diff = compare(
            load_csv(open("one.csv")),
            load_csv(open("two.csv"))
        )
        return csv_diff

    @staticmethod
    def format_csv_changes(csv_diff):
        output_changes = defaultdict(list)
        for change_type, related_changes in csv_diff.items():
            for changes in related_changes:
                if isinstance(changes, dict):
                    for data_reference, change_reason in changes.items():
                        if change_type == "added":
                            result_message = "{}: {}".format(data_reference, change_reason)
                            output_changes["insert"].append(result_message)
                        else:
                            result_message = "{}: {}".format(data_reference, change_reason)
                            output_changes["delete"].append(result_message)
                else:
                    if isinstance(changes, str):
                        if change_type == "columns_added":
                            result_message = "Column inserted: {}".format(changes)
                            output_changes["insert"].append(result_message)
                        else:
                            result_message = "Column deleted: {}".format(changes)
                            output_changes["delete"].append(result_message)
        return output_changes

    def output_changes(self, output_changes):
        changes_df = pd.DataFrame(
            columns=["ID", "OPERATION", "DETECTION_TIME", "DESCRIPTION", "USER_ID", "VERSION_1", "VERSION_2"])
        version_1 = self.form_details.get("CSV_URL_1")
        version_2 = self.form_details.get("CSV_URL_2")
        detection_time = datetime.now()
        change_id = 0
        for change_type, changes in output_changes.items():
            for change_reason in changes:
                new_row = [change_id, change_type, detection_time, change_reason, self.user_id, version_1, version_2]
                changes_df.loc[len(changes_df)] = new_row
                change_id += 1
        changes_df.to_csv("/home/alex/MQI-Framework/static/change_detection_cache/1/changes_info/changes_detected.csv")


    # create CSV file to be uplifted to notification policy
    def create_notification_csv(self):
        # create dictionary with only notification details from form
        # use upper case for R2RML
        df = pd.DataFrame([{
            "USER_ID": self.user_id,
            "INSERT_THRESHOLD": self.form_details.get("insert-threshold", ""),
            "DELETE_THRESHOLD": self.form_details.get("delete-threshold", ""),
            "MOVE_THRESHOLD": self.form_details.get("move-threshold", ""),
            "DATATYPE_THRESHOLD": self.form_details.get("datatype-threshold", ""),
            "MERGE_THRESHOLD": self.form_details.get("merge-threshold", ""),
            "UPDATE_THRESHOLD": self.form_details.get("update-threshold", ""),
            "DETECTION_START": datetime.now().now(),
            "DETECTION_END": self.form_details.get("detection-end", "") + " 00:00:00.0000"
        }])
        df.to_csv(self.notification_details_csv)
        print("NOTIFICATION POLICY SAVED TO CSV")
        return df

    def detect_xml_changes(self, version_1, version_2):
        # retrieve the latest xml data first
        # detect differences between XML file versions
        diff = main.diff_texts(
            version_1,
            version_2,
            formatter=formatting.XMLFormatter())
        # output difference to XML file
        diff_text = open(self.xml_diff_file, "w+")
        diff_text.write(diff)
        diff_text.close()
        self.output_XML_changes()

    def fetch_xml_data(self):
        version_1_url = self.form_details.get("XML_file_1")
        version_2_url = self.form_details.get("XML_file_2")
        version_1_xml = requests.get(version_1_url).text
        version_2_xml = requests.get(version_2_url).text
        self.detect_xml_changes(version_1_xml, version_2_xml)

        # convert XML output to CSV file with the differences
    def output_XML_changes(self):
        # parse XML file and store in CSV format
        # namespace for changes - http://namespaces.shoobx.com/diff
        tree = ET.parse(self.xml_diff_file)
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
        changes_df = pd.DataFrame(
            columns=["ID", "OPERATION", "DETECTION_TIME", "DESCRIPTION", "USER_ID", "VERSION_1", "VERSION_2"])
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
                    changes_df.loc[change_ID] = [change_ID, change_type, detection_time, value, "2", XML_version_1,
                                                 XML_version_2]
                    change_ID += 1
        # remove row indexes
        changes_df.reset_index(drop=True)
        # output changes into CSV file
        changes_df.to_csv("/home/alex/MQI-Framework/static/change_detection_cache/1/changes_info/changes_detected.csv")
        print("CHANGES CSV NEW CREATED")

    def update_r2rml_config(self):
        config_details = """connectionURL =
mappingFile = {}
CSVFiles = {};
outputFile = {}
format= TRIG            
        """.format(self.mapping_file, self.r2rml_input_files, self.r2rml_output_file).strip()
        # write config file generated for user which include their input data
        open(self.r2rml_config_file, "w").write(config_details)
        print("R2RML CONFIG FILE UPDATED")

    def execute_r2rml(self):
        os.system(self.r2rml_run_file)
        print("EXECUTING R2RML ENGINE")


class FileNames:
    def __init__(self, user_id):
        # create dynamic file names
        self.user_id = user_id
        self.graph_directory = "/home/alex/MQI-Framework/static/change_detection_cache/{}/change_graphs".format(self.user_id)
        self.graph_version = self.find_graph_version()
        self.user_graph_directory = "/home/alex/MQI-Framework/static/change_detection_cache/{}/changes_info/".format(self.user_id)
        self.user_directory = "/home/alex/MQI-Framework/static/change_detection_cache/{}/changes_info/".format(self.user_id)
        self.xml_diff_file = "/home/alex/MQI-Framework/static/change_detection_cache/{}/changes_info/diff.xml".format(self.user_id)
        self.notification_details_csv = self.user_directory + "notification_details.csv".format(self.user_id)
        self.mapping_file = "/home/alex/MQI-Framework/static/change_detection_cache/mappings/CSV_change_detection_mapping.ttl"
        self.r2rml_input_files = "/home/alex/MQI-Framework/static/change_detection_cache/{}/changes_info/contact_details.csv;/home/alex/MQI-Framework/static/change_detection_cache/{}/changes_info/changes_detected.csv;/home/alex/MQI-Framework/static/change_detection_cache/{}/changes_info/notification_details.csv".format(self.user_id, self.user_id, self.user_id).strip()
        self.r2rml_output_file = "/home/alex/MQI-Framework/static/change_detection_cache/{}/change_graphs/{}.trig".format(self.user_id, self.graph_version)
        self.r2rml_config_file = "/home/alex/MQI-Framework/static/change_detection_cache/r2rml/config.properties"
        self.r2rml_run_file = "/home/alex/MQI-Framework/static/change_detection_cache/r2rml/run.sh"
        # store file names in dict for retrieval
        self.filename_dict = {
            "user_graph_directory": self.user_graph_directory,
            "user_directory": self.user_directory,
            "graph_directory": self.graph_directory,
            "xml_diff_file": self.xml_diff_file,
            "notification_details_csv": self.notification_details_csv,
            "mapping_file": self.mapping_file,
            "r2rml_input_files": self.r2rml_input_files,
            "r2rml_output_file": self.r2rml_output_file,
            "r2rml_config_file": self.r2rml_config_file,
            "r2rml_run_file": self.r2rml_run_file,
        }

    # find the version number of the graph being created
    def find_graph_version(self):
        onlyfiles = [f for f in listdir(self.graph_directory) if isfile(join(self.graph_directory, f))]
        file_versions = [int(f.split(".")[0]) for f in onlyfiles]
        if file_versions:
            return max(file_versions) + 1
        else:
            return 1

if __name__ == '__main__':
    csv_file_1 = "https://raw.githubusercontent.com/kg-construct/" \
                 "rml-test-cases/master/test-cases/RMLTC0002a-CSV/student.csv"
    csv_file_2 = "https://raw.githubusercontent.com/kg-construct/" \
                 "rml-test-cases/master/test-cases/RMLTC0009a-CSV/student.csv"
    form_details = {
        'CSV-URL_1': csv_file_1,
        'CSV-URL_2': csv_file_2,
        'insert-threshold': '10', 'delete-threshold': '0',
        'move-threshold': '0', 'datatype-threshold': '0',
        'merge-threshold': '0', 'update-threshold': '0',
        'detection-end': '2022-07-10',
        'email-address': 'alexrandles0@gmail.com',
        "user-id": "2",
                }
    cd = DetectChanges(user_id=2, form_details=form_details)
