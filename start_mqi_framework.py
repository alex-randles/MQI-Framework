# imported modules
# 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 token
import calendar
import shortuuid
import copy
import os
import pickle
import random
import re
import shutil
import string
import time
import timeit
import urllib
import multiprocessing
import pandas as pd
from collections import OrderedDict, defaultdict
from datetime import datetime
from datetime import timedelta
from functools import wraps
from os import listdir
from os.path import isfile, join

import rdflib
from flask import Flask, render_template, request, send_file, session, url_for, \
    flash, Markup
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename, redirect

from modules.detect_changes import DetectChanges
from modules.display_changes import DisplayChanges
from modules.detect_mapping_impact import DetectMappingImpact
from modules.fetch_vocabularies import FetchVocabularies
from modules.refinements import Refinements
from modules.serialize import TurtleSerializer
from modules.validate_quality import ValidateQuality
from modules.validation_report import ValidationReport
from modules.visualise_results import VisualiseResults

app = Flask(__name__)
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=5)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.sqlite3"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# The maximum number of items the session stores
# before it starts deleting some, default 500
app.config['SESSION_FILE_THRESHOLD'] = 100
app.url_map.strict_slashes = False
app.config['SECRET_KEY'] = "hello"
sess = Session()
sess.init_app(app)

UPLOAD_FOLDER = 'static/uploads/mappings/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# to prevent caching of previous result
file_counter = 0
app.config["allowed_file_extensions"] = ["ttl"]
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.secret_key = os.urandom(24)


def create_app():
    return app


db = SQLAlchemy(app)


def login_required(f):
    # the user must be logged in to access pages
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("logged_in", None) is None:
            flash("You must log in to access this page!")
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    # the user must be logged in to access pages
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("participant_id", None) is "alex_randles":
            flash("You must log in as administrator access this page!")
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function

class users(db.Model):
    participant_id = db.Column("id", db.Integer, primary_key=True)
    # will default to variable name if none defined
    password = db.Column(db.String(100))
    has_consented = db.Column(db.Boolean, default=False)
    time_consented = db.Column(db.String(100))
    name = db.Column(db.String(100))
    logged_in = db.Column(db.String(100))
    mapping_uploaded = db.Column(db.String(100))
    information_sheet = db.Column(db.String(100))
    task_sheet = db.Column(db.String(100))
    PSSUQ = db.Column(db.String(100))
    experiment_completed = db.Column(db.String(100))
    experiment_started = db.Column(db.String(100))
    assessment_information_generated = db.Column(db.String(100))
    refinements_executed = db.Column(db.String(100))
    refined_mapping_exported = db.Column(db.String(100))
    validation_report_exported = db.Column(db.String(100))
    quality_report_exported = db.Column(db.String(100))
    quality_profile_generated = db.Column(db.String(100))
    current_progress = db.Column(db.String(100))
    quality_report_file = db.Column(db.Text)
    validation_report_file = db.Column(db.Text)
    refined_mapping_file = db.Column(db.Text)

    # for col in ['logged_in', 'home_page_accessed', 'description']:
    #     setattr(db, col, None)
    def __init__(self, password):
        self.password = password

