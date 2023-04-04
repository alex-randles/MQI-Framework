import rdflib
import operator
import re
import pandas as pd
from fs.osfs import OSFS
import json
from rdflib import Graph, URIRef, BNode, RDFS, RDF, OWL

# try:
# import modules.validation_report
# import modules.fetch_vocabularies
# import modules.parse_mapping_graph
# from modules.parse_mapping_graph import ParseMapping
# except:
#     from fetch_vocabularies import FetchVocabularies
#     from validation_report import ValidationReport
#     from parse_mapping_graph import ParseMapping


# SPARQL query abbreviations
# om - object map
# pm - predicate object map
# sm - subject map

#
from modules.validation_report import ValidationReport
from modules.fetch_vocabularies import FetchVocabularies
from modules.parse_mapping_graph import ParseMapping

# from validation_report import ValidationReport
# from fetch_vocabularies import FetchVocabularies
# from parse_mapping_graph import ParseMapping

# program gets thread locked if declared as class variable
current_FS = OSFS(".")


class ValidateQuality:

    def __init__(self, file_name):
        self.file_name = file_name
        self.parsed_mapping = ParseMapping(file_name)
        self.triple_maps = self.parsed_mapping.triple_map_graphs
        self.mapping_graph = self.parsed_mapping.mapping_graph
        self.triple_references = self.create_triple_references()
        self.namespaces = {prefix:namespace for (prefix, namespace) in self.mapping_graph.namespaces()}
        self.vocabularies = FetchVocabularies(file_name)
        # mainly used for vocabulary metrics
        self.unique_namespaces = self.vocabularies.get_unique_namespaces()
        self.unique_namespaces = [namespace for namespace in self.unique_namespaces]
        self.violation_counter = 0
        self.validation_results = {}
        self.undefined_values = []
        self.test_count = 0
        # store the range and domain in cache to speed execution
        self.range_cache = {}
        self.domain_cache = {}
        self.refinements = []
        self.current_graph = None
        self.current_triple_identifier = None
        self.detailed_metric_information = {
            # data quality aspect metrics
            "D1": "https://www.w3.org/TR/dwbp/#AccessRealTime", # undefined property
            "D2": "https://www.w3.org/TR/dwbp/#AccessRealTime", # undefined property
            "D3": "https://www.w3.org/TR/rdf-schema/#ch_domain",  # domain
            "D4": "https://www.w3.org/TR/dwbp/#AccessRealTime",  # undefined class
            "D5": "https://www.w3.org/TR/2004/REC-owl-guide-20040210/#DisjointClasses", # disjoint
            "D6": "https://www.w3.org/TR/rdf-schema/#ch_range",
            "D7": "https://www.w3.org/TR/rdf-schema/#ch_datatype", # incorrect datatype
            # mapping quality aspect metrics
            "MP1": "https://www.w3.org/TR/r2rml/#dfn-triples-map",
            "MP9": "https://tools.ietf.org/html/rfc5646",
            "MP12": "https://www.w3.org/TR/r2rml/#foreign-key",
            "MP10": "https://www.w3.org/TR/r2rml/#typing",
            "MP8": "https://www.w3.org/TR/r2rml/#typing",
            "MP2": "https://www.w3.org/TR/r2rml/#dfn-triples-map",
            "MP11": "https://tools.ietf.org/html/rfc5646", # language tags
            # vocabulary quality aspect metrics
            "VOC1": "https://www.w3.org/TR/dwbp/#ProvideMetadata", # human readable labels
            "VOC2": "https://www.w3.org/TR/rdf-schema/#ch_domain", # domain and range definitions
            "VOC3": "https://www.w3.org/TR/rdf-schema/#ch_domain", # basic provenance
            "VOC4": "https://wiki.creativecommons.org/wiki/License_RDF", # machine readable license
            "VOC5": "https://wiki.creativecommons.org/wiki/License_RDF", # human readable license
        }
        self.metric_descriptions = self.create_metric_descriptions()
        self.validate_triple_maps()

    @staticmethod
    def create_metric_descriptions():
        metric_description_file = "metric_descriptions.csv"
        df = pd.read_csv(metric_description_file)
        metric_descriptions = {}
        for row in df.itertuples():
            metric_identifier = row[1]
            metric_description = row[3]
            metric_descriptions[metric_identifier] = metric_description.replace("\n", " ")
        return metric_descriptions

    def find_prefix(self, IRI):
        # find prefix with longest matching prefix
        if IRI:
            match = []
            # create dictionary with prefix as key and namespace as value
            for (prefix, namespace) in self.namespaces.items():
                if namespace in IRI:
                    match.append(namespace)
            # if matching namesapce, return the longest
            if match:
                match_namespace = max(match)
                prefix = [prefix for (prefix, namespace) in self.namespaces.items() if namespace == match_namespace][0]
                IRI = IRI.replace(match_namespace, prefix + ":")
                return " %s " % (IRI)
            elif type(IRI) is tuple:
                result = "".join(([self.find_prefix(current_identifier) for current_identifier in IRI]))
                return result
            return IRI

    def validate_triple_maps(self):
        # metrics = [self.validate_]
        # iterate each triple map
        # self.update_progress_bar()
        for (triple_map_identifier, graph) in self.triple_maps:
            # self.blank_node_references[triple_map_identifier] = self.generate_triple_references(graph)
            self.current_graph = graph
            self.current_triple_identifier = triple_map_identifier
            print(self.current_triple_identifier)
            self.properties = self.get_properties_range()
            self.classes = self.get_classes()
            self.validate_data_metrics()
            # self.validate_mapping_metrics()
            # self.validate_data_metrics()
            # self.update_progress_bar()
        # each triple map is tested otherwise
        # self.validate_vocabulary_metrics()
        return self.validation_results

    def validate_data_metrics(self):
        # A function to validate all of the data quality metrics
        self.validate_D1()
        self.validate_D2()
        self.validate_D3()
        self.validate_D4()
        self.validate_D5()
        self.validate_D6()
        self.validate_D7()

    def validate_mapping_metrics(self):
        # A function to validate each of the mapping related quality metrics
        self.validate_MP1()
        self.validate_MP2()
        self.validate_MP3()
        self.validate_MP4()
        self.validate_MP5()
        self.validate_MP6()
        self.validate_MP7()
        self.validate_MP8()

    def validate_vocabulary_metrics(self):
        # pass
        self.validate_VOC1()
        # self.validate_VOC2()
        self.validate_VOC3()
        self.validate_VOC4()
        self.validate_VOC5()
        self.validate_VOC6()

    def validate_D1(self):
        # A function to validate the usage of undefined classes
        metric_identifier = "D1"
        for key in list(self.classes):
            class_identifier = self.classes[key]["class"]
            subject_identifier = self.classes[key]["subject"]
            metric_result = self.validate_undefined(class_identifier, subject_identifier, "class", metric_identifier)
            # if class is undefined
            if metric_result:
                del self.classes[key]
                self.add_violation(metric_result)

    def validate_D2(self):
        # A function to validate the usage of undefined properties
        metric_identifier = "D2"
        for key in list(self.properties):
            property_identifier = self.properties[key]["property"]
            subject_identifier = self.properties[key]["subject"]
            metric_result = self.validate_undefined(property_identifier, subject_identifier, "property", metric_identifier)
            # if property is undefined
            if metric_result:
                # remove if undefined
                del self.properties[key]
                self.add_violation(metric_result)

    def validate_D3(self):
        # A function to validate the usage of correct domain definitions
        metric_identifier = "D3"
        for key in list(self.properties):
            property_identifier = self.properties[key]["property"]
            subject_identifier = self.properties[key]["subject"]
            metric_result = self.validate_domain(property_identifier, subject_identifier, metric_identifier)
            # if domain is not present
            if metric_result:
                self.add_violation(metric_result)

    def validate_D4(self):
        result_message = "Query parameters in URI."
        metric_identifier = "D4"
        query = """SELECT ?object ?subject
                    WHERE {
                      ?subject ?predicate ?object
                      FILTER(isIRI(?object) && CONTAINS(STR(?object), "?"))
                    }   
               """
        qres = self.current_graph.query(query)
        for row in qres:
            object_identifier = row[0]
            subject_identifier = row[1]
            self.add_violation([metric_identifier, result_message, object_identifier, subject_identifier])

    def validate_D5(self):
        # A function to validate the usage of disjoint classes
        classes_and_subjects = self.get_classes()
        # a list of only class IRI's
        classes = [values["class"] for values in classes_and_subjects.values()]
        metric_identifier = "D5"
        # more than one class is needed to be disjoint
        if len(classes) <= 1:
            return
        # iterate through each class and find disjoint classes
        for key in classes_and_subjects.keys():
            current_identifier = classes_and_subjects[key]["class"]
            if current_identifier not in self.undefined_values:
                disjoint_classes = self.find_disjoint_classes(current_identifier)
                for class_identifier in disjoint_classes:
                    if class_identifier in classes:
                        subject_identifier = classes_and_subjects[key]["subject"]
                        result_message = "Class %s is disjoint with %s" % (
                        self.find_prefix(current_identifier), self.find_prefix(class_identifier))
                        self.add_violation([metric_identifier, result_message, (current_identifier, class_identifier), subject_identifier])
                        classes.remove(class_identifier)
                        classes.remove(current_identifier)
                    # else:
                    #     continue

    def validate_D6(self):
        # CHECKING THE TYPE OF THE PROPERTY IS ANOTHER OPTION COULD BE SLOWER
        metric_identifier = "D6"
        result_message = "Usage of incorrect range."
        for key in list(self.properties):
            property = self.properties[key]["property"]
            term_type = self.properties[key]["termType"]
            objectMap = self.properties[key]["objectMap"]
            # only retrieve range if term type to speed up execution time
            # if not term_type:
            #     term_type = URIRef("http://www.w3.org/ns/r2rml#Literal")
            if term_type:
                resource_type = self.get_type(property)
                if OWL.DatatypeProperty in resource_type and term_type != URIRef("http://www.w3.org/ns/r2rml#Literal"):
                    result_message = "Usage of incorrect range. Term type should be 'rr:Literal' for property '{}'.".format(self.find_prefix(property))
                    self.add_violation([metric_identifier, result_message, term_type, objectMap])
                elif OWL.ObjectProperty in resource_type and term_type == URIRef("http://www.w3.org/ns/r2rml#Literal"):
                    result_message = "Usage of incorrect range. Term type should be 'rr:IRI' or 'rr:BlankNode' for property '{}'.".format(self.find_prefix(property))
                    self.add_violation([metric_identifier, result_message, term_type, objectMap])

    def validate_D7(self):
        metric_identifier = "D7"
        result_message = "Usage of incorrect datatype."
        # xsd:anySimpleType, xsd:anyType could be declared as datatypes in the vocabulary
        # these can be any datatypes so not need to check
        excluded_datatypes = [URIRef("http://www.w3.org/2001/XMLSchema#anyType"),
                              URIRef("http://www.w3.org/2001/XMLSchema#anySimpleType")]
        # only if datatype
        # datatype_properties = {key:value for (key,value) in properties.items() if value["datatype"] is not None}
        for key in list(self.properties):
            property = self.properties[key]["property"]
            objectMap = self.properties[key]["objectMap"]
            datatype = self.properties[key]["datatype"]
            # if a datatype assigned to object map
            if datatype:
                range = self.get_range(property)
                if range != URIRef("http://www.w3.org/2001/XMLSchema#anyURI"):
                    # if any of the datatypes can be any datatype, skip this iteration
                    if datatype in excluded_datatypes:
                        continue
                    if self.is_datatype_range(range):
                        if datatype != range:
                            self.add_violation([metric_identifier, result_message, property, objectMap])

    def validate_undefined(self, property_identifier, subject_identifier, value_type, metric_identifier):
        result_message = "Usage of undefined %s." % value_type
        query = "ASK { GRAPH ?g { <%s> ?predicate ?object . } } " % property_identifier
        qres = self.vocabularies.query_local_graph(property_identifier, query)
        is_defined_concept = qres["boolean"]
        if is_defined_concept is False:
            query = "ASK { GRAPH <%s> { ?subject ?predicate ?object . } }" % self.get_namespace(property_identifier)
            qres = self.vocabularies.query_local_graph(property_identifier, query)
            is_defined_concept = qres["boolean"]
            if is_defined_concept is True:
                return [metric_identifier, result_message, property_identifier, subject_identifier]

    def validate_VOC1(self):
        # A function to validate no human readable labelling and comments
        result_message = "No Human Readable Labelling and Comments."
        metric_identifier = "VOC1"
        # validate only classes to speed up execution
        classes = self.get_classes()
        for key in classes.keys():
            class_identifier = classes[key]["class"]
            subject_identifier = classes[key]["subject"]
            if class_identifier not in self.undefined_values:
                human_label_predicates = ["rdfs:label", "dcterms:title", "dcterms:description",
                                          "dcterms:alternative", "skos:altLabel", "skos:prefLabel", "powder-s:text",
                                          "skosxl:altLabel", "skosxl:hiddenLabel", "skosxl:prefLabel",
                                          "skosxl:literalForm", "rdfs:comment",
                                          "schema:description", "schema:description", "foaf:name"]
                query = "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> \n" \
                         "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n" \
                         "PREFIX foaf: <http://xmlns.com/foaf/0.1/>\n" \
                         "PREFIX dcterms: <http://purl.org/dc/terms/> \n" \
                         "PREFIX ct: <http://data.linkedct.org/resource/linkedct/> \n" \
                         "PREFIX skos: <http://www.w3.org/2004/02/skos/core#> \n" \
                         "PREFIX skosxl: <http://www.w3.org/2008/05/skos-xl#> \n" \
                         "PREFIX schema: <http://schema.org/> \n" \
                         "PREFIX powder-s: <http://www.w3.org/2007/05/powder-s#> \n" \
                         "ASK { <%s> %s ?label } " % (class_identifier, "|".join(human_label_predicates))
                qres = self.vocabularies.query_local_graph(class_identifier, query)
                if isinstance(qres, rdflib.plugins.sparql.processor.SPARQLResult):
                    for row in qres:
                        if row is False:
                            self.add_violation([metric_identifier, result_message, class_identifier, subject_identifier])

    # def validate_VOC2(self):
    #     metric_identifier = "VOC2"
    #     result_message = "No domain definition ."
    #     properties = self.get_properties()
    #     for key in properties.keys():
    #         property_identifier = properties[key]["property"]
    #         subject_identifier = properties[key]["subject"]
    #         print("VALIDATIN DOMAIN DEFINITION", property_identifier, self.domain_cache, "\n", self.domain_cache.get(property_identifier))
    #         if property_identifier not in self.undefined_values:
    #             print("DOMAIN FROM CACHE")
    #             domain_defintion = self.domain_cache.get(property_identifier)
    #             print(domain_defintion)
    #             print("DOMAIN FROM VOCABULARIES")
    #             print(self.get_domain(property_identifier))

    def validate_VOC3(self):
        # A function to validate basic provenance information
        result_message = "No Basic Provenance Information."
        metric_identifier = "VOC3"
        for namespace in self.unique_namespaces:
            provenance_predicates = ["dc:creator", "dc:publisher", "dct:creator", "dct:contributor",
                                "dcterms:publisher", "dc:title", "dc:description", "rdfs:comment", "foaf:maker"]
            query = "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> " \
                    "PREFIX dc: <http://purl.org/dc/elements/1.1/> " \
                    "PREFIX owl: <http://www.w3.org/2002/07/owl#>\n" \
                     "PREFIX foaf: <http://xmlns.com/foaf/0.1/>\n" \
                     "PREFIX dcterms: <http://purl.org/dc/terms/> \n" \
                    "PREFIX dct: <http://purl.org/dc/terms/> " \
                     "ASK { ?subject a owl:Ontology; " \
                    "              %s ?label } " % ("|".join(provenance_predicates))
            qres = self.vocabularies.query_local_graph(namespace, query)
            if isinstance(qres, rdflib.plugins.sparql.processor.SPARQLResult):
                for row in qres:
                    if row is False:
                        self.add_violation([metric_identifier, result_message, namespace, None])

    def validate_VOC4(self):
        # A function to validate basic provenance information
        result_message = "No Machine-Readable license."
        metric_identifier = "VOC4"
        # returning true for now as testing mappings
        # return True
        unique_namespaces = list(set(self.unique_namespaces))
        print("VALIDATING NAMESPACES", unique_namespaces)
        for namespace in unique_namespaces:
            query = """
            PREFIX dct: <http://purl.org/dc/terms/>
            PREFIX dc: <http://purl.org/dc/elements/1.1/>
            PREFIX xhtml: <http://www.w3.org/1999/xhtml#>
            PREFIX cc: <http://creativecommons.org/ns#>
            PREFIX doap: <http://usefulinc.com/ns/doap#>
            PREFIX schema: <http://schema.org/>
            SELECT ?subject ?predicate ?object
            WHERE {
              ?subject ?predicate ?object
              FILTER(?predicate IN (dct:license, dct:rights, dc:rights, xhtml:license, cc:license, dc:license, doap:license, schema:license))
            }
            """
            qres = self.vocabularies.query_local_graph(namespace, query)
            if isinstance(qres, rdflib.plugins.sparql.processor.SPARQLResult):
                if not qres:
                    self.add_violation([metric_identifier, result_message, namespace, None])

    def validate_VOC5(self):
        # A function to validate basic provenance information
        result_message = "No Human-Readable license."
        metric_identifier = "VOC5"
        # returning true for now as testing mappings
        # return True
        unique_namespaces = list(set(self.unique_namespaces))
        for namespace in unique_namespaces:
            query = """
            SELECT ?subject ?predicate ?object
            WHERE {
              ?subject ?predicate ?object
              FILTER(CONTAINS(?object, "license")) 
            }
            """
            qres = self.vocabularies.query_local_graph(namespace, query)
            if isinstance(qres, rdflib.plugins.sparql.processor.SPARQLResult):
                if not qres:
                    self.add_violation([metric_identifier, result_message, namespace, None])

    def get_triple_maps_identifier(self):
        # returns IRI for all triple maps
        triple_maps = []
        for (s, p, o) in self.mapping_graph.triples((None, None, None)):
            if not isinstance(s, BNode):
                if s not in triple_maps:
                    triple_maps.append(s)
        return triple_maps

    def assign_triples_to_each_map(self):
        # returns a dic with the triple map as key and the triples within that triple map as values
        # it will only include triples linked to the triple map IRI
        triple_maps_identifier = self.get_triple_maps_identifier()
        # iterate each triple map and find triples which have blank nodes
        # e.g #ORGANISATIONOFOFFICE http://www.w3.org/ns/r2rml#predicateObjectMap ub1bL248C24
        triple_map_triples = {}
        for IRI in triple_maps_identifier:
            # empty dictionary assign triples to this triple map
            triple_map_triples[IRI] = {}
            for (s, p, o) in self.mapping_graph.triples((IRI, None, None)):
                # if object is blank node such as rr:logicalTable relate that property to the blank node
                if isinstance(o, BNode):
                    if p in triple_map_triples[IRI].keys():
                        triple_map_triples[IRI][p].append(o)
                    else:
                        triple_map_triples[IRI][p] = [o]
                else:
                    # for values not relating to blank nodes such as #ORGANISATIONOFOFFICE rr:predicate foaf:Agent
                    not_bNode_key = "not_bNode"
                    if not_bNode_key in triple_map_triples[IRI].keys():
                        triple_map_triples[IRI][not_bNode_key].append((p, o))
                    else:
                        triple_map_triples[IRI][not_bNode_key] = [(p, o)]
        return triple_map_triples

    @staticmethod
    def find_identifier(node_value):
        regex = re.search('L(.+?)C', node_value)
        if regex:
            match = regex.group(1)
            return int(match)
        return int(0)

    def sort_bNodes(self, bNodes_values):
        # takes list similar to this  [rdflib.term.BNode('ub1bL306C24'), rdflib.term.BNode('ub1bL317C24')]
        # order by which blank node  appeared first
        add_identifier = [(bNode, self.find_identifier(bNode)) for bNode in bNodes_values]
        sorted_bNode = sorted(add_identifier, key=lambda x: x[1])
        remove_identifier = [bNode for (bNode, _) in sorted_bNode]
        return remove_identifier

    def order_triple_maps_triples(self, triple_references):
        # will order triples based on the blank node identifier assigned
        ordered_triples = {}
        for (triple_map, values) in triple_references.items():
            for (predicate, bNodes) in values.items():
                if predicate != "not_bNode":
                    sorted_bNodes = self.sort_bNodes(bNodes)
                    triple_references[triple_map][URIRef(predicate)] = sorted_bNodes
        return triple_references

    def create_triple_references(self):
        triple_map_triples = self.assign_triples_to_each_map()
        triple_references = self.order_triple_maps_triples(triple_map_triples)
        return triple_references

    def find_violation_location(self, violation_identifier):
        # A function which returns the triple map and the location within it
        for (triple_map, values) in self.triple_references.items():
            for (predicate, bNodes_values) in self.triple_references[triple_map].items():
                if violation_identifier in bNodes_values:
                    location_num = bNodes_values.index(violation_identifier) + 1
                    violation_location = self.format_user_location(predicate, location_num)
                    return  violation_location
                elif self.violation_is_object(bNodes_values, violation_identifier):
                    bNode = self.violation_is_object(bNodes_values, violation_identifier)
                    location_num = bNodes_values.index(bNode) + 1
                    violation_location = self.format_user_location(predicate, location_num)
                    return  violation_location

    def violation_is_object(self, bNode_values, violation_identifier):
        # since we only store blank nodes for logical table, subjectMap, predicateObjectMap
        # this function can tell if the violation is within these
        for bNode in bNode_values:
            for (s,p,o) in self.mapping_graph.triples((bNode, None, None)):
                if o == violation_identifier:
                    return bNode
                # if the violation is contained with a join condition for example
                elif isinstance(o, BNode):
                    for (s, p, o) in self.mapping_graph.triples((o, None, None)):
                        if o == violation_identifier:
                            return bNode

    def format_user_location(self, predicate, location_num):
        # ( http://www.w3.org/ns/r2rml#predicateObjectMap , 1) -> predicateObjectMap1
        # making it easier for the user to read
        if predicate != URIRef("http://www.w3.org/ns/r2rml#subjectMap"):
            location_predicate = self.strip_identifier(predicate)
            location = "%s-%s" % (location_predicate, location_num)
        else:
            location = self.strip_identifier(predicate)
        return location

    def strip_identifier(self, IRI):
        # (http://www.w3.org/ns/r2rml#predicateObjectMap) -> #predicateObjectMap
        if "#" in IRI:
            return IRI.split("#")[-1]
        elif "/" in IRI:
            return IRI.split("/")[-1]
        return IRI

    def get_namespace(self, IRI):
        if "#" in IRI:
            IRI = IRI[:IRI.rfind("#") + 1]
        else:
            IRI = IRI[:IRI.rfind("/") + 1]
        return IRI


    def validate_MP2(self):
        result_message = "Term type for subject map should be an IRI or Blank Node"
        metric_identifier = "MP2"
        query = """PREFIX rr: <http://www.w3.org/ns/r2rml#>
                    SELECT ?subjectMap ?termType
                    WHERE {
                      ?subject rr:subjectMap ?subjectMap .
                      ?subjectMap rr:termType ?termType . 
                      FILTER(?termType NOT IN (rr:IRI, rr:BlankNode))
                    }
                """
        qres = self.current_graph.query(query)
        for row in qres:
            subject = row[0]
            term_type = row[1]
            self.add_violation([metric_identifier, result_message, term_type, subject])

    def validate_MP3(self):
        result_message = "Term type for predicate map should be an IRI."
        metric_identifier = "MP3"
        query = """PREFIX rr: <http://www.w3.org/ns/r2rml#>
                    SELECT ?predicateMap ?termType
                    WHERE {
                      ?subject rr:predicateObjectMap ?pom . 
                      ?pom rr:predicateMap ?predicateMap . 
                      ?predicateMap rr:termType ?termType . 
                      FILTER(?termType NOT IN (rr:IRI))
                    }
                """
        qres = self.current_graph.query(query)
        for row in qres:
            subject = row[0]
            term_type = row[1]
            self.add_violation([metric_identifier, result_message, term_type, subject])

    def validate_MP4(self):
        # The user may spell one of the term types incorrect e.g rr:Literal(s)
        result_message = "Term type for object map should be an IRI, Blank Node or Literal."
        metric_identifier = "MP4"
        query = """PREFIX rr: <http://www.w3.org/ns/r2rml#>
                    SELECT ?objectMap ?termType
                    WHERE {
                      ?subject rr:predicateObjectMap ?pom . 
                      ?pom rr:objectMap ?objectMap . 
                      ?objectMap rr:termType ?termType . 
                      FILTER(?termType NOT IN (rr:IRI, rr:BlankNode, rr:Literal))
                    }
                """
        qres = self.current_graph.query(query)
        for row in qres:
            subject = row[0]
            term_type = row[1]
            self.add_violation([metric_identifier, result_message, term_type, subject])

    def find_disjoint_classes(self, IRI):
        # a function which finds the classes disjoint to IRI argument (if any)
        query = """PREFIX owl: <http://www.w3.org/2002/07/owl#>
                   SELECT DISTINCT ?disjointClass
                   WHERE {
                      GRAPH <%s> {
                          <%s> owl:disjointWith ?disjointClass .
                      }
                   }
                """ % (self.get_namespace(IRI), IRI)
        qres = self.vocabularies.query_local_graph(IRI, query)
        disjoint_classes = []
        for binding in qres.get("results").values():
            for result in binding:
                current_class = URIRef(result["disjointClass"]["value"])
                disjoint_classes.append(current_class)
        return disjoint_classes

    def get_triple_map_id(self, triple_map_identifier):
        # returns 'TripleMap1' from <file://Desktop/TripleMap1>
        if "#" in triple_map_identifier:
            return triple_map_identifier.split("#")[-1]
        return triple_map_identifier.split("/")[-1]

    def add_violation(self, metric_result):
        metric_results = [self.violation_counter] + metric_result
        triple_map_identifier = self.current_triple_identifier
        metric_results.append(triple_map_identifier)
        self.violation_counter += 1
        self.add_violation_to_report(metric_results)

    def add_violation_to_report(self, metric_results):
        # adding violation to report using violation ID as key which is mapped to a dictionary with the below keys
        violation_identifier = metric_results[0]
        key_values = ["metric_identifier", "result_message", "value", "location", "triple_map"]
        self.validation_results[violation_identifier] = {key:value for (key, value) in zip(key_values, metric_results[1:len(metric_results)])}

    def find_blank_node_reference(self, violation_location, triple_map_identifier):
        if isinstance(violation_location, BNode):
            current_blank_node_references = self.blank_node_references[triple_map_identifier]
            for (reference_item, bnode) in current_blank_node_references.items():
                if bnode == violation_location:
                    return reference_item
    @staticmethod
    def order_blank_node_identifiers(triple_references):
        # wokring on values such as <DEPT_VIEW>
        for key in triple_references.keys():
            triple_references[key].sort(key=operator.itemgetter(1))

    @staticmethod
    def add_unique_name(triple_references):
        # create a unique name for each blank node
        unique_name_blank_name = {}
        for predicate in triple_references.keys():
            split_predicate = predicate.split("#")[1]
            # iterate current references
            count = 1
            for blank_nodes in triple_references[predicate]:
                unique_name_blank_name[split_predicate + str(count)] = blank_nodes[0]
                count += 1
        return unique_name_blank_name

    def generate_triple_references(self, graph):
        # find the starting triples for the graph which connect to the triple map name
        triple_references = {}
        for (s, p, o) in graph.triples((None, None, None)):
            if isinstance(o, BNode):
                str_p = str(p)
                if str_p in triple_references:
                    triple_references[str_p].append((BNode(o), self.find_identifier(o)))
                else:
                    triple_references[str_p] = [(BNode(o), self.find_identifier(o))]
            elif not isinstance(s, BNode):
                str_p = str(p)
                if str_p in triple_references:
                    triple_references[str_p].append((o, self.find_identifier(o)))
                else:
                    triple_references[str_p] = [(o, self.find_identifier(o))]
        self.order_blank_node_identifiers(triple_references)
        blank_node_references = self.add_unique_name(triple_references)
        return blank_node_references

    def create_validation_report(self, output_file):
        ValidationReport(self.validation_results, output_file, self.file_name, None, None)

    def get_properties_datatype(self):
        # A function to retrieve all properties in the mapping with data types related
        query = """SELECT ?pom ?objectMap ?property ?dataType
                    WHERE {
                      ?subject rr:predicateObjectMap ?pom . 
                      ?pom    rr:predicate ?property .
                      ?pom    rr:objectMap ?objectMap . 
                      ?objectMap rr:datatype ?dataType . 
                    }
               """
        qres = self.current_graph.query(query)
        properties = {}
        counter = 0
        for row in qres:
            # properties.append([row[0], row[1], row[2]])
            properties[counter] = {"predicateObjectMap": row[0], "objectMap": row[1],
                                   "property": row[2],
                                   "datatype": row[3]}
            counter += 1
        return properties

    def get_properties(self):
        self.test_count += 1
        # A function to retrieve all properties in the mapping
        properties = {}
        query = """SELECT ?subject ?property
                    WHERE {
                      ?subject rr:predicate ?property .
                    }
               """
        qres = self.current_graph.query(query)
        counter = 0
        for row in qres:
            # properties.append([row[0], row[1]])
            properties[counter] = {"subject": row[0], "property": row[1]}
            counter += 1
        return properties

    # def validate_D6(self):
    #     # CHECKING THE TYPE OF THE PROPERTY IS ANOTHER OPTION COULD BE SLOWER
    #     metric_identifier = "D6"
    #     result_message = "Usage of incorrect range."
    #     properties = self.get_properties_range()
    #     for key in properties.keys():
    #         property = properties[key]["property"]
    #         if property not in self.undefined_values:
    #             term_type = properties[key]["termType"]
    #             objectMap = properties[key]["objectMap"]
    #             # only retrieve range if term type to speed up execution time
    #             if not term_type:
    #                 term_type = URIRef("http://www.w3.org/ns/r2rml#Literal")
    #             range = self.get_range(property)
    #             if range:
    #                 # if literal range
    #                 if range.startswith("http://www.w3.org/2001/XMLSchema#") or \
    #                         range == URIRef("http://www.w3.org/2000/01/rdf-schema#Literal"):
    #                     correct_term_type = [URIRef("http://www.w3.org/ns/r2rml#Literal")]
    #                 else:
    #                     correct_term_type = [URIRef("http://www.w3.org/ns/r2rml#IRI"), URIRef("http://www.w3.org/ns/r2rml#BlankNode")]
    #                 if term_type not in correct_term_type:
    #                     result_message = "Usage of incorrect range. Term type should be {} for property {}.".format(self.find_prefix(correct_term_type[0]), self.find_prefix(property))
    #                     self.add_violation([metric_identifier, result_message, term_type, properties[key]["objectMap"]])


    def get_properties_range(self):
        # A function to retrieve all properties in the mapping with term types related
        query = """SELECT ?property ?pom ?objectMap ?termType ?dataType ?constant ?object
                    WHERE {
                      ?subject rr:predicateObjectMap ?pom . 
                      ?pom        rr:predicate ?property . 
                      ?pom         rr:objectMap ?objectMap . 
                      OPTIONAL { ?objectMap rr:termType ?termType }. 
                      OPTIONAL { ?objectMap rr:datatype ?dataType }. 
                      OPTIONAL { ?objectMap rr:constant ?constant }. 
                      # OPTIONAL { ?pom rr:object ?object }. 
                    }
               """
        qres = self.current_graph.query(query)
        properties = {}
        counter = 0
        for row in qres:
            # properties.append([row[0], row[1], row[2]])
            properties[counter] = {"property": row["property"], "predicateObjectMap": row["pom"],
                                   "objectMap": row["objectMap"], "termType": row["termType"],
                                   "datatype": row["dataType"], "constant": row["constant"],
                                   "subject": row["pom"]
                                   }
            # if they are using constant shortcut rr:object
            # if row["constant"]:
            #     properties[counter]["constant"] = row["constant"]
            # elif row["object"]:
            #     properties[counter]["constant"] = row["object"]
            counter += 1
        # print(properties)
        # exit()
        return properties

    def is_datatype_range(self, range):
        # if range is datatype such as xsd:date etc
        if range:
            datatype_prefix = "http://www.w3.org/2001/XMLSchema#"
            return range.startswith(datatype_prefix)

    def get_classes(self):
        # A function to retrieve all classes in the mapping
        classes = {}
        query = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                    PREFIX rr: <http://www.w3.org/ns/r2rml#>
                    SELECT ?subject ?class
                    WHERE {
                        {
                          ?tripleMap rr:subjectMap ?sm .
                          ?subject rr:class ?class . 
                        }
                        UNION {
                          ?pom rr:predicate rdf:type ;
                               rr:objectMap ?subject . 
                          ?subject  rr:constant ?class . 
                        }
                        FILTER (isIRI(?class)) .
                    }
               """
        qres = self.current_graph.query(query)
        counter = 0
        for row in qres:
            # class related functions remove whitespace and recreate IRI
            classes[counter] = {"subject": row[0], "class": URIRef("".join(str(row[1]).split()))}
            counter += 1
        return classes


    @staticmethod
    def is_excluded_domain(domains):
        excluded_domains = ["http://www.w3.org/2000/01/rdf-schema#Class",
                            "http://www.w3.org/2000/01/rdf-schema#Resource",
                            "http://www.w3.org/2002/07/owl#Thing"]
        for class_name in domains:
            if class_name in excluded_domains:
                return True
        return False

    def validate_domain(self, property_identifier, subject_identifier, metric_identifier):
        domain = self.get_domain(property_identifier)
        # The hierarchical inference ignores the universal super-concepts, i.e. owl:Thing and rdfs:Resource
        excluded_domain = ValidateQuality.is_excluded_domain(domain)
        if domain and not excluded_domain:
            classes = self.get_classes()
            match_domain = [v["class"] for k,v in classes.items() if str(v["class"]) in domain]
            if not match_domain:
                result_message = "Usage of incorrect domain."
                return [metric_identifier, result_message, property_identifier, subject_identifier]
        else:
            return None

    def get_type(self, IRI):
        # get the type of the specified IRI E.G owl:ObjectProperty or owl:DatatypeProperty
        if isinstance(IRI, URIRef) and IRI not in self.undefined_values:
            query = """
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT ?type
                        WHERE {
                          GRAPH <%s> { <%s> rdf:type ?type . }
                        }   
                   """ % (self.get_namespace(IRI), IRI)
            qres = self.vocabularies.query_local_graph(IRI, query)
            resource_type = []
            if qres["results"]["bindings"]:
                for row in qres["results"]["bindings"]:
                    print(row)
                    resource_type.append(URIRef(row["type"]["value"]))
            return resource_type
        else:
            return []

    def get_range(self, IRI):
        if IRI not in self.range_cache.keys():
            query = """
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                PREFIX dcam: <http://purl.org/dc/dcam/>
                PREFIX schema: <http://schema.org/>
                SELECT ?range
                WHERE {
                GRAPH <%s>
                    { <%s> rdfs:range|dcam:rangeIncludes|schema:rangeIncludes ?range . }
                }
                """ % (self.get_namespace(IRI), IRI)
            qres = self.vocabularies.query_local_graph(IRI, query)
            range = None
            query_bindings = qres["results"]["bindings"]
            # if a range returned
            if query_bindings:
                for row in query_bindings:
                    range = URIRef(row["range"]["value"])
            self.range_cache[IRI] = range
            return range
        else:
            return self.range_cache[IRI]

    def get_domain(self, IRI):
        if IRI not in self.domain_cache.keys():
            query = """PREFIX dcam: <http://purl.org/dc/dcam/> 
                       PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
                       PREFIX schema: <http://schema.org/> 
                       PREFIX prov: <http://www.w3.org/ns/prov#> 
                       PREFIX owl: <http://www.w3.org/2002/07/owl#>
                       PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                       SELECT DISTINCT ?domainClass ?superClass ?superClass2 ?superClass3 ?comment
                       WHERE {
                          GRAPH <%s> {
                            {
                              <%s> rdfs:domain|dcam:domainIncludes|schema:domainIncludes ?domain . 
                              ?domain owl:unionOf ?list .
                              ?list rdf:rest*/rdf:first ?domainClass .
                              OPTIONAL { ?domainClass  rdfs:comment|prov:definition ?comment .} 
                            }
                            UNION 
                            {
                              <%s> rdfs:domain|dcam:domainIncludes|schema:domainIncludes ?domainClass . 
                              OPTIONAL { ?domainClass  rdfs:comment|prov:definition ?comment .} 
                              FILTER (!isBlank(?domainClass))
                            }
                            OPTIONAL { ?superClass rdfs:subClassOf ?domainClass. } 
                            OPTIONAL { ?superClass rdfs:subClassOf ?domainClass.  ?superClass2 rdfs:subClassOf ?superClass . ?superClass3 rdfs:subClassOf ?superClass2 . }
    OPTIONAL { ?superClass rdfs:subClassOf ?domainClass.  ?superClass2 rdfs:subClassOf ?superClass . ?superClass3 rdfs:subClassOf ?superClass2 . ?superClass3 rdfs:subClassOf ?superClass2 }
                          }
                       }   
                       """ % (self.get_namespace(IRI), IRI, IRI)
            qres = self.vocabularies.query_local_graph(IRI, query)
            domain = []
            if qres["results"]["bindings"]:
                for row in qres["results"]["bindings"]:
                    if "domainClass" in row:
                        domain.append(row["domainClass"]["value"])
                        if "superClass" in row:
                            domain.append(row["superClass"]["value"])
                        if "superClass2" in row:
                            domain.append(row["superClass2"]["value"])
                        if "superClass3" in row:
                            domain.append(row["superClass3"]["value"])
                self.domain_cache[IRI] = list(set(domain))
                return domain
            return domain
        else:
            return self.domain_cache[IRI]

    def validate_MP1(self):
        result_message = "An object map with a language tag and datatype."
        metric_identifier = "MP1"
        query = """SELECT ?om ?pm 
               WHERE {
                  ?s rr:predicateObjectMap ?pm .
                  ?pm rr:objectMap ?om .
                  ?om rr:datatype ?value1;
                      rr:language ?value2.
               }
               """
        qres = self.current_graph.query(query)
        for row in qres:
            self.add_violation([metric_identifier, result_message, None, row[0]])

    def validate_MP5(self):
        result_message = "Subject map class must be a valid IRI."
        metric_identifier = "MP5"
        query = """SELECT ?class ?subjectMap
                    WHERE { 
                            ?subject rr:subjectMap ?subjectMap .
                            ?subjectMap rr:class ?class 
                            FILTER(!isIRI(?class))
                    }
                    """
        qres = self.current_graph.query(query)
        for row in qres:
            object_identifier = row[0]
            subject_identifier = row[1]
            self.add_violation([metric_identifier, result_message, object_identifier, subject_identifier])

    def validate_MP6(self):
        result_message = "Language tag not defined in RFC 5646."
        metric_identifier = "MP6"
        language_tags = ('af', 'af-ZA', 'ar', 'ar-AE', 'ar-BH', 'ar-DZ', 'ar-EG', 'ar-IQ', 'ar-JO', 'ar-KW', 'ar-LB', 'ar-LY', 'ar-MA', 'ar-OM', 'ar-QA', 'ar-SA', 'ar-SY', 'ar-TN', 'ar-YE', 'az', 'az-AZ', 'az-Cyrl-AZ', 'be', 'be-BY', 'bg', 'bg-BG', 'bs-BA', 'ca', 'ca-ES', 'cs', 'cs-CZ', 'cy', 'cy-GB', 'da', 'da-DK', 'de', 'de-AT', 'de-CH', 'de-DE', 'de-LI', 'de-LU', 'dv', 'dv-MV', 'el', 'el-GR', 'en', 'en-AU', 'en-BZ', 'en-CA', 'en-CB', 'en-GB', 'en-IE', 'en-JM', 'en-NZ', 'en-PH', 'en-TT', 'en-US', 'en-ZA', 'en-ZW', 'eo', 'es', 'es-AR', 'es-BO', 'es-CL', 'es-CO', 'es-CR', 'es-DO', 'es-EC', 'es-ES', 'es-GT', 'es-HN', 'es-MX', 'es-NI', 'es-PA', 'es-PE', 'es-PR', 'es-PY', 'es-SV', 'es-UY', 'es-VE', 'et', 'et-EE', 'eu', 'eu-ES', 'fa', 'fa-IR', 'fi', 'fi-FI', 'fo', 'fo-FO', 'fr', 'fr-BE', 'fr-CA', 'fr-CH', 'fr-FR', 'fr-LU', 'fr-MC', 'gl', 'gl-ES', 'gu', 'gu-IN', 'he', 'he-IL', 'hi', 'hi-IN', 'hr', 'hr-BA', 'hr-HR', 'hu', 'hu-HU', 'hy', 'hy-AM', 'id', 'id-ID', 'is', 'is-IS', 'it', 'it-CH', 'it-IT', 'ja', 'ja-JP', 'ka', 'ka-GE', 'kk', 'kk-KZ', 'kn', 'kn-IN', 'ko', 'ko-KR', 'kok', 'kok-IN', 'ky', 'ky-KG', 'lt', 'lt-LT', 'lv', 'lv-LV', 'mi', 'mi-NZ', 'mk', 'mk-MK', 'mn', 'mn-MN', 'mr', 'mr-IN', 'ms', 'ms-BN', 'ms-MY', 'mt', 'mt-MT', 'nb', 'nb-NO', 'nl', 'nl-BE', 'nl-NL', 'nn-NO', 'ns', 'ns-ZA', 'pa', 'pa-IN', 'pl', 'pl-PL', 'ps', 'ps-AR', 'pt', 'pt-BR', 'pt-PT', 'qu', 'qu-BO', 'qu-EC', 'qu-PE', 'ro', 'ro-RO', 'ru', 'ru-RU', 'sa', 'sa-IN', 'se', 'se-FI', 'se-NO', 'se-SE', 'sk', 'sk-SK', 'sl', 'sl-SI', 'sq', 'sq-AL', 'sr-BA', 'sr-Cyrl-BA', 'sr-SP', 'sr-Cyrl-SP', 'sv', 'sv-FI', 'sv-SE', 'sw', 'sw-KE', 'syr', 'syr-SY', 'ta', 'ta-IN', 'te', 'te-IN', 'th', 'th-TH', 'tl', 'tl-PH', 'tn', 'tn-ZA', 'tr', 'tr-TR', 'tt', 'tt-RU', 'ts', 'uk', 'uk-UA', 'ur', 'ur-PK', 'uz', 'uz-UZ', 'uz-Cyrl-UZ', 'vi', 'vi-VN', 'xh', 'xh-ZA', 'zh', 'zh-CN', 'zh-HK', 'zh-MO', 'zh-SG', 'zh-TW', 'zu', 'zu-ZA')
        query = """SELECT ?objectMap ?languageTag
                   WHERE {
                        ?subject rr:predicateObjectMap ?pom.
                        ?pom rr:objectMap ?objectMap .  
                        ?objectMap rr:language ?languageTag .
                        FILTER (?languageTag NOT IN  %s) .
                      }
               """ % (language_tags,)
        qres = self.current_graph.query(query)
        for row in qres:
            subject = row[0]
            language_tag = row[1]
            self.add_violation([metric_identifier, result_message, language_tag, subject])

    def validate_MP7(self):
        result_message = "Join condition should have a child column."
        metric_identifier = "MP7"
        query = """
                        SELECT ?joinCondition 
                        WHERE {
                           ?objectMap rr:joinCondition ?joinCondition .
                           FILTER NOT EXISTS {
                             ?joinCondition rr:child ?child . 
                           }
                        }"""
        qres = self.current_graph.query(query)
        for row in qres:
            subject = row[0]
            self.add_violation([metric_identifier, result_message, None, subject])

    def validate_MP8(self):
        result_message = "Join condition should have a parent column."
        metric_identifier = "MP8"
        query = """
                        SELECT ?joinCondition 
                        WHERE {
                           ?objectMap rr:joinCondition ?joinCondition .
                           FILTER NOT EXISTS {
                             ?joinCondition rr:parent ?parent . 
                           }
                        }"""
        qres = self.current_graph.query(query)
        for row in qres:
            subject = row[0]
            self.add_violation([metric_identifier, result_message, None, subject])

    def display_validation_results(self):
        for (violation_identifier, metric_identifier, result_message, value, triple_) in self.validation_results:
            print(violation_identifier, metric_identifier, result_message, value)
            # self.query_validation_results(value)


if __name__ == "__main__":
    t = ValidateQuality("/home/alex/Desktop/Evaluation-1 (Validation Reports)/28 (FAIRVASC-Mapping2)/fairvasc_euvas_test_mapping_v3.ttl")
    print(json.dumps(t.validation_results, indent = 4))
