import requests
import io
import urllib.request
import pandas as pd
import xml.etree.ElementTree as ET

class SHACLShape:

    def __init__(self, form_data):
        self.form_data = form_data

    def create_shape(self):
        try:
            source_data_url = self.form_data.get("source_data_url")
            url_request = requests.get(source_data_url)
            if url_request.status_code == 200:
                source_data = url_request.content
                if source_data_url.endswith("csv"):
                    csv_data = pd.read_csv(io.StringIO(source_data.decode('utf-8')))
                    columns = " ".join(['"{}"'.format(column) for column in list(csv_data.columns)])
                else:
                    with urllib.request.urlopen(source_data_url) as f:
                        xml_tree = ET.parse(f)
                        elements = []
                        for element in xml_tree.iter():
                            elements.append(element.tag)
                        element_tags = list(set(elements))
                        columns = " ".join(['"{}"'.format(column) for column in element_tags])
                shape_template = f"""@prefix schema: <http://schema.org/> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix rr: <http://www.w3.org/ns/r2rml#> .
@prefix rml: <http://semweb.mmlab.be/ns/rml#>.

schema:PersonShape
    a sh:NodeShape ;
    sh:targetObjectsOf rr:objectMap ;
    sh:property [
      sh:path rr:column, rml:reference;
      sh:in ({columns});
      sh:message "Data reference no longer in source data." ;
    ] .
                            """
                open("./static/shacl_shape.ttl", "w+").write(shape_template.strip())
                return "Shape Generated"
            else:
                return "Unable to retrieve data"
        except Exception as e:
            print(f"exception {e}")
            return "Invalid URL"