class API:

    def __init__(self):
        app.add_template_filter(API.mapping)
        app.run(host="127.0.0.1", port=5000, threaded=True, debug=True)
        # if timeout error occurs
        # try:
        #     app.run(host="127.0.0.1", port="5000", threaded=True, debug=True)
        # except:
        #     app.run(host="127.0.0.1", port="5000", threaded=True, debug=True)

    @app.errorhandler(404)
    def error_404(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def error_500(error):
        print(error)
        return render_template("errors/500.html"), 500

    # @app.errorhandler(Exception)
    # def general_errors(error):
    #     print(error)
    #     return render_template("errors/500.html"), 500

    @app.errorhandler(403)
    def error_403(error):
        return render_template("errors/403.html"), 403

    @staticmethod
    def validate_RDF(filename):
        print("testing")
        try:
            rdflib.Graph().parse(filename, format="ttl")
            return True
        except Exception as e:
            return False

    @staticmethod
    def run_assessment(filename):
        quality_assessment = ValidateQuality(filename)
        return quality_assessment

    @staticmethod
    def create_validation_report(more_info_data):
        cache_find_location = session.get("find_violation_location")
        cache_validation_result = session.get("validation_result")
        cache_validation_report_file = session.get("validation_report_file")
        cache_mapping_file = session.get("mapping_file")
        formatted_validation_result = copy.deepcopy(cache_validation_result)
        for violation_ID in formatted_validation_result.keys():
            violation_location = formatted_validation_result[violation_ID]["location"]
            new_location = cache_find_location(violation_location)
            formatted_validation_result[violation_ID]["location"] = new_location
        timestamp = session.get("timestamp")
        ValidationReport(formatted_validation_result, cache_validation_report_file,
                         cache_mapping_file, more_info_data, timestamp)

    @staticmethod
    def split_camel_case(word):
        split_word = re.sub('([A-Z][a-z]+)', r' \1', re.sub('([A-Z]+)', r' \1', word)).split()
        result = " ".join(split_word)
        return result

    @staticmethod
    def store_ontology_file(ontology_file):
        for file in ontology_file:
            filename = secure_filename(file.filename)
            file_path = "./static/uploads/local_ontologies/" + filename
            file.save(file_path)
            # if uploaded file is not valid RDF
            error_message = FetchVocabularies.store_local_vocabulary(file_path)
            if error_message:
                return error_message

    @app.route(("/"), methods=["GET", "POST"])
    @app.route(("/welcome"), methods=["GET", "POST"])
    def welcome():
        return redirect(url_for("component_choice"))

    @app.route(("/component-choice"), methods=["GET"])
    def component_choice():
        if request.method == "GET":
            participant_id = session.get("participant_id")
            return render_template("component_choice.html", participant_id=participant_id)

    @app.route(("/format-choice"), methods=["GET"])
    def format_choice():
        if request.method == "GET":
            participant_id = session.get("participant_id")
            return render_template("change_detection/data_format_choice.html", participant_id=participant_id)


    @app.route("/return-user-graph/", methods=['GET', 'POST'])
    def download_user_graph():
        # refined_mapping_file_name = session.get("mapping_file").split(".")[0] + "_refined_mapping.ttl"
        participant_id = session.get("participant_id")
        user_graph_file = "/home/alex/Desktop/Mapping-Quality-Framework/change_detection/database_change_detection/user_files/graphs/user_{}.trig".format(
            participant_id)
        return send_file(user_graph_file, attachment_filename="user_graph.trig", as_attachment=True,
                         cache_timeout=0)

    @app.route(("/CSV-changes"), methods=["GET", "POST"])
    def detect_CSV_changes():
        participant_id = session.get("participant_id")
        if request.method == "GET":
            session["change_process_executed"] = False
            return render_template("change_detection/CSV_file_details.html", participant_id=participant_id)
        elif request.method == "POST":
            # create a graph with 3 named graphs for user
            form_id = str(shortuuid.ShortUUID().random(length=12))
            session["form_id"] = form_id
            session["change_process_executed"] = True
            form_details = request.form
            change_detection = DetectChanges(participant_id, form_details)
            # invalid URL
            if change_detection.error_code == 1:
                flash("Invalid URL. Try again and make sure it is the raw file Github link - if using Gihtub.")
                return redirect(url_for('detect_CSV_changes'))
            elif change_detection.error_code == 2:
                flash("Incorrect file format.")
                return redirect(url_for('detect_CSV_changes'))
            else:
                return redirect(url_for('change_detection'))

    @app.route(("/xml-changes"), methods=["GET", "POST"])
    def detect_xml_changes():
        participant_id = session.get("participant_id")
        if request.method == "GET":
            session["change_process_executed"] = False
            return render_template("change_detection/XML_file_details.html", participant_id=participant_id)
        elif request.method == "POST":
            session["change_process_executed"] = True
            form_details = request.form
            change_detection = DetectChanges(participant_id, form_details)
            if change_detection.error_code == 1:
                flash("Invalid URL. Try again and make sure it is the raw file Github link - if using Gihtub.")
                return redirect(url_for('detect_xml_changes'))
            elif change_detection.error_code == 2:
                flash("Incorrect file format.")
                return redirect(url_for('detect_xml_changes'))
            else:
                return redirect(url_for('change_detection'))

    @staticmethod
    def mapping(test_dict):
        return isinstance(test_dict, dict)

    @staticmethod
    def get_session_id():
        # return random.randint(0,1000000000)
        return random.randint(0,1000000000)

    # generate a html file with mapping impacted details
    @app.route('/mappings_impacted/<mapping_unique_id>/<graph_id>', methods=['GET', 'POST'])
    def mappings_impacted(mapping_unique_id=None, graph_id=None):
        mapping_graph = session.get("mapping_details").get(int(mapping_unique_id))
        graph_id = int(graph_id.split(".")[0])
        change_graph_details = session.get("graph_details").get(graph_id)
        impact = DetectMappingImpact(mapping_graph, change_graph_details.get("filename"))
        mapping_impact = impact.mapping_impact
        change_template_colors = {
            "insert": "success",
            "delete": "danger",
            "move": "primary",
        }
        change_type_banners = {
            "insert": "Column inserted",
            "delete": "Column deleted",
            "move": "Source data moved",
        }
        mapping_filename = mapping_graph.get("filename")
        return render_template("change_detection/mappings_impacted.html",
                               change_template_colors=change_template_colors,
                               mapping_id=mapping_unique_id,
                               mapping_impact=mapping_impact,
                               mapping_filename=mapping_filename,
                               change_type_banners=change_type_banners,
                               change_graph_details=change_graph_details)

    # generate a html file with all the thresholds for a specific process
    @app.route('/process_thresholds/<graph_filename>', methods=['GET', 'POST'])
    def process_thresholds(graph_filename):
        # reassign as pycharm underlines as error
        str_graph_filename = str(graph_filename)
        participant_id = session.get("participant_id")
        notification_thresholds = DisplayChanges.generate_thresholds_html(str_graph_filename, participant_id)
        graph_id =  "".join(str_graph_filename.split("_")[-1].split("-")[1:]).split(".")[0]
        change_graph_details = session.get("graph_details")
        return render_template("change_detection/notification_thresholds.html",
                               participant_id=participant_id,
                               graph_id=graph_id,
                               graph_filename=graph_filename,
                               change_graph_details=change_graph_details,
                               notification_thresholds=notification_thresholds)

    # view change detection processes running by a user
    @app.route(("/change-processes"), methods=["GET", "POST"])
    def change_detection():
        participant_id = 1
        # no alert if no process executed
        if request.method == "GET":
            change_process_executed = session.get("change_process_executed")
            session["change_process_executed"] = False
            # get graph details for user
            # try:
            display_changes = DisplayChanges(participant_id)
            error_code = display_changes.error_code
            if error_code == 0:
                user_graph_details = display_changes.graph_details
                mapping_details = display_changes.mapping_details
                session["graph_details"] = user_graph_details
                session["mapping_details"] = mapping_details
                return render_template(
                    "change_detection/change_results.html",
                    participant_id=participant_id,
                    change_process_executed=change_process_executed,
                    process_removed=False,
                    graph_details=OrderedDict(sorted(user_graph_details.items(), key=lambda t: t[0])),
                    mapping_details=OrderedDict(sorted(mapping_details.items(), key=lambda t: t[0])),
                    # mappings_impacted = mappings_impacted,
                )
            # this is the error for when an uploaded file is not valid mapping
            # except rdflib.plugins.parsers.notation3.BadSyntax as e:
            # SPARQLWrapper.SPARQLExceptions.QueryBadFormed - incorrect SPARQL query
            # pass
            else:
                return "<h1>Error!!!!!</h1>"
        else:
            uploaded_file = request.files['mapping-file']
            if uploaded_file.filename != '':
                file_version = API.iterate_user_files(participant_id)
                filename = uploaded_file.filename + "_{}-{}".format(participant_id, file_version)
                filename = os.path.join(app.config['UPLOAD_FOLDER'] + session.get("participant_id") + "/", filename)
                uploaded_file.save(filename)
                mapping_uploaded = True
            else:
                mapping_uploaded = False
            # mapping uploaded = True to display banner
            # get graph details for user
            display_changes = DisplayChanges(participant_id)
            user_graph_details = display_changes.graph_details
            mapping_details = display_changes.mapping_details
            return render_template("change_detection/change_results.html",
                                   mapping_uploaded=mapping_uploaded,
                                   participant_id=participant_id,
                                   change_process_executed=change_process_executed,
                                   graph_details=OrderedDict(
                                       sorted(user_graph_details.items(), key=lambda t: t[0])),
                                   mapping_details=OrderedDict(sorted(mapping_details.items(), key=lambda t: t[0])),
                                   )

    @app.route('/remove/<file_id>/')
    def remove(file_id):
        filename = f"{file_id}"
        # alert message if process or mapping removed
        process_removed = mapping_deleted = None
        if "trig" in filename:
            # user_id = 1
            filename = f"./static/change_detection_cache/change_graphs/{file_id}"
            process_removed = True
        else:
            filename = f"./static/uploads/mappings/{file_id}"
            mapping_deleted = True
        try:
            os.remove(filename)
        except:
            print("file could not be removed....", filename)
        participant_id = session.get("participant_id")
        # get graph details for user
        display_changes = DisplayChanges(participant_id)
        user_graph_details = display_changes.graph_details
        mapping_details = display_changes.mapping_details
        return render_template("change_detection/change_results.html",
                               participant_id=participant_id,
                               mapping_deleted=mapping_deleted,
                               change_process_executed=False,
                               process_removed=process_removed,
                               graph_details=OrderedDict(sorted(user_graph_details.items(), key=lambda t: t[0])),
                               mapping_details=OrderedDict(sorted(mapping_details.items(), key=lambda t: t[0])),
                               mappings_impacted=session.get("mappings_impacted"),
                               )

    # iterate user files to get next file version
    @staticmethod
    def iterate_user_files(user_id):
        graph_directory = "./modules/change_detection_cache/change_graphs/"
        directory_files = [f for f in listdir(graph_directory) if isfile(join(graph_directory, f))]
        # find files related to user ID
        user_versions = []
        for file in directory_files:
            file_version = file.split(".")
            user_versions.append(file_version)
        if user_versions:
            return max(user_versions) + 1
        else:
            return 1

    @app.route(("/logout"), methods=["GET", "POST"])
    def logout():
        logged_in = session.pop("logged_in", None)
        if logged_in:
            flash("You have been logged out")
        return redirect(url_for("login"))

    @app.route("/view")
    @admin_required
    def view():
        return render_template("mapping_quality/view.html", values=users.query.all())

    @staticmethod
    def create_participant_details(num_participants):
        # add participant passwords to database
        for i in range(1, num_participants):
            length = 10
            chars = string.ascii_letters + string.digits
            random.seed = (os.urandom(1024))
            # password = ''.join(random.choice(chars) for i in range(length))
            password = "1"
            usr = users(password)
            db.session.add(usr)
            db.session.commit()

    @staticmethod
    def update_database_time(participant_id, action):
        if participant_id:
            current_time = datetime.now()
            found_users = users.query.filter_by(participant_id=participant_id).first()
            if found_users:
                # column_names = {"User logged in" : found_users.logged_in}
                # current_column = column_names.get(action)
                setattr(found_users, action, current_time)
                db.session.commit()

    @staticmethod
    def get_file_extension(filename):
        split_filename = filename.split(".")
        if len(split_filename) <= 1:
            return "ttl"
        else:
            file_extension = split_filename[1].lower()
            return file_extension

    @app.route("/index/<filename>", methods=["GET", "POST"])
    @app.route("/index", methods=["GET", "POST"])
    def assess_mapping(filename=None):
        session["participant_id"] = 1
        participant_id = session.get("participant_id")
        if request.method == "POST":
            # get file uploaded
            file = request.files['mapping_file']
            ontology_file = request.files.getlist('ontology_file')
            if ontology_file:
                if ontology_file[0].filename != "":
                    # if ontology added successfully
                    error_message = API.store_ontology_file(ontology_file)
                    if error_message:
                        flash("Local upload errror, ensure it's RDF format")
                        return render_template("mapping_quality/index.html")
            predefined_filename = filename
            filename = secure_filename(file.filename)
            if filename and len(filename) > 1:
                file_extension = API.get_file_extension(filename)
                mapping_file = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                session["mapping_file"] = mapping_file
                file.save(mapping_file)
                if file and file_extension in app.config["allowed_file_extensions"]:
                    if API.validate_RDF(mapping_file):
                        try:
                            print(mapping_file)
                            current_time = time.gmtime()
                            timestamp = str(calendar.timegm(current_time))
                            session["timestamp"] = timestamp
                            assessment_result = ValidateQuality(mapping_file)

                            content = pickle.dumps(assessment_result)
                            print(mapping_file)
                            session["assessment_result"] = content
                            validation_result = assessment_result.validation_results
                            print(validation_result)
                            i = 0
                            new_results = defaultdict(dict)
                            print("hdhdh")
                            # i = 0
                            # while i <= validation_result.qsize() + 1:
                            #     new_results[i] = validation_result.get()
                            #     i += 1
                            # validation_result = new_results
                            session["validation_result"] = validation_result
                            triple_references = assessment_result.triple_references
                            session["triple_references"] = triple_references
                            more_info_data = request.form
                            session["more_info_data"] = more_info_data
                            # if violations exist within validation result
                            # print(validation_result.qsize())
                            # exit()
                            if len(validation_result) > 0:
                                participant_id = session.get("participant_id")
                                validation_report_file = "validation_report-{}.ttl".format(participant_id)
                                session["validation_report_file"] = validation_report_file
                                session["namespaces"] = assessment_result.namespaces
                                # user wants to add more info to reports
                                add_information = request.form.get("add-information")
                                session["add_information"] = add_information
                                mapping_graph = assessment_result.mapping_graph
                                session["mapping_graph"] = assessment_result.mapping_graph
                                find_violation_location = assessment_result.find_violation_location
                                session["find_violation_location"] = find_violation_location
                                detailed_metric_information = assessment_result.detailed_metric_information
                                metric_descriptions = assessment_result.metric_descriptions
                                session["refinements"] = Refinements(validation_result, triple_references,
                                                                     mapping_graph)
                                suggested_refinements = session["refinements"].provide_suggested_refinements()
                                session["suggested_refinements"] = suggested_refinements
                                refinement_descriptions = session["refinements"].refinement_descriptions
                                serializer = TurtleSerializer(mapping_graph)
                                parse_violation_value = serializer.parse_violation_value
                                find_prefix = assessment_result.find_prefix
                                session["find_prefix"] = find_prefix
                                API.create_validation_report(more_info_data)
                                get_triple_map_id = assessment_result.get_triple_map_id
                                session["get_triple_map_id"] = get_triple_map_id
                                participant_id = session["participant_id"]
                                cache_validation_result = session.get("validation_result")
                                bar_chart_html = VisualiseResults.chart_dimensions(cache_validation_result)
                                session["bar_chart_html"] = bar_chart_html
                                return render_template(
                                    "mapping_quality/assessment_result.html",
                                    bar_chart_html=bar_chart_html,
                                    refinement_descriptions=refinement_descriptions,
                                    participant_id=participant_id,
                                    display_violation=serializer.display_violation,
                                    metric_descriptions=metric_descriptions,
                                    len=len(validation_result),
                                    assessment_report=validation_result,
                                    find_prefix=find_prefix,
                                    suggested_refinements=suggested_refinements,
                                    find_violation_location=find_violation_location,
                                    split_camel_case=API.split_camel_case,
                                    detailed_metric_information=detailed_metric_information,
                                    validation_result=session.get("validation_result"),
                                    find_bNode_reference=assessment_result.find_blank_node_reference,
                                    get_triple_map_ID=assessment_result.get_triple_map_id,
                                    parse_violation_value=parse_violation_value
                                )

                            else:
                                API.create_validation_report(more_info_data)
                                return render_template("mapping_quality/no_violations.html", participant_id=participant_id)
                        except urllib.error.URLError as server_error:
                            print(server_error)
                            flash("Start the Apache fueski server!")
                            return render_template("mapping_quality/index.html")
                        # except Exception as e:
                        #     print(e)
                        #     flash("Check the mapping and upload again. Validate with http://ttl.summerofcode.be/")
                        #     return render_template("mapping_quality/index.html")
                    else:
                        os.remove(mapping_file)
                        flash(Markup('Mapping file contains invalid RDF. Validate your mapping <a href="http://ttl.summerofcode.be/" target="_blank" class="alert-link">here</a>'))
                        return render_template("mapping_quality/index.html")
                else:
                    os.remove(mapping_file)
                    flash("File must be turtle (ttl) format")
                    return render_template("mapping_quality/index.html")

            else:
                flash("Please Upload a Mapping File!")
                return render_template("mapping_quality/index.html")
        else:
            participant_id = session.get("participant_id")
            return render_template("mapping_quality/index.html", participant_id=participant_id)
            # return render_template("mapping_quality/index.html")

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
        cache_mapping_graph = session.get("mapping_graph")
        session["mapping_graph"] = copy.deepcopy(cache_mapping_graph)
        cache_triple_references = session.get("triple_references")
        cache_validation_result = session.get("validation_result")
        cache_add_information = session.get("add_information")
        cache_mapping_file = session.get("mapping_file")
        cache_validation_report_file = session.get("validation_report_file")
        cache_namespaces = session.get("namespaces")
        cache_find_violation = session.get("find_violation_location")
        more_info_data = session.get("more_info_data")
        find_prefix = session.get("find_prefix")
        participant_id = session.get("participant_id")
        if request.method == "POST":
            session["request_form"] = request.form.to_dict()
            # create validation report incase user goes back and then forward,not to include multiple refinement queries
            API.create_validation_report(more_info_data)
            print(request.form.to_dict(), "REQUEST FORM INFO")
            cache_refinement_values = session.get("refinement_values")
            print(cache_refinement_values, "CACHE REFINEMENT VALUES ")
            print(cache_mapping_graph.serialize(format="ttl").decode('utf8'))

            session["refinements"] = Refinements(cache_validation_result, cache_triple_references,
                                                 cache_mapping_graph,
                                                 session.get("more_info_data"), participant_id)
            session["refinements"].process_user_input(session["request_form"], cache_refinement_values,
                                                      cache_mapping_file,
                                                      cache_mapping_graph, cache_validation_report_file)
            session["triple_references"] = session.get("refinements").triple_references
            print(cache_mapping_graph.serialize(format="ttl").decode('utf8'))
            refinements = session["refinements"]
            find_triple_map = refinements.find_triple_map
            find_violation_location = cache_find_violation
            serializer = TurtleSerializer(cache_mapping_graph)
            parse_violation_value = serializer.parse_violation_value
            display_violation = serializer.display_violation
            get_triple_map_id = session.get("get_triple_map_id")
            assessment_result = session.get("assessment_result")
            print(type(assessment_result), "ASSESSMENT result")
            assessment_result = pickle.loads(assessment_result)
            metric_descriptions = assessment_result.metric_descriptions
            refinement_descriptions = session["refinements"].refinement_descriptions
            detailed_metric_information = assessment_result.detailed_metric_information
            suggested_refinements = session.get("suggested_refinements")
            refinement_values = session["refinement_values"]
            # boolean to show export refined mapping button etc
            show_refinement_buttons = True
            participant_id = session.get("participant_id")
            return render_template(
                "mapping_quality/refinements.html",
                participant_id=participant_id,
                show_refinement_buttons=show_refinement_buttons,
                bar_chart_html=session.get("bar_chart_html"),
                split_camel_case=API.split_camel_case,
                find_prefix=find_prefix,
                validation_result=cache_validation_result,
                namespaces=cache_namespaces,
                refinements=refinement_values,
                prefix_values=refinements.prefix_values,
                display_violation=display_violation,
                find_triple_map=find_triple_map,
                find_violation_location=find_violation_location,
                assessment_report=cache_validation_result,
                refinement_descriptions=refinement_descriptions,
                parse_violation_value=parse_violation_value,
                get_triple_map_ID=get_triple_map_id,
                metric_descriptions=metric_descriptions,
                detailed_metric_information=detailed_metric_information,
                suggested_refinements=suggested_refinements
            )
        else:
            selected_refinements = request.values
            refinement_options = API.refinements_selected(selected_refinements)
            if refinement_options:
                refinements = Refinements(cache_validation_result, cache_triple_references,
                                          cache_mapping_graph,
                                          cache_add_information)
                refinement_values = refinements.provide_refinements(selected_refinements)
                session["refinement_values"] = refinement_values
                print("REFINEMENT VALUES", refinement_values)
                # find_prefix = refinements.find_prefix
                find_triple_map = refinements.find_triple_map
                find_violation_location = cache_find_violation
                serializer = TurtleSerializer(cache_mapping_graph)
                parse_violation_value = serializer.parse_violation_value
                display_violation = serializer.display_violation
                get_triple_map_id = session.get("get_triple_map_id")
                assessment_result = session.get("assessment_result")
                print(type(assessment_result), "ASSESSMENT result")
                assessment_result = pickle.loads(assessment_result)
                metric_descriptions = assessment_result.metric_descriptions
                refinement_descriptions = session["refinements"].refinement_descriptions
                detailed_metric_information = assessment_result.detailed_metric_information
                suggested_refinements = session.get("suggested_refinements")
                return render_template(
                    "mapping_quality/refinements.html",
                    participant_id=participant_id,
                    bar_chart_html=session.get("bar_chart_html"),
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
                return redirect("get_refinements")
                # # if no refinements return quality profile and give option to go back and add refinements
                # bar_chart_html = VisualiseResults.chart_dimensions(cache_validation_result)
                # return render_template("mapping_quality/no_refinements.html", bar_chart_html=bar_chart_html)

    @app.route("/return-refined-mapping/", methods=['GET', 'POST'])
    def download_refined_mapping():
        # refined_mapping_file_name = session.get("mapping_file").split(".")[0] + "_refined_mapping.ttl"
        participant_id = session.get("participant_id")
        local_filename = "refined_mapping-{}.ttl".format(participant_id)
        refined_mapping_filename = "refined-mapping.ttl"
        return send_file(local_filename, attachment_filename=refined_mapping_filename, as_attachment=True,
                         cache_timeout=0)

    @app.route("/return-refinement-report/", methods=['GET', 'POST'])
    def download_refinement_report():
        cache_validation_report_file = session.get("validation_report_file")
        participant_id = session.get("participant_id")
        validation_report_filename = "validation_report-1.ttl"
        # API.save_file_to_database(validation_report_filename, "validation_report_file")
        # API.save_cache_file(validation_report_filename, validation_report_filename)
        return send_file(
            validation_report_filename,
            attachment_filename="validation_report.ttl",
            as_attachment=True, cache_timeout=0
        )

    @app.route("/return-validation-report/", methods=['GET', 'POST'])
    def download_validation_report():
        cache_validation_report_file = session.get("validation_report_file")
        participant_id = session.get("participant_id")
        quality_report_filename = "validation_report-{}.ttl".format(participant_id)
        return send_file(quality_report_filename,
                         attachment_filename=quality_report_filename,
                         as_attachment=True, cache_timeout=0)

    @app.route("/return-sample-mapping/", methods=['GET', 'POST'])
    def download_sample_mapping():
        return send_file("./static/sample_mapping.ttl", as_attachment=True, cache_timeout=0)

    @app.route("/return-impacted-mapping/<mapping_filename>", methods=['GET', 'POST'])
    def download_impacted_mapping(mapping_filename):
        filename = session.get("mapping_details").get(int(mapping_filename)).get("filename")
        mapping_path = "./static/uploads/" + filename
        if os.path.exists(mapping_path):
            exit()
            return send_file(mapping_path, as_attachment=True, cache_timeout=0)
        else:
            mapping_path = "./static/sample_mapping.ttl"
            return send_file(mapping_path, as_attachment=True, cache_timeout=0)

    @app.route("/return-change-graph/<graph_file_name>", methods=['GET', 'POST'])
    def download_change_report(graph_file_name):
        graph_location = "./static/change_detection_cache/change_graphs/" + graph_file_name
        return send_file(graph_location,
                         attachment_filename="change_graph.trig",
                         as_attachment=True, cache_timeout=0)

    @app.route("/display-sample-mappings", methods=['GET', 'POST'])
    @app.route("/display-sample-mappings/<mapping_identifier>", methods=['GET', 'POST'])
    def download_sample_mappings(mapping_identifier=None):
        if mapping_identifier:
            mapping_identifier = int(mapping_identifier)
            if mapping_identifier == 1:
                graph_location = "./static/sample_mappings/student_mapping.ttl"
            elif mapping_identifier == 2:
                graph_location = "./static/sample_mappings/student_mapping.ttl"
            elif mapping_identifier == 2:
                graph_location = "./static/sample_mappings/student_mapping.ttl"
            else:
                graph_location = "./static/sample_mappings/student_mapping.ttl"
            return send_file(graph_location, attachment_filename="student-mapping.ttl", as_attachment=True, cache_timeout=0)

        return render_template("mapping_quality/sample_mappings.html")

if __name__ == "__main__":
    # start api
    API()
