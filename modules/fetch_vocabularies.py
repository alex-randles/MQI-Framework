from rdflib import *
import os
import hashlib
import requests
import urllib
from SPARQLWrapper import SPARQLWrapper, JSON


class FetchVocabularies:

    def __init__(self, file_name=None):
        self.file_name = file_name
        self.mapping_graph = None
        self.cache_directory = "./modules/cache/"
        self.localhost = "http://127.0.0.1:3030/MQI-Framework-Ontologies"
        self.create_graph()

    # runs ontology retrieval process
    def create_graph(self):
        if self.file_name:
            self.mapping_graph = Graph().parse(self.file_name, format="ttl")
            # self.fetch_mapping_ontologies()

    # retrieves and queries local graph
    def query_local_graph(self, property_IRI, query):
        if "#" in property_IRI:
            property_namespace = property_IRI[:property_IRI.rfind("#") + 1]
        else:
            property_namespace = property_IRI[:property_IRI.rfind("/") + 1]
        sparql = SPARQLWrapper(self.localhost)
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        qres = sparql.queryAndConvert()
        # check if results from query - otherwise graph does not exist
        if "results" in qres.keys():
            results = qres["results"]["bindings"]
            if results == []:
                self.http_retrieval(property_namespace)
        return qres

    # uses rdflib to retrieve graph
    def rdflib_retrieval(self, url):
        g = Graph().parse("http://www.w3.org/ns/prov#")
        filename = self.hash_filename(url)
        file_location = self.cache_directory + filename
        # some graphs return rdf:nil with rdflib
        if len(g) < 10:
            raise Exception("Sorry, no graphs with < 10 triples.")
        g.serialize(destination=file_location)
        return True

    def http_retrieval(self, url):
        headers = {'Accept': 'application/rdf+xml'}
        graph_name = urllib.parse.quote(url)
        try:
            r = requests.get(url, headers=headers)
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
        ##
        # filename = self.hash_filename(url)
        # file_location = self.cache_directory + filename
        # f = open(file_location, "w")
        # f.write(r.text)
        return True

    # A function which returns a list containing unique namespaces in the object position
    def get_unique_namespaces(self):
        unqiue_namespaces = []
        query = """
                     PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                     PREFIX rr: <http://www.w3.org/ns/r2rml#>
                     PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                     SELECT DISTINCT ?ns
                     WHERE   
                     { 
                        ?s rr:class|rr:predicate ?o.
                        BIND(REPLACE(str(?o), "(#|/)[^#/]*$", "$1") AS ?ns)
                        # FILTER OUT KNOWN NS WHICH WILL NOT BE NEEDED (xsd, rr)
                        Filter(isURI(?o) && isBlank(?s) && !(STRSTARTS(STR(?o), STR(xsd:))) 
                        && !(STRSTARTS(STR(?o), STR(rr:))) && 
                        !(STRSTARTS(STR(?o), "file")))
                     }

             """
        qres = self.mapping_graph.query(query)
        for row in qres:
            unqiue_namespaces.append("%s" % row)
        print(unqiue_namespaces)
        return unqiue_namespaces

    # attempts to retrieve ontology using rdflib and request module
    def retrieve_ontology(self, url):
        for func in [self.http_retrieval]:  # change list order to change execution order.
            try:
                len = func(url)
                return len
            except Exception as err:
                print(err)
        return 0

    @staticmethod
    def store_local_vocabulary(file_path):
        # print(str(file_path).split(".")[-1])
        # exit()
        if str(file_path).split(".")[-1] == "owl":
            format = "xml"
        else:
            format = "ttl"
        ontology_graph = Graph().parse(file_path, format=format)
        query = """
            SELECT ?ns (COUNT(?ns) AS ?count)
            WHERE {
              ?subject ?predicate ?object                        
              BIND(REPLACE(str(?subject), "(#|/)[^#/]*$", "$1") AS ?ns)
            }
            GROUP BY ?ns
        """
        qres = ontology_graph.query(query)
        max_value = (None, -1)
        for row in qres:
            count = int(row["count"])
            namespace = str(row["ns"])
            if count > max_value[1]:
                max_value = (namespace, count)
        headers = {'Accept': 'application/rdf+xml'}
        graph_name = urllib.parse.quote(max_value[0])
        localhost = "http://127.0.0.1:3030/MQI-Framework-Ontologies/data?graph={}".format(graph_name)
        # if host returns xml or turtle RDF data
        try:
            requests.post(localhost, data=open(file_path).read(), headers={"content-type": "application/rdf+xml"})
        except Exception as e:
            requests.post(localhost, data=open(file_path).read().encode('utf-8'), headers={"content-type": "text/turtle"})

    # checks if ontology already saved
    def check_cache(self, namespace):
        # returns True if file exists in cache
        filename = self.cache_directory + self.hash_filename(namespace)
        return os.path.isfile(filename)

    # attempts to fetch each ontology in the mapping
    def fetch_mapping_ontologies(self):
        namespaces = self.get_unique_namespaces()
        for ns in namespaces:
            # if not already cached
            ontology_cached = self.check_cache(ns)
            if not ontology_cached:
                # different ontology storage methods
                exceptions = {
                    "http://xmlns.com/foaf/0.1/": "http://xmlns.com/foaf/0.1/index.rdf",
                    "http://ont.virtualtreasury.ie/ontology#": "https://ont.virtualtreasury.ie/ontology/ontology.ttl",
                }
                if ns in exceptions.keys():
                    ns = exceptions[ns]
                # if success returned
                return_value = self.retrieve_ontology(ns)
                if return_value is True:
                    print("Ontology saved: ", ns)
            else:
                print("Ontology ALREADY saved", ns)


if __name__ == "__main__":
    f = FetchVocabularies("/home/alex/Desktop/testing_mapping.ttl")
    f.query_local_graph("http://www.w3.org/ns/prov#generated")
