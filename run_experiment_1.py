from modules.validate_quality import ValidateQuality
from modules.validation_report import ValidationReport
import os
import sys
import rdflib
import time
import json
import multiprocessing

jobs = []

directory = "/home/alex/Desktop/Evaluation-1 (Validation Reports)/"


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
            if file.endswith(".ttl") and file != "validation_report.ttl":
                mapping_file = str_sub_directory + "/" + file
                output_file = str_sub_directory + "/validation_report.ttl"
                print(mapping_file)
                print(output_file)
                t = ValidateQuality(mapping_file)
                validation_results = t.validation_results
                ValidationReport(validation_results, output_file, mapping_file)
                break



