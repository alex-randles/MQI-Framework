from rdflib import Graph, Namespace, URIRef, BNode, Literal, RDF, RDFS

try:
    from modules.validate_quality import ValidateQuality
except:
    from validate_quality import ValidateQuality
import re
import operator

# from modules.validate_quality import ValidateQuality


class TurtleSerialzer:

    def __init__(self, mapping_graph, triple_references=None, output_file=None):
        self.current_tab = 2
        self.triple_references = triple_references
        self.mapping_graph = mapping_graph
        self.output_file = output_file
        self.output = ""
        self.erase_file()
        self.namespaces = self.get_namespaces()
        self.RR = Namespace('http://www.w3.org/ns/r2rml#')
        self.add_namespaces()
        self.create_output_file()

    def create_output_file(self):
        if self.output_file:
            for triple_map_IRI in self.triple_references:
                self.output = ""
                self.add_triple_map(triple_map_IRI)

    def add_triple_map(self, triple_map_IRI):
        # add triple map IRI to output file
        self.output  +=  "\n%s\n" % (self.get_triple_map_name(triple_map_IRI))
        triple_map_values = self.triple_references[triple_map_IRI]
        self.add_non_bNodes(triple_map_values)
        self.add_bNodes(triple_map_values)
        self.output += ".\n"
        self.format_final_output()

    def format_final_output(self):
        # add spacing to the output file
        final_output = "\t\n".join(self.output.split("\n"))
        self.write_to_file(final_output)

    def add_non_bNodes(self, triple_map_values):
        # values which relate single triples not blank nodes
        # e.g {'not_bNode': [(rdflib.term.URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'), rdflib.term.URIRef('http://www.w3.org/ns/r2rml#TriplesMap'))]
        non_bNode_key = "not_bNode"
        if non_bNode_key in triple_map_values.keys():
            for (predicate, object) in triple_map_values[non_bNode_key]:
                self.output += self.format_IRI(predicate) + self.format_IRI(object) + ";\n"

    def add_bNodes(self, triple_map_values):
        # the order we want the output mapping in
        mapping_ordering = [self.RR.logicalTable, self.RR.subjectMap, self.RR.predicateObjectMap]
        for predicate in mapping_ordering:
            if predicate in triple_map_values.keys():
                triples = triple_map_values[predicate]
                self.add_triples(triples, predicate)
                # continue
                # self.iterate_triples(predicate, bNodes)

    def add_triples(self, all_triples, first_predicate):
        print(all_triples, type(all_triples))
        while all_triples:
            triples = [all_triples[0]]
            all_triples.pop(0)
            print(triples, first_predicate)
            self.current_tab = 2
            self.output += self.format_IRI(first_predicate) + "[ \n"
            num_brackets = 0
            while triples:
                non_bNode_objects = []
                bNode_predicates = []
                current_triple = triples[0]
                for s,p,o in self.mapping_graph.triples((current_triple, None, None)):
                    if not isinstance(o, BNode):
                        print("ADDING TRIPLES", p, o )
                        if not p == RDF.first and not p == RDF.rest:
                            non_bNode_objects.append((p,o))
                    else:
                        bNode_predicates.append(p)
                        triples.append(o)
                grouped_predicate_objects = self.group_objects(non_bNode_objects)
                for predicate in bNode_predicates:
                    if predicate == RDF.first or predicate == RDF.rest:
                        print("MATCHHHH", predicate)
                        pass
                    else:
                        self.output +="\t" * self.current_tab + self.format_IRI(predicate) + "[\n"
                        num_brackets += 1
                self.current_tab += 1
                triples.pop(0)
            for num in range(0,num_brackets+1):
                self.output += "\t" * self.current_tab   +  "];\n"
                self.current_tab -= 1
                # print(l)
            self.output += "\n"



    def iterate_triples(self, predicate, bNodes):
        # (http://www.w3.org/ns/r2rml#logicalTable [rdflib.term.BNode('ub2bL391C18')] )
        # iterates through each values related to predicates
        count = 0
        values = {}
        test = []
        for bNode in bNodes:
            bNode_objects = []
            test.append(bNode_objects)
            non_bNode_objects = []
            self.output += "\n" + self.format_IRI(predicate) + "[ \n "
            for (s,p,o) in self.mapping_graph.triples((bNode, None, None)):
                print(p, o, "TEST")
                if not isinstance(o, BNode):
                    print("line 69", p,o , count)
                    count+=1
                    # self.output += "\t" + self.format_IRI(p) + self.format_IRI(o) + ";\n"
                    non_bNode_objects.append((p,o))
                elif isinstance(o, BNode):
                    print("IS BNODE", p ,o)
                    bNode_objects.append(o)
            self.add_non_bNode_objects(non_bNode_objects)
            self.add_bNode_objects(bNode_objects)
            self.output += " ];\n"
        # print(test)
        # exit()

    def add_non_bNode_objects(self, non_bNode_objects):
        grouped_objects = self.group_objects(non_bNode_objects)
        for (p,o) in grouped_objects.items():
            print("adding",p,o)
            self.output += "\t" + self.format_IRI(p)
            objects = grouped_objects[p]
            if objects:
                formatted_objects = [self.format_IRI(object) for object in objects]
                self.output += ",".join(formatted_objects)
            print("OBJECTS ", objects, "ADD NON BNODE OBJECTS")
            self.output += ";\n"

    def group_objects(self, predicate_objects):
        # groups predicates and objects, with predicate as key and object as value
        grouped_object = {}
        for (p,o) in predicate_objects:
            if p in grouped_object.keys():
                grouped_object[p] =  grouped_object[p] + [o]
            else:
                grouped_object[p] = [o]
        self.add_grouped_objects(grouped_object)
        return grouped_object

    def add_grouped_objects(self, grouped_objects):
        if grouped_objects:
            for predicate, objects in grouped_objects.items():
                self.output += self.current_tab * "\t"
                self.output += self.format_IRI(predicate)
                self.output += ",".join([self.format_IRI(object) for object in grouped_objects[predicate]]) + ";\n"


    def display_violation(self, bNode, triple_map, violation_value):
        try:
            self.output = ""
            bNode = BNode(bNode)
            subject = list(self.mapping_graph.subjects(None, bNode))[0]
            # if violation is in a objectMap, display the predicateObjectMap aswell
            if isinstance(subject, BNode):
                bNodes = [subject]
            else:
                bNodes = [bNode]
            self.output += self.format_IRI(triple_map)
            predicate = list(self.mapping_graph.predicates(None, bNodes[0]))[0]
            # (http://www.w3.org/ns/r2rml#logicalTable [rdflib.term.BNode('ub2bL391C18')] )
            # iterates through each values related to predicates
            for current_bNode in bNodes:
                bNode_objects = []
                self.output += "\n" + self.format_IRI(predicate) + "[ \n "
                # remove duplicate predicates
                predicates = list(set(self.mapping_graph.predicates(current_bNode, None)))
                # iterate each predicate and if more than object for a predicate join with "," and end with ";"s if not a blank node
                for current_predicate in predicates:
                    non_bNode_objects = [self.format_IRI(object) for object in list(self.mapping_graph.objects(current_bNode, current_predicate)) if
                                         not isinstance(object, BNode)]
                    current_bNode_objects = [object for object in list(self.mapping_graph.objects(current_bNode, current_predicate)) if
                                     isinstance(object, BNode)]
                    if non_bNode_objects:
                        self.output += "\t" + self.format_IRI(current_predicate) + " " + ", ".join(non_bNode_objects) + "; \n "
                    elif current_bNode_objects:
                        bNode_objects += current_bNode_objects
                # iterate through the blank node objects last e.g objectMap
                self.add_bNode_objects(bNode_objects)
                self.output += " ];\n"
            return self.output.split("\n")
        except:
            return None
            return "Violation has no triples related."


    def change_violation_color(self, violation_value):
        # displays the violation value in a red color
        # format value so its the same as whats already in the string
        value = self.format_IRI(violation_value)
        # change to red color
        formatted_value = '***** %s *****' % (value)

    def add_bNode_objects(self, bNode_objects):
        # blank nodes with blank nodes as object such as predicateObjectMap with object maps
        for bNode in bNode_objects:
            # e.g rr:objectMap
            predicate = list(self.mapping_graph.predicates(None, bNode))[0]
            self.output += "\t" + self.format_IRI(predicate) + " [\n"
            new_bNode_objects = []
            tab_count = 2
            # while their are no more blank node objects to iterate
            while True:
                for (s, p, o) in self.mapping_graph.triples((bNode, None, None)):
                    if not isinstance(o, BNode):
                        self.output += "\t" * tab_count + self.format_IRI(p) + self.format_IRI(o) + ";\n"
                    elif isinstance(o, BNode):
                        new_bNode_objects.append(o)
                # if the blank node subject has blank node as object
                if new_bNode_objects:
                    # for new_bNode in new_bNode_objects:
                    while new_bNode_objects:
                        new_bNode = new_bNode_objects[0]
                        predicate = list(self.mapping_graph.predicates(None, new_bNode))[0]
                        self.output += "\t" * tab_count + self.format_IRI(predicate) + " [\n"
                        tab_count += 1
                        for (s, p, o) in self.mapping_graph.triples((new_bNode, None, None)):
                            if predicate == RDF.first or predicate == RDF.rest:
                                self.output += self.format_IRI(o)
                            else:
                                if isinstance(o, BNode):
                                    new_bNode_objects.append(o)
                                else:
                                    self.output += "\t" * tab_count + self.format_IRI(p) + self.format_IRI(o) + ";\n"
                        new_bNode_objects.pop(0)
                    self.output += "\t" * tab_count + " ];\n "
                    break
                else:
                    break
            self.output += "\t" * 2 + "]; \n"

    def get_triple_map_name(self, triple_map_IRI):
        if "#" in triple_map_IRI:
            return "<#%s>" % (triple_map_IRI.split("#")[-1])
        elif "/" in triple_map_IRI:
            return "<%s>" % (triple_map_IRI.split("/")[-1])
        return triple_map_IRI

    def write_to_file(self, text):
        if self.output_file:
            with open(self.output_file, "a") as output_file:
                output_file.write(text)

    def erase_file(self):
        if self.output_file:
            open(self.output_file, 'w').close()

    def print_file(self):
        if self.output_file:
            with open(self.output_file, 'r') as f:
                print(f.read())

    def is_multi_line(self, literal):
        if len(literal.split("\n")) > 1:
            # escape characters are replaced correctly, one backslash with two backslash
            literal = literal.replace('\\', '\\\\')
            return '""" %s """' % (literal)
        else:
            return ' "%s" ' % (literal)

    def is_file_name(self, IRI):
        # for objects such as <file:///home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/valid_mapping.ttl#TriplesMap2>
        # remove the file directory relating to my system
        if IRI.startswith("file:"):
            try:
                new_IRI = IRI.split("#")[1]
                return   " <#%s> " % (new_IRI)
            except:
                return " <%s> " % (IRI)
        return " <%s> " % (IRI)

    @staticmethod
    def parse_violation_value(violation_value):
        # if more than one, return first one for violation value
        if type(violation_value) is not tuple:
            return violation_value
        else:
            return violation_value[0]

    def add_prefix(self, IRI):
        # find prefix with longest matching prefix
        match = []
        for (prefix, namespace) in self.namespaces.items():
            if namespace in IRI:
                match.append(namespace)
        # if matching namesapce, return the longest
        if match:
            match_namespace = max(match)
            prefix = [prefix for (prefix, namespace) in self.namespaces.items() if namespace == match_namespace][0]
            IRI = IRI.replace(match_namespace, prefix + ":")
            return " %s " % (IRI)

    def format_IRI(self, IRI):
        if isinstance(IRI, Literal):
            return self.is_multi_line(IRI)
        elif self.add_prefix(IRI):
            return self.add_prefix(IRI)
        elif isinstance(IRI, URIRef):
            return self.is_file_name(IRI)
        else:
            return self.is_file_name(IRI)

    def get_namespaces(self):
        namespaces = {}
        for (prefix, namespace) in self.mapping_graph.namespaces():
            namespaces[prefix] = namespace
        return namespaces

    def add_namespaces(self):
        result = ""
        for (prefix, namespace) in self.mapping_graph.namespaces():
            current = "@prefix %s: <%s> . \n" % (prefix, namespace)
            result = result + current
        result = result + "\n"
        self.write_to_file(result)


if __name__ == "__main__":
    validate_quality = ValidateQuality("/home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/mappings/OSI-Mappings/1Spatial-2ndDump/daq-observation-mapping/mappingDAQobservation.ttl")
    validate_quality = ValidateQuality("/home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/mappings/chief-governers.ttl")
    print(validate_quality.triple_references)
    TurtleSerialzer(validate_quality.mapping_graph, validate_quality.triple_references, "new.ttl")
    output_lines = open("new.ttl").readlines()
    for line in output_lines:
        print(line)
    # g = Graph().parse("new.ttl", format="ttl")
    # print(len(g))
    # # def __init__(self, mapping_graph, triple_references=None, output_file=None):

