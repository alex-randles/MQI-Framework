from rdflib import  *
namespaces = ["https://w3id.org/OSCD#","https://w3id.org/MQV"]
for ns in namespaces:
    g = Graph().parse(ns)
    d = Dataset()


    g2 = d.graph(URIRef(ns))


    for s,p,o in g.triples((None, None, None)):
        g2.add((s,p,o))


g = Graph().parse("/home/alex/Downloads/dbpedia.owl")
t = []
for s,p,o in g.triples((None, None, None)):
    t.append(s)
print(t)

d.serialize("test.trig", format="trig")

query = """
PREFIX owl: <http://www.w3.org/2002/07/owl#> 
ASK 
 {
 GRAPH ?g {
        <https://alex-randles.github.io/MQV/#MappingAssessment> a ?class .
        FILTER (?class IN (owl:Class))
         }
}"""
qres = d.query(query)
for row in qres:
    print(row)