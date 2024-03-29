import rdflib
import operator
import re
import pandas as pd
import json
import multiprocessing
from modules.validation_report import ValidationReport
from modules.fetch_vocabularies import FetchVocabularies
from modules.parse_mapping_graph import ParseMapping


# SPARQL query abbreviations
# om - object map
# pm - predicate object map
# sm - subject map


class ValidateQuality:

    def __init__(self, file_name):
        self.R2RML = rdflib.Namespace("http://www.w3.org/ns/r2rml#")
        self.file_name = file_name
        self.parsed_mapping = ParseMapping(file_name)
        self.triple_maps = self.parsed_mapping.triple_map_graphs
        self.mapping_graph = self.parsed_mapping.mapping_graph
        self.triple_references = self.create_triple_references()
        self.namespaces = {prefix: namespace for (prefix, namespace) in self.mapping_graph.namespaces()}
        self.vocabularies = FetchVocabularies(file_name)
        # mainly used for vocabulary metrics
        self.excluded_namespaces = ["http://ontology.openfit.org#",
                                    "http://recipes.workingclass.org#",
                                    "http://ontology.foodlog.eu#",
                                    "http://ontology.recipepicker.eu#",
                                    "http://www.foodreport.be/ontology#",
                                    "http://data.virtualworkout.com/",
                                    "http://openfridge.eu/ontology#",
                                    "http://www.semanticweb.org/FlavourTown#",
                                    "http://ontology.smartfitgym.eu#",
                                    "http://ontology.wearehungry.be#",
                                    ]
        self.unique_namespaces = list(set([namespace for namespace in self.vocabularies.get_unique_namespaces() if
                                           namespace not in self.excluded_namespaces]))
        self.violation_counter = 0
        self.manager = multiprocessing.Manager()
        self.validation_results = {}  # Shared Proxy to a list
        self.validation_results = self.manager.Queue()
        self.undefined_values = []
        self.undefined_namespaces = set()
        # store the range and domain in cache to speed execution
        # self.data_quality_results = self.manager.Queue()
        # self.mapping_quality_results = self.manager.Queue()
        # self.vocabulary_quality_results = self.manager.Queue()
        self.range_cache = {}
        self.domain_cache = {}
        self.refinements = []
        self.current_graph = None
        self.classes = None
        self.distinct_properties = None
        self.properties = None
        self.current_triple_identifier = None
        self.detailed_metric_information = {
            # Data quality aspect metrics
            "D1": "https://www.w3.org/TR/dwbp/#AccessRealTime",
            "D2": "https://www.w3.org/TR/dwbp/#AccessRealTime",
            "D3": "https://www.w3.org/TR/rdf-schema/#ch_domain",
            "D4": "https://www.w3.org/TR/dwbp/#AccessRealTime",
            "D5": "https://www.w3.org/TR/2004/REC-owl-guide-20040210/#DisjointClasses",
            "D6": "https://www.w3.org/TR/rdf-schema/#ch_range",
            "D7": "https://www.w3.org/TR/rdf-schema/#ch_datatype",
            # Mapping quality aspect metrics
            "MP1": "https://www.w3.org/TR/r2rml/#dfn-triples-map",
            "MP2": "https://www.w3.org/TR/r2rml/#dfn-triples-map",
            "MP3": "https://www.w3.org/TR/r2rml/#dfn-triples-map",
            "MP4": "https://www.w3.org/TR/r2rml/#dfn-triples-map",
            "MP5": "https://www.w3.org/TR/r2rml/#dfn-triples-map",
            "MP6": "https://www.w3.org/TR/r2rml/#dfn-triples-map",
            "MP7": "https://www.w3.org/TR/r2rml/#dfn-triples-map",
            "MP8": "https://www.w3.org/TR/r2rml/#typing",
            "MP9": "https://tools.ietf.org/html/rfc5646",
            "MP10": "https://www.w3.org/TR/r2rml/#foreign-key",
            "MP11": "https://www.w3.org/TR/r2rml/#typing",
            "MP12": "https://tools.ietf.org/html/rfc5646",
            # Vocabulary quality aspect metrics
            "VOC1": "https://www.w3.org/TR/dwbp/#ProvideMetadata",
            "VOC2": "https://www.w3.org/TR/rdf-schema/#ch_domain",
            "VOC3": "https://www.w3.org/TR/rdf-schema/#ch_domain",
            "VOC4": "https://wiki.creativecommons.org/wiki/License_RDF",
            "VOC5": "https://wiki.creativecommons.org/wiki/License_RDF",
        }
        self.metric_descriptions = self.create_metric_descriptions()
        self.validate_triple_maps()
        self.manager = None

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

    def find_prefix(self, identifier):
        # find prefix with longest matching prefix
        if identifier:
            match = []
            # create dictionary with prefix as key and namespace as value
            for (prefix, namespace) in self.namespaces.items():
                if namespace in identifier:
                    match.append(namespace)
            # if matching namespace, return the longest
            if match:
                match_namespace = max(match)
                prefix = [prefix for (prefix, namespace) in self.namespaces.items() if namespace == match_namespace][0]
                identifier = identifier.replace(match_namespace, prefix + ":")
                return " %s " % identifier
            elif type(identifier) is tuple:
                result = "".join(([self.find_prefix(current_identifier) for current_identifier in identifier]))
                return result
            return identifier

    def validate_triple_maps(self):
        # pr3 = multiprocessing.Process(target=self.validate_vocabulary_metrics)
        # processes = [multiprocessing.Process(target=self.validate_mapping_metrics)]
        # processes[0].start()
        processes = [multiprocessing.Process(target=self.validate_vocabulary_metrics)]
        processes[0].start()
        for (triple_map_identifier, graph) in self.triple_maps:
            # self.blank_node_references[triple_map_identifier] = self.generate_triple_references(graph)
            self.current_graph = graph
            self.current_triple_identifier = triple_map_identifier
            self.properties = self.get_properties_range()
            self.classes = self.get_classes()
            self.distinct_properties = self.get_distinct_properties()
            pr2 = multiprocessing.Process(target=self.validate_term_map_metrics)
            pr1 = multiprocessing.Process(target=self.validate_data_metrics)
            pr1.start()
            pr2.start()
            processes.append(pr1)
            processes.append(pr2)
        print("exit loop")
        self.current_triple_identifier = None
        for job in processes:
            job.join()
        print("jobs joined...")
        self.manager = None
        self.validation_results = self.convert_results_queue()
        return self.validation_results

    def convert_results_queue(self):
        # A function to convert threading queue into dictionary for easier processing
        validation_results = []
        while not self.validation_results.empty():
            item = self.validation_results.get()
            validation_results.append(item)
        validation_results = {i: dict(validation_results[i]) for i in range(0, len(validation_results))}
        return validation_results

    def validate_data_metrics(self):
        self.validate_D1()
        self.validate_D2()
        self.validate_D3()
        self.validate_D4()
        self.validate_D5()
        self.validate_D6()
        self.validate_D7()
        self.validate_VOC1()
        self.validate_VOC2()

    def validate_term_map_metrics(self):
        self.validate_MP1()
        self.validate_MP2()
        self.validate_MP3()
        self.validate_MP4()
        self.validate_MP5()
        self.validate_MP6()
        self.validate_MP7()
        self.validate_MP8()
        self.validate_MP9()
        self.validate_MP10()
        self.validate_MP11()
        self.validate_MP12()

    def validate_vocabulary_metrics(self):
        self.validate_VOC3()
        self.validate_VOC4()
        self.validate_VOC5()

    def validate_D1(self):
        # A function to validate the usage of undefined classes
        metric_identifier = "D1"
        for key in list(self.classes):
            class_identifier = self.classes[key].get("class")
            subject_identifier = self.classes[key].get("subject")
            metric_result = self.validate_undefined(class_identifier, subject_identifier, "class", metric_identifier)
            print(class_identifier)
            if metric_result:
                del self.classes[key]
                self.add_violation(metric_result)

    def validate_D2(self):
        # A function to validate the usage of undefined properties
        metric_identifier = "D2"
        for key in list(self.properties):
            property_identifier = self.properties[key].get("property")
            subject_identifier = self.properties[key].get("subject")
            metric_result = self.validate_undefined(property_identifier, subject_identifier, "property", metric_identifier)
            if metric_result:
                # remove if undefined
                del self.properties[key]
                self.add_violation(metric_result)

    def validate_undefined(self, property_identifier, subject_identifier, value_type, metric_identifier):
        result_message = "Usage of undefined %s." % value_type
        property_namespace = self.vocabularies.get_identifier_namespace(property_identifier)
        query = """
            ASK 
            WHERE { 
                {
                   GRAPH ?g { 
                        <%s> ?predicate ?object . 
                     } 
                }
             #   UNION 
            #    {
             #      GRAPH <%s> {
             #           ?subject ?predicate ?object
            #            FILTER(STRAFTER(STR(?subject), "#") = "%s")
             #       }
            #    }
            }
        """ % (property_identifier, property_namespace, property_identifier.split("#")[-1])
        print(query)
        query_results = self.vocabularies.query_local_graph(property_identifier, query)
        is_defined_concept = query_results.get("boolean")
        if is_defined_concept is False:
            query = "ASK { GRAPH <%s> { ?subject ?predicate ?object . } }" % property_namespace
            query_results = self.vocabularies.query_local_graph(property_identifier, query)
            graph_exists = query_results.get("boolean")
            if graph_exists is True:
                return [metric_identifier, result_message, property_identifier, subject_identifier]
            else:
                self.undefined_namespaces.add(property_namespace)
                return False

    def validate_D3(self):
        # A function to validate the usage of correct domain definitions
        metric_identifier = "D3"
        for key in list(self.properties):
            property_identifier = self.properties[key].get("property")
            subject_identifier = self.properties[key].get("subject")
            metric_result = self.validate_domain(property_identifier, subject_identifier, metric_identifier)
            if metric_result:
                self.add_violation(metric_result)

    def validate_domain(self, property_identifier, subject_identifier, metric_identifier):
        domain = self.get_domain(property_identifier)
        # The hierarchical inference ignores the universal super-concepts, i.e. owl:Thing and rdfs:Resource
        if domain:
            classes = self.get_classes()
            super_classes = []
            excluded_domain = ValidateQuality.is_excluded_domain(classes, domain)
            if not excluded_domain:
                for k, v in classes.items():
                    identifier = str(v["class"])
                    query = """
                    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                    SELECT ?superClass
                                WHERE {
                                  GRAPH <%s> {   ?superClass rdfs:subClassOf <%s> .  }
                                }   
                           """ % (self.vocabularies.get_identifier_namespace(identifier), identifier)
                    query_results = self.vocabularies.query_local_graph(identifier, query)
                    if query_results.get("results").get("bindings"):
                        for result in query_results.get("results").get("bindings"):
                            super_classes.append(result.get("superClass").get("value"))
                for class_identifier in super_classes:
                    if class_identifier in domain:
                        return
                match_domain = [v["class"] for k, v in classes.items() if str(v["class"]) in domain]
                if not match_domain:
                    result_message = "Usage of incorrect domain."
                    return [metric_identifier, result_message, property_identifier, subject_identifier]
        else:
            return None

    def validate_D4(self):
        # A function to validate the presence of query parameters in URIs
        result_message = "Query parameters in URI."
        metric_identifier = "D4"
        query = """SELECT ?object ?subject
                    WHERE {
                      ?subject ?predicate ?object
                      FILTER(isIRI(?object) && CONTAINS(STR(?object), "?"))
                    }   
               """
        query_results = self.current_graph.query(query)
        for row in query_results:
            object_identifier = row.get("object")
            subject_identifier = row.get("subject")
            self.add_violation([metric_identifier, result_message, object_identifier, subject_identifier])

    def validate_D5(self):
        # A function to validate the usage of disjoint classes
        classes_and_subjects = self.get_classes()
        # a list of only class IRIs
        classes = [values["class"] for values in classes_and_subjects.values()]
        metric_identifier = "D5"
        # more than one class is needed to be disjoint
        if len(classes) > 1:
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
                            self.add_violation([metric_identifier, result_message, (current_identifier, class_identifier),
                                                subject_identifier])
                            classes.remove(class_identifier)
                            classes.remove(current_identifier)

    def validate_D6(self):
        # A function to validate the usage of correct range
        metric_identifier = "D6"
        for key in list(self.properties):
            property = self.properties[key].get("property")
            term_type = self.properties[key].get("termType")
            objectMap = self.properties[key].get("objectMap")
            if term_type:
                resource_type = self.get_type(property)
                if (rdflib.OWL.DatatypeProperty in resource_type) and (term_type != self.R2RML.Literal):
                    result_message = "Usage of incorrect range. Term type should be 'rr:Literal' for property '{}'.".format(
                        self.find_prefix(property).strip())
                    self.add_violation([metric_identifier, result_message, term_type, objectMap])
                elif (rdflib.OWL.ObjectProperty in resource_type or rdflib.RDF.Property in resource_type) and (term_type == self.R2RML.Literal):
                    range = self.get_range(property)
                    if range:
                        range = range.strip()
                        if range != str(rdflib.RDFS.Literal) and not range.startswith(str(rdflib.XSD)):
                            result_message = "Usage of incorrect range. Term type should be 'rr:IRI' or 'rr:BlankNode' for property '{}'.".format(
                                self.find_prefix(property).strip())
                            self.add_violation([metric_identifier, result_message, term_type, objectMap])

    @staticmethod
    def validate_sub_type(datatype, range):
        sub_types = [rdflib.XSD.long, rdflib.XSD.nonNegativeInteger, rdflib.XSD.nonPositiveInteger, rdflib.XSD.integer,]
        if range in sub_types and datatype in sub_types:
            return True
        return False

    def validate_D7(self):
        # A function to validate the usage of correct datatype
        metric_identifier = "D7"
        result_message = "Usage of incorrect datatype."
        # xsd:anySimpleType, xsd:anyType could be declared as datatypes in the vocabulary
        excluded_datatypes = [rdflib.XSD.anyType, rdflib.XSD.anySimpleType]
        # only if datatype
        for key in list(self.properties):
            property = self.properties[key]["property"]
            object_map_identifier = self.properties[key]["objectMap"]
            datatype = self.properties[key]["datatype"]
            # if a datatype assigned to object map
            if datatype:
                range = self.get_range(property)
                if range != rdflib.XSD.anyURI:
                    # if any of the datatypes can be any datatype, skip this iteration
                    if datatype in excluded_datatypes:
                        continue
                    if ValidateQuality.is_datatype_range(range):
                        # non positive integer
                        sub_type = ValidateQuality.validate_sub_type(datatype, range)
                        if not sub_type:
                            if datatype != range:
                                self.add_violation([metric_identifier, result_message, property, object_map_identifier])

    def validate_MP1(self):
        result_message = "No logical table in this triple map."
        metric_identifier = "MP1"
        query = """
                PREFIX rr: <http://www.w3.org/ns/r2rml#>
                PREFIX rml: <http://semweb.mmlab.be/ns/rml#>
                SELECT DISTINCT ?tripleMap 
                WHERE {
                  ?tripleMap  rr:predicateObjectMap|rr:subjectMap ?object .
                  FILTER NOT EXISTS { ?tripleMap  rr:logicalTable|rml:logicalSource ?logicalSource . }    
                } 
        """
        query_results = self.current_graph.query(query)
        for row in query_results:
            triple_map = row.get("tripleMap")
            self.add_violation([metric_identifier, result_message, None, triple_map])

    def validate_MP2(self):
        result_message = "No subjectMap defined in this triple map."
        metric_identifier = "MP2"
        query = """PREFIX rr: <http://www.w3.org/ns/r2rml#>
                    PREFIX rml: <http://semweb.mmlab.be/ns/rml#>
                    SELECT DISTINCT ?tripleMap 
                    WHERE {
                      ?tripleMap rr:logicalTable|rml:logicalSource|rr:predicateObjectMap ?object .
                      FILTER NOT EXISTS { ?tripleMap rr:subjectMap ?sm . }    
                    } 
                """
        query_results = self.current_graph.query(query)
        for row in query_results:
            triple_map = row.get("tripleMap")
            self.add_violation([metric_identifier, result_message, None, triple_map])

    def validate_MP3(self):
        result_message = "Invalid predicateObjectMap definition."
        metric_identifier = "MP3"
        query = """
            PREFIX rr: <http://www.w3.org/ns/r2rml#>
            SELECT ?pom
            WHERE {
              OPTIONAL { ?tripleMap rr:predicateObjectMap ?pom . ?pom rr:predicateMap|rr:predicate ?predicate . }
              OPTIONAL { ?tripleMap rr:predicateObjectMap ?pom . ?pom rr:objectMap|rr:object ?om . }
              FILTER(!BOUND(?predicate) || !BOUND(?om))
            }
        """
        query_results = self.current_graph.query(query)
        for row in query_results:
            if row:
                subject_identifier = row.get("pom")
                self.add_violation([metric_identifier, result_message, None, subject_identifier])

    def validate_MP4(self):
        result_message = "Join condition should have a parent and child column."
        metric_identifier = "MP4"
        query = """
                 PREFIX rr: <http://www.w3.org/ns/r2rml#>
                 SELECT ?joinCondition 
                 WHERE {
                    ?objectMap rr:joinCondition ?joinCondition .
                    FILTER NOT EXISTS {
                      ?joinCondition rr:child ?child . 
                    }
                 }"""
        query_results = self.current_graph.query(query)
        for row in query_results:
            subject = row.get("joinCondition")
            self.add_violation(
                [metric_identifier, result_message, self.R2RML.child, subject])
        query = """
                 PREFIX rr: <http://www.w3.org/ns/r2rml#>
                 SELECT ?joinCondition 
                 WHERE {
                    ?objectMap rr:joinCondition ?joinCondition .
                    FILTER NOT EXISTS {
                      ?joinCondition rr:parent ?parent . 
                    }
                 }"""
        query_results = self.current_graph.query(query)
        for row in query_results:
            subject = row.get("joinCondition")
            self.add_violation(
                [metric_identifier, result_message, self.R2RML.parent, subject])

    def validate_MP5(self):
        result_message = "An object map with a datatype and language tag."
        metric_identifier = "MP5"
        query = """
               PREFIX rr: <http://www.w3.org/ns/r2rml#>
               SELECT ?om ?pm ?languageTag ?datatype
               WHERE {
                  ?s rr:predicateObjectMap ?pm .
                  ?pm rr:objectMap ?om .
                  ?om rr:datatype ?datatype ;
                      rr:language ?languageTag .
               }
               """
        query_results = self.current_graph.query(query)
        for row in query_results:
            subject_identifier = row.get("om")
            language_tag = row.get("languageTag")
            datatype = row.get("datatype")
            self.add_violation([metric_identifier, result_message, (language_tag, datatype), subject_identifier])

    def validate_MP6(self):
        result_message = "Invalid term type definition."
        metric_identifier = "MP6"
        query = """
                    PREFIX rr: <http://www.w3.org/ns/r2rml#>
                    SELECT ?sm ?termType
                    WHERE {
                      ?subject rr:subjectMap ?sm . 
                      ?sm      rr:termType   ?termType . 
                      FILTER(?termType NOT IN (rr:IRI, rr:BlankNode))
                    }
                """
        query_results = self.current_graph.query(query)
        for row in query_results:
            subject = row.get("sm")
            term_type = row.get("termType")
            self.add_violation([metric_identifier, result_message, term_type, subject])
        query = """
                    PREFIX rr: <http://www.w3.org/ns/r2rml#>
                    SELECT ?objectMap ?termType
                    WHERE {
                      ?subject rr:predicateObjectMap ?pom . 
                      ?pom rr:objectMap ?objectMap . 
                      ?objectMap rr:termType ?termType . 
                      FILTER(?termType NOT IN (rr:IRI, rr:BlankNode, rr:Literal))
                    }
                """
        query_results = self.current_graph.query(query)
        for row in query_results:
            subject = row.get("objectMap")
            term_type = row.get("termType")
            self.add_violation([metric_identifier, result_message, term_type, subject])
        query = """PREFIX rr: <http://www.w3.org/ns/r2rml#>
                    SELECT ?predicateMap ?termType
                    WHERE {
                      ?subject rr:predicateObjectMap ?pom .
                      ?pom rr:predicateMap ?predicateMap .
                      ?predicateMap rr:termType ?termType .
                      FILTER(?termType NOT IN (rr:IRI))
                    }
                """
        query_results = self.current_graph.query(query)
        for row in query_results:
            subject = row.get("predicateMap")
            term_type = row.get("termType")
            self.add_violation([metric_identifier, result_message, term_type, subject])

    def validate_MP7(self):
        result_message = "Subject map class must be a valid IRI."
        metric_identifier = "MP7"
        query = """
                     PREFIX rr: <http://www.w3.org/ns/r2rml#>
                     SELECT ?class ?subjectMap
                     WHERE { 
                             ?subject rr:subjectMap ?subjectMap .
                             ?subjectMap rr:class ?class 
                             FILTER(!isIRI(?class))
                     }
                     """
        query_results = self.current_graph.query(query)
        for row in query_results:
            object_identifier = row.get("class")
            subject_identifier = row.get("subjectMap")
            self.add_violation([metric_identifier, result_message, object_identifier, subject_identifier])

    def validate_MP8(self):
        result_message = "Predicate must be a valid IRI."
        metric_identifier = "MP8"
        query = """
                     PREFIX rr: <http://www.w3.org/ns/r2rml#>
                     SELECT ?predicate ?pom
                     WHERE { 
                             ?subject rr:predicateObjectMap ?pom . 
                             ?pom rr:predicate ?predicate . 
                             FILTER(!isIRI(?predicate))
                     }
                     """
        query_results = self.current_graph.query(query)
        for row in query_results:
            object_identifier = row.get("predicate")
            subject_identifier = row.get("pom")
            self.add_violation([metric_identifier, result_message, object_identifier, subject_identifier])

    def validate_MP9(self):
        result_message = "Named graph must be a valid IRI."
        metric_identifier = "MP9"
        query = """
                     PREFIX rr: <http://www.w3.org/ns/r2rml#>
                     SELECT ?graph ?sm
                     WHERE { 
                             ?subject rr:subjectMap ?sm . 
                             ?sm rr:graph ?graph . 
                             FILTER(!isIRI(?graph))
                     }
                     """
        query_results = self.current_graph.query(query)
        for row in query_results:
            object_identifier = row.get("graph")
            subject_identifier = row.get("sm")
            self.add_violation([metric_identifier, result_message, object_identifier, subject_identifier])

    def validate_MP10(self):
        result_message = "Datatype must be a valid IRI."
        metric_identifier = "MP10"
        query = """
                     PREFIX rr: <http://www.w3.org/ns/r2rml#>
                     SELECT ?datatype ?om
                     WHERE { 
                             ?subject rr:predicateObjectMap ?pom .
                             ?pom rr:objectMap ?om . 
                             ?om rr:datatype ?datatype . 
                             FILTER(!isIRI(?datatype))
                     }
                     """
        query_results = self.current_graph.query(query)
        for row in query_results:
            object_identifier = row.get("datatype")
            subject_identifier = row.get("om")
            self.add_violation([metric_identifier, result_message, object_identifier, subject_identifier])

    def validate_MP11(self):
        result_message = "Language tag not defined in RFC 5646."
        metric_identifier = "MP11"
        language_tags = (
            'af', 'af-ZA', 'ar', 'ar-AE', 'ar-BH', 'ar-DZ', 'ar-EG', 'ar-IQ', 'ar-JO', 'ar-KW', 'ar-LB', 'ar-LY',
            'ar-MA',
            'ar-OM', 'ar-QA', 'ar-SA', 'ar-SY', 'ar-TN', 'ar-YE', 'az', 'az-AZ', 'az-Cyrl-AZ', 'be', 'be-BY', 'bg',
            'bg-BG',
            'bs-BA', 'ca', 'ca-ES', 'cs', 'cs-CZ', 'cy', 'cy-GB', 'da', 'da-DK', 'de', 'de-AT', 'de-CH', 'de-DE',
            'de-LI',
            'de-LU', 'dv', 'dv-MV', 'el', 'el-GR', 'en', 'en-AU', 'en-BZ', 'en-CA', 'en-CB', 'en-GB', 'en-IE', 'en-JM',
            'en-NZ', 'en-PH', 'en-TT', 'en-US', 'en-ZA', 'en-ZW', 'eo', 'es', 'es-AR', 'es-BO', 'es-CL', 'es-CO',
            'es-CR',
            'es-DO', 'es-EC', 'es-ES', 'es-GT', 'es-HN', 'es-MX', 'es-NI', 'es-PA', 'es-PE', 'es-PR', 'es-PY', 'es-SV',
            'es-UY', 'es-VE', 'et', 'et-EE', 'eu', 'eu-ES', 'fa', 'fa-IR', 'fi', 'fi-FI', 'fo', 'fo-FO', 'fr', 'fr-BE',
            'fr-CA', 'fr-CH', 'fr-FR', 'fr-LU', 'fr-MC', 'gl', 'gl-ES', 'gu', 'gu-IN', 'he', 'he-IL', 'hi', 'hi-IN',
            'hr',
            'hr-BA', 'hr-HR', 'hu', 'hu-HU', 'hy', 'hy-AM', 'id', 'id-ID', 'is', 'is-IS', 'it', 'it-CH', 'it-IT', 'ja',
            'ja-JP', 'ka', 'ka-GE', 'kk', 'kk-KZ', 'kn', 'kn-IN', 'ko', 'ko-KR', 'kok', 'kok-IN', 'ky', 'ky-KG', 'lt',
            'lt-LT', 'lv', 'lv-LV', 'mi', 'mi-NZ', 'mk', 'mk-MK', 'mn', 'mn-MN', 'mr', 'mr-IN', 'ms', 'ms-BN', 'ms-MY',
            'mt', 'mt-MT', 'nb', 'nb-NO', 'nl', 'nl-BE', 'nl-NL', 'nn-NO', 'ns', 'ns-ZA', 'pa', 'pa-IN', 'pl', 'pl-PL',
            'ps', 'ps-AR', 'pt', 'pt-BR', 'pt-PT', 'qu', 'qu-BO', 'qu-EC', 'qu-PE', 'ro', 'ro-RO', 'ru', 'ru-RU', 'sa',
            'sa-IN', 'se', 'se-FI', 'se-NO', 'se-SE', 'sk', 'sk-SK', 'sl', 'sl-SI', 'sq', 'sq-AL', 'sr-BA',
            'sr-Cyrl-BA',
            'sr-SP', 'sr-Cyrl-SP', 'sv', 'sv-FI', 'sv-SE', 'sw', 'sw-KE', 'syr', 'syr-SY', 'ta', 'ta-IN', 'te', 'te-IN',
            'th', 'th-TH', 'tl', 'tl-PH', 'tn', 'tn-ZA', 'tr', 'tr-TR', 'tt', 'tt-RU', 'ts', 'uk', 'uk-UA', 'ur',
            'ur-PK',
            'uz', 'uz-UZ', 'uz-Cyrl-UZ', 'vi', 'vi-VN', 'xh', 'xh-ZA', 'zh', 'zh-CN', 'zh-HK', 'zh-MO', 'zh-SG',
            'zh-TW',
            'zu', 'zu-ZA'
        )
        language_tags = tuple([tag.lower() for tag in language_tags])
        query = """
                    PREFIX rr: <http://www.w3.org/ns/r2rml#>
                    SELECT ?objectMap ?languageTag
                    WHERE {
                         ?subject rr:predicateObjectMap ?pom.
                         ?pom rr:objectMap ?objectMap .  
                         ?objectMap rr:language ?languageTag .
                         FILTER (LCASE(STR(?languageTag)) NOT IN  %s) .
                       }
                """ % (language_tags,)
        query_results = self.current_graph.query(query)
        for row in query_results:
            object_map = row.get("objectMap")
            language_tag = row.get("languageTag")
            self.add_violation([metric_identifier, result_message, language_tag, object_map])

    def validate_MP12(self):
        result_message = "Duplicate triples defined."
        metric_identifier = "MP12"
        query = """
                    SELECT (COUNT(*) AS ?count)
                    WHERE {
                        ?subject rr:predicateObjectMap ?pom;
                                 rr:predicate  ?predicate .
                        ?pom rr:objectMap ?om .
                        ?om  rr:column ?column .
                    }
                    HAVING (?count > 1)
                     """
        query_results = self.current_graph.query(query)
        for row in query_results:
            object_identifier = row.get("count")
            self.add_violation([metric_identifier, result_message, object_identifier, subject_identifier])

    def validate_VOC1(self):
        # A function to validate no human readable labelling and comments
        result_message = "No Human Readable Labelling and Comments."
        metric_identifier = "VOC1"
        for key, values in self.classes.items():
            class_identifier = values.get("class")
            namespace = self.vocabularies.get_identifier_namespace(class_identifier)
            if namespace not in self.excluded_namespaces:
                human_label_predicates = ["rdfs:label", "dcterms:title", "dcterms:description",
                                          "dcterms:alternative", "skos:altLabel", "skos:prefLabel", "powder-s:text",
                                          "skosxl:altLabel", "skosxl:hiddenLabel", "skosxl:prefLabel",
                                          "skosxl:literalForm", "rdfs:comment",
                                          "schema:description", "schema:description", "foaf:name"]
                query = """
                    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
                    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
                    PREFIX dcterms: <http://purl.org/dc/terms/> 
                    PREFIX ct: <http://data.linkedct.org/resource/linkedct/> 
                    PREFIX skos: <http://www.w3.org/2004/02/skos/core#> 
                    PREFIX skosxl: <http://www.w3.org/2008/05/skos-xl#> 
                    PREFIX schema: <http://schema.org/> 
                    PREFIX powder-s: <http://www.w3.org/2007/05/powder-s#> 
                    ASK { 
                      GRAPH <%s> 
                         { <%s> %s ?label 
                         } 
                    }            
                """ % (namespace, class_identifier, "|".join(human_label_predicates))
                query_results = self.vocabularies.query_local_graph(namespace, query)
                has_label_comment = query_results.get("boolean")
                if has_label_comment is False:
                    query = "ASK { GRAPH <%s> { ?subject ?predicate ?object . } }" % namespace
                    query_results = self.vocabularies.query_local_graph(class_identifier, query)
                    graph_exists = query_results.get("boolean")
                    if graph_exists is True:
                        self.add_violation([metric_identifier, result_message, class_identifier, None])
        for key in list(self.distinct_properties):
            property_identifier = self.distinct_properties[key].get("property")
            namespace = self.vocabularies.get_identifier_namespace(property_identifier)
            if namespace not in self.excluded_namespaces:
                human_label_predicates = ["rdfs:label", "dcterms:title", "dcterms:description",
                                          "dcterms:alternative", "skos:altLabel", "skos:prefLabel", "powder-s:text",
                                          "skosxl:altLabel", "skosxl:hiddenLabel", "skosxl:prefLabel",
                                          "skosxl:literalForm", "rdfs:comment",
                                          "schema:description", "schema:description", "foaf:name"]
                query = """
                    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
                    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
                    PREFIX dcterms: <http://purl.org/dc/terms/> 
                    PREFIX ct: <http://data.linkedct.org/resource/linkedct/> 
                    PREFIX skos: <http://www.w3.org/2004/02/skos/core#> 
                    PREFIX skosxl: <http://www.w3.org/2008/05/skos-xl#> 
                    PREFIX schema: <http://schema.org/> 
                    PREFIX powder-s: <http://www.w3.org/2007/05/powder-s#> 
                    ASK { 
                      GRAPH <%s> 
                         { <%s> %s ?label 
                         } 
                    }            
                """ % (namespace, property_identifier, "|".join(human_label_predicates))
                query_results = self.vocabularies.query_local_graph(namespace, query)
                has_label_comment = query_results.get("boolean")
                if has_label_comment is False:
                    query = "ASK { GRAPH <%s> { <%s> ?predicate ?object . } }" % (namespace, property_identifier)
                    query_results = self.vocabularies.query_local_graph(property_identifier, query)
                    graph_exists = query_results.get("boolean")
                    property_location = self.distinct_properties[key].get("subject")
                    if graph_exists is True:
                        self.add_violation([metric_identifier, result_message, property_identifier, property_location])

    def validate_VOC2(self):
        metric_identifier = "VOC2"
        result_message = "No domain definition or range definition."
        for key in list(self.distinct_properties):
            property_identifier = self.distinct_properties[key].get("property")
            namespace = self.vocabularies.get_identifier_namespace(property_identifier)
            if namespace not in self.excluded_namespaces:
                query = """
                           PREFIX dcam: <http://purl.org/dc/dcam/> 
                           PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
                           PREFIX schema: <http://schema.org/> 
                           PREFIX prov: <http://www.w3.org/ns/prov#> 
                           PREFIX owl: <http://www.w3.org/2002/07/owl#>
                           PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                           ASK
                           WHERE {
                              GRAPH <%s> {
                                {
                                  <%s> rdfs:domain|dcam:domainIncludes|schema:domainIncludes|rdfs:range|dcam:rangeIncludes|schema:rangeIncludes ?object .
                                }
                            }
                          }
                """ % (namespace, property_identifier)
                query_results = self.vocabularies.query_local_graph(namespace, query)
                has_domain_range = query_results.get("boolean")
                if has_domain_range is False:
                    query = """ 
                        PREFIX owl: <http://www.w3.org/2002/07/owl#>
                        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                        ASK { GRAPH <%s> {  <%s> a ?type .  FILTER(?type in ( rdf:Property, owl:ObjectProperty, owl:AnnotationProperty, owl:DataProperty, owl:FunctionalProperty, owl:DatatypeProperty )) }} """ % (
                    self.vocabularies.get_identifier_namespace(property_identifier), property_identifier)
                    query_results = self.vocabularies.query_local_graph(namespace, query)
                    is_property = query_results.get("boolean")
                    property_location = self.distinct_properties[key].get("subject")
                    if is_property:
                        self.add_violation([metric_identifier, result_message, property_identifier, property_location])

    def validate_VOC3(self):
        # A function to validate basic provenance information
        result_message = "No Basic Provenance Information."
        metric_identifier = "VOC3"
        for namespace in self.unique_namespaces:
            provenance_predicates = ["dc:creator", "dc:publisher", "dct:creator", "dct:contributor",
                                     "dcterms:publisher", "dc:title", "dct:description", "dc:description",
                                     "rdfs:comment", "foaf:maker"]
            query = """
                    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
                    PREFIX dc: <http://purl.org/dc/elements/1.1/> 
                    PREFIX owl: <http://www.w3.org/2002/07/owl#>
                    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
                    PREFIX dcterms: <http://purl.org/dc/terms/> 
                    PREFIX dct: <http://purl.org/dc/terms/>
                    ASK 
                    WHERE { 
                        {
                        GRAPH <%s>
                        { ?subject a owl:Ontology;                             
                                   %s  ?label . }   
                      }
                      UNION 
                      {
                        GRAPH <%s>
                        { <%s>  %s ?label . }   
                      
                      }
                    } """ % (namespace, "|".join(provenance_predicates), namespace, namespace, "|".join(provenance_predicates))
            query_results = self.vocabularies.query_local_graph(namespace, query)
            has_license = query_results.get("boolean")
            if not has_license:
                query = "ASK { GRAPH <%s> { ?subject ?predicate ?object . } }" % namespace
                query_results = self.vocabularies.query_local_graph(namespace, query)
                graph_exists = query_results.get("boolean")
                if graph_exists:
                    self.add_violation([metric_identifier, result_message, namespace, None])

    def validate_VOC4(self):
        # A function to validate basic provenance information
        result_message = "No Machine-Readable License."
        metric_identifier = "VOC4"
        for namespace in self.unique_namespaces:
            query = """
            PREFIX dct: <http://purl.org/dc/terms/>
            PREFIX dc: <http://purl.org/dc/elements/1.1/>
            PREFIX xhtml: <http://www.w3.org/1999/xhtml#>
            PREFIX cc: <http://creativecommons.org/ns#>
            PREFIX doap: <http://usefulinc.com/ns/doap#>
            PREFIX schema: <http://schema.org/>
            ASK {
              GRAPH <%s> {
                ?subject dct:license|dct:rights|dc:rights|xhtml:license|cc:license|dc:license|doap:license|schema:license ?object .
               }
            }
            """ % namespace
            query_results = self.vocabularies.query_local_graph(namespace, query)
            has_license = query_results.get("boolean")
            if not has_license:
                query = "ASK { GRAPH <%s> { ?subject ?predicate ?object . } }" % namespace
                query_results = self.vocabularies.query_local_graph(namespace, query)
                graph_exists = query_results.get("boolean")
                if graph_exists:
                    self.add_violation([metric_identifier, result_message, namespace, None])

    def validate_VOC5(self):
        # A function to validate basic provenance information
        result_message = "No Human-Readable License."
        metric_identifier = "VOC5"
        for namespace in self.unique_namespaces:
            query = """
                ASK WHERE {
                  GRAPH <%s> {
                      ?subject ?predicate ?object
                      FILTER(CONTAINS(LCASE(str(?object)), "license")) 
                  }
                }
            """ % namespace
            query_results = self.vocabularies.query_local_graph(namespace, query)
            has_license = query_results.get("boolean")
            if not has_license:
                query = "ASK { GRAPH <%s> { ?subject ?predicate ?object . } }" % namespace
                query_results = self.vocabularies.query_local_graph(namespace, query)
                graph_exists = query_results.get("boolean")
                if graph_exists:
                    self.add_violation([metric_identifier, result_message, namespace, None])

    def get_triple_maps_identifier(self):
        triple_maps = []
        for (s, p, o) in self.mapping_graph.triples((None, None, None)):
            if not isinstance(s, rdflib.term.BNode):
                if s not in triple_maps:
                    triple_maps.append(s)
        return triple_maps

    def assign_triples_to_each_map(self):
        # returns a dic with the triple map as key and the triples within that triple map as values
        triple_maps_identifier = self.get_triple_maps_identifier()
        # iterate each triple map and find triples which have blank nodes
        triple_map_triples = {}
        for IRI in triple_maps_identifier:
            # empty dictionary assign triples to this triple map
            triple_map_triples[IRI] = {}
            for (s, p, o) in self.mapping_graph.triples((IRI, None, None)):
                # if object is blank node such as rr:logicalTable relate that property to the blank node
                if isinstance(o, rdflib.term.BNode):
                    if p in triple_map_triples[IRI].keys():
                        triple_map_triples[IRI][p].append(o)
                    else:
                        triple_map_triples[IRI][p] = [o]
                else:
                    # for values not relating to blank nodes such as #ORGANISATIONOFOFFICE rr:predicate foaf:Agent
                    not_blank_node_key = "not_blank_node"
                    if not_blank_node_key in triple_map_triples[IRI].keys():
                        triple_map_triples[IRI][not_blank_node_key].append((p, o))
                    else:
                        triple_map_triples[IRI][not_blank_node_key] = [(p, o)]
        return triple_map_triples

    @staticmethod
    def find_identifier(node_value):
        regex = re.search('L(.+?)C', node_value)
        if regex:
            match = regex.group(1)
            return int(match)
        return int(0)

    def sort_blank_nodes(self, blank_nodes_values):
        # A function to order the blank nodes for preserving mapping layout
        add_identifier = [(blank_node, self.find_identifier(blank_node)) for blank_node in blank_nodes_values]
        sorted_blank_node = sorted(add_identifier, key=lambda x: x[1])
        remove_identifier = [blank_node for (blank_node, _) in sorted_blank_node]
        return remove_identifier

    def order_triple_maps_triples(self, triple_references):
        # will order triples based on the blank node identifier assigned
        for (triple_map, values) in triple_references.items():
            for (predicate, blank_nodes) in values.items():
                if predicate != "not_blank_node":
                    sorted_blank_nodes = self.sort_blank_nodes(blank_nodes)
                    triple_references[triple_map][rdflib.term.URIRef(predicate)] = sorted_blank_nodes
        return triple_references

    def create_triple_references(self):
        triple_map_triples = self.assign_triples_to_each_map()
        triple_references = self.order_triple_maps_triples(triple_map_triples)
        return triple_references

    def find_violation_location(self, violation_identifier):
        # A function which returns the triple map and the location within it
        for (triple_map, values) in self.triple_references.items():
            for (predicate, blank_nodes_values) in self.triple_references[triple_map].items():
                if violation_identifier in blank_nodes_values:
                    location_num = blank_nodes_values.index(violation_identifier) + 1
                    violation_location = self.format_user_location(predicate, location_num)
                    return violation_location
                elif self.violation_is_object(blank_nodes_values, violation_identifier):
                    blank_node = self.violation_is_object(blank_nodes_values, violation_identifier)
                    location_num = blank_nodes_values.index(blank_node) + 1
                    violation_location = self.format_user_location(predicate, location_num)
                    return violation_location

    def violation_is_object(self, blank_node_values, violation_identifier):
        # since we only store blank nodes for logical table, subjectMap, predicateObjectMap
        # this function can tell if the violation is within these
        for blank_node in blank_node_values:
            for (s, p, o) in self.mapping_graph.triples((blank_node, None, None)):
                if o == violation_identifier:
                    return blank_node
                # if the violation is contained with a join condition for example
                elif isinstance(o, rdflib.term.BNode):
                    for (s, p, o) in self.mapping_graph.triples((o, None, None)):
                        if o == violation_identifier:
                            return blank_node

    def format_user_location(self, predicate, location_num):
        # ( http://www.w3.org/ns/r2rml#predicateObjectMap , 1) -> predicateObjectMap1
        # making it easier for the user to read
        if predicate != self.R2RML.subjectMap:
            location_predicate = ValidateQuality.strip_identifier(predicate)
            location = "%s-%s" % (location_predicate, location_num)
        else:
            location = ValidateQuality.strip_identifier(predicate)
        return location

    @staticmethod
    def strip_identifier(identifier):
        # (http://www.w3.org/ns/r2rml#predicateObjectMap) -> #predicateObjectMap
        if "#" in identifier:
            return identifier.split("#")[-1]
        elif "/" in identifier:
            return identifier.split("/")[-1]
        return identifier

    def find_disjoint_classes(self, identifier):
        # a function which finds the classes disjoint to IRI argument (if any)
        query = """PREFIX owl: <http://www.w3.org/2002/07/owl#>
                   SELECT DISTINCT ?disjointClass
                   WHERE {
                      GRAPH <%s> {
                          <%s> owl:disjointWith ?disjointClass .
                      }
                   }
                """ % (self.vocabularies.get_identifier_namespace(identifier), identifier)
        query_results = self.vocabularies.query_local_graph(identifier, query)
        disjoint_classes = []
        for binding in query_results.get("results").values():
            for result in binding:
                current_class = rdflib.term.URIRef(result["disjointClass"]["value"])
                disjoint_classes.append(current_class)
        return disjoint_classes

    def get_triple_map_id(self, triple_map_identifier):
        # returns 'TripleMap1' from <file://Desktop/TripleMap1>
        if triple_map_identifier:
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
        key_values = ["metric_identifier", "result_message", "value", "location", "triple_map"]
        self.validation_results.put({key: value for (key, value) in zip(key_values, metric_results[1:len(metric_results)])})

    def find_blank_node_reference(self, violation_location, triple_map_identifier):
        if isinstance(violation_location, rdflib.term.BNode):
            current_blank_node_references = self.blank_node_references[triple_map_identifier]
            for (reference_item, bnode) in current_blank_node_references.items():
                if bnode == violation_location:
                    return reference_item

    @staticmethod
    def order_blank_node_identifiers(triple_references):
        # working on values such as <DEPT_VIEW>
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
            if isinstance(o, rdflib.term.BNode):
                str_p = str(p)
                if str_p in triple_references:
                    triple_references[str_p].append((rdflib.term.BNode(o), self.find_identifier(o)))
                else:
                    triple_references[str_p] = [(rdflib.term.BNode(o), self.find_identifier(o))]
            elif not isinstance(s, rdflib.term.BNode):
                str_p = str(p)
                if str_p in triple_references:
                    triple_references[str_p].append((o, self.find_identifier(o)))
                else:
                    triple_references[str_p] = [(o, self.find_identifier(o))]
        self.order_blank_node_identifiers(triple_references)
        blank_node_references = self.add_unique_name(triple_references)
        return blank_node_references

    def create_validation_report(self, output_file):
        ValidationReport(self.validation_results, output_file, self.file_name, None)

    def get_properties_datatype(self):
        # A function to retrieve all properties in the mapping with data types related
        query = """SELECT ?pom ?om ?property ?dataType
                    WHERE {
                      ?subject rr:predicateObjectMap ?pom . 
                      ?pom     rr:predicate ?property .
                      ?pom     rr:objectMap ?om . 
                      ?om      rr:datatype ?dataType . 
                    }
               """
        query_results = self.current_graph.query(query)
        properties = {}
        counter = 0
        for row in query_results:
            properties[counter] = {"predicateObjectMap": row.get("pom"),
                                   "objectMap": row.get("om"),
                                   "property": row.get("property"),
                                   "datatype": row.get("dataType")}
            counter += 1
        return properties

    def get_properties(self):
        # A function to retrieve all properties in the mapping
        properties = {}
        query = """SELECT ?subject ?property
                    WHERE {
                      ?subject rr:predicate ?property .
                    }
               """
        query_results = self.current_graph.query(query)
        counter = 0
        for row in query_results:
            # properties.append([row[0], row[1]])
            properties[counter] = {"subject": row.get("subject"),
                                   "property": row.get("property")}
            counter += 1
        return properties

    def get_distinct_properties(self):
        query = """SELECT DISTINCT ?pom ?property
                    WHERE {
                      ?subject rr:predicateObjectMap ?pom . 
                      ?pom rr:predicate ?property .
                    }
               """
        query_results = self.current_graph.query(query)
        properties = {}
        counter = 0
        for row in query_results:
            properties[counter] = {"property": row.get("property"),
                                   "subject": row.get("pom")
                                   }
            counter += 1
        return properties

    def get_properties_range(self):
        # A function to retrieve all properties in the mapping with term types related
        query = """
           SELECT ?property ?pom ?objectMap ?termType ?dataType ?constant ?column ?hasLiteralType
                    WHERE {
                      ?subject rr:predicateObjectMap ?pom . 
                      ?pom        rr:predicate ?property . 
                      ?pom         rr:objectMap ?objectMap . 
                      OPTIONAL { ?objectMap rr:column ?column }. 
                      OPTIONAL { ?objectMap rr:termType ?termType }. 
                      OPTIONAL { ?objectMap rr:datatype ?dataType }. 
                      OPTIONAL { ?objectMap rr:constant ?constant }. 
                      BIND(BOUND(?column) AS ?hasColumn)
                      BIND(BOUND(?termType) AS ?hasTermType)
                      BIND((?hasColumn && !?hasTermType) AS ?hasLiteralType )

                    }
      
               """
        query_results = self.current_graph.query(query)
        properties = {}
        counter = 0
        for row in query_results:
            if row["hasLiteralType"] and not row["termType"]:
                term_type = self.R2RML.Literal
            else:
                term_type = row["termType"]
            properties[counter] = {
                "property": row["property"],
               "predicateObjectMap": row["pom"],
               "objectMap": row["objectMap"],
               "termType": term_type,
               "datatype": row["dataType"],
               "constant": row["constant"],
               "subject": row["pom"]
             }
            counter += 1
        return properties

    @staticmethod
    def is_datatype_range(range):
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
                          ?tripleMap rr:subjectMap|rr:subject ?subject .
                          ?subject rr:class ?class . 
                        }
                        FILTER (isIRI(?class)) .
                    }
               """
        query_results = self.current_graph.query(query)
        counter = 0
        for row in query_results:
            # class related functions remove whitespace and recreate IRI
            classes[counter] = {"subject": row[0], "class": rdflib.term.URIRef("".join(str(row[1]).split()))}
            counter += 1
        return classes

    @staticmethod
    def is_excluded_domain(classes, domains):
        excluded_domains = [str(rdflib.RDFS.Class), str(rdflib.RDFS.Resource), str(rdflib.OWL.Thing)]
        for class_name in [str(v["class"]) for k, v in classes.items()]:
            if class_name in excluded_domains:
                return True
        for class_name in domains:
            if class_name in excluded_domains:
                return True
        return False

    def get_type(self, identifier):
        # get the type of the specified IRI E.G owl:ObjectProperty or owl:DatatypeProperty
        if isinstance(identifier, rdflib.term.URIRef) and identifier not in self.undefined_values:
            query = """
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT ?type
                        WHERE {
                          GRAPH <%s> { <%s> rdf:type ?type . }
                        }   
                   """ % (self.vocabularies.get_identifier_namespace(identifier), identifier)
            query_results = self.vocabularies.query_local_graph(identifier, query)
            resource_type = []
            if query_results["results"]["bindings"]:
                for row in query_results["results"]["bindings"]:
                    resource_type.append(rdflib.term.URIRef(row["type"]["value"]))
            return resource_type
        else:
            return []

    def get_range(self, identifier):
        if identifier not in self.range_cache.keys():
            # print(self.range_cache, "False Range", identifier, type(identifier))
            query = """
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                PREFIX dcam: <http://purl.org/dc/dcam/>
                PREFIX schema: <http://schema.org/>
                SELECT ?range
                WHERE {
                GRAPH <%s>
                    { <%s> rdfs:range|dcam:rangeIncludes|schema:rangeIncludes ?range . }
                }
                """ % (self.vocabularies.get_identifier_namespace(identifier), identifier)
            query_results = self.vocabularies.query_local_graph(identifier, query)
            range = None
            query_bindings = query_results["results"]["bindings"]
            # if a range returned
            if query_bindings:
                for row in query_bindings:
                    range = rdflib.term.URIRef(row["range"]["value"])
            self.range_cache[identifier] = range
            return range
        else:
            # print(self.range_cache, "True", identifier)
            return self.range_cache[identifier]

    def get_domain(self, identifier):
        if identifier not in self.domain_cache.keys():
            # print(self.range_cache, "False Domain", identifier, type(identifier))
            query = """PREFIX dcam: <http://purl.org/dc/dcam/> 
                       PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
                       PREFIX schema: <http://schema.org/> 
                       PREFIX prov: <http://www.w3.org/ns/prov#> 
                       PREFIX owl: <http://www.w3.org/2002/07/owl#>
                       PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                       SELECT DISTINCT ?domainClass ?subClass ?subClass2 ?subClass3 ?comment
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
                             OPTIONAL {  ?subClass rdfs:subClassOf ?domainClass } 
                             OPTIONAL {  ?subClass rdfs:subClassOf ?domainClass . ?subClass2 rdfs:subClassOf ?subClass } 
                             OPTIONAL {  ?subClass rdfs:subClassOf ?domainClass . ?subClass2 rdfs:subClassOf ?subClass . ?subClass3 rdfs:subClassOf ?subClass2  } 

                          }
                       }   
                       """ % (self.vocabularies.get_identifier_namespace(identifier), identifier, identifier)
            query_results = self.vocabularies.query_local_graph(identifier, query)
            domain = []
            result_bindings = query_results["results"].get("bindings")
            if result_bindings:
                for row in result_bindings:
                    if "domainClass" in row:
                        domain.append(row["domainClass"]["value"])
                        if "subClass" in row:
                            domain.append(row["subClass"]["value"])
                        if "subClass2" in row:
                            domain.append(row["subClass2"]["value"])
                        if "subClass3" in row:
                            domain.append(row["subClass3"]["value"])
                            domain.append("http://www.w3.org/2000/01/rdf-schema#Resource")
                self.domain_cache[identifier] = list(set(domain))
                return domain
            self.domain_cache[identifier] = list(set(domain))
            return domain
        else:
            print("IN CACHE", identifier, self.domain_cache[identifier])
            return self.domain_cache[identifier]

    def display_validation_results(self):
        for (violation_identifier, metric_identifier, result_message, value, triple_) in self.validation_results:
            pass
            # print(violation_identifier, metric_identifier, result_message, value)
            # self.query_validation_results(value)


if __name__ == "__main__":
    quality_assessment  = ValidateQuality("mapping.ttl")
    print(json.dumps(quality_assessment.validation_results, indent=4))
