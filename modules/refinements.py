import difflib
import re
from datetime import datetime
import pandas as pd
import rdflib
from modules.fetch_vocabularies import FetchVocabularies
from modules.validation_report import ValidationReport
from modules.serialize import TurtleSerializer
from rdflib import Graph, URIRef, BNode, Namespace, RDF, RDFS, Literal, OWL, XSD
from rdflib.plugins.sparql import *


class Refinements:

    # add information -> add additional information added by users to validation report
    def __init__(self, validation_results=None, triple_references=None,
                 mapping_graph=None, add_information=None, participant_id=None):
        self.participant_id = participant_id
        self.R2RML = Namespace("http://www.w3.org/ns/r2rml#")
        self.MQV = Namespace("https://w3id.org/MQIO#")
        self.MQV_METRIC = Namespace("https://w3id.org/MQIO-metrics/#")
        self.PROV = Namespace("http://www.w3.org/ns/prov#")
        self.EX = Namespace("http://example.org/")
        self.add_information = add_information
        self.validation_results = validation_results
        self.prefix_file = "prefixes.txt"
        self.prefix_values = self.create_prefix_value_dict(self.prefix_file)
        self.triple_references = triple_references
        self.mapping_graph = mapping_graph
        self.namespaces = {prefix: namespace for (prefix, namespace) in self.mapping_graph.namespaces()}
        self.refinement_count = 0
        self.refinement_graph = Graph()
        self.refinement_graph.bind("prov", Namespace("http://www.w3.org/ns/prov#"))
        # relates to refinements suggested to the users on the dashboard
        self.suggested_refinements = {
            # mapping metric refinements #
            "MP1": ["RemoveLanguageTag", "RemoveDatatype"],
            "MP2": ["ChangeTermType", "RemoveTermType"],
            "MP3": ["ChangeTermType", "RemoveTermType"],
            "MP4": ["ChangeTermType", "RemoveTermType"],
            "MP5": ["ChangeClass"],
            "MP6": ["ChangeLanguageTag", "RemoveLanguageTag"],
            "MP7": ["AddChildColumn"],
            "MP8": ["AddParentColumn"],
            # data metric refinenements
            "D1": ["FindSimilarClasses", "ChangeClass", "RemoveClass"],  # Usage of undefined classes
            "D2": ["FindSimilarPredicates", "ChangePredicate"],  # Usage of undefined properties
            "D3": ["AddDomainClass", "ChangePredicate"],  # Usage of incorrect Domain
            "D4": ["ChangeURI"],  # No query parameters in URI's
            "D5": ["ChangeClass", "RemoveClass"], # No use of entities as members of disjoint classes
            "D6": ["ChangeTermType", "RemoveTermType"], # Usage of incorrect Range
            "D7": ["AddCorrectDatatype", "ChangeDatatype", "RemoveDatatype"],  # Usage of incorrect datatype
        }
        # user_input relates to whether the user is required to input values into the framework
        # requires prefixes relates to whether or not the refinement requires prefixes e.g FOAF, RDF etc, literal values will not
        self.refinement_options = {
            "AddDomainClass": {"user_input": True, "requires_prefixes": False, "restricted_values": self.find_domain,
                               "user_input_values": [self.R2RML + "class"]},

            "ChangeLanguageTag": {"user_input": True, "requires_prefixes": False,
                                  "restricted_values": self.get_language_tags(),
                                  "user_input_values": [self.R2RML + "language"]},

            "AddParentColumn": {"user_input": True, "requires_prefixes": False, "restricted_values": None,
                                "user_input_values": [self.R2RML + "parent"]},

            "AddChildColumn": {"user_input": True, "requires_prefixes": False, "restricted_values": None,
                               "user_input_values": [self.R2RML + "child"]},

            "ChangePredicate": {"user_input": True, "requires_prefixes": True, "restricted_values": None,
                                "user_input_values": [self.R2RML + "predicate"]},

            "FindSimilarPredicates": {"user_input": True, "requires_prefixes": False,
                                      "restricted_values": self.get_vocabulary_properties,
                                      "user_input_values": [self.R2RML + "predicate"]},

            "FindSimilarClasses": {"user_input": True, "requires_prefixes": False,
                                   "restricted_values": self.get_vocabulary_classes,
                                   "user_input_values": [self.R2RML + "class"]},

            "RemoveClass": {"user_input": True, "requires_prefixes": False, "restricted_values": self.get_classes,
                            "user_input_values": [self.R2RML + "class"]},

            "ChangeClass": {"user_input": True, "requires_prefixes": True, "restricted_values": None,
                            "user_input_values": [self.R2RML + "class"]},

            "ChangeConstantValue": {"user_input": True, "requires_prefixes": True, "restricted_values": None,
                                    "user_input_values": [self.R2RML + "class"]},

            "AddCorrectRange": {"user_input": False, "requires_prefixes": False, "restricted_values": None,
                                "user_input_values": self.find_range},

            "RemoveIRI": {"user_input": False, "requires_prefixes": False, "restricted_values": None,
                          "user_input_values": None},

            "ChangeURI": {"user_input": True, "requires_prefixes": True, "restricted_values": None,
                          "user_input_values": ["URI"]},

            "ChangeClassIRI": {"user_input": True, "requires_prefixes": True, "restricted_values": None,
                               "user_input_values": [self.R2RML + "class"]},

            "RemoveLanguageTag": {"user_input": False, "requires_prefixes": False, "restricted_values": None,
                                  "user_input_values": None},

            "RemoveDatatype": {"user_input": False, "requires_prefixes": False, "restricted_values": None,
                               "user_input_values": None},

            "RemoveDuplicateTriples": {"user_input": False, "requires_prefixes": False, "restricted_values": None,
                                       "user_input_values": None},

            "ChangeTermType": {"user_input": True, "requires_prefixes": False,
                               "restricted_values": self.get_correct_term_types,
                               "user_input_values": [self.R2RML + "termType"]},

            "RemoveTermType": {"user_input": False, "requires_prefixes": False, "restricted_values": None,
                               "user_input_values": None},

            "ChangeDatatype": {"user_input": True, "requires_prefixes": True, "restricted_values": None,
                               "user_input_values": [self.R2RML + "datatype"]},

            "AddCorrectDatatype": {"user_input": False, "requires_prefixes": False, "restricted_values": None,
                                   "user_input_values": self.find_range},

        }
        self.refinement_descriptions = self.create_refinement_descriptions()
        self.refinement_functions = {"AddDomainClass": self.add_domain,
                                     "AddCorrectRange": self.add_correct_range,
                                     "RemoveLanguageTag": self.remove_language_tag,
                                     'AddSubjectMap': self.add_subject_map,
                                     'ChangeLanguageTag': self.change_language_tag,
                                     "ChangeClass": self.change_class,
                                     "RemoveDisjointClass": self.remove_class,
                                     "ChangePredicate": self.change_predicate,
                                     "ChangeURI": self.change_IRI,
                                     "ChangeClassIRI": self.change_class_IRI,
                                     "AddParentColumn": self.add_parent_column,
                                     "AddChildColumn": self.add_child_column,
                                     "FindSimilarPredicates": self.change_predicate,
                                     "FindSimilarClasses": self.change_class,
                                     "RemoveIRI": self.remove_IRI,
                                     "RemoveClass": self.remove_class,
                                     #  ("ChangeTermType", "ChangeOMTermType") : self.change_term_type,
                                     "ChangeTermType": self.change_term_type,
                                     "RemoveTermType": self.remove_term_type,
                                     "ChangeDatatype": self.change_datatype,
                                     "AddCorrectDatatype": self.change_datatype,
                                     "RemoveDatatype": self.remove_datatype,
                                     "ChangeConstantValue": self.change_constant_range,
                                     "RemoveDuplicateTriples": self.remove_duplicate_triples,
                                     }

    @staticmethod
    def create_refinement_descriptions():
        refinement_description_file = "Framework metric_refinement HOVER descriptions - Refinement Descriptions.csv"
        df = pd.read_csv(refinement_description_file)
        refinement_descriptions = {}
        for row in df.itertuples():
            refinement_name = row[1]
            refinement_description = row[2]
            refinement_descriptions[refinement_name] = refinement_description.replace("\n", "")
        return refinement_descriptions

    def get_classes(self, violation_ID):
        # get classes from triple map for removing disjoint
        classes = []
        triple_map = self.validation_results[violation_ID]["triple_map"]
        query = """SELECT ?class
                    WHERE {
                      <%s> rr:subjectMap ?subjectMap .
                      ?subjectMap rr:class ?class .
                    }
               """ % (triple_map)
        qres = self.mapping_graph.query(query)
        for row in qres:
            classes.append("%s" % row)
        output = {"Classes": classes}
        return output

    def remove_duplicate_triples(self, query_values, mapping_graph, violation_ID):
        current_result = self.validation_results[violation_ID]
        subject_IRI = current_result["location"]
        mapping_graph.remove((None, None, subject_IRI))
        mapping_graph.remove((subject_IRI, None, None))
        update_query = """
                PREFIX rr: <http://www.w3.org/ns/r2rml#>
                DELETE { ?subject ?p2 ?o1 .
                         ?s1 ?p1 ?subject .
                       }
                WHERE {
                SELECT ?subject ?s1 ?p1 ?o1 ?p2
                WHERE {
                         ?subject ?p2 ?o1 .
                         ?s1 ?p1 ?subject .
                         FILTER(str(?subject) = "%s").
                    }

                }
                """ % subject_IRI
        print("Remove duplicate triple query\n" + update_query)
        return update_query

    def get_correct_term_types(self, violation_ID):
        metric_ID = self.validation_results[violation_ID]["metric_ID"]
        violation_value = self.validation_results[violation_ID]["value"]
        all_term_types = [self.R2RML + "IRI", self.R2RML + "BlankNode", self.R2RML + "Literal"]
        print(violation_value, "VIOLATION VALUE", str(self.R2RML + "Literal") != violation_value)
        # M4 -> objectMap,  M12 -> subjectMap, M15 -> IRI
        correct_term_types = {"MP4": [self.R2RML + "IRI", self.R2RML + "BlankNode", self.R2RML + "Literal"],
                              "MP2": [self.R2RML + "IRI", self.R2RML + "BlankNode"],
                              "MP8": [self.R2RML + "IRI"],
                              "D6": [value for value in all_term_types if value != str(violation_value)]}

        select_placeholder = "Choose a valid term type"
        term_types = correct_term_types[metric_ID]
        print(term_types)
        output = {select_placeholder: term_types}
        return output

    def create_refinement(self, refinement_name, refinement_values, violation_ID):
        user_input_values = refinement_values["user_input_values"]
        user_input = refinement_values["user_input"]
        requires_prefixes = refinement_values["requires_prefixes"]
        restricted_values = refinement_values["restricted_values"]
        optional_values = refinement_values.get("optional_values")
        violation_value = self.get_violation_value(violation_ID)
        if not callable(user_input_values) and not callable(restricted_values):
            refinement = {"name": refinement_name, "user_input": user_input, "requires_prefixes": requires_prefixes,
                          "restricted_values": restricted_values, "values": user_input_values,
                          "optional_values": optional_values}
        elif callable(user_input_values) and callable(restricted_values):
            refinement = {"name": refinement_name, "user_input": user_input, "requires_prefixes": requires_prefixes,
                          "restricted_values": restricted_values(violation_ID),
                          "values": user_input_values(violation_value), "optional_values": optional_values}
        elif callable(user_input_values):
            refinement = {"name": refinement_name, "user_input": user_input, "requires_prefixes": requires_prefixes,
                          "restricted_values": restricted_values, "values": user_input_values(violation_value),
                          "optional_values": optional_values}
        elif callable(restricted_values):
            refinement = {"name": refinement_name, "user_input": user_input, "requires_prefixes": requires_prefixes,
                          "restricted_values": restricted_values(violation_ID), "values": user_input_values,
                          "optional_values": optional_values}
        else:
            refinement = {"name": refinement_name, "user_input": user_input, "requires_prefixes": requires_prefixes,
                          "restricted_values": restricted_values, "values": user_input_values,
                          "optional_values": optional_values}
        return refinement

    def parse_mapping_value(self, mapping_value):
        # for inserting into SPARQL query
        # if string return "" or IRI < > or tuple return first IRI
        if isinstance(mapping_value, URIRef):
            return "<{}>".format(mapping_value)
        elif isinstance(mapping_value, tuple):
            return "<{}>".format(mapping_value[0])
        else:
            return '"{}"'.format(mapping_value)

    def get_language_tags(self):
        # placeholder for the drop down menu as key and then options  as values
        language_tags = ['af', 'af-ZA', 'ar', 'ar-AE', 'ar-BH', 'ar-DZ', 'ar-EG', 'ar-IQ', 'ar-JO', 'ar-KW', 'ar-LB',
                         'ar-LY', 'ar-MA', 'ar-OM', 'ar-QA', 'ar-SA', 'ar-SY', 'ar-TN', 'ar-YE', 'az', 'az-AZ',
                         'az-Cyrl-AZ', 'be', 'be-BY', 'bg', 'bg-BG', 'bs-BA', 'ca', 'ca-ES', 'cs', 'cs-CZ', 'cy',
                         'cy-GB', 'da', 'da-DK', 'de', 'de-AT', 'de-CH', 'de-DE', 'de-LI', 'de-LU', 'dv', 'dv-MV', 'el',
                         'el-GR', 'en', 'en-AU', 'en-BZ', 'en-CA', 'en-CB', 'en-GB', 'en-IE', 'en-JM', 'en-NZ', 'en-PH',
                         'en-TT', 'en-US', 'en-ZA', 'en-ZW', 'eo', 'es', 'es-AR', 'es-BO', 'es-CL', 'es-CO', 'es-CR',
                         'es-DO', 'es-EC', 'es-ES', 'es-GT', 'es-HN', 'es-MX', 'es-NI', 'es-PA', 'es-PE', 'es-PR',
                         'es-PY', 'es-SV', 'es-UY', 'es-VE', 'et', 'et-EE', 'eu', 'eu-ES', 'fa', 'fa-IR', 'fi', 'fi-FI',
                         'fo', 'fo-FO', 'fr', 'fr-BE', 'fr-CA', 'fr-CH', 'fr-FR', 'fr-LU', 'fr-MC', 'gl', 'gl-ES', 'gu',
                         'gu-IN', 'he', 'he-IL', 'hi', 'hi-IN', 'hr', 'hr-BA', 'hr-HR', 'hu', 'hu-HU', 'hy', 'hy-AM',
                         'id', 'id-ID', 'is', 'is-IS', 'it', 'it-CH', 'it-IT', 'ja', 'ja-JP', 'ka', 'ka-GE', 'kk',
                         'kk-KZ', 'kn', 'kn-IN', 'ko', 'ko-KR', 'kok', 'kok-IN', 'ky', 'ky-KG', 'lt', 'lt-LT', 'lv',
                         'lv-LV', 'mi', 'mi-NZ', 'mk', 'mk-MK', 'mn', 'mn-MN', 'mr', 'mr-IN', 'ms', 'ms-BN', 'ms-MY',
                         'mt', 'mt-MT', 'nb', 'nb-NO', 'nl', 'nl-BE', 'nl-NL', 'nn-NO', 'ns', 'ns-ZA', 'pa', 'pa-IN',
                         'pl', 'pl-PL', 'ps', 'ps-AR', 'pt', 'pt-BR', 'pt-PT', 'qu', 'qu-BO', 'qu-EC', 'qu-PE', 'ro',
                         'ro-RO', 'ru', 'ru-RU', 'sa', 'sa-IN', 'se', 'se-FI', 'se-NO', 'se-SE', 'sk', 'sk-SK', 'sl',
                         'sl-SI', 'sq', 'sq-AL', 'sr-BA', 'sr-Cyrl-BA', 'sr-SP', 'sr-Cyrl-SP', 'sv', 'sv-FI', 'sv-SE',
                         'sw', 'sw-KE', 'syr', 'syr-SY', 'ta', 'ta-IN', 'te', 'te-IN', 'th', 'th-TH', 'tl', 'tl-PH',
                         'tn', 'tn-ZA', 'tr', 'tr-TR', 'tt', 'tt-RU', 'ts', 'uk', 'uk-UA', 'ur', 'ur-PK', 'uz', 'uz-UZ',
                         'uz-Cyrl-UZ', 'vi', 'vi-VN', 'xh', 'xh-ZA', 'zh', 'zh-CN', 'zh-HK', 'zh-MO', 'zh-SG', 'zh-TW',
                         'zu', 'zu-ZA']
        select_placeholder = "Choose a valid language tag"
        output = {select_placeholder: language_tags}
        return output

    def get_vocabulary_properties(self, violation_ID):
        # returns similar predicates from the vocabulary which caused the violation
        violation_value = self.validation_results[violation_ID]["value"]
        select_placeholder = "Choose a new predicate"
        # query = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        #             PREFIX owl: <http://www.w3.org/2002/07/owl#>
        #             SELECT ?property
        #             WHERE {
        #               { ?property rdf:type rdf:Property. }
        #               UNION
        #               {  ?property rdf:type owl:ObjectProperty. }
        #               UNION
        #               {  ?property rdf:type owl:DataProperty. }
        #               UNION
        #               {  ?property rdf:type owl:FunctionalProperty. }
        #               UNION
        #               {  ?property rdf:type owl:DatatypeProperty. }
        #             }
        #             """
        query = """PREFIX owl: <http://www.w3.org/2002/07/owl#>
                    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                    PREFIX skos: <http://www.w3.org/2004/02/skos/core#> 
                    SELECT ?property (GROUP_CONCAT(?commentProperty ; separator=' ') AS ?comment) 
                    WHERE {
                      GRAPH <%s> { 
                      ?property a ?type;
                                 rdfs:comment|skos:definition ?commentProperty . 
                      FILTER(?type IN (rdf:Property, owl:ObjectProperty, owl:DataProperty, owl:FunctionalProperty, owl:DatatypeProperty))
                      }
                    }
                    GROUP BY ?property
                    """ % (self.get_namespace(violation_value))
        qres = FetchVocabularies().query_local_graph(violation_value, query)
        predicates = []
        for binding in qres.get("results").values():
            for result in binding:
                current_class = result["property"]["value"]
                current_comment = result["comment"]["value"].split(".")[0] + "."
                predicates.append((current_class, current_comment))
        return {select_placeholder: predicates}

    def order_similar_matches(self, values, violation_value):
        # find predicates with closest match to violation predicate
        closest_matches = difflib.get_close_matches(violation_value, values)
        ordered_predicates = [value for value in values if value not in closest_matches]
        most_similar = closest_matches + ordered_predicates
        return most_similar

    def get_vocabulary_classes(self, violation_ID):
        # returns similar predicates from the vocabulary which caused the violation
        violation_value = self.validation_results[violation_ID]["value"]
        select_placeholder = "Choose a new class"
        query = """ PREFIX owl: <http://www.w3.org/2002/07/owl#>
                    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                    PREFIX skos: <http://www.w3.org/2004/02/skos/core#> 
                    PREFIX prov: <http://www.w3.org/ns/prov#> 
                    SELECT ?classOnto (GROUP_CONCAT(?commentOnto ; separator=' ') AS ?comment) 
                    WHERE {
                      GRAPH <%s> { 
                          ?classOnto a ?type . 
                          OPTIONAL { ?classOnto  rdfs:comment|skos:definition|prov:definition ?commentOnto . } 
                          FILTER(?type IN (owl:Class, rdfs:Class) && !isBlank(?classOnto) )
                      }
                    }
                    GROUP BY ?classOnto
                    """ % (self.get_namespace(violation_value))
        # violation_value = violation_value[:violation_value.rfind("#")+1]
        qres = FetchVocabularies().query_local_graph(violation_value, query)
        classes = []
        for binding in qres.get("results").values():
            for result in binding:
                current_class = result["classOnto"]["value"]
                if "comment" in result:
                    current_comment = result["comment"]["value"].split(".")[0] + "."
                else:
                    current_comment = ""
                classes.append((current_class, current_comment))
        classes = self.order_similar_matches(classes, violation_value)
        return {select_placeholder: classes}

    def find_violation_triple_map_ID(self, violation_ID):
        violation_triple_map = self.validation_results[violation_ID]["triple_map"]
        for key in self.triple_references:
            if violation_triple_map == key.split("/")[-1]:
                return key

    ################################################################################################
    # Refinement functions need the following parameters (query_values, mapping_graph, violation_ID)
    #################################################################################################
    ##### Validation report format
    # {'location': 'ub2bL24C24', 'metric_ID': 'M9', 'result_message': 'Language tag not defined in RFC 5646.',
    #  'triple_map': 'file:///home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/static/uploads/TripleMap1',
    #  'value': 'dhhdhd'

    def find_triple_map(self, violation_ID):
        violation_triple_map = self.validation_results[violation_ID]["triple_map"]
        # find triple map for a violation and return formatted output which is easier to read
        if len(violation_triple_map.split("#")) > 1:
            return violation_triple_map.split("#")[-1]
        elif len(violation_triple_map.split("/")) > 1:
            return violation_triple_map.split("/")[-1]
        return violation_triple_map

    def find_prefix(self, IRI):
        # this is different from validate_quality find_prefix as it requires the graph
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
            return IRI

    def remove_IRI(self, query_values, mapping_graph, violation_ID):
        current_result = self.validation_results[int(violation_ID)]
        subject_IRI = current_result["location"]
        current_value = current_result["value"]
        update_query = """
                PREFIX rr: <http://www.w3.org/ns/r2rml#> 
                DELETE { ?subject rr:class "%s" } 
                WHERE { 
                SELECT ?subject
                WHERE {
                      ?subject rr:class "%s".
                      FILTER(str(?subject) = "%s").
                    }
                }
               """ % (current_value, current_value, subject_IRI)
        print("Remove IRI query\n" + update_query)
        processUpdate(mapping_graph, update_query)
        return update_query

    def change_class_IRI(self, query_values, mapping_graph, violation_ID):
        new_IRI = self.get_user_input(query_values)
        current_result = self.validation_results[violation_ID]
        subject_IRI = current_result["location"]
        old_IRI = self.parse_mapping_value(current_result["value"])
        update_query = """
                PREFIX rr: <http://www.w3.org/ns/r2rml#> 
                DELETE { ?subject rr:class %s }
                INSERT { ?subject rr:class %s }
                WHERE { 
                SELECT ?subject
                WHERE {
                      ?subject rr:class %s .
                      FILTER(str(?subject) = "%s").
                    }
                }
               """ % (old_IRI, new_IRI, old_IRI, subject_IRI)
        # print("Changing IRI query\n" + update_query)
        # exit()
        processUpdate(mapping_graph, update_query)
        return update_query

    def change_constant_range(self, query_values, mapping_graph, violation_ID):
        new_IRI = query_values["IRI"]
        current_result = self.validation_results[violation_ID]
        subject_IRI = current_result["location"]
        old_IRI = current_result["value"]
        update_query = """
                PREFIX rr: <http://www.w3.org/ns/r2rml#>
                DELETE { ?subject rr:class "%s"  }
                INSERT { ?subject rr:class <%s> }
                WHERE {
                SELECT ?subject
                WHERE {
                      ?subject rr:class "%s" .
                      FILTER(str(?subject) = "%s").
                    }
                }
               """ % (old_IRI, new_IRI, old_IRI, subject_IRI)
        print("Changing IRI query\n" + update_query)
        processUpdate(mapping_graph, update_query)
        return update_query

    def change_IRI(self, query_values, mapping_graph, violation_ID):
        print(query_values)
        new_IRI = query_values["URI"]
        current_result = self.validation_results[violation_ID]
        subject_IRI = current_result["location"]
        old_IRI = current_result["value"]
        update_query = """
                PREFIX rr: <http://www.w3.org/ns/r2rml#>
                DELETE { ?subject rr:class <%s>  }
                INSERT { ?subject rr:class <%s> }
                WHERE {
                SELECT ?subject
                WHERE {
                      ?subject rr:class <%s> .
                      FILTER(str(?subject) = "%s").
                    }
                }
               """ % (old_IRI, new_IRI, old_IRI, subject_IRI)
        print("Changing IRI query\n" + update_query)
        processUpdate(mapping_graph, update_query)
        return update_query

    def change_term_type(self, query_values, mapping_graph, violation_ID):
        new_term_type = list(query_values.values())[0]
        current_result = self.validation_results[violation_ID]
        subject_IRI = current_result["location"]
        # delete current term type (if applicable)
        # then insert term type input
        update_query = """
                PREFIX rr: <http://www.w3.org/ns/r2rml#> 
                DELETE { ?subject rr:termType ?currentTermType  } 
                INSERT { ?subject rr:termType <%s> } 
                WHERE { 
                    SELECT ?subject 
                    WHERE {
                          ?subject ?p ?o . 
                          FILTER(str(?subject) = "%s").
                    }
                }; 
               """ % (new_term_type, subject_IRI)
        print("Changing term type query\n" + update_query)
        processUpdate(mapping_graph, update_query)
        return update_query

    def remove_term_type(self, query_values, mapping_graph, violation_ID):
        current_result = self.validation_results[violation_ID]
        subject_IRI = current_result["location"]
        term_type_value = current_result["value"]
        update_query = """
                PREFIX rr: <http://www.w3.org/ns/r2rml#> 
                DELETE { ?subject rr:termType <%s> .  } 
                WHERE { 
                    SELECT ?subject
                    WHERE {
                          ?subject rr:termType <%s> .
                          FILTER(str(?subject) = "%s").
                        }
                }
               """ % (term_type_value, term_type_value, subject_IRI)
        print("Removing term type query\n" + update_query)
        processUpdate(mapping_graph, update_query)
        return update_query

    def remove_datatype(self, query_values, mapping_graph, violation_ID):
        current_result = self.validation_results[violation_ID]
        object_map_IRI = current_result["location"]
        update_query = """
                PREFIX rr: <http://www.w3.org/ns/r2rml#>
                DELETE { ?subject rr:datatype ?datatype .  }
                WHERE {
                SELECT ?subject ?datatype
                WHERE {
                      ?subject rr:datatype ?datatype.
                      FILTER(str(?subject) = "%s").
                    }
                }
               """ % (object_map_IRI)
        print("Removing data type query\n" + update_query)
        processUpdate(mapping_graph, update_query)
        return update_query

    # not remove class IRI as the value is a literal
    def remove_class(self, query_values, mapping_graph, violation_ID):
        current_result = self.validation_results[violation_ID]
        subject_IRI = current_result["location"]
        # this value is most likely a literal
        old_class_value = self.get_user_input(query_values)
        print(old_class_value, "OLD CLASS VALUE")
        print(query_values, "QUERY values")
        update_query = """
                PREFIX rr: <http://www.w3.org/ns/r2rml#> 
                DELETE { ?subject rr:class %s  }
                WHERE { 
                SELECT ?subject
                WHERE {
                      ?subject rr:class %s.
                      FILTER(str(?subject) = "%s").
                    }
                }
               """ % (old_class_value, old_class_value, subject_IRI)
        print("Remove class query\n" + update_query)
        processUpdate(mapping_graph, update_query)
        return update_query

    def change_class(self, query_values, mapping_graph, violation_ID):
        new_class = self.get_user_input(query_values)
        current_result = self.validation_results[violation_ID]
        triple_map = current_result["triple_map"]
        old_class = self.validation_results[violation_ID]["value"]
        old_class = self.parse_mapping_value(current_result["value"])
        update_query = """
            PREFIX rr: <http://www.w3.org/ns/r2rml#> 
            DELETE {
                ?subject rr:class %s . 
            }
            INSERT {
                ?subject rr:class %s
            }
            WHERE {
                <%s> rr:subjectMap ?subject .
            }
            """ % (old_class, new_class, triple_map)
        print("CHANGING CLASS QUERY", update_query)
        print(self.validation_results)
        print(type(current_result["value"]))
        # exit()
        processUpdate(mapping_graph, update_query)
        return update_query

    def change_predicate(self, query_values, mapping_graph, violation_ID):
        new_predicate = self.get_user_input(query_values)
        if new_predicate:
            violation_info = self.validation_results[violation_ID]
            violation_location = violation_info["location"]
            old_predicate = violation_info["value"]
            update_query = """
                PREFIX rr: <http://www.w3.org/ns/r2rml#> 
                DELETE {   ?pom rr:predicate <%s>  .  }
                INSERT {   ?pom rr:predicate %s .     }
                WHERE {
                    ?pom rr:predicate <%s>  .
                    FILTER(str(?pom) = "%s").
                }
                """ % (old_predicate, new_predicate, old_predicate, violation_location)
            print("CHANGING PREDICATE QUERY", query_values)
            print(update_query)
            processUpdate(mapping_graph, update_query)
            return update_query

    def change_language_tag(self, query_values, mapping_graph, violation_ID):
        current_result = self.validation_results[int(violation_ID)]
        pom_IRI = current_result["location"]
        old_language_tag = current_result["value"]
        new_language_tag = list(query_values.values())[0]
        update_query = """
                PREFIX rr: <http://www.w3.org/ns/r2rml#> 
                DELETE { ?objectMap rr:language "%s" } 
                INSERT { ?objectMap rr:language "%s" } 
                WHERE { 
                SELECT ?objectMap
                WHERE {
                      ?objectMap rr:language "%s" .
                      FILTER(str(?objectMap) = "%s").
                    }
                }
               """ % (old_language_tag, new_language_tag, old_language_tag, pom_IRI)
        print("Changing language query\n" + update_query)
        processUpdate(mapping_graph, update_query)
        return update_query

    def change_datatype(self, query_values, mapping_graph, violation_ID):
        correct_datatype = self.get_user_input(query_values)
        current_result = self.validation_results[violation_ID]
        object_map_IRI = current_result["location"]
        old_datatype = current_result["value"]
        update_query = """
                PREFIX rr: <http://www.w3.org/ns/r2rml#>
                DELETE { ?objectMap rr:datatype ?datatype }
                INSERT { ?objectMap rr:datatype %s }
                WHERE {
                    SELECT ?objectMap ?datatype
                    WHERE {
                          ?objectMap rr:datatype ?datatype.
                          FILTER(str(?objectMap) = "%s").
                    }
                }
               """ % (correct_datatype, object_map_IRI)
        print("Changing datatype query\n" + update_query)
        print("OLD DATATYPE", old_datatype)
        processUpdate(mapping_graph, update_query)
        return update_query

    def add_correct_range(self, correct_range, mapping_graph, violation_ID):
        current_result = self.validation_results[int(violation_ID)]
        object_map_IRI = current_result["location"]
        update_query = """
                PREFIX rr: <http://www.w3.org/ns/r2rml#>
                DELETE { ?objectMap rr:constant ?range }
                INSERT { ?objectMap rr:constant <%s> }
                WHERE {
                SELECT ?objectMap ?range
                WHERE {
                      ?objectMap rr:constant ?range.
                      FILTER(str(?objectMap) = "%s").
                    }
                }
               """ % (correct_range, object_map_IRI)
        print("Changing range query\n" + update_query)
        processUpdate(mapping_graph, update_query)
        return update_query

    def add_parent_column(self, query_values, mapping_graph, violation_ID):
        parent_column = list(query_values.values())[0]
        if parent_column:
            current_result = self.validation_results[violation_ID]
            join_IRI = current_result["location"]
            update_query = """
                    PREFIX rr: <http://www.w3.org/ns/r2rml#> 
                    INSERT { ?joinCondition rr:parent "%s" } 
                    WHERE { 
                    SELECT ?joinCondition
                    WHERE {
                          ?subject rr:joinCondition ?joinCondition.
                          FILTER(str(?joinCondition) = "%s").
                        }
                    }
                   """ % (parent_column, join_IRI)
            print("Adding parent column query\n" + update_query)
            processUpdate(mapping_graph, update_query)
            return update_query

    def add_child_column(self, query_values, mapping_graph, violation_ID):
        child_column = list(query_values.values())[0]
        if child_column:
            current_result = self.validation_results[violation_ID]
            join_IRI = current_result["location"]
            update_query = """
                    PREFIX rr: <http://www.w3.org/ns/r2rml#> 
                    INSERT { ?joinCondition rr:child "%s" } 
                    WHERE { 
                    SELECT ?joinCondition
                    WHERE {
                          ?subject rr:joinCondition ?joinCondition.
                          FILTER(str(?joinCondition) = "%s").
                        }
                    }
                   """ % (child_column, join_IRI)
            print("Adding child column query\n" + update_query)
            processUpdate(mapping_graph, update_query)
            return update_query

    def add_subject_map(self, query_values, mapping_graph, violation_ID):
        triple_map_IRI = self.validation_results[violation_ID]["triple_map"]
        subjectBlankNode = BNode("_:b1")
        # generate SPARQL query triples with user input for each property with input
        user_values = "\n\t\t\t".join(
            ["{} <{}> <{}> .".format(subjectBlankNode, p, o) for (p, o) in query_values.items() if o])
        updateQuery = """
                    PREFIX rr: <http://www.w3.org/ns/r2rml#> 
                    INSERT DATA { <%s> rr:subjectMap  %s .
                                   %s 
                    }
                    """ % (triple_map_IRI, subjectBlankNode, user_values)
        print("UPDATE QUERY", updateQuery)
        print(mapping_graph.serialize(format="turtle").decode("utf-8"))
        processUpdate(mapping_graph, updateQuery)
        print(mapping_graph.serialize(format="turtle").decode("utf-8"))
        return updateQuery

    def find_properties(self, IRI):
        # A function to retrieve the domain of an IRI
        domain = []
        query = """SELECT ?subject 
                    WHERE {
                      { ?subject rdfs:domain ?IRI . }
                      UNION
                      { ?subject rdfs:domain <http://www.w3.org/ns/r2rml#TermMap> }
                    }
               """
        query_IRI = URIRef(IRI)
        qres = Graph().parse("http://www.w3.org/ns/r2rml#").query(query, initBindings={'IRI': query_IRI})
        for row in qres:
            domain.append("%s" % row)
        return domain

    def remove_language_tag(self, query_values, mapping_graph, violation_ID):
        current_result = self.validation_results[violation_ID]
        subject_IRI = current_result["location"]
        # this value is most likely a literal
        language_tag = current_result["value"]
        update_query = """
                PREFIX rr: <http://www.w3.org/ns/r2rml#>
                DELETE { ?subject rr:language ?language  }
                WHERE {
                SELECT ?subject  ?language
                WHERE {
                      ?subject rr:language ?language .
                      FILTER(str(?subject) = "%s").
                    }
                }
               """ % subject_IRI
        print("Removing language tag\n" + update_query)
        processUpdate(mapping_graph, update_query)
        print(mapping_graph.serialize(format="turtle").decode("utf-8"))
        return update_query

    def add_domain(self, query_values, mapping_graph, violation_ID):
        domain_IRI = list(query_values.values())[0]
        triple_map_IRI = self.validation_results[violation_ID]["triple_map"]
        print("ADDING DOMAIN" + domain_IRI)
        update_query = """
            INSERT {
                ?subject rr:class <%s> .
            }
            WHERE {
              <%s> rr:subjectMap ?subject
            }
            """ % (domain_IRI, triple_map_IRI)
        print(update_query)
        mapping_graph.update(update_query)
        return update_query

    @staticmethod
    def get_user_input(query_values):
        # parsing user input for refinement SPARQL query
        if isinstance(query_values, URIRef):
            return "<%s>" % query_values
        values = list(query_values.values())[0]
        if values[0] == "<" and values[-1] == ">":
            return values
        elif "<" not in values or ">" not in values:
            return "<%s>" % values
        elif ">" in values and "<" in values:
            values = values.replace("<", "")
            values = values.replace(">", "")
            return "<%s>" % values
        # elif type(violation_value) is tuple:
        #     print("VIOLATION VALUE")
        #     print(violation_value)
        #     print(str(violation_value))
        #     return "<%s>" % violation_value[0]
        else:
            return "<%s>" % values

    def get_violation_value(self, violation_ID):
        violation_value = self.validation_results[violation_ID]["value"]
        return str(violation_value)

    def provide_refinements(self, selected_refinements):
        refinements = {}
        print(selected_refinements, "SELECTED REFINEMETS")
        # Provides values/inputs for the refinements suggested by the user
        for (violation_ID, selected_refinement) in selected_refinements.items():
            # Find which values will be displayed to the user, input boxes or fetched values
            violation_ID = int(violation_ID)
            if selected_refinement != "Manual":
                if selected_refinement in self.refinement_options:
                    refinement_name = selected_refinement
                    refinement_values = self.refinement_options[selected_refinement]
                    refinement = self.create_refinement(refinement_name, refinement_values, violation_ID)
                    refinements[violation_ID] = refinement
                else:
                    refinements[violation_ID] = {"name": selected_refinement, "user_input": False,
                                                 "values": selected_refinement}
        return refinements

    def get_complex_domain(self, IRI, g):
        IRI = URIRef(IRI)
        domain = list(g.objects(IRI, RDFS.domain))[0]
        domain_identifier = list(g.objects(domain, OWL.unionOf))[0]
        domain_values = []
        new_blank_nodes = []
        while True:
            for (s, p, o) in g.triples((domain_identifier, None, None)):
                if p == RDF.first:
                    domain_values.append(o)
                elif p == RDF.rest:
                    new_blank_nodes.append(o)
            if not new_blank_nodes:
                break
            else:
                domain_identifier = new_blank_nodes.pop(0)
        return domain_values

    def get_namespace(self, IRI):
        if "#" in IRI:
            IRI = IRI[:IRI.rfind("#") + 1]
        else:
            IRI = IRI[:IRI.rfind("/") + 1]
        return IRI

    def find_domain(self, IRI):
        property_IRI = self.validation_results[IRI]["value"]
        query = """PREFIX dcam: <http://purl.org/dc/dcam/> 
                   PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
                   PREFIX schema: <http://schema.org/> 
                   PREFIX prov: <http://www.w3.org/ns/prov#> 
                   PREFIX owl: <http://www.w3.org/2002/07/owl#>
                   PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                   SELECT DISTINCT ?domainClass ?comment
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
                      }
                   }   
                   GROUP BY ?domainClass ?comment
                   """% (self.get_namespace(property_IRI), property_IRI, property_IRI)
        qres = FetchVocabularies().query_local_graph(property_IRI, query)
        domain = []
        for row in qres["results"]["bindings"]:
            current_domain = row["domainClass"]["value"]
            if "comment" in row:
                current_comment = row["comment"]["value"].split(".")[0] + "."
            else:
                current_comment = "No description of class in ontology."
            domain.append((current_domain, current_comment))
        output = {"Choose class value: ": domain}
        return output

    def find_range(self, IRI):
        # returns  domain for IRI if applicable
        query = """PREFIX dcam: <http://purl.org/dc/dcam/>
                   PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                   PREFIX schema: <http://schema.org/>  
                   SELECT ?range
                    WHERE {
                      GRAPH <%s> {
                            <%s> rdfs:range|dcam:rangeIncludes|schema:rangeIncludes ?range . 
                      }
                    }   
               """ % (self.get_namespace(IRI), IRI)
        qres = FetchVocabularies().query_local_graph(IRI, query)
        for binding in qres.get("results").values():
            for result in binding:
                correct_range = result["range"]["value"]
                return URIRef(correct_range)


    def create_filename(self, IRI):
        # A function which will create a filename from a URI
        filename = "./modules/cache/" + ''.join(e for e in IRI if e.isalnum()) + ".xml"
        # filename = "./cache/" + ''.join(e for e in IRI if e.isalnum()) + ".xml"
        return filename

    def provide_suggested_refinements(self):
        # Provides a list of suggested refinements which could fix a violation caused by a particular metric
        # Maps the refinement to the violation ID
        # e.g {0: ['RemoveTermType', 'ChangeOMTermType'], 1: ['AddDomainClass']}
        suggested_refinements = {}
        for violation_ID in self.validation_results.keys():
            metric_ID = self.validation_results[violation_ID]["metric_ID"]
            if metric_ID in self.suggested_refinements.keys():
                suggested_refinements[violation_ID] = self.suggested_refinements[metric_ID]
        print(suggested_refinements, "SUGGESTED REFINEEMNTS")
        return suggested_refinements

    def process_user_input(self, refinements_values, refinements, mapping_file, mapping_graph, validation_report_file):
        # iterate each refinement which has been selected to be executed and capture user input
        selected_violation_ID = self.get_selected_refinements(refinements_values)
        refinement_input = {}
        # concatenate the prefix value to the user input
        self.process_prefix_values(refinements_values, mapping_file)
        print(refinements, "early refinement values")
        print(self.process_prefix_values(refinements_values, mapping_file))
        for violation_ID in selected_violation_ID:
            for dic_key in refinements_values.keys():
                # if current key is associated with input
                # e.g '0-http://www.w3.org/ns/r2rml#template' is with violation ID
                print(dic_key, "dic key")
                if self.is_violation_input(dic_key, violation_ID):
                    current_input_value = refinements_values[dic_key].strip()
                    property_name = self.get_property_name(dic_key)
                    # if an input has been associated with the violation
                    if violation_ID in refinement_input.keys():
                        refinement_input[violation_ID][property_name] = current_input_value
                    else:
                        refinement_input[violation_ID] = {property_name: current_input_value}
        print(refinement_input, "refinement input earlier")
        print(refinements, "refinements earlier")
        # refinement input associates each input value with the violation ID it is refining
        self.execute_refinements(selected_violation_ID, refinements, refinement_input, validation_report_file)

    def get_function_name(self, refinement_name):
        # returns the correct function name which relates to the refinement_function dictionary, some values may be tuples
        dic_keys = list(self.refinement_functions)
        if refinement_name in dic_keys:
            return self.refinement_functions[refinement_name]
        # check if tuple contains key
        tuple_check = [key for key in dic_keys if refinement_name in key]
        if tuple_check:
            return self.refinement_functions[tuple(tuple_check[0])]

    def execute_refinements(self, selected_violation_ID, refinements, refinement_input, validation_report_file):
        # refinement graph updates the validation report graph
        self.refinement_graph = self.refinement_graph.parse(validation_report_file, format="ttl")
        # execute each refinement selected to be executed with or without user input
        print("SELECTED REFINEMENTS", selected_violation_ID)
        print(refinements)
        print(type(list(refinements.keys())[0]))
        for violation_ID in selected_violation_ID:
            # html forms store values as strings
            int_violation_ID = int(violation_ID)
            user_input_required = refinements[int_violation_ID]["user_input"]
            print("CHECKING USER INPUT LINE 860")
            print(user_input_required)
            print(refinements)
            refinement_name = refinements[int_violation_ID]["name"]
            print(refinements, "REFINEMENT INPUT")
            if user_input_required:
                function_input = refinement_input[violation_ID]
            else:
                function_input = refinements[int_violation_ID]["values"]
            function_name = self.get_function_name(refinement_name)
            print(function_name)
            refinement_query = function_name(function_input, self.mapping_graph,
                                             int_violation_ID)
            # the function from self.refinement functions is called with the refinement name, user input and the mapping graph
            print(refinement_query)
            #             exit()
            self.add_refinement_information(int_violation_ID, refinement_query, refinement_name)
            self.refinement_count += 1
        self.create_refinement_report(validation_report_file)

    def create_refinement_report(self, validation_report_file):
        self.format_file_name_IRI()
        # self.save_graph_to_file(mapping_graph, "comparison_mapping.ttl")
        # remove full file path from validation report
        # add information is set to true
        # mapping = list(self.refinement_graph.objects(None, self.MQV.assessedMapping))[0]
        # self.refinement_graph.remove((None, RDF.type, self.MQV.MappingDocument))
        # self.refinement_graph.add((mapping, RDF.type, self.MQV.MappingDocument))
        # self.add_metadata(mapping)
        # print(validation_report_file)
        self.refinement_graph.serialize(destination=validation_report_file, format="ttl")
        # __init__(self, mapping_graph, blank_node_references, output_file)
        # uses custom serializer to keep mapping ordering
        TurtleSerializer(self.mapping_graph, self.triple_references, "refined_mapping-{}.ttl".format(self.participant_id))

    def add_metadata(self, mapping):
        # adding metadata about the mapping entered by users
        if self.add_information is not None:
            # mapping = list(self.refinement_graph.objects(None, self.MQV.assessedMapping))[0]
            creator = list(self.refinement_graph.objects(None, self.MQV.createdBy))[0]
            # prov_generated = URIRef("http://www.w3.org/ns/prov#generatedAtTime")
            # prov_generated = self.prov.generatedAtTime
            # generationTime = list(self.refinement_graph.objects(None, prov_generated))[0]
            # self.refinement_graph.remove((None, RDF.type, self.MQV.MappingDocument))
            # self.refinement_graph.add((mapping, RDF.type, self.MQV.MappingDocument))
            self.refinement_graph.remove((None, self.MQV.createdBy, None))
            self.refinement_graph.add((mapping, self.MQV.createdBy, creator))
            # self.refinement_graph.remove((None, prov_generated, None))
            # self.refinement_graph.add((mapping, prov_generated, generationTime))

    def format_file_name_IRI(self):
        # remove local file name from IRI's
        # e.g <file:///home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/
        for (s, p, o) in self.refinement_graph.triples((None, None, None)):
            if str(o).startswith("file"):
                new_object = ValidationReport.format_triple_map_IRI(o)
                self.refinement_graph.remove((s, p, o))
                self.refinement_graph.add((s, p, new_object))

    @staticmethod
    def split_camel_case(word):
        splitted = re.sub('([A-Z][a-z]+)', r' \1', re.sub('([A-Z]+)', r' \1', word)).split()
        result = " ".join(splitted)
        return result

    def add_refinement_information(self, violation_ID, refinement_query, refinement_name):
        # each refinement has a unique IRI and is associated with a refinement query
        refinement_IRI = URIRef(self.EX + "refinement" + "-" + str(self.refinement_count))
        self.refinement_graph.add((refinement_IRI, RDF.type, self.MQV.MappingRefinement))
        self.refinement_graph.add((refinement_IRI, self.PROV.endedAtTime, Literal(datetime.utcnow(), datatype=XSD.dateTime)))
        # adding the SPARQL query used for the refinement
        refinement_query = Literal(refinement_query, datatype=XSD.string)
        self.refinement_graph.add((refinement_IRI, self.MQV.hasRefinementQuery, refinement_query))
        # adding the refinement name e.g FindSimilarClasses
        refinement_name = Literal(self.split_camel_case(refinement_name), datatype=XSD.string)
        self.refinement_graph.add(
            (refinement_IRI, self.MQV.refinementName, refinement_name))
        # adding the wasRefinedBy property related to the previously defined refinement
        violation_IRI = URIRef(self.EX + "violation" + "-" + str(violation_ID))
        self.refinement_graph.add((violation_IRI, self.MQV.wasRefinedBy, refinement_IRI))
        # add inverse property for mqv:refinedViolation, relating this refinement to the violation
        self.refinement_graph.add((refinement_IRI, self.MQV.refinedViolation, violation_IRI))

    def process_prefix_values(self, user_input, mapping_file):
        # a function to concatenate the prefix with the user input value provided
        # e.g prefix selected is FOAF and input value is Person = FOAF Person
        for form_id in list(user_input.keys()):
            current_input = user_input[form_id]
            # if current form value is associated with a prefix
            if self.is_prefix_value(form_id):
                current_form_id = self.is_prefix_value(form_id)
                if self.has_prefix_value(current_form_id, user_input):
                    self.add_prefix_value(current_form_id, user_input, mapping_file)
                del user_input[form_id]

    def add_prefix_value(self, form_id, user_input, mapping_file):
        # will concatenate the prefix value to the user input
        prefix = user_input[form_id]
        # if prefix value present
        if prefix:
            # matching_form_id 0-PREFIX-http://www.w3.org/ns/r2rml#column -> 0-http://www.w3.org/ns/r2rml#column
            matching_form_id = "-".join(form_id.split("-")[0:3:2])
            # concatenate the prefix to the user value
            user_input[matching_form_id] = self.get_prefix_value(prefix) + user_input[matching_form_id]
            # bind prefix namesapce to graph
            self.bind_prefix_namespace(prefix, self.get_prefix_value(prefix))

    def bind_prefix_namespace(self, prefix, prefix_value):
        # remove last character which is ':' to prevent adding foaf:: instead of foaf:
        prefix = prefix[:-1]
        prefix_NS = Namespace(prefix_value)
        self.mapping_graph.bind(prefix, prefix_NS)

    def get_prefix_value(self, prefix):
        # retrieve the IRI for a prefix e.g FOAF -> http://xmlns.com/foaf/0.1/
        if prefix in self.prefix_values:
            return self.prefix_values[prefix]

    def has_prefix_value(self, form_id, user_input):
        # '0-PREFIX-http://www.w3.org/ns/r2rml#class': 'None'
        # if the prefix value is not set to None
        prefix_value = user_input[form_id]
        if prefix_value != "None":
            return True
        return False

    def is_prefix_value(self, form_id):
        # if the input is a prefix e.g '0-PREFIX-http://www.w3.org/ns/r2rml#class'
        split_value = form_id.split("-")
        if len(split_value) == 3 and split_value[1] == "PREFIX":
            return form_id

    def create_prefix_value_dict(self, file_name):
        # take a file name containing prefix, prefix values and store in a dictionary
        # prefix set to None is default for no prefix
        prefix_values = {"None": None}
        with open(file_name) as f:
            for line in f:
                line_values = line.split()
                prefix = line_values[1]
                prefix_value = line_values[2]
                new_prefix_value = self.remove_angle_brackets(prefix_value)
                prefix_values[prefix] = new_prefix_value
        # sort prefix values alphabetically
        dict_keys = list(prefix_values.keys())
        dict_keys.sort()
        sorted_prefix_values = {i: prefix_values[i] for i in dict_keys}
        return sorted_prefix_values

    def remove_angle_brackets(self, value):
        # removes angle brackets from a string e.g <http://pgxo.loria.fr/> -> http://pgxo.loria.fr/
        return value.split("<")[1].split(">")[0]

    @staticmethod
    def save_graph_to_file(graph, file_name):
        graph.serialize(destination=file_name, format="ttl")

    @staticmethod
    def get_selected_refinements(refinement_values):
        # return the violation IDs which have been selected to be executed
        selected_violation_ID = []
        for (violation_ID, value) in refinement_values.items():
            if value == "Execute":
                selected_violation_ID.append(violation_ID)
        # sort list as refinements have ordering
        selected_violation_ID.sort()
        return selected_violation_ID

    def get_property_name(self, input_value):
        # '0-http://www.w3.org/ns/r2rml#template' returns http://www.w3.org/ns/r2rml#template
        return input_value.split("-")[1]

    def is_violation_input(self, dic_key, violation_ID):
        # violation ID = 0 and dic_key '0-http://www.w3.org/ns/r2rml#template', this means the input is associated
        if len(dic_key.split("-")) == 1:
            return False
        elif dic_key.split("-")[0] == violation_ID:
            return True
        return False

    @staticmethod
    def reformat_user_input(user_input, violation_ID):
        # 'input_values' is the user input values associated with 'violation_ID'
        input_values = {}
        for (key, value) in user_input.items():
            # group each input based on violation ID
            current_violation_ID = key.split("-")[0]
            property_name = key.split("-")[1]
            if current_violation_ID == violation_ID:
                # each value is associated with the property outlined in the form and strip whitespace
                input_values[property_name] = value.strip()
        return input_values


