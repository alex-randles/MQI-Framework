import jsondiff
import json
from deepdiff import DeepDiff
import re
import deepdiff
import pprint
from collections import defaultdict
json1 = json.loads('{"isDynamic": false, "name": "", "value": "SID:<sid>", "description": "instance","argsOrder": 1,"isMultiSelect": false}')

json2 = json.loads('{ "name": "ss","isDynamic": false, "module": "CS171", "ss": {"1":"test", "2": "try"}, "description": "instance","argsOrder": 1,"isMultiSelect": false}')

ddiff = DeepDiff(json1, json2, ignore_order=True)
# res = jsondiff.diff(json1, json2)
# print(res)
# print(re.findall('"([^"]*)"', '[root["value"]]'))

output_changes = defaultdict(dict)
output_changes["insert"] = defaultdict(dict)
output_changes["delete"] = defaultdict(dict)
change_id = 0
for k,v in ddiff.items():
    if k == "dictionary_item_removed" or k == "dictionary_item_added":
        change_type = "delete" if "removed" in k else "insert"
        for object in v:
            if object:
                name = "{}".format(object.replace("'", '"'))
                object_name = re.findall('"([^"]*)"', name)
                if object_name:
                    object_name = object_name[0]
                    object_value = json1.get(object_name)
                    if not object_value:
                        object_value = json2.get(object_name)
                    if not isinstance(object_value, dict):
                        output_changes[change_type][change_id] = {
                                                     "structural_reference": "Key",
                                                     "change_reason": "{}".format(object_name),
                                                 }
                        change_id += 1
                        output_changes[change_type][change_id] = {
                                                     "data_reference": "{}".format(object_name),
                                                     "change_reason": "{}".format(object_value),
                                                 }
                        change_id += 1
                    else

pprint.pprint(json.loads(json.dumps(output_changes)))


   # if change_type == "columns_added":
   #                          output_changes["insert"][change_id] = {
   #                              "structural_reference": structural_reference,
   #                              "change_reason": changes,
   #                          }