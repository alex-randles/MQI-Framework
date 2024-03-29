import copy
import os
import pickle
import random
import re
import string
import urllib
import datetime
import collections
from sematch.semantic.similarity import WordNetSimilarity
from functools import wraps

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
from modules.shacl_shapes import SHACLShape

app = Flask(__name__)
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(hours=5)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.sqlite3"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['SESSION_FILE_THRESHOLD'] = 100
app.url_map.strict_slashes = False
app.config['SECRET_KEY'] = "x633UE2xYRC"
UPLOAD_FOLDER = 'static/uploads/mappings/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config["allowed_file_extensions"] = ["ttl"]
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.secret_key = os.urandom(24)

sess = Session()
sess.init_app(app)


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
        if session.get("user_id", None) == "alex_randles":
            flash("You must log in as administrator access this page!")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


class users(db.Model):
    entry_id = db.Column("id", db.Integer, primary_key=True)
    user_id = db.Column("user_id", db.Integer)
    # will default to variable name if none defined
    password = db.Column(db.String(100))

    def __init__(self, user_id, password):
        self.user_id = user_id
        self.password = password


class API:

    def __init__(self):
        with app.app_context():
            db.create_all()
        app.run(host="127.0.0.1", port=5000, threaded=True, debug=True)

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
    def add_user(user_id, password):
        usr = users(user_id, password)
        db.session.add(usr)
        db.session.commit()
        os.makedirs(f"./static/user_files/mappings/{user_id}", exist_ok=True)
        os.makedirs(f"./static/user_files/change_graphs/{user_id}", exist_ok=True)

    @staticmethod
    def validate_rdf(filename):
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
    def create_validation_report():
        formatted_validation_result = copy.deepcopy(session.get("validation_result"))
        for violation_ID in formatted_validation_result.keys():
            violation_location = formatted_validation_result[violation_ID]["location"]
            new_location = session.get("find_violation_location")(violation_location)
            formatted_validation_result[violation_ID]["location"] = new_location
        ValidationReport(formatted_validation_result, session.get("validation_report_file"),
                         session.get("mapping_file"), session.get("more_info_data"))

    @staticmethod
    def split_camel_case(word):
        split_word = re.sub('([A-Z][a-z]+)', r' \1', re.sub('([A-Z]+)', r' \1', word)).split()
        result = " ".join(split_word)
        return result

    @staticmethod
    def store_ontology_file(ontology_file):
        for file in ontology_file:
            filename = secure_filename(file.filename)
            file_path = f"./static/user_files/local_ontologies/{filename}"
            file.save(file_path)
            error_message = FetchVocabularies.store_local_vocabulary(file_path)
            if error_message:
                return error_message

    @app.route("/", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            if "logged_in" not in session:
                return render_template("login.html")
            else:
                return redirect(url_for("component_choice"))
        elif request.method == "POST":
            session.permanent = True
            user_id = request.form["user_id"]
            password = request.form["password"]
            found_users = users.query.filter_by(user_id=user_id).first()
            if found_users:
                correct_password = found_users.password
                if correct_password == password.strip():
                    session["logged_in"] = True
                    session["user_id"] = user_id
                    return redirect(url_for("component_choice"))
                else:
                    flash("Invalid credentials, try again!")
                    return render_template("login.html")
            else:
                flash("Invalid credentials, try again!")
                return render_template("login.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "GET":
            found_users = users.query.all()
            existing_ids = [user.user_id for user in found_users if isinstance(user.user_id, int)]
            new_user_id = max(existing_ids) + 1 if existing_ids else 1
            new_password = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(10))

            return render_template("register.html", new_user_id=new_user_id, new_password=new_password)
        else:
            user_id = request.form.get("user_id")
            password = request.form.get("password")
            API.add_user(user_id, password)
            return redirect(url_for('login'), code=307)

    @app.route("/logout", methods=["GET", "POST"])
    @login_required
    def logout():
        logged_in = session.pop("logged_in", None)
        if logged_in:
            flash("You have been logged out")
        return redirect(url_for("login"))

    @app.route("/component-choice", methods=["GET", "POST"])
    @login_required
    def component_choice():
        if request.method == "GET":
            return render_template("component_choice.html", user_id=session.get("user_id"))

    @app.route("/format-choice", methods=["GET"])
    @login_required
    def format_choice():
        if request.method == "GET":
            session["change_process_executed"] = False
            return render_template("change_detection/data_format_choice.html", user_id=session.get("user_id"))

    @app.route("/csv-changes", methods=["GET", "POST"])
    @login_required
    def detect_csv_changes():
        user_id = session.get("user_id")
        if request.method == "GET":
            session["change_process_executed"] = False
            return render_template("change_detection/CSV_file_details.html", user_id=user_id)
        elif request.method == "POST":
            # create a graph with 3 named graphs for user
            form_details = request.form
            change_detection = DetectChanges(user_id, form_details)
            if change_detection.error_code == 1:
                flash("Invalid URL. Try again and make sure it is the raw file Github link - if using Gihtub.")
                return redirect(url_for('detect_csv_changes'))
            elif change_detection.error_code == 2:
                flash("Unable to retrieve data due to connection issues.")
                return redirect(url_for('detect_csv_changes'))
            else:
                session["change_process_executed"] = True
                return redirect(url_for('change_detection'))

    @app.route("/xml-changes", methods=["GET", "POST"])
    @login_required
    def detect_xml_changes():
        user_id = session.get("user_id")
        if request.method == "GET":
            session["change_process_executed"] = False
            return render_template("change_detection/XML_file_details.html", user_id=user_id)
        elif request.method == "POST":
            session["change_process_executed"] = True
            form_details = request.form
            change_detection = DetectChanges(user_id, form_details)
            if change_detection.error_code == 1:
                flash("Invalid URL. Try again and make sure it is the raw file Github link - if using Gihtub.")
                return redirect(url_for('detect_xml_changes'))
            elif change_detection.error_code == 2:
                flash("Incorrect file format.")
                return redirect(url_for('detect_xml_changes'))
            else:
                return redirect(url_for('change_detection'))

    @app.route("/shacl-shapes", methods=["GET", "POST"])
    @login_required
    def generate_shacl_shapes():
        if request.method == "GET":
            return render_template("change_detection/shacl_shape_details.html", user_id=session.get("user_id"))
        else:
            print(request.form)
            shacl_shape = SHACLShape(request.form).create_shape()
            return shacl_shape

    @app.route('/mappings_impacted/<mapping_unique_id>/<graph_id>', methods=['GET', 'POST'])
    @app.route('/mappings_impacted/<mapping_unique_id>', methods=['GET', 'POST'])
    @login_required
    def mappings_impacted(mapping_unique_id=None, graph_id=None):
        user_id = session.get("user_id")
        if request.method == "GET":
            mapping_graph_details = session.get("mapping_details").get(int(mapping_unique_id))
            graph_id = int(graph_id.split(".")[0])
            change_graph_details = session.get("graph_details").get(graph_id)
            impact = DetectMappingImpact(user_id, mapping_graph_details, change_graph_details.get("filename"))
            mapping_impact = impact.mapping_impact
            change_template_colors =  impact.change_template_colors
            change_type_banners = impact.change_type_banners
            mapping_updated = session.get("mapping_updated")
            session["mapping_updated"] = False
            mapping_filename = mapping_graph_details.get("filename")
            mapping_data_references = [reference.lower() for reference in mapping_graph_details.get("data_references")]
            similarity_measurement = WordNetSimilarity().word_similarity
            return render_template("change_detection/mappings_impacted.html",
                                   similarity_measurement=similarity_measurement,
                                   user_id=user_id,
                                   mapping_data_references=mapping_data_references,
                                   change_template_colors=change_template_colors,
                                   mapping_id=mapping_unique_id,
                                   mapping_impact=mapping_impact,
                                   mapping_filename=mapping_filename,
                                   change_type_banners=change_type_banners,
                                   mapping_updated=mapping_updated,
                                   change_graph_details=change_graph_details)
        else:
            mapping_file_name = session.get("mapping_details").get(int(mapping_unique_id)).get("filename")
            DetectMappingImpact.update_impacted_mapping(user_id, request.form, mapping_file_name)
            print(request.form)
            session["mapping_updated"] = True
            return redirect(request.referrer)

    @app.route('/process_thresholds/<graph_filename>', methods=['GET', 'POST'])
    @login_required
    def process_thresholds(graph_filename):
        # reassign as pycharm underlines as error
        str_graph_filename = str(graph_filename)
        user_id = session.get("user_id")
        notification_thresholds = DisplayChanges.generate_thresholds_html(str_graph_filename, session.get("user_id"))
        graph_id = "".join(str_graph_filename.split("."))[0]
        change_graph_details = session.get("graph_details")
        return render_template("change_detection/notification_thresholds.html",
                               user_id=user_id,
                               graph_id=graph_id,
                               graph_filename=graph_filename,
                               change_graph_details=change_graph_details,
                               notification_thresholds=notification_thresholds)

    @app.route("/change-processes", methods=["GET", "POST"])
    @login_required
    def change_detection():
        change_process_executed = session.get("change_process_executed")
        # no alert if no process executed
        if request.method == "GET":
            session["change_process_executed"] = False
            # get graph details for user
            # try:
            user_id = session.get("user_id")
            display_changes = DisplayChanges(user_id)
            error_code = display_changes.error_code
            if error_code == 0:
                user_graph_details = display_changes.graph_details
                mapping_details = display_changes.mapping_details
                session["graph_details"] = user_graph_details
                session["mapping_details"] = mapping_details
                return render_template(
                    "change_detection/change_results.html",
                    user_id=user_id,
                    change_process_executed=change_process_executed,
                    process_removed=False,
                    graph_details=collections.OrderedDict(sorted(user_graph_details.items(), key=lambda t: t[0])),
                    mapping_details=collections.OrderedDict(sorted(mapping_details.items(), key=lambda t: t[0])),
                )
            else:
                return "<h1>Error!!!!!</h1>"
        else:
            uploaded_file = request.files['mapping-file']
            if uploaded_file.filename != '':
                user_id = session.get("user_id")
                file_version = API.iterate_user_files(user_id)
                filename = uploaded_file.filename + "_{}-{}".format(user_id, file_version)
                upload_folder = f'./static/uploads/{session.get("user_id")}/mappings/'
                filename = os.path.join(upload_folder + session.get("user_id") + "/", filename)
                uploaded_file.save(filename)
                mapping_uploaded = True
            else:
                mapping_uploaded = False
            # mapping uploaded = True to display banner
            display_changes = DisplayChanges(session.get("user_id"))
            user_graph_details = display_changes.graph_details
            mapping_details = display_changes.mapping_details
            return render_template("change_detection/change_results.html",
                                   mapping_uploaded=mapping_uploaded,
                                   change_process_executed=change_process_executed,
                                   graph_details=collections.OrderedDict(
                                       sorted(user_graph_details.items(), key=lambda t: t[0])),
                                   mapping_details=collections.OrderedDict(sorted(mapping_details.items(), key=lambda t: t[0])),
                                   )

    @app.route('/remove/<file_id>/')
    @login_required
    def remove(file_id):
        filename = f"{file_id}"
        # alert message if process or mapping removed
        process_removed = mapping_deleted = None
        if "trig" in filename:
            filename = f"./static/user_files/change_graphs/{session.get('user_id')}/{file_id}"
            process_removed = True
        else:
            filename = f"./static/user_files/mappings/{session.get('user_id')}/{file_id}"
            mapping_deleted = True
        try:
            os.remove(filename)
        except Exception as e:
            print("file could not be removed....", filename, e)
        # get graph details for user
        display_changes = DisplayChanges(session.get("user_id"))
        user_graph_details = display_changes.graph_details
        mapping_details = display_changes.mapping_details
        return render_template("change_detection/change_results.html",
                               mapping_deleted=mapping_deleted,
                               change_process_executed=False,
                               process_removed=process_removed,
                               user_id=session.get("user_id"),
                               graph_details=collections.OrderedDict(sorted(user_graph_details.items(), key=lambda t: t[0])),
                               mapping_details=collections.OrderedDict(sorted(mapping_details.items(), key=lambda t: t[0])),
                               mappings_impacted=session.get("mappings_impacted"),
                               )

    @staticmethod
    def iterate_user_files(user_id):
        graph_directory = f"./user_files/change_graphs/{user_id}"
        directory_files = [f for f in os.listdir(graph_directory) if os.path.isfile(os.path.join(graph_directory, f))]
        # find files related to user ID
        user_versions = []
        for file in directory_files:
            file_version = file.split(".")
            user_versions.append(file_version)
        if user_versions:
            return max(user_versions) + 1
        else:
            return 1

    @staticmethod
    def get_file_extension(filename):
        split_filename = filename.split(".")
        if len(split_filename) <= 1:
            return "ttl"
        else:
            file_extension = split_filename[1].lower()
            return file_extension

    @app.route("/index/<user_file>", methods=["GET", "POST"])
    @app.route("/index", methods=["GET", "POST"])
    @login_required
    def assess_mapping(user_file=None):
        user_id = session.get("user_id")
        if request.method == "POST":
            # get file uploaded
            file = request.files['mapping_file']
            ontology_file = request.files.getlist('ontology_file')
            if ontology_file:
                if ontology_file[0].filename != "":
                    # if ontology added successfully
                    error_message = API.store_ontology_file(ontology_file)
                    if error_message:
                        flash("Local Ontology must be valid RDF")
                        return render_template("mapping_quality/index.html", user_id=user_id)
            filename = secure_filename(file.filename)
            if filename and len(filename) > 1:
                file_extension = API.get_file_extension(filename)
                upload_folder = f'./static/user_files/mappings/{session.get("user_id")}/'
                mapping_file = os.path.join(upload_folder, filename)
                file.save(mapping_file)
                session["mapping_file"] = mapping_file
                if file and file_extension in app.config["allowed_file_extensions"]:
                    if API.validate_rdf(mapping_file):
                        try:
                            assessment_result = ValidateQuality(mapping_file)
                            content = pickle.dumps(assessment_result)
                            session["assessment_result"] = content
                            validation_result = assessment_result.validation_results
                            session["validation_result"] = validation_result
                            triple_references = assessment_result.triple_references
                            session["triple_references"] = triple_references
                            more_info_data = request.form
                            session["more_info_data"] = more_info_data
                            if len(validation_result) > 0:
                                user_id = session.get("user_id")
                                validation_report_file = "validation_report-{}.ttl".format(user_id)
                                session["validation_report_file"] = validation_report_file
                                session["namespaces"] = assessment_result.namespaces
                                # user wants to add more info to reports
                                session["add_information"] = request.form.get("add-information")
                                mapping_graph = assessment_result.mapping_graph
                                session["mapping_graph"] = assessment_result.mapping_graph
                                session["find_violation_location"] = assessment_result.find_violation_location
                                detailed_metric_information = assessment_result.detailed_metric_information
                                session["refinements"] = Refinements(validation_result, triple_references, mapping_graph)
                                suggested_refinements = session["refinements"].provide_suggested_refinements()
                                session["suggested_refinements"] = suggested_refinements
                                serializer = TurtleSerializer(mapping_graph)
                                parse_violation_value = serializer.parse_violation_value
                                session["find_prefix"] = assessment_result.find_prefix
                                API.create_validation_report()
                                get_triple_map_id = assessment_result.get_triple_map_id
                                session["get_triple_map_id"] = get_triple_map_id
                                user_id = session["user_id"]
                                # bar_chart_html = VisualiseResults.chart_dimensions(session.get("validation_result"), user_id)
                                # session["bar_chart_html"] = bar_chart_html
                                chart_file = VisualiseResults.chart_dimensions(session.get("validation_result"), user_id)
                                session["chart_file"] = chart_file
                                return render_template(
                                    "mapping_quality/assessment_result.html",
                                    open=open,
                                    # bar_chart_html=bar_chart_html,
                                    chart_file=chart_file,
                                    refinement_descriptions=session["refinements"].refinement_descriptions,
                                    user_id=user_id,
                                    display_violation=serializer.display_violation,
                                    metric_descriptions=assessment_result.metric_descriptions,
                                    len=len(validation_result),
                                    assessment_report=validation_result,
                                    find_prefix= assessment_result.find_prefix,
                                    suggested_refinements=suggested_refinements,
                                    find_violation_location=assessment_result.find_violation_location,
                                    split_camel_case=API.split_camel_case,
                                    detailed_metric_information=detailed_metric_information,
                                    validation_result=session.get("validation_result"),
                                    find_bNode_reference=assessment_result.find_blank_node_reference,
                                    get_triple_map_ID=assessment_result.get_triple_map_id,
                                    parse_violation_value=parse_violation_value
                                )
                            else:
                                API.create_validation_report()
                                return render_template("mapping_quality/no_violations.html", user_id=user_id)
                        except urllib.error.URLError as server_error:
                            print(server_error)
                            flash("Start the Apache fueski server!")
                            return render_template("mapping_quality/index.html", user_id=user_id)
                        # except Exception as e:
                        #     print(e)
                        #     flash("Check the mapping and upload again. Validate with http://ttl.summerofcode.be/")
                        #     return render_template("mapping_quality/index.html")
                    else:
                        os.remove(mapping_file)
                        flash(Markup('Mapping file contains invalid RDF. Validate your mapping '
                                     '<a href="http://ttl.summerofcode.be/" target="_blank" '
                                     'class="alert-link">here</a>'))
                        return render_template("mapping_quality/index.html", user_id=user_id)
                else:
                    os.remove(mapping_file)
                    flash("File must be turtle (ttl) format")
                    return render_template("mapping_quality/index.html", user_id=user_id)

            else:
                flash("Please Upload a Mapping File!")
                return render_template("mapping_quality/index.html")
        else:
            return render_template("mapping_quality/index.html", user_id=user_id)

    @staticmethod
    def refinements_selected(selected_refinements):
        # check if the user has selected all refinements to be manual or not
        selected_options = [refinement_selected for (ID, refinement_selected) in selected_refinements.items()]
        for option in selected_options:
            if option != "Manual":
                return True
        return False

    @app.route("/refinement", methods=["GET", "POST"])
    @login_required
    def get_refinements():
        cache_mapping_graph = session.get("mapping_graph")
        session["mapping_graph"] = copy.deepcopy(cache_mapping_graph)
        cache_triple_references = session.get("triple_references")
        cache_validation_result = session.get("validation_result")
        cache_add_information = session.get("add_information")
        cache_mapping_file = session.get("mapping_file")
        cache_namespaces = session.get("namespaces")
        cache_find_violation = session.get("find_violation_location")
        find_prefix = session.get("find_prefix")
        user_id = session.get("user_id")
        if request.method == "POST":
            session["request_form"] = request.form.to_dict()
            # create validation report incase user goes back and then forward,not to include multiple refinement queries
            API.create_validation_report()
            cache_refinement_values = session.get("refinement_values")
            session["refinements"] = Refinements(cache_validation_result,
                                                 cache_triple_references,
                                                 cache_mapping_graph,
                                                 session.get("more_info_data"),
                                                 user_id)
            session["refinements"].process_user_input(session.get("request_form"),
                                                      cache_refinement_values,
                                                      cache_mapping_file,
                                                      cache_mapping_graph,
                                                      session.get("validation_report_file"))
            session["triple_references"] = session.get("refinements").triple_references
            serializer = TurtleSerializer(cache_mapping_graph)
            assessment_result = pickle.loads(session.get("assessment_result"))
            # boolean to show export refined mapping button etc
            show_refinement_buttons = True
            return render_template(
                "mapping_quality/refinements.html",
                user_id=session.get("user_id"),
                show_refinement_buttons=show_refinement_buttons,
                # bar_chart_html=session.get("bar_chart_html"),
                chart_file=session.get("chart_file"),
                split_camel_case=API.split_camel_case,
                find_prefix=find_prefix,
                validation_result=cache_validation_result,
                namespaces=cache_namespaces,
                refinements=session.get("refinement_values"),
                prefix_values=session.get("refinements").prefix_values,
                display_violation=serializer.display_violation,
                find_triple_map=session.get("refinements").find_triple_map,
                find_violation_location=cache_find_violation,
                assessment_report=cache_validation_result,
                refinement_descriptions=session.get("refinements").refinement_descriptions,
                parse_violation_value=serializer.parse_violation_value,
                get_triple_map_ID=session.get("get_triple_map_id"),
                metric_descriptions=assessment_result.metric_descriptions,
                detailed_metric_information=assessment_result.detailed_metric_information,
                suggested_refinements=session.get("suggested_refinements")
            )
        else:
            selected_refinements = request.values
            refinement_options = API.refinements_selected(selected_refinements)
            if refinement_options:
                refinements = Refinements(cache_validation_result,
                                          cache_triple_references,
                                          cache_mapping_graph,
                                          cache_add_information)
                refinement_values = refinements.provide_refinements(selected_refinements)
                session["refinement_values"] = refinement_values
                serializer = TurtleSerializer(cache_mapping_graph)
                assessment_result = pickle.loads(session.get("assessment_result"))
                suggested_refinements = session.get("suggested_refinements")
                return render_template(
                    "mapping_quality/refinements.html",
                    user_id=session.get("user_id"),
                    # bar_chart_html=session.get("bar_chart_html"),
                    chart_file=session.get("chart_file"),
                    split_camel_case=API.split_camel_case,
                    refinement_descriptions=session.get("refinements").refinement_descriptions,
                    find_prefix=find_prefix,
                    validation_result=cache_validation_result,
                    namespaces=cache_namespaces,
                    refinements=refinement_values,
                    prefix_values=refinements.prefix_values,
                    display_violation=serializer.display_violation,
                    find_triple_map=refinements.find_triple_map,
                    find_violation_location=cache_find_violation,
                    assessment_report=cache_validation_result,
                    parse_violation_value=serializer.parse_violation_value,
                    get_triple_map_ID=session.get("get_triple_map_id"),
                    metric_descriptions=assessment_result.metric_descriptions,
                    detailed_metric_information=assessment_result.detailed_metric_information,
                    suggested_refinements=suggested_refinements
                )
            else:
                return redirect("get_refinements")

    @app.route("/return-quality-report/", methods=['GET', 'POST'])
    def download_quality_report():
        return send_file("./static/validation_report.ttl",
                         download_name="quality_report.ttl",
                         as_attachment=True, max_age=0)

    @app.route("/return-sample-mapping/", methods=['GET', 'POST'])
    @login_required
    def download_sample_mapping():
        return send_file("./static/sample_mapping.ttl", as_attachment=True, max_age=0)

    @app.route("/return-refined-mapping/", methods=['GET', 'POST'])
    @login_required
    def download_refined_mapping():
        return send_file("refined_mapping.ttl", as_attachment=True, max_age=0)

    @app.route("/return-validation-report/", methods=['GET', 'POST'])
    @login_required
    def download_validation_report():
        return send_file("validation_report.ttl", as_attachment=True, max_age=0)

    @app.route("/return-change-graph/<graph_file_name>", methods=['GET', 'POST'])
    @login_required
    def download_change_report(graph_file_name):
        graph_location = f"./static/change_detection_cache/change_graphs/{graph_file_name}"
        return send_file(graph_location,
                         attachment_filename="change_graph.trig",
                         as_attachment=True, max_age=0)

    @app.route("/display-sample-mappings", methods=['GET', 'POST'])
    @login_required
    def download_sample_mappings():
        return render_template("mapping_quality/sample_mappings.html", user_id=session.get("user_id"))


if __name__ == "__main__":
    # start the app
    API()
