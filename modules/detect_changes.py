import pandas as pd
import os
import requests
import xml.etree.ElementTree as ET
import io
import datetime
import xmldiff
import csv_diff
import csv
import modules.r2rml as r2rml
from collections import defaultdict
from modules.validate_notification_policy import ValidateNotificationPolicy


class DetectChanges:

    def __init__(self, user_id, form_details):
        self.form_details = form_details
        self.version_1_source, self.version_2_source, self.diff = None, None, None
        self.user_id = user_id
        self.is_csv_data = "CSV-URL-2" in self.form_details.keys()
        try:
            self.fetch_source_data()
            self.error_code = 0
        except requests.exceptions.SSLError:
            self.error_code = 2
        self.graph_version = self.find_graph_version()
        self.output_file = r2rml.r2rml_output_file.format(user_id, self.graph_version)
        self.detect_source_changes()
        self.run_uplift()
        self.validate_notification_policy()

    def run_uplift(self):
        if self.error_code == 0:
            self.create_notification_csv()
            self.create_contact_csv()
            self.update_r2rml_config()
            self.execute_r2rml()
        else:
            print("UPLIFT ERROR ")

    def create_contact_csv(self):
        df = pd.DataFrame(
            columns=["EMAIL_ADDRESS", "USER_ID"])
        df.loc[len(df)] = [self.form_details.get("email-address"), self.user_id]
        df.to_csv(r2rml.contact_details_csv)

    def fetch_source_data(self):
        if self.is_csv_data:
            self.version_1_source = requests.get(self.form_details.get("CSV-URL-1")).text
            self.version_2_source = requests.get(self.form_details.get("CSV-URL-2")).text
            print("RETRIEVED FILE DATA ", self.version_1_source )
        else:
            self.version_1_source = requests.get(self.form_details.get("XML-URL-1")).text
            self.version_2_source = requests.get(self.form_details.get("XML-URL-2")).text

    def detect_source_changes(self):
        if self.error_code == 0:
            try:
                if self.is_csv_data:
                    diff = self.detect_csv_changes()
                    diff = self.format_csv_changes(diff)
                    self.output_changes(diff)
                else:
                    self.detect_xml_changes()
            except StopIteration:
                print("EXCEPTION STOP ITERATION")
                print()
                self.error_code = 1
                return None

    def detect_xml_changes(self):
        # detect differences between XML file versions
        self.diff = xmldiff.main.diff_texts(
            self.version_1_source,
            self.version_2_source,
            formatter=xmldiff.formatting.XMLFormatter(),
            )
        print(self.diff)
        exit()
        self.format_xml_changes()

    def format_xml_changes(self):
        # parse XML file and store in CSV format
        # namespace for changes - http://namespaces.shoobx.com/diff
        tree = ET.ElementTree(ET.fromstring(self.diff))
        result = ""
        results = defaultdict(list)
        # create a dictionary with changes
        for element in tree.iter():
            element_tag = element.tag
            element_text = element.text
            print(element_tag, element_text)
        return results

    def find_graph_version(self):
        # find the version number of the graph being created
        only_files = [f for f in os.listdir(r2rml.graph_directory.format(self.user_id)) if os.path.isfile(os.path.join(r2rml.graph_directory.format(self.user_id), f))]
        file_versions = [int(f.split(".")[0]) for f in only_files]
        if file_versions:
            return max(file_versions) + 1
        else:
            return 1

    def detect_csv_changes(self):
        version_1_file_object = io.StringIO(self.version_1_source)
        version_2_file_object = io.StringIO(self.version_2_source)
        diff = csv_diff.compare(
            csv_diff.load_csv(version_1_file_object),
            csv_diff.load_csv(version_2_file_object),
        )
        return diff

    @staticmethod
    def fitem(item):
        item = item.strip()
        try:
            item = str(item)
        except ValueError:
            pass
        return item

    @staticmethod
    def detect_duplicates(csv_data):
        with io.StringIO(csv_data) as csvin:
            reader = csv.DictReader(csvin)
            data = {k.strip(): [DetectChanges.fitem(v)] for k, v in next(reader).items()}
            for line in reader:
                for k, v in line.items():
                    k = k.strip()
                    data[k].append(DetectChanges.fitem(v))
        csv_tuples = []
        for k, v in data.items():
            for value in v:
                csv_tuples.append((k, value))
        return csv_tuples

    def format_csv_changes(self, csv_diff):
        output_changes = defaultdict(dict)
        output_changes["insert"] = defaultdict(dict)
        output_changes["delete"] = defaultdict(dict)
        change_id = 0
        # process output from csv diff library
        csv_tuples_1 = DetectChanges.detect_duplicates(self.version_1_source)
        csv_tuples_2 = DetectChanges.detect_duplicates(self.version_2_source)
        for change_type, related_changes in csv_diff.items():
            for changes in related_changes:
                if isinstance(changes, dict):
                    for data_reference, change_reason in changes.items():
                        if change_type == "added":
                            if (data_reference, change_reason) not in csv_tuples_1:
                                output_changes["insert"][change_id] = {
                                    "data_reference": data_reference,
                                    "change_reason": change_reason
                                }
                                change_id += 1
                            else:
                                csv_tuples_1.remove((data_reference, change_reason))
                        else:
                            if (data_reference, change_reason) not in csv_tuples_2:
                                # print(self.detect_duplicates(self.version_1_csv))
                                print(type(data_reference), type(change_reason))
                                output_changes["delete"][change_id] = {
                                    "data_reference": data_reference,
                                    "change_reason": change_reason
                                }
                                change_id += 1
                            else:
                                pass
                else:
                    if isinstance(changes, str):
                        structural_reference = "Columns"
                        if change_type == "columns_added":
                            output_changes["insert"][change_id] = {
                                "structural_reference": structural_reference,
                                "change_reason": changes,
                            }
                            change_id += 1
                        else:
                            output_changes["delete"][change_id] = {
                                "structural_reference": structural_reference,
                                "change_reason": changes,
                            }
                            change_id += 1
        version_1_url = self.form_details.get("CSV-URL-1").split("/")[-1]
        version_2_url = self.form_details.get("CSV-URL-2").split("/")[-1]
        if version_1_url.strip() !=  version_2_url.strip():
            output_changes["move"][change_id + 1] = {"new_location": version_2_url}
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
                     "NEW_LOCATION",
                     "USER_ID",
                     "VERSION_1",
                     "VERSION_2"]
        )
        version_1 = self.form_details.get("CSV-URL-1")
        version_2 = self.form_details.get("CSV-URL-2")
        detection_time = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        for change_type, changes in output_changes.items():
            if change_type != "move":
                for change_id, changed_values in changes.items():
                    data_reference = changed_values.get("data_reference")
                    structural_reference = changed_values.get("structural_reference")
                    changed_data = changed_values.get("change_reason")
                    if changed_data == "":
                        changed_data = "No associated values."
                    new_row = [change_id, change_type, detection_time, changed_data, structural_reference,
                               data_reference, None, self.user_id, version_1, version_2]
                    df.loc[len(df)] = new_row
            else:
                change_id = list(changes.keys())[0]
                new_location = changes.get(change_id).get("new_location")
                new_row = [change_id, change_type, detection_time, "location", None, "location",
                           new_location, self.user_id, version_1, version_2]
                df.loc[len(df)] = new_row
        df.to_csv(r2rml.changes_detected_csv)

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
            "DETECTION_START": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "DETECTION_END": self.form_details.get("detection-end", "") + " 00:00:00.0000"
        }])
        df.to_csv(r2rml.notification_details_csv)
        print("NOTIFICATION POLICY SAVED TO CSV")
        return df

    def update_r2rml_config(self):
        config_details = r2rml.r2rml_config.format(r2rml.mapping_file, r2rml.r2rml_input_files, self.output_file).strip()
        # write config file generated for user which include their input data
        open(r2rml.r2rml_config_file, "w").write(config_details)
        print("R2RML CONFIG FILE UPDATED")

    def validate_notification_policy(self):
        if self.error_code == 0:
            # pass
            ValidateNotificationPolicy(self.output_file, self.user_id)

    @staticmethod
    def execute_r2rml():
        os.system(r2rml.run_command)


if __name__ == '__main__':
    csv_file_1 = "https://raw.githubusercontent.com/alex-randles/Change-Detection-System-Examples/main/version_1_files/employee.csv"
    csv_file_2 = "https://raw.githubusercontent.com/alex-randles/Change-Detection-System-Examples/main/version_2_files/employee-v6.csv"
    xml_file_1 = "https://raw.githubusercontent.com/alex-randles/Change-Detection-System-Examples/main/version_1_files/student.xml"
    xml_file_2 = "https://raw.githubusercontent.com/alex-randles/Change-Detection-System-Examples/main/version_2_files/student.xml"
    form_details = {
        'XML-URL-1': xml_file_1,
        'XML-URL-2': xml_file_2,
        'insert-threshold': '10', 'delete-threshold': '0',
        'move-threshold': '0', 'datatype-threshold': '0',
        'merge-threshold': '0', 'update-threshold': '0',
        'detection-end': '2022-07-10',
        'email-address': 'alexrandles0@gmail.com',
        "user-id": "2",
                }
    cd = DetectChanges(user_id=2, form_details=form_details)

