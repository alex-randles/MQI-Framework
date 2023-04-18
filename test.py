import jsondiff
import json

json1 = json.loads(
    '{"isDynamic": false, "name": "", "value": "SID:<sid>", "description": "instance","argsOrder": 1,"isMultiSelect": false}')

json2 = json.loads(
    '{ "name": "", "value": "SID:<sid>","isDynamic": false, "description": "instance","argsOrder": 1,"isMultiSelect": false}')

res = jsondiff.diff(json1, json2)
print(res)