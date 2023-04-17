import rdflib
import re


class TurtleSerializer:

    def __init__(self, mapping_graph, triple_references=None, output_file=None):
        self.triple_references = triple_references
        self.tab_count = 1
        self.mapping_graph = mapping_graph
        self.output_file = output_file
        self.output = ""
        self.erase_file()
        self.namespaces = self.get_namespaces()
        self.RR = rdflib.Namespace('http://www.w3.org/ns/r2rml#')
        self.RML = rdflib.Namespace("http://semweb.mmlab.be/ns/rml#")
        self.add_namespaces()
        self.create_output_file()

    @staticmethod
    def find_identifier(node_value):
        regex = re.search('L(.+?)C', node_value)
        if regex:
            match = regex.group(1)
            return int(match)
        return int(0)

    def sort_triple_maps(self):
        # returns the triple map's in input order
        # result maps triple map to lowest valued identifier
        result = []
        for triple_map in self.triple_references:
            blank_node_identifiers = []
            for predicate, identifiers in self.triple_references[triple_map].items():
                if predicate != "not_blank_node":
                    blank_node_identifiers.append(identifiers)
            lowest_identifier = [self.find_identifier(str(identifier)) for identifier in blank_node_identifiers]
            lowest_identifier = min(lowest_identifier, default=0)
            result.append((triple_map, lowest_identifier))
        sorted_result = sorted(result, key=lambda x: x[1])
        triple_map_sorted = [triple_map for triple_map, _ in sorted_result]
        return triple_map_sorted

    def create_output_file(self):
        if self.output_file:
            sorted_triple_maps = self.sort_triple_maps()
            for triple_map_identifier in sorted_triple_maps:
                self.output = ""
                self.add_triple_map(triple_map_identifier)

    def add_triple_map(self, triple_map_identifier):
        # add triple map IRI to output file
        self.output += "\n%s\n" % (self.get_triple_map_name(triple_map_identifier))
        triple_map_values = self.triple_references[triple_map_identifier]
        self.add_non_blank_nodes(triple_map_values)
        self.add_blank_nodes(triple_map_values)
        self.output += ".\n"
        self.format_final_output()

    def format_final_output(self):
        # add spacing to the output file
        final_output = "\t\n".join(self.output.split("\n"))
        self.write_to_file(final_output)

    def add_non_blank_nodes(self, triple_map_values):
        # values which relate single triples not blank nodes
        # e.g {'not_blank_node': [(rdflib.term.URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'), rdflib.term.URIRef('http://www.w3.org/ns/r2rml#TriplesMap'))]
        non_blank_node_key = "not_blank_node"
        if non_blank_node_key in triple_map_values.keys():
            for (predicate, object) in triple_map_values[non_blank_node_key]:
                self.output = self.output + self.format_identifier(predicate) + self.format_identifier(object) + ";\n"

    def add_blank_nodes(self, triple_map_values):
        # rml mappings define source differently
        is_rml_mapping = self.RML.logicalSource in self.mapping_graph.predicates(None, None)
        if is_rml_mapping:
            mapping_ordering = [self.RML.logicalSource, self.RR.subjectMap, self.RR.predicateObjectMap]
        else:
            mapping_ordering = [self.RR.logicalTable, self.RR.subjectMap, self.RR.predicateObjectMap]
        for predicate in mapping_ordering:
            if predicate in triple_map_values.keys():
                blank_nodes = triple_map_values[predicate]
                self.iterate_triples(predicate, blank_nodes)

    def iterate_triples(self, predicate, blank_nodes):
        # (http://www.w3.org/ns/r2rml#logicalTable [rdflib.term.BNode('ub2bL391C18')] )
        # iterates through each values related to predicates
        for blank_node in blank_nodes:
            blank_node_objects = []
            non_blank_node_objects = []
            self.output += "\n" + self.format_identifier(predicate) + " [ \n "
            for (s, p, o) in self.mapping_graph.triples((blank_node, None, None)):
                if not isinstance(o, rdflib.term.BNode):
                    non_blank_node_objects.append((p,o))
                elif isinstance(o, rdflib.term.BNode):
                    blank_node_objects.append(o)
            self.add_non_blank_node_objects(non_blank_node_objects)
            self.add_blank_node_objects(blank_node_objects)
            self.output += " ];\n"

    def add_non_blank_node_objects(self, predicate_objects):
        self.group_objects(predicate_objects)

    def group_objects(self, predicate_objects):
        # groups predicates and objects, with predicate as key and object as value
        grouped_object = {}
        for p, o in predicate_objects:
            if p in grouped_object.keys():
                grouped_object[p] = grouped_object[p] + [o]
            else:
                grouped_object[p] = [o]
        self.add_grouped_objects(grouped_object)
        return grouped_object

    def add_grouped_objects(self, grouped_objects):
        # add in form inline rr:predicate foaf:name, foaf:age; instead of one per line
        if grouped_objects:
            for predicate, objects in grouped_objects.items():
                self.output += "\t" * self.tab_count + self.format_identifier(predicate)
                self.output += ",".join([self.format_identifier(object) for object in grouped_objects[predicate]]) + ";\n"

    def display_violation(self, blank_node, triple_map, violation_value):
        try:
            self.output = ""
            blank_node = rdflib.term.BNode(blank_node)
            subject = list(self.mapping_graph.subjects(None, blank_node))[0]
            # if violation is in a objectMap, display the predicateObjectMap aswell
            if isinstance(subject, rdflib.term.BNode):
                blank_nodes = [subject]
            else:
                blank_nodes = [blank_node]
            self.output += self.format_identifier(triple_map)
            predicate = list(self.mapping_graph.predicates(None, blank_nodes[0]))[0]
            # (http://www.w3.org/ns/r2rml#logicalTable [rdflib.term.BNode('ub2bL391C18')] )
            # iterates through each values related to predicates
            for current_blank_node in blank_nodes:
                blank_node_objects = []
                self.output += "\n" + self.format_identifier(predicate) + " [ \n "
                # remove duplicate predicates
                predicates = list(set(self.mapping_graph.predicates(current_blank_node, None)))
                # iterate each predicate and if more than object for a predicate join with "," and end with ";"s if not a blank node
                for current_predicate in predicates:
                    non_blank_node_objects = [self.format_identifier(object) for object in list(self.mapping_graph.objects(current_blank_node, current_predicate)) if
                                         not isinstance(object, rdflib.term.BNode)]
                    current_blank_node_objects = [object for object in list(self.mapping_graph.objects(current_blank_node, current_predicate)) if
                                     isinstance(object, rdflib.term.BNode)]
                    if non_blank_node_objects:
                        self.output += "\t" + self.format_identifier(current_predicate) + " " + ", ".join(non_blank_node_objects) + "; \n "
                    elif current_blank_node_objects:
                        blank_node_objects += current_blank_node_objects
                # iterate through the blank node objects last e.g objectMap
                self.add_blank_node_objects(blank_node_objects)
                self.output += " ];\n"
            return self.output.split("\n")
        except:
            return None

    def change_violation_color(self, violation_value):
        # displays the violation value in a red color
        # format value so its the same as whats already in the string
        value = self.format_identifier(violation_value)
        # change to red color
        formatted_value = '***** %s *****' % (value)

    def add_blank_node_objects(self, blank_node_objects):
        # blank nodes with blank nodes as object such as predicateObjectMap with object maps
        for blank_node in blank_node_objects:
            predicate = list(self.mapping_graph.predicates(None, blank_node))[0]
            self.output += "\t" + self.format_identifier(predicate) + " [\n"
            new_blank_node_objects = []
            self.tab_count = 2
            non_blank_nodes = []
            # while their are no more blank node objects to iterate
            while True:
                for (s, p, o) in self.mapping_graph.triples((blank_node, None, None)):
                    if not isinstance(o, rdflib.term.BNode):
                        non_blank_nodes.append((p,o))
                    elif isinstance(o, rdflib.term.BNode):
                        new_blank_node_objects.append(o)
                self.add_non_blank_node_objects(non_blank_nodes)
                # if the blank node subject has blank node as object
                if new_blank_node_objects:
                    while new_blank_node_objects:
                        current_blank_node = new_blank_node_objects[0]
                        predicate = list(self.mapping_graph.predicates(None, current_blank_node))[0]
                        self.output += "\t" * self.tab_count + self.format_identifier(predicate) + " [\n"
                        self.tab_count += 1
                        non_blank_nodes = []
                        for (s, p, o) in self.mapping_graph.triples((current_blank_node, None, None)):
                            if not isinstance(o, rdflib.term.BNode):
                                non_blank_nodes.append((p,o))
                                # self.output += "\t" * self.tab_count + self.format_identifier(p) + self.format_identifier(o) + ";\n"
                            else:
                                new_blank_node_objects.append(o)
                        new_blank_node_objects.pop(0)
                        self.add_non_blank_node_objects(non_blank_nodes)
                        self.output += "\t" * self.tab_count + " ];\n "
                    break
                else:
                    break
            self.output += "\t" * 2 + "]; \n"
            self.tab_count = 1

    def get_triple_map_name(self, triple_map_identifier):
        if "#" in triple_map_identifier:
            return "<#%s>" % (triple_map_identifier.split("#")[-1])
        elif "/" in triple_map_identifier:
            return "<%s>" % (triple_map_identifier.split("/")[-1])
        return triple_map_identifier

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

    def is_typed_literal(self, literal):
        converted_literal = rdflib.term._castPythonToLiteral(literal, datatype=None)
        datatype = converted_literal[0].datatype
        language = converted_literal[0].language
        if datatype:
            prefix_datatype = self.format_identifier(datatype).strip()
            new_literal = '"{}"^^{} '.format(literal, prefix_datatype)
            return new_literal
        elif language:
            new_literal = '"{}"@{} '.format(literal, language)
            return new_literal
        return ' "%s"' % literal

    def is_multi_line(self, literal):
        if len(literal.split("\n")) > 1:
            # escape characters are replaced correctly, one backslash with two backslash
            literal = literal.replace('\\', '\\\\')
            return '""" %s """' % (literal)
        else:
            literal = self.is_typed_literal(literal)
            print(rdflib.term.Literal(literal).datatype, "DATATYPE")
            return literal
            # return ' "%s" ' % (literal)

    def is_file_name(self, identifier):
        # remove the local file directory from a file identifier
        if identifier.startswith("file:"):
            try:
                new_identifier = identifier.split("#")[1]
                return " <#%s> " % new_identifier
            except:
                return " <%s> " % identifier
        return " <%s> " % identifier

    @staticmethod
    def parse_violation_value(violation_value):
        # print("PARSING VIOLATION VALUE")
        # check if query parameter for matching violation
        violation_value = TurtleSerializer.check_query_parameter(violation_value)
        if type(violation_value) is tuple:
            return violation_value[0].strip()
        else:
            return violation_value.strip()

    def add_prefix(self, identifier):
        # find prefix with longest matching prefix
        match = []
        for (prefix, namespace) in self.namespaces.items():
            if namespace in identifier:
                match.append(namespace)
        # if matching namesapce, return the longest
        if match:
            match_namespace = max(match)
            prefix = [prefix for (prefix, namespace) in self.namespaces.items() if namespace == match_namespace][0]
            identifier = identifier.replace(match_namespace, prefix + ":")
            return " %s" % identifier

    @staticmethod
    def check_query_parameter(identifier):
        # add escape (\) if it has a query parameter (?)
        if "?" in identifier:
            new_identifier = "\\?".join(identifier.split("?"))
            return rdflib.term.URIef(new_identifier)
        return identifier

    def format_identifier(self, identifier):
        if isinstance(identifier, rdflib.term.Literal):
            return self.is_multi_line(identifier)
        identifier = self.check_query_parameter(identifier)
        if self.add_prefix(identifier):
            return self.add_prefix(identifier)
        elif isinstance(identifier, rdflib.term.URIRef):
            return self.is_file_name(identifier)
        else:
            return self.is_file_name(identifier)

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
    file_name = "/home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/mappings/video_demo.ttl"
    validate_quality = ValidateQuality(file_name)
    print(validate_quality.triple_references)
    TurtleSerialzer(validate_quality.mapping_graph, validate_quality.triple_references, "new.ttl")
    output_file = open("new.ttl")
    input_file = open(file_name)
    # print(output_file.readlines())
    input_file_lines = input_file.readlines()
    output_file_lines = output_file.readlines()
    # map comment to index i.e line number
    comments = {}
    for line in input_file_lines:
        # if a comment
        if line.strip().startswith("#"):
            line_number = input_file_lines.index(line)
            comments[line_number] = line
    print(comments)
    for line_number, comments in comments.items():
        output_file_lines.insert(line_number+4, comments)
    for line in output_file_lines:
        print(line)


    # # iterate triples with inline predicates e.g rr:class foaf:Person, foaf:Agent;
    # def new_iterate_triples(self, predicate, blank_nodes):
    #     # (http://www.w3.org/ns/r2rml#logicalTable [rdflib.term.BNode('ub2bL391C18')] )
    #     # iterates through each values related to predicates
    #     count = 0
    #     values = {}
    #     for blank_node in blank_nodes:
    #         blank_node_objects = []
    #         self.output += "\n" + self.format_identifier(predicate) + "[ \n "
    #         for (s, p, o) in self.mapping_graph.triples((blank_node, None, None)):
    #             if not isinstance(o, rdflib.term.BNode):
    #                 # print("line 69", p, o, count)
    #                 count += 1
    #                 if p not in values.keys():
    #                     values[p] = [o]
    #                 elif p in values.keys():
    #                     # print(values[p], "IN KEYS")
    #                     values[p] = values[p] + [o]
    #                 self.output += "\t" + self.format_identifier(p) + self.format_identifier(o) + ";\n"
    #             elif isinstance(o, rdflib.term.BNode):
    #                 blank_node_objects.append(o)
    #         if count == 0:
    #             print(values)
    #         values = {}
    #         self.add_blank_node_objects(blank_node_objects)
    #         self.output += " ];\n"