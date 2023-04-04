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
        self.unique_report_IRI = self.create_unique_report_IRI()
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
        self.assessment_IRI = None
        self.create_validation_report()


    def create_unique_report_IRI(self):
        # A unique IRI created for each report
        # mapping_name = self.mapping_file.split("/")[-1]
        # current_report_number = self.get_current_report_number()
        # report_IRI = "-" + mapping_name + "-" + str(current_report_number)
        # current_time = time.gmtime()
        # timestamp = calendar.timegm(current_time)
        report_IRI = "-" + "testing"
        return report_IRI

    def get_mapping_IRI(self):
        # A function that returns the mapping name with the full path
        mapping_file_IRI = URIRef(self.mapping_file.split("/")[-1])
        return mapping_file_IRI

    def create_validation_report(self):
        # A function create the validation report and add each violation
        validation_report_IRI = self.insert_validation_report()
        self.insert_assessment_information()
        self.iterate_violations(validation_report_IRI)
        # add more information only if check box selected
        # if "add-information" in self.form_data.keys():
        #     self.add_form_data()
        self.add_form_data()
        self.save_validation_report()

    def add_form_data(self):
        # adding mapping information
        # DEBUGGING - YOU WILL HAVE TO CHANGE IN REFINEMENTS
        if self.form_data.get("add-information"):
            mapping_file_IRI = URIRef(self.mapping_file.split("/")[-1])
            self.validation_graph.add((URIRef(self.mapping_file.split("/")[-1]), RDF.type, self.MQIO.MappingArtefact))
            mapping = mapping_file_IRI
            # adding creator name
            creator_name = self.form_data.get('creator-name')
            creator_name_IRI = URIRef("http://example.org/" + creator_name)
            self.validation_graph.add((mapping, self.MQIO.wasCreatedBy, creator_name_IRI))
            # adding the person who performed the assessment
            performed_by_name = self.form_data["performed-by-name"]
            performed_by_IRI = URIRef("http://example.org/" + performed_by_name)
            self.validation_graph.add((self.assessment_IRI, self.PROV.wasAssociatedWith, performed_by_IRI))

    def add_assessment_time(self):
        # time the mapping information was generated - prov:startedAtTime
        current_time = Literal(datetime.utcnow(), datatype=XSD.dateTime)
        self.validation_graph.add((self.assessment_IRI, self.PROV.endedAtTime, current_time))

    def add_report_time(self):
        validation_report_IRI = self.EX.mappingValidationReport + "-0"
        # time the mapping information was generated - prov:startedAtTime
        current_time = Literal(datetime.utcnow(), datatype=XSD.dateTime)
        self.validation_graph.add((validation_report_IRI, self.PROV.generatedAtTime, current_time))

    def add_creation_date(self, mapping):
        # the date the mapping was created - prov:generatedAtTime dateTime
        mapping_creation_time = time.ctime(
            os.path.getctime(self.mapping_file))
        creation_date_time_format = datetime.strptime(mapping_creation_time, "%a %b %d %H:%M:%S %Y")
        creation_date_IRI = Literal(creation_date_time_format, datatype=XSD.dateTime)
        # self.validation_graph.add((mapping, self.PROV.generatedAtTime, creation_date_IRI))
        print(creation_date_IRI)
        print(self.mapping_file)
        # creation_date = self.form_data["creation-date"]
        # if creation_date:
        #     # add midnight as the time as prov:generatedAtTime needs date time
        #     creation_date = creation_date + "T00:00:00Z"
        #     creation_date = creation_date
        #     creation_date_IRI = Literal(creation_date, datatype=XSD.dateTime)
        #     self.validation_graph.add((mapping, self.PROV.generatedAtTime, creation_date_IRI))

    def add_PROV_Agent(self, name):
        name_IRI = URIRef(self.EX + "".join(name.split()))
        self.validation_graph.add((name_IRI, RDF.type, self.PROV.Agent))
        self.validation_graph.add((name_IRI, RDFS.label, Literal(name)))
        return name_IRI

    def insert_assessment_information(self):
        # ex:mappingQualityAssessment a mqv:MappingAssessment ;
        quality_assessment_IRI = self.EX.mappingQualityAssessment
        self.assessment_IRI = quality_assessment_IRI
        self.validation_graph.add((quality_assessment_IRI, RDF.type, self.MQIO.MappingAssessment))
        # mqv:assessedMapping </home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/valid_mapping.ttl> .
        mapping_file_IRI = URIRef(self.mapping_file.split("/")[-1])
        self.validation_graph.add((quality_assessment_IRI, self.MQIO.assessedMapping, mapping_file_IRI))
        mapping = URIRef(list(self.validation_graph.objects(None, self.MQIO.assessedMapping))[0])
        self.validation_graph.add((URIRef(str(mapping).split("/")[-1]), RDF.type, self.MQIO.MappingArtefact))
        # self.add_assessment_time()
        # self.add_report_time()
        # add agent details
        name = URIRef(self.EX.alexRandles)
        validation_report_IRI = self.EX.mappingValidationReport + "-0"
        # self.validation_graph.add((name, RDF.type , self.PROV.Agent))
        # self.validation_graph.add((quality_assessment_IRI, self.MQIO.wasPerfomedBy, name))
        self.validation_graph.add((quality_assessment_IRI, self.MQIO.hasValidationReport, validation_report_IRI))
        return quality_assessment_IRI

    def insert_validation_report(self):
        validation_report_IRI = self.EX.mappingValidationReport + "-0"
        self.validation_graph.add((validation_report_IRI, RDF.type, self.MQIO.MappingValidationReport))
        return validation_report_IRI

    def iterate_violations(self, validation_report_IRI):
        for violation_ID in self.validation_results:
            current_violation = self.validation_results[violation_ID]
            self.insert_violation(violation_ID, current_violation, validation_report_IRI)

    def insert_violation(self, violation_ID, violation_information, validation_report_IRI):
        # mqv:hasViolation mqv:violation0,
        current_violation_IRI = self.EX.violation + "-" + str(violation_ID)
        self.validation_graph.add((validation_report_IRI, self.MQIO.hasViolation, current_violation_IRI))
        self.insert_violation_information(violation_information, current_violation_IRI)

    def insert_violation_information(self, violation_information, current_violation_IRI):
        metric_IRI = URIRef(self.EX + violation_information["metric_identifier"])
        mqio_metric_IRI = URIRef(self.MQIO_METRIC + violation_information["metric_identifier"])
        result_message = Literal(violation_information["result_message"], datatype=XSD.string)
        self.validation_graph.add((current_violation_IRI, RDF.type, self.MQIO.MappingViolation))
        self.validation_graph.add((current_violation_IRI, self.MQIO.isDescribedBy, mqio_metric_IRI))
        # self.validation_graph.add((metric_IRI, RDF.type, mqv_metric_IRI))
        self.validation_graph.add((current_violation_IRI, self.MQIO.hasResultMessage, result_message))
        self.insert_violation_value(violation_information, current_violation_IRI)
        self.insert_violation_location(violation_information, current_violation_IRI)

    def insert_violation_location(self, violation_information, current_violation_IRI):
        # the triple map and location within the triple map
        self.insert_triple_map(violation_information, current_violation_IRI)
        violation_location = Literal(violation_information["location"], datatype=XSD.string)
        self.validation_graph.add((current_violation_IRI, self.MQIO.hasLocation, violation_location))

    @staticmethod
    def format_triple_map_IRI(triple_map_name):
        # removes local file name
        # e.g <file:///home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/validation_report.ttl#MapERA5SamplePoint>
        if "#" in triple_map_name:
            formatted_IRI = triple_map_name.split("#")[-1]
            return URIRef("#%s" % formatted_IRI)
        elif "/" in triple_map_name:
            formatted_IRI = triple_map_name.split("/")[-1]
        else:
            formatted_IRI = triple_map_name
        return URIRef("%s" % formatted_IRI)

    def insert_triple_map(self, violation_information, current_violation_IRI):
        triple_map_name = violation_information["triple_map"]
        triple_map_IRI = self.format_triple_map_IRI(triple_map_name)
        self.validation_graph.add((current_violation_IRI, self.MQIO.inTripleMap, triple_map_IRI))

    def insert_violation_value(self, violation_information, current_violation_IRI):
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
                    self.validation_graph.add((current_violation_IRI, self.MQIO.hasLiteralValue, violation_value))
                else:
                    self.validation_graph.add((current_violation_IRI, self.MQIO.hasObjectValue, URIRef(violation_value)))
            else:
                for value in violation_value:
                    violation_value_type = type(violation_value)
                    if violation_value_type == Literal:
                        self.validation_graph.add((current_violation_IRI, self.MQIO.hasLiteralValue, value))
                    else:
                        self.validation_graph.add((current_violation_IRI, self.MQIO.hasObjectValue, value))

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
        for (prefix, namespace) in self.mapping_namespaces.items():
            print(prefix, namespace)
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
