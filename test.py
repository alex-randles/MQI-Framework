import requests
version_1_file = "https://raw.githubusercontent.com/kg-construct/rml-test-cases/master/test-cases/RMLTC0001a-JSON/student.json"
json_1 = requests.get(version_1_file).json()
version_2_file = "https://raw.githubusercontent.com/kg-construct/rml-test-cases/master/test-cases/RMLTC0009a-JSON/student.json"
json_2 = requests.get(version_2_file).json()


import jsondiff as jd
from jsondiff import diff
# print(json_1)
# print(json_2)
diff_result = diff(json_1, json_2)

for result in diff_result:
    for change_type in (diff_result.get(result)):
        current_result = diff_result.get(result).get(change_type)
        if isinstance(current_result, list):
            for entry in current_result:
                changed_values = entry[1]
                print(change_type, changed_values)
        else:
            for key, values in current_result.items():
                print(result)
                pass