# imported modules
# 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 token
import time
import shutil
import csv
import pickle
from datetime import datetime
from pathlib import Path
from fs.osfs import OSFS
from fs import open_fs
from datetime import datetime
import calendar
import rdflib
from rdflib import URIRef
from flask import Flask, render_template, request, send_file, send_from_directory, session, jsonify, g, Markup, url_for
from flask_caching import Cache
from werkzeug import  Response
from werkzeug.utils import secure_filename, redirect
import os
import copy
from modules import *
import modules.fetch_vocabularies
import modules.refinements
import modules.validate_quality
import modules.serialize
import modules.validation_report
import modules.visualise_results
# from modules.common import cache
import timeit
import re
import sqlite3
#   function redirect()
# {
#    if(document.getElementById("accept-form").checked == true)
#    {
#         window.location.href = '/index';
#    }
# }

from modules.fetch_vocabularies import FetchVocabularies
from modules.refinements import Refinements
from modules.serialize import TurtleSerializer
from modules.validate_quality import ValidateQuality
from modules.validation_report import ValidationReport
from modules.visualise_results import VisualiseResults

# cache = Cache(config={'CACHE_TYPE': 'SimpleCache'})
# app = Flask(__name__)
# app.config['SESSION_TYPE'] = 'filesystem'
# app.url_map.strict_slashes = False
# cache.init_app(app=app, config={"CACHE_TYPE": "filesystem",'CACHE_DIR': Path('/tmp')})

from flask_session import Session
from datetime import timedelta

app = Flask(__name__)
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=5)

# The maximum number of items the session stores
# before it starts deleting some, default 500
app.config['SESSION_FILE_THRESHOLD'] = 100
app.url_map.strict_slashes = False
app.config['SECRET_KEY'] = "hello"
sess = Session()
sess.init_app(app)

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# to prevent caching of previous result
file_counter = 0
app.config["allowed_file_extensions"] = ["ttl"]
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.secret_key = os.urandom(24)
home_fs = OSFS("..")

