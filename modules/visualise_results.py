# Creating a bar plot with seaborn
import pandas as pd
import rdflib
import plotly.express as px


class VisualiseResults:

    @staticmethod
    def get_dimension_description(dimension_name):
        dimension_descriptions = {
              "Data Consistency": "The dimension refers to the extent to which a dataset will be generated "
                                  "with no conflicting information.",
              "Mapping Consistency": "The dimension refers to the extent to which a mapping is conformant"
                                     " to its mapping language. ",
              "Syntactic Validity": "The dimension refers to the extent to which a mapping correctly"
                                      " defines RDF terms.",
              "Interpretability": "The dimension is concerned to information being represented in an "
                                  "appropriate notation, and whether it is machine-processable.",
              "Representational Conciseness": "The dimension refers to the representational of the "
                                              "resulting dataset being compact, well-formatted, and clear.",
              "Trustworthiness": "The dimension refers to the extent to which data producers involved "
                                 "in the mapping process believe that the information in those mappings is 'true'. " ,
              "Understandability": "The dimension is concerned with human-readable information being provided "
                                   "to mappings and the resources being generated such that data producers and "
                                   "consumers are able to understand them.",
              "Availability": "The dimension refers to the extent to which the mapping, the mapped data, and "
                              "the resulting dataset are available.",
              "Licensing": "The dimension refers to the license under which a mapping and its resulting dataset"
                           " can be (re) used."
                             }
        if dimension_name in dimension_descriptions.keys():
            return dimension_descriptions[dimension_name]
        else:
            return ""

    @staticmethod
    def create_violation_counts(validation_result):
        dimensions_metrics = {
              "Data Consistency": ["D5", "D6", "D7"],
              "Mapping Consistency": ["MP1", "MP2", "MP3", "MP4", "MP6", "MP7"],
              "Syntactic Validity": ["MP9", "MP10", "MP11", "MP12"],
              "Interpretability": ["D3", "D4"],
              "Representational Conciseness": ["MP13", "D1", "D2"],
              "Trustworthiness": ["VOC3"],
              "Understandability": ["VOC1", "VOC2"],
              "Licensing": ["VOC4", "VOC5"],
                             }
        # takes the validation result and counts violations in each dimension
        # dimension_counts = {key: {"count":0, "violation_IDS" : []} for (key, value) in dimensions_metrics.items()}
        dimension_counts = {key: { "count": 0, "violations": []}  for (key, value) in dimensions_metrics.items()}
        for violation in validation_result.keys():
            metric_ID = validation_result[violation]["metric_identifier"]
            dimension = [dimension for (dimension, metrics) in dimensions_metrics.items() if metric_ID in metrics]
            if dimension:
                # update violation count for dimension
                dimension_name = dimension[0]
                dimension_counts[dimension_name]["count"] += 1
                # add violation ID to dimension
                dimension_counts[dimension_name]["violations"].append("Violation {}".format(violation))
        return dimension_counts


    @staticmethod
    def chart_dimensions(validation_result):
        # Creates the chart which show violation counts to there dimensions
        dimension_counts = VisualiseResults.create_violation_counts(validation_result)
        df = pd.DataFrame(columns=["Quality Dimensions", "Violation Count", "Violations"])
        for dimension in dimension_counts:
            violation_count = dimension_counts[dimension]["count"]
            violations = dimension_counts[dimension]["violations"]
            new_row = {"Quality Dimensions": dimension, "Violation Count":violation_count,
                       "Violations": " ".join(violations)}
            df = df.append(new_row, ignore_index=True)
        dimensions = df["Quality Dimensions"]
        print(df)
        length = len(dimensions)
        values = [i for i in range(0,length)]
        dimension_text = [VisualiseResults.get_dimension_description(dimension) for dimension in dimensions]
        fig = px.bar(df, y="Quality Dimensions", text="Violations" , x="Violation Count", orientation='h',
                     hover_name="Quality Dimensions", hover_data={'Quality Dimensions':False, "Description" : dimension_text}, color="Quality Dimensions")
        fig.update_layout(title_text="<b>Number of violations detected by metrics within each dimension.</b>",
                          autosize=True,
                          hoverlabel=dict(font=dict(family='sans-serif', size=16)),
                          font=dict(
                              size=18,
                          ),
                          height=750,
                          margin=dict(
                              l=50,
                              r=50,
                              b=0,
                              t=50,
                              pad=1
                          ),
                          yaxis={'categoryorder': 'total ascending'},
                          # dtick is the increment of xaxis
                          xaxis= {"dtick": 1, "nticks" : 3},
                        )
        # fig.show()
        num_violations = max(df["Violation Count"])
        if num_violations < 3:
            fig.update_xaxes(range = [0,5])
        div = fig.to_html(full_html=False)
        return div



