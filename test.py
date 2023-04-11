import time
from modules.detect_changes import DetectChanges

def main():
    while True:
        csv_file_1 = "https://raw.githubusercontent.com/alex-randles/Change-Detection-System-Examples/main/version_1_files/employee.csv"
        csv_file_2 = "https://raw.githubusercontent.com/alex-randles/Change-Detection-System-Examples/main/version_2_files/employee-v6.csv"
        form_details = {
            'CSV-URL-1': csv_file_1,
            'CSV-URL-2': csv_file_2,
            'insert-threshold': '10', 'delete-threshold': '0',
            'move-threshold': '0', 'datatype-threshold': '0',
            'merge-threshold': '0', 'update-threshold': '0',
            'detection-end': '2022-07-10',
            'email-address': 'alexrandles0@gmail.com',
            "user-id": "2",
                    }
        cd = DetectChanges(user_id=2, form_details=form_details)
        time.sleep(300)

main()

exit()






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
