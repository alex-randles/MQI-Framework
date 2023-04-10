from rdflib.plugins.sparql import *
from rdflib import *
import urllib.parse
g = Graph().parse("/home/alex/Downloads/refined-mapping(82).ttl", format="ttl")
import urllib

# print(urllib.parse.quote_plus("refined-mapping82.ttl#STARTDATEEVENT"))
#
# # triple_map_identifier = urllib.parse.urlencode("refined-mapping82.ttl#STARTDATEEVENT")
# # print(triple_map_identifier)
# exit()
query = """
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX rr: <http://www.w3.org/ns/r2rml#>
INSERT 
{ 
  ?tripleMap rr:subjectMap _:b1 .
  _:b1 rr:class rr:test .
}
WHERE {
  ?tripleMap rr:predicateObjectMap ?pom . 
}
"""
print(len(g))
processUpdate(g, query)
print(len(g))
print(g.serialize(format="ttl").decode("utf-8"))
