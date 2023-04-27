import rdflib
import urllib
import requests

headers = {'Accept': 'application/rdf+xml'}
url = "http://example.org/change-report-1"
graph_name = urllib.parse.quote(url)
graph_file_name = "/home/alex/MQI-Framework/static/change_detection_cache/change_graphs/2.trig"
g = rdflib.Graph().parse(graph_file_name, format="trig")
print(len(g))
graph_contents = open(graph_file_name, "r").read()
print(graph_contents)
exit()
# print(urllib.parse.quote(graph_contents))
# exit()

localhost = "http://127.0.0.1:3030/User-1/data?graph={}".format(graph_name)
requests.post(localhost, data=graph_contents, headers={"content-type": "text/n3"})