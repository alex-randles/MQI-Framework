from rdflib import *
import os
import hashlib
import requests
import urllib
import rdflib
from SPARQLWrapper import SPARQLWrapper, JSON


class FetchVocabularies:

    def __init__(self, file_name=None):
        self.file_name = file_name
        self.mapping_graph = None
        self.cache_directory = "./modules/cache/"
        self.create_graph()

    # runs ontology retrieval process
    def create_graph(self):
        if self.file_name:
            self.mapping_graph = rdflib.Graph().parse(self.file_name, format="ttl")
            # self.fetch_mapping_ontologies()

    # retrieves and queries local graph
    def query_local_graph(self, property_identifier, query):
        sparql = SPARQLWrapper("http://127.0.0.1:3030/MQI-Framework-Ontologies")
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        query_results = sparql.queryAndConvert()
        # check if results from query - otherwise graph does not exist
        if "results" in query_results.keys():
            results = query_results["results"].get("bindings")
            if not results:
                namespace = FetchVocabularies.get_identifier_namespace(property_identifier)
                self.http_retrieval(namespace)
        return query_results

    @staticmethod
    def get_identifier_namespace(identifier):
        if identifier.startswith("http://dbpedia.org/ontology/"):
            return identifier
        if "#" in identifier:
            namespace = identifier[:identifier.rfind("#") + 1]
        else:
            namespace = identifier[:identifier.rfind("/") + 1]
        return namespace

    # uses rdflib to retrieve graph
    def rdflib_retrieval(self, url):
        g = rdflib.Graph().parse("http://www.w3.org/ns/prov#")
        filename = self.hash_filename(url)
        file_location = self.cache_directory + filename
        # some graphs return rdf:nil with rdflib
        if len(g) < 10:
            raise Exception("Sorry, no graphs with < 10 triples.")
        g.serialize(destination=file_location)
        return True

    @staticmethod
    def http_retrieval(url):
        headers = {'Accept': 'application/rdf+xml'}
        graph_name = urllib.parse.quote(url)
        try:
            print("test")
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                localhost = "http://127.0.0.1:3030/MQI-Framework-Ontologies/data?graph={}".format(graph_name)
                # if host returns xml or turtle RDF data
                try:
                    requests.post(localhost, data=r, headers={"content-type": "application/rdf+xml"})
                except requests.exceptions.ConnectionError as e:
                    requests.post(localhost, data=r, headers={"content-type": "text/turtle"})
        except requests.exceptions.SSLError as e:
            pass
        except requests.exceptions.ConnectionError as e:
            pass
        except requests.exceptions.MissingSchema as e:
            pass
        except requests.exceptions.ReadTimeout as e:
            pass
        except requests.exceptions.InvalidSchema as e:
            pass
        return True

    # A function which returns a list containing unique namespaces in the object position
    def get_unique_namespaces(self):
        unique_namespaces = []
        query = """
                     PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                     PREFIX rr: <http://www.w3.org/ns/r2rml#>
                     PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                     SELECT DISTINCT ?ns
                     WHERE   
                     { 
                        ?s rr:class|rr:predicate|rr:object ?o.
                        BIND(REPLACE(str(?o), "(#|/)[^#/]*$", "$1") AS ?ns)
                        # FILTER OUT KNOWN NS WHICH WILL NOT BE NEEDED (xsd, rr)
                        Filter(isURI(?o) && isBlank(?s) && !(STRSTARTS(STR(?o), STR(xsd:))) 
                        && !(STRSTARTS(STR(?o), STR(rr:))) && 
                        !(STRSTARTS(STR(?o), "file")))
                     }

             """
        query_results = self.mapping_graph.query(query)
        for row in query_results:
            unique_namespaces.append("%s" % row)
        print(unique_namespaces)
        return unique_namespaces

    # attempts to retrieve ontology using rdflib and request module
    @staticmethod
    def retrieve_ontology(url):
        for func in [FetchVocabularies.http_retrieval]:  # change list order to change execution order.
            try:
                len = func(url)
                return len
            except Exception as err:
                print(err)
        return 0

    @staticmethod
    def store_local_vocabulary(file_path):
        # rdflib.plugins.parsers.notation3.BadSyntax
        # rdflib.plugin.PluginException - Wrong file format
        try:
            graph_format = rdflib.util.guess_format(file_path)
            ontology_graph = Graph().parse(file_path, format=graph_format)
            query = """
                SELECT ?ns (COUNT(?ns) AS ?count)
                WHERE {
                  ?subject ?predicate ?object                        
                  BIND(REPLACE(str(?subject), "(#|/)[^#/]*$", "$1") AS ?ns)
                }
                GROUP BY ?ns
            """
            query_results = ontology_graph.query(query)
            max_value = (None, -1)
            for row in query_results:
                count = int(row["count"])
                namespace = str(row["ns"])
                if count > max_value[1]:
                    max_value = (namespace, count)
            graph_name = urllib.parse.quote(max_value[0])
            localhost = "http://127.0.0.1:3030/MQI-Framework-Ontologies/data?graph={}".format(graph_name)
            # if host returns xml or turtle RDF data
            if graph_format == "xml":
                requests.post(localhost, data=open(file_path).read(), headers={"content-type": "application/rdf+xml"})
            if graph_format == "turtle":
                requests.post(localhost, data=open(file_path).read().encode('utf-8'), headers={"content-type": "text/turtle"})
        except Exception as e:
            return 1


if __name__ == "__main__":
    f = FetchVocabularies("/home/alex/Desktop/testing_mapping.ttl")
    f.query_local_graph("http://www.w3.org/ns/prov#generated")
