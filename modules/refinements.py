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
        self.RML = Namespace("http://semweb.mmlab.be/ns/rml#")
        self.MQIO = Namespace("https://w3id.org/MQIO#")
        self.MQIO_METRIC = Namespace("https://w3id.org/MQIO-metrics/#")
        self.PROV = Namespace("http://www.w3.org/ns/prov#")
        self.EX = Namespace("http://example.org/")
        self.add_information = add_information
        self.validation_results = validation_results
        self.prefix_values = {entry.get("prefix"):entry.get("namespace") for entry in pd.read_csv("prefixes.csv").to_dict(orient='records')}
        self.triple_references = triple_references
        self.mapping_graph = mapping_graph
        self.namespaces = {prefix: namespace for (prefix, namespace) in self.mapping_graph.namespaces()}
        self.refinement_count = 0
        self.refinement_graph = rdflib.Graph()
        self.refinement_graph.bind("prov", Namespace("http://www.w3.org/ns/prov#"))
        self.vocabularies = FetchVocabularies()
        # relates to refinements suggested to the users on the dashboard
        self.suggested_refinements = {
            # mapping metric refinements
            "MP1": ["AddLogicalTable", "AddLogicalSource"],
            "MP2": ["AddSubjectMap"],
            "MP3": ["AddPredicate", "AddObjectMap"],
            "MP4": ["AddChildColumn", "AddParentColumn"],
            "MP6": ["ChangeTermType", "RemoveTermType"],
            "MP7": ["RemoveLanguageTag", "RemoveDatatype"],
            "MP8": ["ChangeClass"],
            "MP9": ["ChangeIRI"],
            "MP10": ["ChangeIRI", "RemoveDatatype"],
            "MP11": ["ChangeLanguageTag", "RemoveLanguageTag"],
            "MP12": ["AddSubjectMap"],

            # data metric refinements
            "D1": ["FindSimilarClasses", "ChangeClass", "RemoveClass"],  # Usage of undefined classes
            "D2": ["FindSimilarPredicates", "ChangePredicate"],  # Usage of undefined properties
            "D3": ["AddDomainClass", "ChangePredicate"],  # Usage of incorrect Domain
            "D4": ["ChangeIRI"],  # No query parameters in URI's
            "D5": ["ChangeClass", "RemoveClass"], # No use of entities as members of disjoint classes
            "D6": ["ChangeTermType", "RemoveTermType"], # Usage of incorrect Range
            "D7": ["AddCorrectDatatype", "ChangeDatatype", "RemoveDatatype"],  # Usage of incorrect datatype
        }
        # user_input relates to whether the user is required to input values into the framework
        # requires prefixes relates to whether or not the refinement requires prefixes e.g FOAF, RDF etc, literal values will not
        self.refinement_options = {
            "AddDomainClass": {"user_input": True, "requires_prefixes": False, "restricted_values": self.find_domain,
                               "user_input_values": [self.R2RML + "class"]},

            "AddPredicate": {"user_input": True,
                             "user_input_values": {
                                 "requires_prefixes": [self.R2RML.predicate],
                             },
            },

            "AddObjectMap": {"user_input": True,
                             "user_input_values": {
                                 "no_prefixes": [self.R2RML.column],
                             },
            },

            "ChangeLanguageTag": {"user_input": True, "requires_prefixes": False,
                                  "restricted_values": self.get_language_tags(),
                                  "user_input_values": [self.R2RML.language]},

            "AddParentColumn": {"user_input": True,
                                "user_input_values": {
                                    "no_prefixes": [self.R2RML.parent],
                                }
            },

            "AddChildColumn": {"user_input": True,
                               "user_input_values": {
                                   "no_prefixes": [self.R2RML.child],
                               }
            },

            "AddSubjectMap": {"user_input": True,
                              "user_input_values": {
                                  "requires_prefixes": [self.R2RML + "class"],
                                  "no_prefixes":       [str(self.R2RML.template)],
                             },
            },

            "AddLogicalTable": {"user_input": True,
                                "user_input_values": {
                                    "no_prefixes": [self.R2RML.tableName, self.R2RML.sqlQuery, self.R2RML.sqlVersion],
                                }
            },

            "AddLogicalSource": {"user_input": True,
                                 "user_input_values": {
                                     "no_prefixes": [self.RML.source, ],
                                     "requires_prefixes": [self.RML.referenceFormulation, ],
                                 }
             },

            "ChangePredicate": {"user_input": True,
                                "user_input_values": {
                                    "no_prefixes": [self.R2RML.predicate],
                                }
            },

            "FindSimilarPredicates": {"user_input": True, "requires_prefixes": False,
                                      "restricted_values": self.get_vocabulary_properties,
                                      "user_input_values": [self.R2RML.predicate]},

            "FindSimilarClasses": {"user_input": True, "requires_prefixes": False,
                                   "restricted_values": self.get_vocabulary_classes,
                                   "user_input_values": [self.R2RML + "class"]},

            "RemoveClass": {"user_input": True, "requires_prefixes": False, "restricted_values": self.get_classes,
                            "user_input_values": [self.R2RML + "class"]},

            "ChangeClass": {"user_input": True,
                            "user_input_values": {
                                "requires_prefixes": [self.R2RML + "class"],
                            },
            },

            "RemoveIRI": {"user_input": False, "requires_prefixes": False, "restricted_values": None,
                          "user_input_values": None},

            "ChangeIRI": {"user_input": True,
                          "user_input_values": {
                              "requires_prefixes": ["URI"],
                          }
            },

            "RemoveLanguageTag": {"user_input": False, "requires_prefixes": False, "restricted_values": None,
                                  "user_input_values": None},

            "RemoveDatatype": {"user_input": False, "requires_prefixes": False, "restricted_values": None,
                               "user_input_values": None},

            "ChangeTermType": {"user_input": True, "requires_prefixes": False,
                               "restricted_values": self.get_correct_term_types,
                               "user_input_values": [self.R2RML.termType]},

            "RemoveTermType": {"user_input": False, "requires_prefixes": False, "restricted_values": None,
                               "user_input_values": None},

            "ChangeDatatype": {"user_input": True,
                               "user_input_values": {
                                   "requires_prefixes": [self.R2RML.datatype],
                               }
                               },

            "AddCorrectDatatype": {"user_input": False, "requires_prefixes": False, "restricted_values": None,
                                   "user_input_values": self.find_range},

        }
        self.refinement_descriptions = self.create_refinement_descriptions()
        self.refinement_functions = {"AddDomainClass": self.add_domain,
                                     "AddPredicate": self.add_predicate,
                                     "AddObjectMap": self.add_object_map,
                                     "AddSubjectMap": self.add_subject_map,
                                     "AddLogicalTable": self.add_logical_table,
                                     "AddLogicalSource": self.add_logical_table,
                                     "RemoveLanguageTag": self.remove_language_tag,
                                     'ChangeLanguageTag': self.change_language_tag,
                                     "ChangeClass": self.change_class,
                                     "ChangePredicate": self.change_predicate,
                                     "ChangeIRI": self.change_identifier,
                                     "AddParentColumn": self.add_parent_column,
                                     "AddChildColumn": self.add_child_column,
                                     "FindSimilarPredicates": self.change_predicate,
                                     "FindSimilarClasses": self.change_class,
                                     "RemoveIRI": self.remove_identifier,
                                     "RemoveClass": self.remove_class,
                                     "ChangeTermType": self.change_term_type,
                                     "RemoveTermType": self.remove_term_type,
                                     "ChangeDatatype": self.change_datatype,
                                     "AddCorrectDatatype": self.change_datatype,
                                     "RemoveDatatype": self.remove_datatype,
                                     }


    @staticmethod
    def create_refinement_descriptions():
        refinement_description_file = "refinement_descriptions.csv"
        df = pd.read_csv(refinement_description_file)
        refinement_descriptions = {}
        for row in df.itertuples():
            refinement_name = row[1]
            refinement_description = row[2]
            refinement_descriptions[refinement_name] = refinement_description.replace("\n", "")
        return refinement_descriptions

    def get_classes(self, violation_identifier):
        # get classes from triple map for removing disjoint
        classes = []
        triple_map = self.validation_results[violation_identifier]["triple_map"]
        query = """SELECT ?class
                    WHERE {
                      <%s> rr:subjectMap ?subjectMap .
                      ?subjectMap rr:class ?class .
                    }
               """ % triple_map
        query_results = self.mapping_graph.query(query)
        for row in query_results:
            classes.append("%s" % row)
        output = {"Classes": classes}
        return output

    def get_correct_term_types(self, violation_identifier):
        metric_identifier = self.validation_results[violation_identifier]["metric_identifier"]
        violation_value = self.validation_results[violation_identifier]["value"]
        all_term_types = [self.R2RML + "IRI", self.R2RML + "BlankNode", self.R2RML + "Literal"]
        print(violation_value, "VIOLATION VALUE", str(self.R2RML + "Literal") != violation_value)
        # M4 -> objectMap,  M12 -> subjectMap, M15 -> IRI
        # correct_term_types = {"MP4": [self.R2RML + "IRI", self.R2RML + "BlankNode", self.R2RML + "Literal"],
        #                       "MP2": [self.R2RML + "IRI", self.R2RML + "BlankNode"],
        #                       "MP8": [self.R2RML + "IRI"],
        #                       "D6": [value for value in all_term_types if value != str(violation_value)]}
        correct_term_types = {"MP6": [value for value in all_term_types if value != str(violation_value)],
                              "D6": [value for value in all_term_types if value != str(violation_value)]}
        select_placeholder = "Choose a valid term type"
        term_types = correct_term_types.get(metric_identifier)
        print(term_types)
        output = {select_placeholder: term_types}
        return output

    def create_refinement(self, refinement_name, refinement_values, violation_identifier):
        user_input_values = refinement_values.get("user_input_values")
        user_input = refinement_values.get("user_input")
        requires_prefixes = refinement_values.get("requires_prefixes")
        restricted_values = refinement_values.get("restricted_values")
        optional_values = refinement_values.get("optional_values")
        violation_value = self.get_violation_value(violation_identifier)
        if not callable(user_input_values) and not callable(restricted_values):
            refinement = {"name": refinement_name, "user_input": user_input, "requires_prefixes": requires_prefixes,
                          "restricted_values": restricted_values, "values": user_input_values,
                          "optional_values": optional_values}
        elif callable(user_input_values) and callable(restricted_values):
            refinement = {"name": refinement_name, "user_input": user_input, "requires_prefixes": requires_prefixes,
                          "restricted_values": restricted_values(violation_identifier),
                          "values": user_input_values(violation_value), "optional_values": optional_values}
        elif callable(user_input_values):
            refinement = {"name": refinement_name, "user_input": user_input, "requires_prefixes": requires_prefixes,
                          "restricted_values": restricted_values, "values": user_input_values(violation_value),
                          "optional_values": optional_values}
        elif callable(restricted_values):
            refinement = {"name": refinement_name, "user_input": user_input, "requires_prefixes": requires_prefixes,
                          "restricted_values": restricted_values(violation_identifier), "values": user_input_values,
                          "optional_values": optional_values}
        else:
            refinement = {"name": refinement_name, "user_input": user_input, "requires_prefixes": requires_prefixes,
                          "restricted_values": restricted_values, "values": user_input_values,
                          "optional_values": optional_values}
        return refinement

    def provide_refinements(self, selected_refinements):
        refinements = {}
        print(selected_refinements, "SELECTED REFINEMETS")
        # Provides values/inputs for the refinements suggested by the user
        for (violation_identifier, selected_refinement) in selected_refinements.items():
            # Find which values will be displayed to the user, input boxes or fetched values
            violation_identifier = int(violation_identifier)
            if selected_refinement != "Manual":
                if selected_refinement in self.refinement_options:
                    refinement_name = selected_refinement
                    refinement_values = self.refinement_options[selected_refinement]
                    refinement = self.create_refinement(refinement_name, refinement_values, violation_identifier)
                    refinements[violation_identifier] = refinement
                else:
                    refinements[violation_identifier] = {"name": selected_refinement, "user_input": False,
                                                         "values": selected_refinement}
        return refinements


    @staticmethod
    def get_rdflib_term_value(str):
        try:
            return rdflib.term.URIRef(str)
        except Exception as e:
            return rdflib.term.Literal(str)

    @staticmethod
    def parse_mapping_value(mapping_value):
        # for inserting into SPARQL query
        # if string return "" or IRI < > or tuple return first IRI
        if isinstance(mapping_value, rdflib.term.URIRef):
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

    def get_vocabulary_properties(self, violation_identifier):
        # A function which returns suggested defined properties in an ontology
        violation_value = self.validation_results[violation_identifier].get("value")
        select_placeholder = "Choose a new predicate"
        query = """ PREFIX owl: <http://www.w3.org/2002/07/owl#>
                    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                    PREFIX skos: <http://www.w3.org/2004/02/skos/core#> 
                    PREFIX prov: <http://www.w3.org/ns/prov#>
                    SELECT ?property (GROUP_CONCAT(?commentProperty ; separator=' ') AS ?comment) 
                    WHERE {
                      GRAPH <%s> { 
                      ?property a ?type .
                      OPTIONAL { ?property  rdfs:comment|skos:definition|prov:definition ?commentProperty . } 
                      FILTER(CONTAINS (LCASE(STR(?type)), 'property'))
                      # FILTER(?type IN (rdf:Property, owl:AnnotationProperty, owl:ObjectProperty, owl:DataProperty, owl:FunctionalProperty, owl:DatatypeProperty))
                      }
                    }
                    GROUP BY ?property
                    """ % (self.vocabularies.get_identifier_namespace(violation_value))
        query_results = self.vocabularies.query_local_graph(violation_value, query)
        predicates = []
        for binding in query_results.get("results").values():
            for result in binding:
                current_class = result["property"].get("value")
                if result.get("comment"):
                    current_comment = result["comment"]["value"].split(".")[0] + "."
                else:
                    current_comment = "No description in ontology."
                predicates.append((current_class, current_comment))
        return {select_placeholder: predicates}

    def get_vocabulary_classes(self, violation_identifier):
        # A function which returns suggested defined classes in an ontology
        violation_value = self.validation_results[violation_identifier].get("value")
        select_placeholder = "Choose a new class"
        query = """ 
                    PREFIX owl: <http://www.w3.org/2002/07/owl#>
                    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                    PREFIX skos: <http://www.w3.org/2004/02/skos/core#> 
                    PREFIX prov: <http://www.w3.org/ns/prov#> 
                    SELECT ?classOnto (GROUP_CONCAT(?commentOnto ; separator=' ') AS ?comment) 
                    WHERE {
                      GRAPH <%s> { 
                          ?classOnto a ?type . 
                          OPTIONAL { ?classOnto  rdfs:comment|skos:definition|prov:definition ?commentOnto . } 
                        #  FILTER(?type IN (owl:Class, rdfs:Class) && !isBlank(?classOnto) )
                         FILTER(CONTAINS (LCASE(STR(?type)),'class')  && !isBlank(?classOnto)  )
                         BIND(lang(?commentProperty) AS ?languageTag ) 
                         FILTER (?languageTag = 'en' || !bound(?languageTag))
                      }
                    }
                    GROUP BY ?classOnto
                    """ % (self.vocabularies.get_identifier_namespace(violation_value))
        query_results = self.vocabularies.query_local_graph(violation_value, query)
        classes = []
        result_bindings = query_results.get("results").values()
        for binding in result_bindings:
            for result in binding:
                current_class = result["classOnto"].get("value")
                if "comment" in result:
                    current_comment = result["comment"].get("value").split(".")[0] + "."
                else:
                    current_comment = "No class description in ontology."
                classes.append((current_class, current_comment))
        return {select_placeholder: classes}

    ################################################################################################
    # Refinement functions need the following parameters (query_values, mapping_graph, violation_identifier)
    #################################################################################################
    ##### Validation report format
    # {'location': 'ub2bL24C24', 'metric_identifier': 'M9', 'result_message': 'Language tag not defined in RFC 5646.',
    #  'triple_map': 'file:///home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/static/uploads/TripleMap1',
    #  'value': 'dhhdhd'

    def find_triple_map(self, violation_identifier):
        violation_triple_map = self.validation_results[violation_identifier]["triple_map"]
        # find triple map for a violation and return formatted output which is easier to read
        if len(violation_triple_map.split("#")) > 1:
            return violation_triple_map.split("#")[-1]
        elif len(violation_triple_map.split("/")) > 1:
            return violation_triple_map.split("/")[-1]
        return violation_triple_map

    def find_prefix(self, identifier):
        # this is different from validate_quality find_prefix as it requires the graph
        # find prefix with longest matching prefix
        if identifier:
            match = []
            # create dictionary with prefix as key and namespace as value
            for (prefix, namespace) in self.namespaces.items():
                if namespace in identifier:
                    match.append(namespace)
            # if matching namesapce, return the longest
            if match:
                match_namespace = max(match)
                prefix = [prefix for (prefix, namespace) in self.namespaces.items() if namespace == match_namespace][0]
                identifier = identifier.replace(match_namespace, prefix + ":")
                return " %s " % identifier
            return identifier

    def remove_identifier(self, query_values, mapping_graph, violation_identifier):
        current_result = self.validation_results[int(violation_identifier)]
        subject_identifier = current_result["location"]
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
               """ % (current_value, current_value, subject_identifier)
        print("Remove IRI query\n" + update_query)
        processUpdate(mapping_graph, update_query)
        return update_query

    def change_graph_identifier(self, query_values, mapping_graph, violation_identifier):
        new_identifier = self.get_user_input(query_values)
        current_result = self.validation_results[violation_identifier]
        subject_identifier = current_result.get("location")
        old_identifier = Refinements.parse_mapping_value(current_result.get("value"))
        update_query = """
                PREFIX rr: <http://www.w3.org/ns/r2rml#> 
                DELETE { ?subject rr:graph %s }
                INSERT { ?subject rr:graph %s }
                WHERE { 
                SELECT ?subject
                WHERE {
                      ?subject rr:graph %s .
                      FILTER(str(?subject) = "%s").
                    }
                }
               """ % (old_identifier, new_identifier, old_identifier, subject_identifier)
        # print("Changing IRI query\n" + update_query)
        processUpdate(mapping_graph, update_query)
        return update_query

    def change_class_identifier(self, query_values, mapping_graph, violation_identifier):
        new_identifier = self.get_user_input(query_values)
        current_result = self.validation_results[violation_identifier]
        subject_identifier = current_result.get("location")
        old_identifier = Refinements.parse_mapping_value(current_result["value"])
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
               """ % (old_identifier, new_identifier, old_identifier, subject_identifier)
        processUpdate(mapping_graph, update_query)
        return update_query

    def change_constant_range(self, query_values, mapping_graph, violation_identifier):
        new_identifier = query_values["IRI"]
        current_result = self.validation_results[violation_identifier]
        subject_identifier = current_result.get("location")
        old_identifier = current_result["value"]
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
               """ % (old_identifier, new_identifier, old_identifier, subject_identifier)
        print("Changing IRI query\n" + update_query)
        processUpdate(mapping_graph, update_query)
        return update_query

    def change_identifier(self, query_values, mapping_graph, violation_identifier):
        # new_identifier = query_values["URI"]
        current_result = self.validation_results[violation_identifier]
        subject_identifier = current_result.get("location")
        old_identifier = self.get_user_input(current_result.get("value"))
        new_identifier = self.get_user_input(query_values)
        update_query = """
                PREFIX rr: <http://www.w3.org/ns/r2rml#>
                DELETE { ?subject ?predicate %s  }
                INSERT { ?subject ?predicate %s }
                WHERE {
                SELECT ?subject ?predicate
                WHERE {
                      ?subject ?predicate %s .
                      FILTER(str(?subject) = "%s").
                    }
                }
               """ % (rdflib.term.URIRef(str(old_identifier).replace("\/", "")), new_identifier, old_identifier, subject_identifier)
        print("Changing IRI query\n" + update_query)
        processUpdate(mapping_graph, update_query)
        return update_query

    def change_term_type(self, query_values, mapping_graph, violation_identifier):
        new_term_type = self.get_user_input(query_values)
        current_result = self.validation_results[violation_identifier]
        subject_identifier = current_result.get("location")
        # delete current term type (if applicable) - then inserts input term type
        update_query = """
                PREFIX rr: <http://www.w3.org/ns/r2rml#> 
                DELETE { ?subject rr:termType ?currentTermType  } 
                INSERT { ?subject rr:termType %s } 
                WHERE { 
                    SELECT ?subject ?currentTermType
                    WHERE {
                          ?subject ?p ?o . 
                          OPTIONAL { ?subject rr:termType ?currentTermType }
                          FILTER(str(?subject) = "%s").
                    }
                }
               """ % (new_term_type, subject_identifier)
        print("Changing term type query\n" + update_query)
        processUpdate(mapping_graph, update_query)
        return update_query

    def remove_term_type(self, query_values, mapping_graph, violation_identifier):
        current_result = self.validation_results[violation_identifier]
        subject_identifier = current_result.get("location")
        term_type_value = Refinements.parse_mapping_value(current_result.get("value"))
        update_query = """
                PREFIX rr: <http://www.w3.org/ns/r2rml#> 
                DELETE { ?subject rr:termType %s .  } 
                WHERE { 
                    SELECT ?subject
                    WHERE {
                          ?subject rr:termType %s .
                          FILTER(str(?subject) = "%s").
                        }
                }
               """ % (term_type_value, term_type_value, subject_identifier)
        print("Removing term type query\n" + update_query)
        processUpdate(mapping_graph, update_query)
        return update_query

    def remove_datatype(self, query_values, mapping_graph, violation_identifier):
        current_result = self.validation_results.get(violation_identifier)
        object_map_identifier = current_result.get("location")
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
               """ % (object_map_identifier)
        print("Removing data type query\n" + update_query)
        processUpdate(mapping_graph, update_query)
        return update_query

    # not remove class IRI as the value is a literal
    def remove_class(self, query_values, mapping_graph, violation_identifier):
        current_result = self.validation_results[violation_identifier]
        subject_identifier = current_result.get("location")
        # this value is most likely a literal
        old_class_value = self.get_user_input(query_values)
        if old_class_value:
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
                   """ % (old_class_value, old_class_value, subject_identifier)
            print("Remove class query\n" + update_query)
            processUpdate(mapping_graph, update_query)
            return update_query

    def change_class(self, query_values, mapping_graph, violation_identifier):
        new_class = self.get_user_input(query_values)
        if new_class:
            current_result = self.validation_results[violation_identifier]
            triple_map = current_result.get("triple_map")
            old_class = Refinements.parse_mapping_value(current_result.get("value"))
            update_query = """
                PREFIX rr: <http://www.w3.org/ns/r2rml#> 
                DELETE { ?subject rr:class %s .  }
                INSERT {   ?subject rr:class %s  }
                WHERE {
                    <%s> rr:subjectMap ?subject .
                }
                """ % (old_class, new_class, triple_map)
            processUpdate(mapping_graph, update_query)
            return update_query

    def change_predicate(self, query_values, mapping_graph, violation_identifier):
        new_predicate = self.get_user_input(query_values)
        if new_predicate:
            violation_information = self.validation_results.get(violation_identifier)
            violation_location = violation_information.get("location")
            old_predicate = self.get_user_input(violation_information.get("value"))
            update_query = """
                PREFIX rr: <http://www.w3.org/ns/r2rml#> 
                DELETE {   ?pom rr:predicate %s  .  }
                INSERT {   ?pom rr:predicate %s .     }
                WHERE {
                    ?pom rr:predicate %s  .
                    FILTER(str(?pom) = "%s").
                }
                """ % (old_predicate, new_predicate, old_predicate, violation_location)
            print("CHANGING PREDICATE QUERY", query_values)
            print(update_query)
            processUpdate(mapping_graph, update_query)
            return update_query

    def change_language_tag(self, query_values, mapping_graph, violation_identifier):
        current_result = self.validation_results[int(violation_identifier)]
        pom_identifier = current_result.get("location")
        old_language_tag = Refinements.parse_mapping_value(current_result.get("value"))
        new_language_tag = query_values.get(str(self.R2RML.language))
        update_query = """
                PREFIX rr: <http://www.w3.org/ns/r2rml#> 
                DELETE { ?objectMap rr:language %s } 
                INSERT { ?objectMap rr:language '%s' } 
                WHERE { 
                SELECT ?objectMap
                WHERE {
                      ?objectMap ?p ?o .
                      OPTIONAL { ?objectMap rr:language %s . } 
                      FILTER(str(?objectMap) = "%s").
                    }
                }
               """ % (old_language_tag, new_language_tag, old_language_tag, pom_identifier)
        print("Changing language query\n" + update_query)
        processUpdate(mapping_graph, update_query)
        return update_query

    def change_datatype(self, query_values, mapping_graph, violation_identifier):
        correct_datatype = self.get_user_input(query_values)
        current_result = self.validation_results[violation_identifier]
        object_map_identifier = current_result.get("location")
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
               """ % (correct_datatype, object_map_identifier)
        processUpdate(mapping_graph, update_query)
        return update_query

    def add_correct_range(self, correct_range, mapping_graph, violation_identifier):
        current_result = self.validation_results[int(violation_identifier)]
        object_map_identifier = current_result.get("location")
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
               """ % (correct_range, object_map_identifier)
        print("Changing range query\n" + update_query)
        processUpdate(mapping_graph, update_query)
        return update_query

    def add_parent_column(self, query_values, mapping_graph, violation_identifier):
        parent_column = query_values.get("http://www.w3.org/ns/r2rml#parent")
        if parent_column:
            current_result = self.validation_results[violation_identifier]
            join_identifier = current_result.get("location")
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
                   """ % (parent_column, join_identifier)
            print("Adding parent column query\n" + update_query)
            processUpdate(mapping_graph, update_query)
            return update_query

    def add_subject_map(self, query_values, mapping_graph, violation_identifier):
        violation_information = self.validation_results.get(violation_identifier)
        subject_map_identifier = rdflib.term.BNode()
        template_string = query_values.pop(str(self.R2RML.template))
        triple_map = violation_information.get("triple_map")
        class_identifier = self.get_user_input(query_values).replace("<","").replace(">", "")
        update_query = """
            PREFIX rr: <http://www.w3.org/ns/r2rml#>
            INSERT
            {
              ?tripleMap rr:subjectMap _:%s .
               _:%s rr:class <%s>  ;
                    rr:template '%s' . 
            }
            WHERE {
              ?tripleMap rr:predicateObjectMap ?pom .
              FILTER(str(?tripleMap) = "%s").
            }
        """ % (subject_map_identifier, subject_map_identifier, class_identifier, template_string, triple_map)
        # processUpdate() does not update mapping correctly for this case
        mapping_graph.add((rdflib.term.URIRef(triple_map), self.R2RML.subjectMap, subject_map_identifier))
        mapping_graph.add((subject_map_identifier, rdflib.term.URIRef("http://www.w3.org/ns/r2rml#class"), rdflib.term.URIRef(class_identifier)))
        mapping_graph.add((subject_map_identifier, self.R2RML.template, rdflib.term.Literal(template_string)))
        self.triple_references[URIRef(triple_map)][self.R2RML.subjectMap] = [subject_map_identifier]
        print("yeyeys")
        return update_query

    def add_predicate(self, query_values, mapping_graph, violation_identifier):
        current_result = self.validation_results[violation_identifier]
        violation_location = current_result.get("location")
        predicate_identifier = self.get_user_input(query_values)
        update_query = """
                PREFIX rr: <http://www.w3.org/ns/r2rml#> 
                INSERT { ?pom rr:predicate %s } 
                WHERE { 
                SELECT ?pom
                WHERE {
                      ?subject rr:predicateObjectMap ?pom.
                      FILTER(str(?pom) = "%s").
                    }
                }
               """ % (predicate_identifier, violation_location)
        processUpdate(mapping_graph, update_query)
        return update_query

    def add_object_map(self, query_values, mapping_graph, violation_identifier):
        current_result = self.validation_results[violation_identifier]
        violation_location = current_result.get("location")
        column_string = query_values.get(self.R2RML.column)
        print(column_string)
        exit()
        update_query = """
                PREFIX rr: <http://www.w3.org/ns/r2rml#> 
                INSERT { ?pom rr:predicate %s } 
                WHERE { 
                SELECT ?pom
                WHERE {
                      ?subject rr:predicateObjectMap ?pom.
                      FILTER(str(?pom) = "%s").
                    }
                }
               """ % (predicate_identifier, violation_location)
        processUpdate(mapping_graph, update_query)
        return update_query

    def add_logical_table(self, query_values, mapping_graph, violation_identifier):
        current_result = self.validation_results[violation_identifier]
        violation_information = self.validation_results.get(violation_identifier)
        triple_map = violation_information.get("triple_map")
        if triple_map:
            triple_map_identifier = rdflib.term.URIRef(triple_map)
            logical_table_identifier = rdflib.term.BNode()
            mapping_graph.add((triple_map_identifier, self.R2RML.logicalTable, logical_table_identifier))
            table_name = query_values.pop(str(self.R2RML.tableName))
            sql_query = query_values.pop(str(self.R2RML.sqlQuery))
            sql_version = query_values.pop(str(self.R2RML.sqlVersion))
            # processUpdate() does not update mapping correctly
            if table_name:
                mapping_graph.add((logical_table_identifier, self.R2RML.tableName, rdflib.term.Literal(table_name)))
            if sql_query:
                mapping_graph.add((logical_table_identifier, self.R2RML.sqlQuery, rdflib.term.Literal(sql_query)))
            if sql_version:
                mapping_graph.add((logical_table_identifier, self.R2RML.sqlVersion, rdflib.term.Literal(sql_version)))
            update_query = """
                PREFIX dc: <http://purl.org/dc/elements/1.1/>
                PREFIX rr: <http://www.w3.org/ns/r2rml#>
                INSERT
                {
                  ?tripleMap rr:subjectMap _:%s .
                   _:%s rr:class %s  ;
                        rr:template '%s' . 
                }
                WHERE {
                  ?tripleMap ?predicate ?object .
                  FILTER(str(?tripleMap) = "%s").
                }
            """ % (logical_table_identifier, logical_table_identifier, sql_query, table_name, triple_map_identifier)
            print("Adding logical table query\n" + update_query)
            self.triple_references[triple_map_identifier][self.R2RML.logicalTable] = [logical_table_identifier]
            return update_query

    def add_child_column(self, query_values, mapping_graph, violation_identifier):
        child_column = query_values.get(str(self.R2RML.child))
        if child_column:
            current_result = self.validation_results[violation_identifier]
            join_identifier = current_result.get("location")
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
                   """ % (child_column, join_identifier)
            print("Adding child column query\n" + update_query)
            processUpdate(mapping_graph, update_query)
            return update_query

    def remove_language_tag(self, query_values, mapping_graph, violation_identifier):
        current_result = self.validation_results[violation_identifier]
        subject_identifier = current_result.get("location")
        # this value is most likely a literal
        language_tag = current_result.get("value")
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
               """ % subject_identifier
        print("Removing language tag\n" + update_query)
        processUpdate(mapping_graph, update_query)
        print(mapping_graph.serialize(format="turtle").decode("utf-8"))
        return update_query

    def add_domain(self, query_values, mapping_graph, violation_identifier):
        domain_identifier = list(query_values.values())[0]
        triple_map_identifier = self.validation_results[violation_identifier].get("triple_map")
        print("ADDING DOMAIN" + domain_identifier)
        update_query = """
            INSERT {
                ?subject rr:class <%s> .
            }
            WHERE {
                <%s> rr:subjectMap ?subject
            }
            """ % (domain_identifier, triple_map_identifier)
        print(update_query)
        mapping_graph.update(update_query)
        return update_query

    def get_user_input(self, query_values, property_name=None):
        # parsing user input for refinement SPARQL query
        if isinstance(query_values, rdflib.term.URIRef):
            return "<%s>" % query_values
        # values = list(query_values.values())[0]
        if isinstance(query_values, dict):
            print(query_values, "jdd")
            prefix_namespace = self.get_prefix_value(query_values.get("PREFIX", ""))
            identifier_key = [key for key in query_values.keys() if key != "PREFIX"][0]
            remaining_identifier = query_values.get(identifier_key)
            if remaining_identifier and prefix_namespace:
                full_identifier = prefix_namespace + remaining_identifier
                self.mapping_graph.bind(query_values.get("PREFIX")[:-1], prefix_namespace)
            elif prefix_namespace:
                full_identifier = prefix_namespace
                self.mapping_graph.bind(query_values.get("PREFIX")[:-1], prefix_namespace)
            else:
                full_identifier = remaining_identifier
            return "<%s>" % full_identifier
        else:
            return "'%s'" % query_values

    def get_violation_value(self, violation_identifier):
        violation_value = self.validation_results[violation_identifier]["value"]
        return str(violation_value)

    def find_domain(self, identifier):
        property_identifier = self.validation_results[identifier].get("value")
        query = """
                   PREFIX dcam: <http://purl.org/dc/dcam/> 
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
                   """% (self.vocabularies.get_identifier_namespace(property_identifier), property_identifier, property_identifier)
        query_results = self.vocabularies.query_local_graph(property_identifier, query)
        domain = []
        for row in query_results["results"]["bindings"]:
            current_domain = row["domainClass"].get("value")
            if "comment" in row:
                current_comment = row["comment"]["value"].split(".")[0] + "."
            else:
                current_comment = "No description of class in ontology."
            domain.append((current_domain, current_comment))
        output = {"Choose class value: ": domain}
        return output

    def find_range(self, identifier):
        # returns  domain for identifier if applicable
        query = """PREFIX dcam: <http://purl.org/dc/dcam/>
                   PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                   PREFIX schema: <http://schema.org/>  
                   SELECT ?range
                    WHERE {
                      GRAPH <%s> {
                            <%s> rdfs:range|dcam:rangeIncludes|schema:rangeIncludes ?range . 
                      }
                    }   
               """ % (self.vocabularies.get_identifier_namespace(identifier), identifier)
        query_results = self.vocabularies.query_local_graph(identifier, query)
        for binding in query_results.get("results").values():
            for result in binding:
                correct_range = result["range"]["value"]
                return rdflib.term.URIRef(correct_range)

    def provide_suggested_refinements(self):
        # Provides a list of suggested refinements which could fix a violation caused by a particular metric
        # Maps the refinement to the violation identifier
        # e.g {0: ['RemoveTermType', 'ChangeOMTermType'], 1: ['AddDomainClass']}
        suggested_refinements = {}
        for violation_identifier in self.validation_results.keys():
            metric_identifier = self.validation_results[violation_identifier]["metric_identifier"]
            if metric_identifier in self.suggested_refinements.keys():
                suggested_refinements[violation_identifier] = self.suggested_refinements[metric_identifier]
        return suggested_refinements

    def process_user_input(self, refinements_values, refinements, mapping_file, mapping_graph, validation_report_file):
        # iterate each refinement which has been selected to be executed and capture user input
        selected_violation_identifier = self.get_selected_refinements(refinements_values)
        refinement_input = {}
        # concatenate the prefix value to the user input
        for violation_identifier in selected_violation_identifier:
            for dic_key in refinements_values.keys():
                # if current key is associated with input
                # e.g '0-http://www.w3.org/ns/r2rml#template' is with violation identifier
                print(dic_key, "dic key")
                if self.is_violation_input(dic_key, violation_identifier):
                    current_input_value = refinements_values[dic_key].strip()
                    property_name = self.get_property_name(dic_key)
                    # if an input has been associated with the violation
                    if violation_identifier in refinement_input.keys():
                        refinement_input[violation_identifier][property_name] = current_input_value
                    else:
                        refinement_input[violation_identifier] = {property_name: current_input_value }

            print(refinement_input)
        # refinement input associates each input value with the violation identifier it is refining
        self.execute_refinements(selected_violation_identifier, refinements, refinement_input, validation_report_file)

    def get_function_name(self, refinement_name):
        # returns the correct function name which relates to the refinement_function dictionary, some values may be tuples
        dic_keys = list(self.refinement_functions)
        if refinement_name in dic_keys:
            return self.refinement_functions[refinement_name]
        # check if tuple contains key
        tuple_check = [key for key in dic_keys if refinement_name in key]
        if tuple_check:
            return self.refinement_functions[tuple(tuple_check[0])]

    def execute_refinements(self, selected_violation_identifier, refinements, refinement_input, validation_report_file):
        # refinement graph updates the validation report graph
        self.refinement_graph = self.refinement_graph.parse("validation_report.ttl", format="ttl")
        # execute each refinement selected to be executed with or without user input
        for violation_identifier in selected_violation_identifier:
            # html forms store values as strings
            int_violation_identifier = int(violation_identifier)
            user_input_required = refinements[int_violation_identifier].get("user_input")
            refinement_name = refinements[int_violation_identifier].get("name")
            if user_input_required:
                function_input = refinement_input[violation_identifier]
            else:
                function_input = refinements[int_violation_identifier].get("values")
            function_name = self.get_function_name(refinement_name)
            print(function_name)
            refinement_query = function_name(function_input, self.mapping_graph, int_violation_identifier)
            # the function from self.refinement functions is called with the refinement name, user input and the mapping graph
            print(refinement_query)
            self.add_refinement_information(int_violation_identifier, refinement_query, refinement_name)
            self.refinement_count += 1
        print(self.mapping_graph.serialize(format="ttl").decode("utf-8"))
        self.create_refinement_report("validation_report.ttl")

    def create_refinement_report(self, validation_report_file):
        # output refinement into RDF report
        self.format_file_name_identifier()
        self.refinement_graph.serialize(destination=validation_report_file, format="ttl")
        self.generated_refined_mapping()

    def generated_refined_mapping(self):
        # uses custom serializer to preserve mapping ordering
        TurtleSerializer(self.mapping_graph, self.triple_references, "refined_mapping.ttl")
        # TurtleSerializer(self.mapping_graph, self.triple_references, "./static/uploads/mappings/video_demo_mapping.ttl".format(self.participant_id))

    def format_file_name_identifier(self):
        # remove local file name from IRI's
        # e.g <file:///home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/
        for (s, p, o) in self.refinement_graph.triples((None, None, None)):
            if str(o).startswith("file"):
                new_object = ValidationReport.format_triple_map_identifier(o)
                self.refinement_graph.remove((s, p, o))
                self.refinement_graph.add((s, p, new_object))

    @staticmethod
    def split_camel_case(word):
        splitted = re.sub('([A-Z][a-z]+)', r' \1', re.sub('([A-Z]+)', r' \1', word)).split()
        result = " ".join(splitted)
        return result

    def add_refinement_information(self, violation_identifier, refinement_query, refinement_name):
        # each refinement has a unique IRI and is associated with a refinement query
        refinement_identifier = rdflib.term.URIRef(self.EX + "refinement" + "-" + str(self.refinement_count))
        self.refinement_graph.add((refinement_identifier, RDF.type, self.MQIO.MappingRefinement))
        # self.refinement_graph.add((refinement_identifier, self.PROV.endedAtTime, Literal(datetime.utcnow(), datatype=XSD.dateTime)))
        # adding the SPARQL query used for the refinement
        refinement_query = Literal(refinement_query, datatype=XSD.string)
        self.refinement_graph.add((refinement_identifier, self.MQIO.hasRefinementQuery, refinement_query))
        # adding the refinement name e.g FindSimilarClasses
        refinement_name = Literal(self.split_camel_case(refinement_name), datatype=XSD.string)
        self.refinement_graph.add((refinement_identifier, self.MQIO.refinementName, refinement_name))
        # adding the wasRefinedBy property related to the previously defined refinement
        violation_identifier = rdflib.term.URIRef(self.EX + "violation" + "-" + str(violation_identifier))
        self.refinement_graph.add((violation_identifier, self.MQIO.wasRefinedBy, refinement_identifier))
        # add inverse property for mqv:refinedViolation, relating this refinement to the violation
        self.refinement_graph.add((refinement_identifier, self.MQIO.refinedViolation, violation_identifier))
        # add refinement agent
        self.add_refinement_agent()
        mapping_file_identifier = list(self.refinement_graph.subjects(rdflib.RDF.type, self.MQIO.MappingArtefact))
        if mapping_file_identifier:
            self.refinement_graph.remove((mapping_file_identifier[0], rdflib.RDF.type, self.MQIO.MappingArtefact))
            mapping_file_identifier = rdflib.term.URIRef(str(mapping_file_identifier[0]).split("/")[-1])
            self.refinement_graph.add((mapping_file_identifier, rdflib.RDF.type, self.MQIO.MappingArtefact))

    def add_refinement_agent(self):
        add_metadata = self.add_information.get("add-information")
        if add_metadata:
            refiner_name = self.add_information.get("refined-by-name")
            if refiner_name:
                refiner_name_identifier = rdflib.term.URIRef("http://example.org/" + "".join([word.capitalize() for word in refiner_name.split()]))
                for s,p,o in self.refinement_graph.triples((None, RDF.type, self.MQIO.MappingRefinement)):
                    print(s,p,o)
                    self.refinement_graph.add((s,self.PROV.wasAssociatedWith, refiner_name_identifier))

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
            print(user_input[matching_form_id])
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
        prefix_value = user_input.get(form_id)
        if prefix_value != "None":
            return True
        return False

    def is_prefix_value(self, form_id):
        # if the input is a prefix e.g '0-PREFIX-http://www.w3.org/ns/r2rml#class'
        split_value = form_id.split("-")
        if len(split_value) == 3 and split_value[1] == "PREFIX":
            print(form_id)
            return form_id

    def create_prefix_value_dict(self, file_name):
        # take a file name containing prefix, prefix values and store in a dictionary
        prefix_values = {"None": None}
        with open(file_name) as f:
            for line in f:
                line_values = line.split()
                prefix = line_values[1]
                prefix_value = line_values[2]
                prefix_values[prefix] = self.remove_angle_brackets(prefix_value)
        # sort prefix values alphabetically
        dict_keys = list(prefix_values.keys())
        dict_keys.sort()
        sorted_prefix_values = {i: prefix_values[i] for i in dict_keys}
        return sorted_prefix_values

    def remove_angle_brackets(self, value):
        # removes angle brackets from a string e.g <http://pgxo.loria.fr/> -> http://pgxo.loria.fr/
        return value.split("<")[1].split(">")[0]

    @staticmethod
    def get_selected_refinements(refinement_values):
        # return the violation identifiers which have been selected to be executed
        selected_violation_identifier = []
        for (violation_identifier, value) in refinement_values.items():
            if value == "Execute":
                selected_violation_identifier.append(violation_identifier)
        # sort list as refinements have ordering
        selected_violation_identifier.sort()
        return selected_violation_identifier

    def get_property_name(self, input_value):
        # '0-http://www.w3.org/ns/r2rml#template' returns http://www.w3.org/ns/r2rml#template
        return input_value.split("-")[1]

    def is_violation_input(self, dic_key, violation_identifier):
        # violation identifier = 0 and dic_key '0-http://www.w3.org/ns/r2rml#template', this means the input is associated
        if len(dic_key.split("-")) == 1:
            return False
        elif dic_key.split("-")[0] == violation_identifier:
            return True
        return False

    @staticmethod
    def reformat_user_input(user_input, violation_identifier):
        # 'input_values' is the user input values associated with 'violation_identifier'
        input_values = {}
        for (key, value) in user_input.items():
            # group each input based on violation identifier
            current_violation_identifier = key.split("-")[0]
            property_name = key.split("-")[1]
            if current_violation_identifier == violation_identifier:
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
