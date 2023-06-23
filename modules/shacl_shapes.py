import requests
import io
import pandas as pd


class SHACLShape:

    def __init__(self, form_data):
        self.form_data = form_data

    def create_shape(self):
        try:
            source_data_url = self.form_data.get("source_data_url")
            url_request = requests.get(source_data_url)
            if url_request.status_code == 200:
                source_data = url_request.content
                csv_data = pd.read_csv(io.StringIO(source_data.decode('utf-8')))
                columns = " ".join(['"{}"'.format(column) for column in list(csv_data.columns)])
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
