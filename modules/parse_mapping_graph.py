# Parses mappings into individuals graphs of triple maps
from rdflib import Graph, BNode, URIRef, Namespace


class ParseMapping:

    def __init__(self, mapping_file):
        self.R2RML_NS = Namespace("http://www.w3.org/ns/r2rml#")
        self.mapping_graph = Graph().parse(mapping_file, format="ttl")
        self.triple_map_graphs = []
        self.create_graphs()

    def get_subjects(self):
        subjects = []
        for s, p, o in self.mapping_graph.triples((None,  None, None)):
            # if it relates to an R2RML view instead of a triples map
            if not isinstance(s, BNode) and not (p == self.R2RML_NS.sqlQuery or p == self.R2RML_NS.sqlVersion):
                if s not in subjects:
                    subjects.append(s)
        return subjects

    def add_values(self, current_object, graph):
        for s, p, o in self.mapping_graph.triples((current_object, None, None)):
            graph.add((s,p,o))
            for s1, p1, o1 in self.mapping_graph.triples((o, None, None)):
                    graph.add((s1, p1, o1))
                    self.iterate_values(o1, graph)
        return graph

    def iterate_values(self, o1, graph):
        for s, p, o in self.mapping_graph.triples((o1, None, None)):
            graph.add((s,p,o))

    def create_graphs(self):
        triple_map_subjects = self.get_subjects()
        for subject in triple_map_subjects:
            new_graph = Graph()
            for s, p, o in self.mapping_graph.triples((subject,  None, None)):
                new_graph.add((s, p, o))
                new_graph = self.add_values(o, new_graph)
            new_graph.bind("rr", "http://www.w3.org/ns/r2rml#")
            self.triple_map_graphs.append((str(subject), new_graph))

    def print_graphs(self):
        for (triple_map_ID, graph) in self.triple_map_graphs:
            print(graph.serialize(format="ttl").decode("utf-8"))

if __name__ == "__main__":
    p = ParseMapping("/home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/mappings/OSI_mappings/mappingQualitySchema.ttl")
    triple_maps = p.triple_map_graphs
    print(len(triple_maps)) # 6
    for (triple_map, triples) in triple_maps:
        if "View" in triple_map:
            print(triple_map, triples)