class API:

    def __init__(self):
        app.run(host="127.0.0.1", port="5000", threaded=True, debug=True)
        # if timeout error occurs
        # try:
        #     app.run(host="127.0.0.1", port="5000", threaded=True, debug=True)
        # except:
        #     app.run(host="127.0.0.1", port="5000", threaded=True, debug=True)

    # @app.route("/return-combined-report/", methods=['GET', 'POST'])
    # def download_combined_report():
    #     filenames = ['refined_mapping.ttl', 'validation_report.ttl']
    #     prefixes = []
    #     rdf_lines = []
    #     with open('combined_report.ttl', 'w') as outfile:
    #         for fname in filenames:
    #             with open(fname) as infile:
    #                 for line in infile:
    #                     if line.startswith("@prefix"):
    #                         prefixes.append(line.strip())
    #                     else:
    #                         rdf_lines.append(line)
    #             rdf_lines.append("\n\n")
    #         # remove duplicate prefixes
    #         new_prefixes = []
    #         for line in prefixes:
    #             if line not in new_prefixes:
    #                 prefix_value = line.split()[-2]
    #                 if not any(prefix in prefix_value for prefix in prefixes):
    #                     new_prefixes.append(line)
    #         # write prefixes first then rdf
    #         print(len(new_prefixes))
    #         for item in new_prefixes:
    #             outfile.write("%s\n" % item)
    #         for item in rdf_lines:
    #             outfile.write("%s" % item)
    #     return send_file("combined_report.ttl", attachment_filename="quality_report.ttl", as_attachment=True,
    #                      cache_timeout=0)

    # @app.errorhandler(Exception)
    # def handle_error(error):
    #     print("error handler ", error)
    #     home_fs.writetext('progress_counter.txt', "0")
    #     return render_template("index.html", error_type="Sever timeout error!",
    #                            error_message="Upload the mapping file again")

    @staticmethod
    def validate_RDF(filename):
        try:
            rdflib.Graph().parse(filename, format="ttl")
            return True
        except rdflib.plugins.parsers.notation3.BadSyntax as exception:
            return False

    @staticmethod
    def get_current_report_number():
        # a function to get the unique number for each report
        report_file = "report_counter.txt"
        with home_fs.open(report_file) as progress_file:
            current_report_number = str(progress_file.read())
            return current_report_number

    @staticmethod
    def update_report_number():
        # a function to get the unique number for each report
        report_file = "report_counter.txt"
        with home_fs.open(report_file) as progress_file:
            current_report_number = str(progress_file.read())
            new_report_number = str(int(current_report_number) + 1)
            home_fs.writetext(report_file, new_report_number)
            return current_report_number

    @staticmethod
    def run_assessment(filename):
        start_time = timeit.default_timer()
        quality_assessment = ValidateQuality(filename)
        elapsed = timeit.default_timer() - start_time
        print("ASSESSMENT TIMING IN API", elapsed)
        # exit()
        return quality_assessment

    @staticmethod
    def create_validation_report(more_info_data):
        cache_find_location = cache.get("find_violation_location")
        cache_validation_result = cache.get("validation_result")
        cache_validation_report_file = cache.get("validation_report_file")
        cache_mapping_file = cache.get("mapping_file")
        formatted_validation_result = copy.deepcopy(cache_validation_result)
        for violation_ID in formatted_validation_result.keys():
            violation_location = formatted_validation_result[violation_ID]["location"]
            new_location = cache_find_location(violation_location)
            formatted_validation_result[violation_ID]["location"] = new_location
        timestamp = cache.get("timestamp")
        ValidationReport(formatted_validation_result, cache_validation_report_file,
                         cache_mapping_file, more_info_data, timestamp)

    @app.route("/return-validation-report/", methods=['GET', 'POST'])
    def download_validation_report():
        cache_validation_report_file = cache.get("validation_report_file")
        current_report_number = API.get_current_report_number()
        quality_report_filename = "quality-report-{}.ttl".format(current_report_number)
        participant_id = cache.get("participant_id")
        quality_report_filename = "quality-report-participant-{}.ttl".format(participant_id)
        API.save_cache_file(cache_validation_report_file, quality_report_filename)
        return send_file(cache_validation_report_file,
                         attachment_filename=quality_report_filename,
                         as_attachment=True, cache_timeout=0)

    @staticmethod
    def split_camel_case(word):
        splitted = re.sub('([A-Z][a-z]+)', r' \1', re.sub('([A-Z]+)', r' \1', word)).split()
        result = " ".join(splitted)
        return result

    @staticmethod
    def add_ontology_file(ontology_file):
        for file in ontology_file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            # if uploaded file is not valid RDF
            error_message = FetchVocabularies.create_local_vocabulary(file_path)
            if error_message:
                return error_message

    @staticmethod
    def update_time_log(participant_id, message):
        current_time = datetime.now().time()
        with open('time-log.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([participant_id, message, current_time])
        # time_log_file = "time_log.txt"
        # f = open(time_log_file, "a")
        # print("updating time log")
        # log = "Participant: {} message: {} time: {}\n".format(participant_id, message, time)
        # f.write(log)
        # f.close()

    @staticmethod
    def create_time_log():
        with open('time-log.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Participant ID", "Task", "Time"])


    @app.route('/progress')
    def progress():
        def generate():
            with home_fs.open('progress_counter.txt') as progress_file:
                current_progress = str(progress_file.read())
                yield "data:" + current_progress + "\n\n"
        return Response(generate(), mimetype='text/event-stream')

    @staticmethod
    def add_consent_information(name, participant_id):
        consent_file = "consent_information.csv"
        current_time = datetime.now()
        with open(consent_file, 'a', newline='\n') as file:
            writer = csv.writer(file)
            writer.writerow([name, participant_id, current_time])

    @app.route(("/information-sheet"), methods=["GET", "POST"])
    def information_sheet():
        if request.method == "GET":
            return render_template("information_sheet.html") 
        else:
            pass


    @app.route(("/task-sheet"), methods=["GET", "POST"])
    def task_sheet():
        if request.method == "GET":
            return render_template("task_sheet.html")
        else:
            pass

    @app.route(("/informed-consent"), methods=["GET", "POST"])
    def informed_consent():
        if request.method == "GET":
            return render_template("informed_consent.html")
        else:
            name = request.form["name"]
            accept_form = request.form["accept-form"]
            print(name==None)
            # if not name:
            #     return render_template("informed_consent.html", error_message="Please enter your name!")
            # elif not accept_form:
            #     return render_template("informed_consent.html", error_message="Please provide consent!")
            participant_id = cache.get("participant_id")
            print(request.form)
            # if request.form.get("accept-form") and request.form.get()
            API.add_consent_information(name, participant_id)
            return redirect(url_for("task_sheet"))
        
    @app.route(("/PSSUQ"), methods=["GET", "POST"])
    def complete_questionnaire():
        if request.method == "GET":
            print(request.form)
            return render_template("PSSUQ.html")
        else:
            print("ENTERINGNGNG")
            pass

    @app.route(("/completion"), methods=["GET", "POST"])
    def experiment_completion():
        if request.method == "GET":
            participant_id = cache.get("participant_id")
            # participant_id = session["participant_id"]
            return render_template("completion_screen.html", participant_id=participant_id)
        else:
            return render_template("completion_screen.html")

    @app.route(("/"), methods=["GET", "POST"])
    def login():
        # return redirect(url_for("read_mapping"))
        API.create_time_log()
        if request.method == "GET":
            return render_template("login_page.html")
        elif request.method == "POST":
            participant_id = request.form["participant_id"]
            password = request.form["password"]
            # participant_details = {"123" : "123"}
            participant_details = {}
            with open("username-passwords.txt") as f:
                for line in f:
                    (key, val) = line.split()
                    participant_details[key] = val
            print(participant_details)
            correct_password = participant_details.get(participant_id)
            print(participant_id, "FORM PARTICIPANT ID")
            if correct_password == password:
                # cache.set("participant_id", participant_id)
                session["participant_id"] = participant_id
                API.update_time_log(int(participant_id), "User logged in")
                return redirect(url_for("information_sheet"))
                return redirect(url_for('read_mapping'))
            else:
                return render_template("login_page.html", error_message="Incorrect Password or Username!")


    @app.route("/index", methods=["GET", "POST"])
    def read_mapping():
        # print(session["participant_id"])
        # return redirect(url_for("experiment_completion"))
        # return redirect(url_for('complete_questionnaire'))
        if request.method == "POST":
            # participant_id = request.form["participant_id"]
            # cache.set("participant_id", participant_id)
            API.update_time_log(session.get("participant_id"), "Mapping uploaded")
            # get file uploaded
            file = request.files['mapping_file']
            ontology_file = request.files.getlist('ontology_file')
            if ontology_file[0].filename != "":
                # if ontology added successfully
                error_message = API.add_ontology_file(ontology_file)
                if error_message:
                    return render_template("index.html", error_message=error_message,
                                           error_type="Local ontology upload Error!")
            filename = secure_filename(file.filename)
            if filename and len(filename) > 1:
                file_extension = (filename.split(".")[1]).lower()
                mapping_file = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                session["mapping_file"] = mapping_file
                file.save(mapping_file)
                if file and file_extension in app.config["allowed_file_extensions"]:
                    if API.validate_RDF(mapping_file):
                        # try:
                            # get timestamp
                            current_time = time.gmtime()
                            timestamp = str(calendar.timegm(current_time))
                            session["timestamp"] = timestamp
                            home_fs.writetext('progress_counter.txt', "10")
                            API.update_report_number()
                            # cache.set("assessment_result", None)
                            assessment_result = API.run_assessment(mapping_file)
                            pickled_object = pickle.dumps(assessment_result)
                            session["assessment_result"] = pickled_object
                            cache.set("assessment_result", assessment_result)
                            validation_result = assessment_result.validation_results
                            cache.set("validation_result", validation_result)
                            triple_references = assessment_result.triple_references
                            cache.set("triple_references", triple_references)
                            more_info_data = request.form
                            cache.set("more_info_data", more_info_data)
                            # if violations exist within validation result
                            if len(validation_result) > 0 :
                                validation_report_file = "validation_report.ttl"
                                cache.set("validation_report_file", validation_report_file)
                                cache.set("triple_references", triple_references)
                                cache.set("namespaces", assessment_result.namespaces)
                                # user wants to add more info to reports
                                add_information = request.form.get("add-information")
                                cache.set("add_information", add_information)
                                mapping_graph = assessment_result.mapping_graph
                                cache.set("mapping_graph", assessment_result.mapping_graph)
                                find_violation_location = assessment_result.find_violation_location
                                cache.set("find_violation_location", find_violation_location)
                                detailed_metric_information = assessment_result.detailed_metric_information
                                metric_descriptions = assessment_result.metric_descriptions
                                refinements = Refinements(timestamp, validation_result, triple_references, mapping_graph)
                                suggested_refinements = refinements.provide_suggested_refinements()
                                cache.set("suggested_refinements", suggested_refinements)
                                serializer = TurtleSerializer(mapping_graph)
                                parse_violation_value = serializer.parse_violation_value
                                find_prefix = assessment_result.find_prefix
                                cache.set("find_prefix", find_prefix)
                                API.create_validation_report(more_info_data)
                                get_triple_map_id = assessment_result.get_triple_map_id
                                cache.set("get_triple_map_id", get_triple_map_id)
                                API.update_time_log(cache.get("participant_id"), "Assessment information generated")
                                return render_template("assessment_result.html",
                                                       display_violation = serializer.display_violation,
                                                       metric_descriptions=metric_descriptions,
                                                       len=len(validation_result),
                                                       assessment_report=validation_result,
                                                       find_prefix=find_prefix ,
                                                       suggested_refinements=suggested_refinements,
                                                       find_violation_location=find_violation_location,
                                                       split_camel_case=API.split_camel_case,
                                                       detailed_metric_information=detailed_metric_information,
                                                       validation_result=cache.get("validation_result"),
                                                       find_bNode_reference=assessment_result.find_blank_node_reference,
                                                       get_triple_map_ID=assessment_result.get_triple_map_id,
                                                       parse_violation_value=parse_violation_value
                                                       )
                            else:
                                API.create_validation_report(more_info_data)
                                return render_template("no_violations.html")
                        # except Exception as e:
                        #     print(e)
                        #     home_fs.writetext('progress_counter.txt', "0")
                        #     return render_template("index.html", error_message=str(e))
                    else:
                        return render_template("index.html", error_type="Mapping file upload",
                                               error_message="Mapping file contains invalid RDF")
                else:
                    return render_template("index.html", error_type="File must be turtle (ttl) format",
                                           error_message="Please upload a mapping File!")

            else:
                return render_template("index.html", error_type="No mapping file error",
                                       error_message="Please upload a File!")
        else:
            home_fs.writetext('progress_counter.txt', '0')
            return render_template("index.html")

    @staticmethod
    def refinements_selected(selected_refinements):
        # check if the user has selected all refinements to be manual or not
        selected_options = [refinement_selected for (ID, refinement_selected) in selected_refinements.items()]
        for option in selected_options:
            if option != "Manual":
                return True
        return False

    @app.route("/refinement", methods=["GET", "POST"])
    def get_refinements():
        cache_mapping_graph = cache.get("mapping_graph")
        cache_assessment_result = cache.get("assessment_result")
        cache_triple_references = cache.get("triple_references")
        cache_validation_result = cache.get("validation_result")
        cache_add_information = cache.get("add_information")
        cache_mapping_file = cache.get("mapping_file")
        cache_validation_report_file = cache.get("validation_report_file")
        cache_namespaces = cache.get("namespaces")
        cache_find_violation = cache.get("find_violation_location")
        more_info_data = cache.get("more_info_data")
        find_prefix = cache.get("find_prefix")
        timestamp = cache.get("timestamp")
        if request.method == "POST":
            API.update_time_log(cache.get("participant_id"), "Refinements executed")
            # create validation report incase user goes back and then forward,not to include multiple refinement queries
            API.create_validation_report(more_info_data)
            print(request.form.to_dict(), "REQUEST FORM INFO")
            cache_refinement_values = cache.get("refinement_values")
            print(cache_refinement_values, "CACHE REFINEMENT VALUES ")
            # refinements = Refinements(cache_validation_result, cache_triple_references, cache_mapping_graph,
            #                           cache_add_information)
            refinements = Refinements(timestamp, cache_validation_result, cache_triple_references, cache_mapping_graph,
                                      cache_add_information)
            bar_chart_html = VisualiseResults.chart_dimensions(cache_validation_result)
            refinements.process_user_input(request.form.to_dict(), cache_refinement_values, cache_mapping_file,
                                           cache_mapping_graph, cache_validation_report_file)
            API.update_time_log(cache.get("participant_id"), "Quality profile generated")
            return render_template("quality_profile.html",  bar_chart_html=bar_chart_html)
        else:
            API.update_time_log(cache.get("participant_id"), "Refinements selected")
            selected_refinements = request.values
            refinement_options = API.refinements_selected(selected_refinements)
            if refinement_options:
                # refinements = Refinements(session.get("validation_result"), triple_references, cache_mapping_graph,
                #                           session.get("add_information"))
                refinements = Refinements(timestamp, cache_validation_result, cache_triple_references, cache_mapping_graph,
                                          cache_add_information)
                refinement_values = refinements.provide_refinements(selected_refinements)
                cache.set("refinement_values", refinement_values)
                print("REFINEMENT VALUES", refinement_values)
                # find_prefix = refinements.find_prefix
                refinement_descriptions = refinements.refinement_descriptions
                find_triple_map = refinements.find_triple_map
                find_violation_location = cache_find_violation
                serializer = TurtleSerializer(cache_mapping_graph)
                parse_violation_value = serializer.parse_violation_value
                display_violation = serializer.display_violation
                get_triple_map_id = cache.get("get_triple_map_id")
                assessment_result = cache.get("assessment_result")
                metric_descriptions = assessment_result.metric_descriptions
                detailed_metric_information = assessment_result.detailed_metric_information
                suggested_refinements = cache.get("suggested_refinements")
                return render_template("refinements.html",
                                       split_camel_case=API.split_camel_case,
                                       refinement_descriptions=refinement_descriptions,
                                       find_prefix=find_prefix,
                                       validation_result=cache_validation_result,
                                       namespaces=cache_namespaces,
                                       refinements=refinement_values,
                                       prefix_values=refinements.prefix_values,
                                       display_violation=display_violation,
                                       find_triple_map=find_triple_map,
                                       find_violation_location=find_violation_location,
                                       assessment_report=cache_validation_result,
                                       parse_violation_value=parse_violation_value,
                                       get_triple_map_ID=get_triple_map_id,
                                       metric_descriptions=metric_descriptions,
                                       detailed_metric_information=detailed_metric_information,
                                       suggested_refinements=suggested_refinements
                                       )
            else:
                # if no refinements return quality profile and give option to go back and add refinements
                bar_chart_html = VisualiseResults.chart_dimensions(cache_validation_result)
                API.update_time_log(cache.get("participant_id"), "Quality profile generated")
                return render_template("no_refinements.html", bar_chart_html=bar_chart_html)

    @staticmethod
    def save_cache_file(filename, cache_filename):
        shutil.copy2(filename, '/home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/modules/participant_cache/' + cache_filename)


    @app.route("/return-refined-mapping/", methods=['GET', 'POST'])
    def download_refined_mapping():
        # refined_mapping_file_name = cache.get("mapping_file").split(".")[0] + "_refined_mapping.ttl"
        mapping_file = "static/uploads/video_demo.ttl"
        file_name = mapping_file.split("/")[-1]
        refined_mapping_filename = file_name.split(".")[0] + "-refined_mapping." + file_name.split(".")[-1]
        participant_id = cache.get("participant_id")
        refined_mapping_filename = "refined-mapping-participant-{}.ttl".format(participant_id)
        # shutil.copy2('refined_mapping.ttl', '/home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/modules/participant_cache/' + refined_mapping_filename)
        API.save_cache_file('refined_mapping.ttl', refined_mapping_filename)
        API.update_time_log(cache.get("participant_id"), "Refined mapping exported")
        return send_file("refined_mapping.ttl", attachment_filename=refined_mapping_filename, as_attachment=True,
                         cache_timeout=0)

    @app.route("/sample_mapping/", methods=["GET"])
    def test_sample_mapping():
        return render_template("sample_mapping.html")

    @app.route("/return-refinement-report/", methods=['GET', 'POST'])
    def download_refinement_report():
        current_report_number = API.get_current_report_number()
        cache_validation_report_file = cache.get("validation_report_file")
        validation_report_filename = "validation-report-{}.ttl".format(current_report_number)
        participant_id = cache.get("participant_id")
        validation_report_filename = "validation-report-participant-{}.ttl".format(participant_id)
        API.update_time_log(cache.get("participant_id"), "Validation report exported")
        API.save_cache_file(cache_validation_report_file, validation_report_filename)
        return send_file(cache_validation_report_file,
                         attachment_filename=validation_report_filename,
                         as_attachment=True, cache_timeout=0)

    @app.route("/return-sample-mapping/", methods=['GET', 'POST'])
    def download_sample_mapping():
        sample_mapping = "static/documents/sample_mapping.ttl"
        return send_file(sample_mapping,
                         attachment_filename="sample_mapping.ttl",
                         as_attachment=True, cache_timeout=0)



    @app.route("/return-MQV-ontology/", methods=['GET', 'POST'])
    def download_MQV_ontology():
        MQV_ontology = "./static/MQV_ontology.ttl"
        return send_file(MQV_ontology, attachment_filename="MQV_ontology.ttl", as_attachment=True,
                         cache_timeout=0)

    @app.route("/download-file/", methods=["GET"])
    def return_file():
        print("Downloading file.......")
        download_path = "test_output.ttl"
        return send_file(download_path, as_attachment=True, cache_timeout=0)


if __name__ == "__main__":
    # start api
    try:
        API()
    except:
        API()