if __name__ == "__main__":
    # r = Refinements([[0, 'D6', 'Usage of incorrect domain.', rdflib.term.URIRef('http://dbpedia.org/ontology/equipment'), 3, rdflib.term.BNode('ub6bL29C32')], [1, 'D6', 'Usage of incorrect domain.', rdflib.term.URIRef('http://xmlns.com/foaf/0.1/age'), 2, rdflib.term.BNode('ub6bL22C32')], [2, 'D6', 'Usage of incorrect domain.', rdflib.term.URIRef('http://xmlns.com/foaf/0.1/publications'), 1, rdflib.term.BNode('ub6bL15C32')], [3, 'M1', 'An object map with a language tag and datatype.', rdflib.term.BNode('ub6bL15C48'), 1, rdflib.term.BNode('ub6bL15C32')]])
    # l = r.find_properties("http://www.w3.org/ns/r2rml#subjectMap")
    validation_result = {
        0: {'metric_ID': 'M3', 'result_message': 'Exactly one subject map should be present.', 'value': None,
            'location': None, 'triple_map': 'TripleMap1'},
        1: {'metric_ID': 'D6', 'result_message': 'Usage of incorrect domain.',
            'value': rdflib.term.URIRef('http://xmlns.com/foaf/0.1/age'), 'location': 'predicateObjectMap2',
            'triple_map': 'TripleMap1'}, 2: {'metric_ID': 'D6', 'result_message': 'Usage of incorrect domain.',
                                             'value': rdflib.term.URIRef('http://dbpedia.org/ontology/equipment'),
                                             'location': 'predicateObjectMap3', 'triple_map': 'TripleMap1'},
        3: {'metric_ID': 'D6', 'result_message': 'Usage of incorrect domain.',
            'value': rdflib.term.URIRef('http://xmlns.com/foaf/0.1/publications'), 'location': 'predicateObjectMap1',
            'triple_map': 'TripleMap1'},
        4: {'metric_ID': 'M9', 'result_message': 'Language tag not defined in RFC 5646.',
            'value': rdflib.term.Literal('dhhdhd'), 'location': 'objectMap3', 'triple_map': 'TripleMap1'},
        5: {'metric_ID': 'M3', 'result_message': 'Exactly one subject map should be present.', 'value': None,
            'location': None, 'triple_map': 'TripleMap2'},
        6: {'metric_ID': 'D6', 'result_message': 'Usage of incorrect domain.',
            'value': rdflib.term.URIRef('http://xmlns.com/foaf/0.1/publications'), 'location': 'predicateObjectMap1',
            'triple_map': 'TripleMap2'}}
    triple_maps = [(
                   'file:///home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/static/uploads/TripleMap1',
                   "TripleMap1"), (
                   'file:///home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/static/uploads/TripleMap2',
                   "TripleMap2")]
    r = Refinements(validation_result, {
        'file:///home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/static/uploads/TripleMap1': {
            'predicateObjectMap1': BNode('ub2bL17C27')}}, triple_maps)
    print(r.find_violation_triple_map_ID(2))
