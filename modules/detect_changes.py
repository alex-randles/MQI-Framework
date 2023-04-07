import pandas as pd
import os
import requests
from xmldiff import main, formatting
from datetime import datetime
from os import listdir
from os.path import isfile, join
import xml.etree.ElementTree as ET
import io
import time
import requests
from rdflib import *
from os import listdir
from os.path import isfile, join
from datetime import datetime
from xmldiff import main, formatting
from collections import defaultdict
from csv_diff import load_csv, compare
from modules.r2rml import *
import modules.r2rml as r2rml
from modules.validate_notification_policy import ValidateNotificationPolicy
# from r2rml import *
# import r2rml as r2rml


class DetectChanges:

    def __init__(self, user_id, form_details):
        self.form_details = form_details
        self.user_id = user_id
        self.error_code = 0
        self.graph_version = self.find_graph_version()
        self.output_file = r2rml.r2rml_output_file.format(self.graph_version)
        self.execute_change_detection()
        self.create_notification_csv()
        self.update_r2rml_config()
        self.execute_r2rml()
        self.validate_notification_policy()

    def find_graph_version(self):
        # find the version number of the graph being created
        only_files = [f for f in listdir(r2rml.graph_directory) if isfile(join(r2rml.graph_directory, f))]
        file_versions = [int(f.split(".")[0]) for f in only_files]
        if file_versions:
            return max(file_versions) + 1
        else:
            return 1

    def execute_change_detection(self):
        self.fetch_csv_data()

    def fetch_csv_data(self):
        # retrieve csv data from
        version_1_url = self.form_details.get("CSV-URL-1")
        version_2_url = self.form_details.get("CSV-URL-2")
        self.version_1_csv = requests.get(version_1_url).text
        self.version_2_csv = requests.get(version_2_url).text
        csv_diff = self.detect_csv_changes()
        output_changes = self.format_csv_changes(csv_diff)
        self.output_changes(output_changes)

    def detect_csv_changes(self):
        version_1_file_object = io.StringIO(self.version_1_csv)
        version_2_file_object = io.StringIO(self.version_2_csv)
        csv_diff = compare(
            load_csv(version_1_file_object),
            load_csv(version_2_file_object),
        )
        # print(csv_diff)
        # exit()
        return csv_diff

    @staticmethod
    def format_csv_changes(csv_diff):
        output_changes = defaultdict(dict)
        output_changes["insert"] = defaultdict(dict)
        output_changes["delete"] = defaultdict(dict)
        change_id = 0
        # process output from csv diff library
        for change_type, related_changes in csv_diff.items():
            for changes in related_changes:
                if isinstance(changes, dict):
                    for data_reference, change_reason in changes.items():
                        if change_type == "added":
                            output_changes["insert"][change_id] = {
                                "data_reference": data_reference,
                                "change_reason": change_reason
                            }
                        else:
                            output_changes["delete"][change_id] = {
                                "data_reference": data_reference,
                                "change_reason": change_reason
                            }
                        change_id += 1
                else:
                    if isinstance(changes, str):
                        structural_reference = "Columns"
                        if change_type == "columns_added":
                            output_changes["insert"][change_id] = {
                                "structural_reference": structural_reference,
                                "change_reason": changes,
                            }
                        else:
                            output_changes["delete"][change_id] = {
                                "structural_reference": structural_reference,
                                "change_reason": changes,
                            }
                        change_id += 1
        return output_changes

    def output_changes(self, output_changes):
        # save differences detected to CSV format for uplift
        df = pd.DataFrame(
            columns=["ID",
                     "OPERATION",
                     "DETECTION_TIME",
                     "DESCRIPTION",
                     "STRUCTURAL_REFERENCE",
                     "DATA_REFERENCE",
                     "USER_ID",
                     "VERSION_1",
                     "VERSION_2"]
        )
        version_1 = self.form_details.get("CSV-URL-1")
        version_2 = self.form_details.get("CSV-URL-2")
        detection_time = datetime.now()
        for change_type, changes in output_changes.items():
            for change_id, changed_values in changes.items():
                data_reference = changed_values.get("data_reference")
                structural_reference = changed_values.get("structural_reference")
                changed_data = changed_values.get("change_reason")
                new_row = [change_id, change_type, detection_time, changed_data, structural_reference, data_reference, self.user_id, version_1, version_2]
                df.loc[len(df)] = new_row
        df.to_csv(changes_detected_csv)

    def create_notification_csv(self):
        # create dictionary with only notification details from form
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
        df.to_csv(r2rml.notification_details_csv)
        print("NOTIFICATION POLICY SAVED TO CSV")
        return df

    def detect_xml_changes(self, version_1, version_2):
        # detect differences between XML file versions
        diff = main.diff_texts(
            version_1,
            version_2,
            formatter=formatting.XMLFormatter())
        # output difference to XML file
        diff_text = open(self.xml_diff_file, "w+")
        diff_text.write(diff)
        diff_text.close()
        self.format_XML_changes()

    def fetch_xml_data(self):
        version_1_url = self.form_details.get("XML_file_1")
        version_2_url = self.form_details.get("XML_file_2")
        version_1_xml = requests.get(version_1_url).text
        version_2_xml = requests.get(version_2_url).text
        self.detect_xml_changes(version_1_xml, version_2_xml)

    def format_XML_changes(self):
        # parse XML file and store in CSV format
        # namespace for changes - http://namespaces.shoobx.com/diff
        tree = ET.parse(r2rml.xml_diff_file)
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
        self.output_XML_changes(results)
        return results
    
    def output_XML_changes(self, results):
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
        config_details = r2rml_config.format(r2rml.mapping_file, r2rml.r2rml_input_files, self.output_file).strip()
        # write config file generated for user which include their input data
        open(r2rml.r2rml_config_file, "w").write(config_details)
        print("R2RML CONFIG FILE UPDATED")

    def validate_notification_policy(self):
        ValidateNotificationPolicy(self.output_file, "11")

    @staticmethod
    def execute_r2rml():
        os.system(run_command)
        print("EXECUTING R2RML ENGINE")

if __name__ == '__main__':
    csv_file_1 = "https://raw.githubusercontent.com/alex-randles/Change-Detection-System-Examples/main/version_1_files/employee.csv"
    csv_file_2 = "https://raw.githubusercontent.com/alex-randles/Change-Detection-System-Examples/main/version_2_files/employee-v2.csv"
    form_details = {
        'CSV-URL-1': csv_file_1,
        'CSV-URL-2': csv_file_2,
        'insert-threshold': '10', 'delete-threshold': '0',
        'move-threshold': '0', 'datatype-threshold': '0',
        'merge-threshold': '0', 'update-threshold': '0',
        'detection-end': '2022-07-10',
        'email-address': 'alexrandles0@gmail.com',
        "user-id": "2",
                }
    cd = DetectChanges(user_id=2, form_details=form_details)
