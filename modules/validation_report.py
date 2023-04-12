# Old validation report which uses SPARQL queries instead of rdflib built in functions to add triples to a graph
from datetime import datetime
import calendar
import time
import os.path
import time
import rdflib
from rdflib import Graph, URIRef, Namespace, RDF, Literal, RDFS, XSD, BNode, RDF
from rdflib.plugins.sparql.processor import processUpdate


class ValidationReport:

    def __init__(self, validation_results, output_file, mapping_file, form_data, timestamp):
        self.timestamp = timestamp
        self.output_file = output_file
        self.form_data = form_data
        self.mapping_file = mapping_file
        self.unique_report_identifier = self.create_unique_report_identifier()
        self.mapping_graph = Graph().parse(mapping_file, format="ttl")
        self.mapping_namespaces = {prefix: namespace for (prefix, namespace) in self.mapping_graph.namespaces()}
        self.validation_graph = Graph()
        self.MQIO = Namespace("https://w3id.org/MQIO#")
        self.MQIO_METRIC = Namespace("https://w3id.org/MQIO-metrics/#")
        self.EX = Namespace("http://example.org/")
        self.R2RML = Namespace("http://www.w3.org/ns/r2rml#")
        self.PROV = Namespace("http://www.w3.org/ns/prov#")
        self.RML = Namespace("http://semweb.mmlab.be/ns/rml#")
        self.bind_namespaces()
        self.validation_results = validation_results
        self.violation_count = 0
        self.assessment_identifier = None
        self.create_validation_report()

    def create_unique_report_identifier(self):
        # A unique identifier created for each report
        # mapping_name = self.mapping_file.split("/")[-1]
        # current_report_number = self.get_current_report_number()
        # report_identifier = "-" + mapping_name + "-" + str(current_report_number)
        # current_time = time.gmtime()
        # timestamp = calendar.timegm(current_time)
        report_identifier = "-" + "testing"
        return report_identifier

    def get_mapping_identifier(self):
        # A function that returns the mapping name with the full path
        mapping_file_identifier = URIRef(self.mapping_file.split("/")[-1])
        return mapping_file_identifier

    def create_validation_report(self):
        # A function create the validation report and add each violation
        validation_report_identifier = self.insert_validation_report()
        self.insert_assessment_information()
        self.iterate_violations(validation_report_identifier)
        # add more information only if check box selected
        # if "add-information" in self.form_data.keys():
        #     self.add_form_data()
        self.add_form_data()
        self.save_validation_report()

    def add_form_data(self):
        # adding mapping information
        # DEBUGGING - YOU WILL HAVE TO CHANGE IN REFINEMENTS
        if self.form_data.get("add-information"):
            mapping_file_identifier = URIRef(self.mapping_file.split("/")[-1])
            self.validation_graph.add((URIRef(self.mapping_file.split("/")[-1]), RDF.type, self.MQIO.MappingArtefact))
            mapping_identifier = mapping_file_identifier
            self.add_creator_agent(mapping_identifier)
            self.add_performer_agent()
            self.add_refinement_agent()

    def add_creator_agent(self, mapping_identifier):
        # adding creator name
        creator_name = self.form_data.get('creator-name')
        if creator_name:
            creator_name_identifier = URIRef("http://example.org/" + creator_name)
            self.validation_graph.add((mapping_identifier, self.MQIO.wasCreatedBy, creator_name_identifier))

    def add_performer_agent(self):
        # adding the person who performed the assessment
        performed_by_name = self.form_data["performed-by-name"]
        if performed_by_name:
            performed_by_identifier = URIRef("http://example.org/" + performed_by_name)
            self.validation_graph.add((self.assessment_identifier, self.PROV.wasAssociatedWith, performed_by_identifier))

    def add_refinement_agent(self):
        pass
        # add agent who performed the refinement of the mapping
        # refinement_agent = self.form_data["refined-by-name"]
        # refinement_agent_identifier = URIRef("http://example.org/" + refinement_agent)
        # self.validation_graph.add((self.assessment_identifier, self.PROV.wasAssociatedWith, refinement_agent_identifier))

    def add_assessment_time(self):
        # time the mapping information was generated - prov:startedAtTime
        current_time = Literal(datetime.utcnow(), datatype=XSD.dateTime)
        self.validation_graph.add((self.assessment_identifier, self.PROV.endedAtTime, current_time))

    def add_report_time(self):
        validation_report_identifier = self.EX.mappingValidationReport + "-0"
        # time the mapping information was generated - prov:startedAtTime
        current_time = Literal(datetime.utcnow(), datatype=XSD.dateTime)
        self.validation_graph.add((validation_report_identifier, self.PROV.generatedAtTime, current_time))

    def add_creation_date(self, mapping):
        # the date the mapping was created - prov:generatedAtTime dateTime
        mapping_creation_time = time.ctime(os.path.getctime(self.mapping_file))
        creation_date_time_format = datetime.strptime(mapping_creation_time, "%a %b %d %H:%M:%S %Y")
        creation_date_identifier = Literal(creation_date_time_format, datatype=XSD.dateTime)
        # self.validation_graph.add((mapping, self.PROV.generatedAtTime, creation_date_identifier))
        print(creation_date_identifier)
        print(self.mapping_file)
        # creation_date = self.form_data["creation-date"]
        # if creation_date:
        #     # add midnight as the time as prov:generatedAtTime needs date time
        #     creation_date = creation_date + "T00:00:00Z"
        #     creation_date = creation_date
        #     creation_date_identifier = Literal(creation_date, datatype=XSD.dateTime)
        #     self.validation_graph.add((mapping, self.PROV.generatedAtTime, creation_date_identifier))

    def add_PROV_Agent(self, name):
        name_identifier = URIRef(self.EX + "".join(name.split()))
        self.validation_graph.add((name_identifier, RDF.type, self.PROV.Agent))
        self.validation_graph.add((name_identifier, RDFS.label, Literal(name)))
        return name_identifier

    def insert_assessment_information(self):
        # ex:mappingQualityAssessment a mqv:MappingAssessment ;
        quality_assessment_identifier = self.EX.mappingQualityAssessment
        self.assessment_identifier = quality_assessment_identifier
        self.validation_graph.add((quality_assessment_identifier, RDF.type, self.MQIO.MappingAssessment))
        # mqv:assessedMapping </home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/valid_mapping.ttl> .
        mapping_file_identifier = URIRef(self.mapping_file.split("/")[-1])
        self.validation_graph.add((quality_assessment_identifier, self.MQIO.assessedMapping, mapping_file_identifier))
        mapping = URIRef(list(self.validation_graph.objects(None, self.MQIO.assessedMapping))[0])
        self.validation_graph.add((URIRef(str(mapping).split("/")[-1]), RDF.type, self.MQIO.MappingArtefact))
        # self.add_assessment_time()
        # self.add_report_time()
        # add agent details
        validation_report_identifier = self.EX.mappingValidationReport + "-0"
        # self.validation_graph.add((name, RDF.type , self.PROV.Agent))
        # self.validation_graph.add((quality_assessment_identifier, self.MQIO.wasPerfomedBy, name))
        self.validation_graph.add((quality_assessment_identifier, self.MQIO.hasValidationReport, validation_report_identifier))
        return quality_assessment_identifier

    def insert_validation_report(self):
        validation_report_identifier = self.EX.mappingValidationReport + "-0"
        self.validation_graph.add((validation_report_identifier, RDF.type, self.MQIO.MappingValidationReport))
        return validation_report_identifier

    def iterate_violations(self, validation_report_identifier):
        for violation_ID in self.validation_results:
            current_violation = self.validation_results[violation_ID]
            self.insert_violation(violation_ID, current_violation, validation_report_identifier)

    def insert_violation(self, violation_ID, violation_information, validation_report_identifier):
        # mqv:hasViolation mqv:violation0,
        current_violation_identifier = self.EX.violation + "-" + str(violation_ID)
        self.validation_graph.add((validation_report_identifier, self.MQIO.hasViolation, current_violation_identifier))
        self.insert_violation_information(violation_information, current_violation_identifier)

    def insert_violation_information(self, violation_information, current_violation_identifier):
        metric_identifier = URIRef(self.EX + violation_information.get("metric_identifier"))
        mqio_metric_identifier = URIRef(self.MQIO_METRIC + violation_information.get("metric_identifier"))
        result_message = Literal(violation_information.get("result_message"), datatype=XSD.string)
        self.validation_graph.add((current_violation_identifier, RDF.type, self.MQIO.MappingViolation))
        self.validation_graph.add((current_violation_identifier, self.MQIO.isDescribedBy, mqio_metric_identifier))
        # self.validation_graph.add((metric_identifier, RDF.type, mqv_metric_identifier))
        self.validation_graph.add((current_violation_identifier, self.MQIO.hasResultMessage, result_message))
        self.insert_violation_value(violation_information, current_violation_identifier)
        self.insert_violation_location(violation_information, current_violation_identifier)

    def insert_violation_location(self, violation_information, current_violation_identifier):
        # the triple map and location within the triple map
        self.insert_triple_map(violation_information, current_violation_identifier)
        violation_location = Literal(violation_information["location"], datatype=XSD.string)
        self.validation_graph.add((current_violation_identifier, self.MQIO.hasLocation, violation_location))

    @staticmethod
    def format_triple_map_identifier(triple_map_name):
        # removes local file name from IRI
        if "#" in triple_map_name:
            formatted_identifier = triple_map_name.split("#")[-1]
            return URIRef("#%s" % formatted_identifier)
        elif "/" in triple_map_name:
            formatted_identifier = triple_map_name.split("/")[-1]
        else:
            formatted_identifier = triple_map_name
        return URIRef("%s" % formatted_identifier)

    def insert_triple_map(self, violation_information, current_violation_identifier):
        triple_map_name = violation_information["triple_map"]
        triple_map_identifier = self.format_triple_map_identifier(triple_map_name)
        self.validation_graph.add((current_violation_identifier, self.MQIO.inTripleMap, triple_map_identifier))

    def insert_violation_value(self, violation_information, current_violation_identifier):
        # 'value': rdflib.term.URIRef('http://www.opengis.net/ont/geosparql#hasGeometry'),
        violation_value = violation_information["value"]
        print(violation_value, "violation value")
        # it could be none for example no parent column defined in join
        if violation_value:
            # check if more than one value
            violation_value_type  = type(violation_value)
            if  violation_value_type is not tuple:
                if violation_value_type == Literal:
                    violation_value = Literal(violation_value,datatype=XSD.string)
                    self.validation_graph.add((current_violation_identifier, self.MQIO.hasLiteralValue, violation_value))
                else:
                    self.validation_graph.add((current_violation_identifier, self.MQIO.hasObjectValue, URIRef(violation_value)))
            else:
                for value in violation_value:
                    violation_value_type = type(violation_value)
                    if violation_value_type == Literal:
                        self.validation_graph.add((current_violation_identifier, self.MQIO.hasLiteralValue, value))
                    else:
                        self.validation_graph.add((current_violation_identifier, self.MQIO.hasObjectValue, value))

    def create_mapping_assessment(self):
        # A function create the validation report and add each violation
        self.validation_graph.add((self.EX.mappingQualityAssessment, RDF.type, self.MQIO.MappingAssessment))

    def bind_namespaces(self):
        self.validation_graph.bind("mqio", self.MQIO)
        self.validation_graph.bind("ex", self.EX)
        self.validation_graph.bind("rr", self.R2RML)
        self.validation_graph.bind("prov", self.PROV)
        self.validation_graph.bind("mqio-metrics", self.MQIO_METRIC)
        self.validation_graph.bind("rml", self.RML)
        self.validation_graph.bind("rdf", Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#"))
        self.bind_mapping_namespaces()

    def bind_mapping_namespaces(self):
        # bind the namespaces used in the original/refined mapping
        validation_report_namespaces = {prefix: namespace for (prefix, namespace) in self.mapping_graph.namespaces()}
        for (prefix, namespace) in self.mapping_namespaces.items():
            if (prefix, namespace) not in validation_report_namespaces.items():
                self.validation_graph.bind(prefix, namespace)

    def print_graph(self):
        print(self.validation_graph.serialize(format='turtle').decode('utf-8'))

    def save_validation_report(self):
        self.validation_graph.serialize(destination=self.output_file, format='ttl')


if __name__ == "__main__":
    # quality_information = ValidateQuality("/home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/valid_mapping.ttl")
    # mapping_file = quality_information.file_name
    mapping_file = "/home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/mappings/video_demo.ttl"
    validation_results = {0: {'metric_ID': 'D6', 'result_message': 'Usage of incorrect domain.', 'value': rdflib.term.URIRef('http://www.opengis.net/ont/geosparql#hasGeometry'), 'location': rdflib.term.BNode('ub5bL55C24'), 'triple_map': 'file:///home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/static/uploads/valid_mapping.ttl#MapERA5SamplePoint'},
                          1: {'metric_ID': 'M9', 'result_message': 'Language tag not defined in RFC 5646.', 'value': rdflib.term.Literal('fff'), 'location': rdflib.term.BNode('ub5bL57C16'), 'triple_map': 'file:///home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/static/uploads/valid_mapping.ttl#MapERA5SamplePoint'}}
    validation_report = ValidationReport(validation_results, "/home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/validation_report.ttl", mapping_file, form_data={})
    validation_report.print_graph()