if __name__ == "__main__":
    # validation_result = {0: {'metric_ID': 'MP7', 'result_message': 'Term type for subject map should be an IRI or Blank Node', 'value': rdflib.term.URIRef('http://www.w3.org/ns/r2rml#Literal'), 'location': rdflib.term.BNode('ub2bL12C19'), 'triple_map': 'file:///home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/static/uploads/test_mapping.ttl#TriplesMap1'}, 1: {'metric_ID': 'MP13', 'result_message': 'Duplicate Triples Defined.', 'value': None, 'location': rdflib.term.BNode('ub2bL42C27'), 'triple_map': 'file:///home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/static/uploads/test_mapping.ttl#TriplesMap1'}, 2: {'metric_ID': 'D6', 'result_message': 'Usage of incorrect domain.', 'value': rdflib.term.URIRef('http://www.w3.org/ns/prov#invalidatedAtTime'), 'location': rdflib.term.BNode('ub2bL26C27'), 'triple_map': 'file:///home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/static/uploads/test_mapping.ttl#TriplesMap1'}, 3: {'metric_ID': 'D6', 'result_message': 'Usage of incorrect domain.', 'value': rdflib.term.URIRef('http://purl.org/eis/vocab/daq#hasObservation'), 'location': rdflib.term.BNode('ub2bL48C27'), 'triple_map': 'file:///home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/static/uploads/test_mapping.ttl#TriplesMap1'}, 4: {'metric_ID': 'D6', 'result_message': 'Usage of incorrect domain.', 'value': rdflib.term.URIRef('http://www.w3.org/ns/prov#invalidatedAtTime'), 'location': rdflib.term.BNode('ub2bL34C27'), 'triple_map': 'file:///home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/static/uploads/test_mapping.ttl#TriplesMap1'}, 5: {'metric_ID': 'D6', 'result_message': 'Usage of incorrect domain.', 'value': rdflib.term.URIRef('http://purl.org/eis/vocab/daq#hasObservation'), 'location': rdflib.term.BNode('ub2bL42C27'), 'triple_map': 'file:///home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/static/uploads/test_mapping.ttl#TriplesMap1'}, 6: {'metric_ID': 'D7', 'result_message': 'Usage of incorrect datatype.', 'value': rdflib.term.URIRef('http://www.w3.org/ns/prov#invalidatedAtTime'), 'location': rdflib.term.BNode('ub2bL28C22'), 'triple_map': 'file:///home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/static/uploads/test_mapping.ttl#TriplesMap1'}, 7: {'metric_ID': 'D7', 'result_message': 'Usage of incorrect datatype.', 'value': rdflib.term.URIRef('http://www.w3.org/ns/prov#invalidatedAtTime'), 'location': rdflib.term.BNode('ub2bL36C22'), 'triple_map': 'file:///home/alex/Desktop/Mapping-Quality-Framework/Mapping-Quality-Model/static/uploads/test_mapping.ttl#TriplesMap1'}}
    # dimension_counts = VisualiseResults.create_violation_counts(validation_result)
    # dimenion_counts = {"Completeness": 5, "PositionalAccuracy": 55}
    validation_result = {0: {'metric_ID': 'D3', 'result_message': 'Usage of incorrect domain.', 'value': rdflib.term.URIRef('http://xmlns.com/foaf/0.1/knows'), 'location': rdflib.term.BNode('ub6bL16C27'), 'triple_map': 'file:///home/alex/Desktop/Mapping-Quality-Framework/static/uploads/test.ttl#TriplesMap1'}, 1: {'metric_ID': 'D3', 'result_message': 'Usage of incorrect domain.', 'value': rdflib.term.URIRef('http://xmlns.com/foaf/0.1/knows'), 'location': rdflib.term.BNode('ub6bL29C27'), 'triple_map': 'file:///home/alex/Desktop/Mapping-Quality-Framework/static/uploads/test.ttl#TriplesMap2'}}
    VisualiseResults.chart_dimensions(validation_result)