import os
import sys
from rdflib import *
import time
import json
from modules.validate_quality import ValidateQuality
directory = "/home/alex/Desktop/Evaluation-1 (Validation Reports)/"
for file in os.listdir(directory):
    mapping_directory = os.fsdecode(file)
    mapping_id = mapping_directory.split("(")[0]
    mapping_project = mapping_directory.split("(")[-1].split(")")[0]
    print(directory + str(file))
    if os.path.isdir(directory + str(file)):
        sub_directory = os.fsencode(directory + str(file))
        str_sub_directory = sub_directory.decode('utf-8')
        print(str_sub_directory)
        for sub_directory_file in os.listdir(str_sub_directory):
            print(sub_directory_file)
            if "group" not in str_sub_directory:
                full_file_path = str_sub_directory + "/" + sub_directory_file
                print(full_file_path)
                if sub_directory_file.endswith(".ttl") and sub_directory_file != "refined_mapping.ttl":
                    RR = Namespace("http://www.w3.org/ns/r2rml#")
                    try:
                        g = Graph().parse(full_file_path, format="ttl")
                        t = ValidateQuality(full_file_path)
                        print(json.dumps(t.validation_results, indent=4))
                        if len(list(g.triples((None, RR.predicateObjectMap, None)))) > 1:
                            t = ValidateQuality(full_file_path)
                            print(json.dumps(t.validation_results, indent=4))
                            t.create_validation_report(str_sub_directory + "/" + "validation_report_1.ttl")
                    except Exception as e:
                        print(e)
                        sys.exit(1)
