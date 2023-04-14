from modules.validate_quality import ValidateQuality
from modules.validation_report import ValidationReport
import json
import multiprocessing

jobs = []


def remove_reports():
    for file in os.listdir(directory):
        mapping_directory = os.fsdecode(file)
        if os.path.isdir(directory + str(file)):
            sub_directory = os.fsencode(directory + str(file))
            str_sub_directory = sub_directory.decode('utf-8')
            # print(str_sub_directory)
            files = os.listdir(str_sub_directory)
            for file in files:
                if file == "validation_report.ttl":
                    file_path = str_sub_directory + "/" + file
                    os.remove(file_path)
exit()

import os
import sys
from rdflib import *
import time
import json
directory = "/home/alex/Desktop/Evaluation-1 (Validation Reports)/"
i = 0

def validate_mapping(mapping_file ,output_file):
    t = ValidateQuality(mapping_file)
    validation_results = t.validation_results
    ValidationReport(validation_results, output_file, mapping_file)


for file in os.listdir(directory):
    mapping_directory = os.fsdecode(file)
    mapping_id = mapping_directory.split("(")[0]
    mapping_project = mapping_directory.split("(")[-1].split(")")[0]
    if os.path.isdir(directory + str(file)):
        sub_directory = os.fsencode(directory + str(file))
        str_sub_directory = sub_directory.decode('utf-8')
        # print(str_sub_directory)
        files = os.listdir(str_sub_directory)
        for file in files:
            if file.endswith(".ttl"):
                mapping_file = str_sub_directory + "/" + file
                output_file = str_sub_directory + "/validation_report.ttl"
                process = multiprocessing.Process(target=validate_mapping, args=(mapping_file, output_file))
                process.start()
                jobs.append(process)
                print(i)

for j in jobs:
    j.join()



