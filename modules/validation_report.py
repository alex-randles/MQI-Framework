# Old validation report which uses SPARQL queries instead of rdflib built in functions to add triples to a graph
import rdflib


class ValidationReport:

    def __init__(self, validation_results, output_file, mapping_file, form_data={}):
        self.output_file = output_file
        self.form_data = form_data
        self.mapping_file = mapping_file
        self.mapping_graph = rdflib.Graph().parse(mapping_file, format="ttl")
        self.mapping_namespaces = {prefix: namespace for (prefix, namespace) in self.mapping_graph.namespaces()}
        self.validation_graph = rdflib.Graph()
        self.MQIO = rdflib.Namespace("https://w3id.org/MQIO#")
        self.MQIO_METRIC = rdflib.Namespace("https://w3id.org/MQIO-metrics/#")
        self.EX = rdflib.Namespace("http://example.org/")
        self.R2RML = rdflib.Namespace("http://www.w3.org/ns/r2rml#")
        self.PROV = rdflib.Namespace("http://www.w3.org/ns/prov#")
        self.RML = rdflib.Namespace("http://semweb.mmlab.be/ns/rml#")
        self.bind_namespaces()
        self.validation_results = validation_results
        self.violation_count = 0
        self.assessment_identifier = None
        self.create_validation_report()

    def get_mapping_identifier(self):
        # A function that returns the mapping name with the full path
        mapping_file_identifier = rdflib.term.URIRef(self.mapping_file.split("/")[-1])
        return mapping_file_identifier

    def create_validation_report(self):
        # A function create the validation report and add each violation
        validation_report_identifier = self.insert_validation_report()
        self.insert_assessment_information()
        self.iterate_violations(validation_report_identifier)
        self.add_form_data()
        self.save_validation_report()

    def add_form_data(self):
        # A function to add additional metadata (creator and other agents)
        if self.form_data.get("add-information"):
            mapping_file_identifier = rdflib.term.URIRef(self.mapping_file.split("/")[-1])
            self.validation_graph.add((mapping_file_identifier, rdflib.RDF.type, self.MQIO.MappingArtefact))
            self.add_creator_agent(mapping_file_identifier)
            self.add_performer_agent()

    def add_creator_agent(self, mapping_identifier):
        # adding creator name
        creator_name = self.form_data.get('creator-name')
        if creator_name:
            creator_name_identifier = rdflib.term.URIRef("http://example.org/" + "".join([name.capitalize() for name in self.form_data.get('creator-name').split()]))
            self.validation_graph.add((mapping_identifier, self.MQIO.wasCreatedBy, creator_name_identifier))

    def add_performer_agent(self):
        # adding the person who performed the assessment
        performed_by_name = self.form_data.get("performed-by-name")
        if performed_by_name:
            performed_by_identifier = rdflib.term.URIRef("http://example.org/" + "".join([name.capitalize() for name in self.form_data.get("performed-by-name").split()]))
            self.validation_graph.add((self.assessment_identifier, self.PROV.wasAssociatedWith, performed_by_identifier))

    def insert_assessment_information(self):
        # ex:mappingQualityAssessment a mqv:MappingAssessment ;
        self.assessment_identifier = self.EX.mappingQualityAssessment
        self.validation_graph.add((self.assessment_identifier, rdflib.RDF.type, self.MQIO.MappingAssessment))
        # mqv:assessedMapping </home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/valid_mapping.ttl> .
        mapping_file_identifier = rdflib.term.URIRef(self.mapping_file.split("/")[-1])
        self.validation_graph.add((self.assessment_identifier, self.MQIO.assessedMapping, mapping_file_identifier))
        mapping = rdflib.term.URIRef(list(self.validation_graph.objects(None, self.MQIO.assessedMapping))[0])
        self.validation_graph.add((rdflib.term.URIRef(str(mapping).split("/")[-1]), rdflib.RDF.type, self.MQIO.MappingArtefact))
        validation_report_identifier = self.EX.mappingValidationReport + "-0"
        self.validation_graph.add((self.assessment_identifier, self.MQIO.hasValidationReport, validation_report_identifier))
        return self.assessment_identifier

    def insert_validation_report(self):
        validation_report_identifier = self.EX.mappingValidationReport + "-0"
        self.validation_graph.add((validation_report_identifier, rdflib.RDF.type, self.MQIO.MappingValidationReport))
        return validation_report_identifier

    def iterate_violations(self, validation_report_identifier):
        for violation_identifier in self.validation_results:
            current_violation = self.validation_results[violation_identifier]
            self.insert_violation(violation_identifier, current_violation, validation_report_identifier)

    def insert_violation(self, violation_identifier, violation_information, validation_report_identifier):
        # mqv:hasViolation mqv:violation0,
        current_violation_identifier = self.EX.violation + "-" + str(violation_identifier)
        self.validation_graph.add((validation_report_identifier, self.MQIO.hasViolation, current_violation_identifier))
        self.insert_violation_information(violation_information, current_violation_identifier)

    def insert_violation_information(self, violation_information, current_violation_identifier):
        metric_identifier = rdflib.term.URIRef(self.EX + violation_information.get("metric_identifier"))
        mqio_metric_identifier = rdflib.term.URIRef(self.MQIO_METRIC + violation_information.get("metric_identifier"))
        result_message = rdflib.term.Literal(violation_information.get("result_message"), datatype=rdflib.XSD.string)
        self.validation_graph.add((current_violation_identifier, rdflib.RDF.type, self.MQIO.MappingViolation))
        self.validation_graph.add((current_violation_identifier, self.MQIO.isDescribedBy, mqio_metric_identifier))
        self.validation_graph.add((current_violation_identifier, self.MQIO.hasResultMessage, result_message))
        self.insert_violation_value(violation_information, current_violation_identifier)
        self.insert_violation_location(violation_information, current_violation_identifier)

    def insert_violation_location(self, violation_information, current_violation_identifier):
        # the triple map and location within the triple map
        self.insert_triple_map(violation_information, current_violation_identifier)
        violation_location = violation_information.get("location")
        if violation_location:
            location_literal = rdflib.term.Literal(violation_location, datatype=rdflib.XSD.string)
            self.validation_graph.add((current_violation_identifier, self.MQIO.hasLocation, location_literal))

    @staticmethod
    def format_triple_map_identifier(triple_map_name):
        # removes local file name from IRI
        if "#" in triple_map_name:
            formatted_identifier = triple_map_name.split("#")[-1]
            return rdflib.term.URIRef("#%s" % formatted_identifier)
        elif "/" in triple_map_name:
            formatted_identifier = triple_map_name.split("/")[-1]
        else:
            formatted_identifier = triple_map_name
        return rdflib.term.URIRef("%s" % formatted_identifier)

    def insert_triple_map(self, violation_information, current_violation_identifier):
        triple_map_name = violation_information.get("triple_map")
        if triple_map_name:
            triple_map_identifier = self.format_triple_map_identifier(triple_map_name)
            self.validation_graph.add((current_violation_identifier, self.MQIO.inTripleMap, triple_map_identifier))

    def insert_violation_value(self, violation_information, current_violation_identifier):
        # 'value': rdflib.term.URIRef('http://www.opengis.net/ont/geosparql#hasGeometry'),
        violation_value = violation_information.get("value")
        print(violation_value, "violation value")
        # it could be none for example no parent column defined in join
        if violation_value:
            # check if more than one value
            violation_value_type  = type(violation_value)
            if  violation_value_type is not tuple:
                if violation_value_type == rdflib.term.Literal:
                    violation_value = rdflib.term.Literal(violation_value,datatype=rdflib.XSD.string)
                    self.validation_graph.add((current_violation_identifier, self.MQIO.hasLiteralValue, violation_value))
                else:
                    self.validation_graph.add((current_violation_identifier, self.MQIO.hasObjectValue, rdflib.term.URIRef(violation_value)))
            else:
                for value in violation_value:
                    violation_value_type = type(violation_value)
                    if violation_value_type == rdflib.term.Literal:
                        self.validation_graph.add((current_violation_identifier, self.MQIO.hasLiteralValue, value))
                    else:
                        self.validation_graph.add((current_violation_identifier, self.MQIO.hasObjectValue, value))

    def create_mapping_assessment(self):
        # A function create the validation report and add each violation
        self.validation_graph.add((self.EX.mappingQualityAssessment, rdflib.RDF.type, self.MQIO.MappingAssessment))

    def bind_namespaces(self):
        self.validation_graph.bind("mqio", self.MQIO)
        self.validation_graph.bind("ex", self.EX)
        self.validation_graph.bind("rr", self.R2RML)
        self.validation_graph.bind("prov", self.PROV)
        self.validation_graph.bind("mqio-metrics", self.MQIO_METRIC)
        self.validation_graph.bind("rml", self.RML)
        self.bind_mapping_namespaces()

    def bind_mapping_namespaces(self):
        # bind the namespaces used in the original/refined mapping
        for (prefix, namespace) in self.mapping_namespaces.items():
            if namespace != rdflib.term.URIRef(self.EX):
                self.validation_graph.bind(prefix, namespace)

    def print_graph(self):
        print(self.validation_graph.serialize(format='turtle').decode('utf-8'))

    def save_validation_report(self):
        self.validation_graph.serialize(destination="validation_report.ttl", format='ttl')


if __name__ == "__main__":
    # quality_information = ValidateQuality("/home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/valid_mapping.ttl")
    # mapping_file = quality_information.file_name
    mapping_file = "/home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/mappings/video_demo.ttl"
    validation_results = {0: {'metric_identifier': 'D6', 'result_message': 'Usage of incorrect domain.', 'value': rdflib.term.URIRef('http://www.opengis.net/ont/geosparql#hasGeometry'), 'location': rdflib.term.BNode('ub5bL55C24'), 'triple_map': 'file:///home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/static/uploads/valid_mapping.ttl#MapERA5SamplePoint'},
                          1: {'metric_identifier': 'M9', 'result_message': 'Language tag not defined in RFC 5646.', 'value': rdflib.term.Literal('fff'), 'location': rdflib.term.BNode('ub5bL57C16'), 'triple_map': 'file:///home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/static/uploads/valid_mapping.ttl#MapERA5SamplePoint'}}
    validation_report = ValidationReport(validation_results, "/home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/validation_report.ttl", mapping_file, form_data={})
    validation_report.print_graph()
