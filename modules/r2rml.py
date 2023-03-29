run_command = 'java -jar "./static/change_detection_cache/r2rml/target/r2rml-fat.jar" "./static/change_detection_cache/r2rml/config.properties"'
r2rml_config = """connectionURL =
mappingFile = {}
CSVFiles = {};
outputFile = {}
format= TRIG     """""
r2rml_input_files = "./static/change_detection_cache/changes_info/contact_details.csv;./static/change_detection_cache/changes_info/changes_detected.csv;./static/change_detection_cache/changes_info/notification_details.csv"
r2rml_output_file = "./static/change_detection_cache/change_graphs/{}.trig"
r2rml_config_file = "./static/change_detection_cache/r2rml/config.properties"
r2rml_run_file = "./static/change_detection_cache/r2rml/run.sh"
graph_directory = "./static/change_detection_cache/change_graphs/"
user_graph_directory = "./static/change_detection_cache/changes_info/"
user_directory = "./static/change_detection_cache/changes_info/"
xml_diff_file = "./static/change_detection_cache/changes_info/diff.xml"
notification_details_csv = "./static/change_detection_cache/changes_info/notification_details.csv"
mapping_file = "./static/change_detection_cache/mappings/CSV_change_detection_mapping.ttl"
upload_directory = "./static/uploads/"
changes_detected_csv = "./static/change_detection_cache/changes_info/changes_detected.csv"