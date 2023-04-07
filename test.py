from collections import defaultdict
dic = {'added': [{'EMPLOYEE_ID': '198', 'LAST_NAME': 'OConnell', 'EMAIL': 'DOCONNEL', 'PHONE_NUMBER': '650.507.9833', 'HIRE_DATE': '21-JUN-07', 'JOB_ID': 'SH_CLERK', 'SALARY': '2600', 'COMMISSION_PCT': ' - ', 'MANAGER_ID': '124', 'DEPARTMENT_ID': '50'}, {'EMPLOYEE_ID': '199', 'LAST_NAME': 'Grant', 'EMAIL': 'DGRANT', 'PHONE_NUMBER': '650.507.9844', 'HIRE_DATE': '13-JAN-08', 'JOB_ID': 'SH_CLERK', 'SALARY': '2600', 'COMMISSION_PCT': ' - ', 'MANAGER_ID': '124', 'DEPARTMENT_ID': '50'}, {'EMPLOYEE_ID': '200', 'LAST_NAME': 'Whalen', 'EMAIL': 'JWHALEN', 'PHONE_NUMBER': '515.123.4444', 'HIRE_DATE': '17-SEP-03', 'JOB_ID': 'AD_ASST', 'SALARY': '4400', 'COMMISSION_PCT': ' - ', 'MANAGER_ID': '101', 'DEPARTMENT_ID': '10'}, {'EMPLOYEE_ID': '201', 'LAST_NAME': 'Hartstein', 'EMAIL': 'MHARTSTE', 'PHONE_NUMBER': '515.123.5555', 'HIRE_DATE': '17-FEB-04', 'JOB_ID': 'MK_MAN', 'SALARY': '13000', 'COMMISSION_PCT': ' - ', 'MANAGER_ID': '100', 'DEPARTMENT_ID': '20'}, {'EMPLOYEE_ID': '202', 'LAST_NAME': 'Fay', 'EMAIL': 'PFAY', 'PHONE_NUMBER': '603.123.6666', 'HIRE_DATE': '17-AUG-05', 'JOB_ID': 'MK_REP', 'SALARY': '6000', 'COMMISSION_PCT': ' - ', 'MANAGER_ID': '201', 'DEPARTMENT_ID': '20'}, {'EMPLOYEE_ID': '203', 'LAST_NAME': 'Mavris', 'EMAIL': 'SMAVRIS', 'PHONE_NUMBER': '515.123.7777', 'HIRE_DATE': '07-JUN-02', 'JOB_ID': 'HR_REP', 'SALARY': '6500', 'COMMISSION_PCT': ' - ', 'MANAGER_ID': '101', 'DEPARTMENT_ID': '40'}, {'EMPLOYEE_ID': '204', 'LAST_NAME': 'Baer', 'EMAIL': 'HBAER', 'PHONE_NUMBER': '515.123.8888', 'HIRE_DATE': '07-JUN-02', 'JOB_ID': 'PR_REP', 'SALARY': '10000', 'COMMISSION_PCT': ' - ', 'MANAGER_ID': '101', 'DEPARTMENT_ID': '70'}, {'EMPLOYEE_ID': '205', 'LAST_NAME': 'Higgins', 'EMAIL': 'SHIGGINS', 'PHONE_NUMBER': '515.123.8080', 'HIRE_DATE': '07-JUN-02', 'JOB_ID': 'AC_MGR', 'SALARY': '12008', 'COMMISSION_PCT': ' - ', 'MANAGER_ID': '101', 'DEPARTMENT_ID': '110'}, {'EMPLOYEE_ID': '206', 'LAST_NAME': 'Gietz', 'EMAIL': 'WGIETZ', 'PHONE_NUMBER': '515.123.8181', 'HIRE_DATE': '07-JUN-02', 'JOB_ID': 'AC_ACCOUNT', 'SALARY': '8300', 'COMMISSION_PCT': ' - ', 'MANAGER_ID': '205', 'DEPARTMENT_ID': '110'}, {'EMPLOYEE_ID': '100', 'LAST_NAME': 'King', 'EMAIL': 'SKING', 'PHONE_NUMBER': '515.123.4567', 'HIRE_DATE': '17-JUN-03', 'JOB_ID': 'AD_PRES', 'SALARY': '24000', 'COMMISSION_PCT': ' - ', 'MANAGER_ID': ' - ', 'DEPARTMENT_ID': '90'}, {'EMPLOYEE_ID': '101', 'LAST_NAME': 'Kochhar', 'EMAIL': 'NKOCHHAR', 'PHONE_NUMBER': '515.123.4568', 'HIRE_DATE': '21-SEP-05', 'JOB_ID': 'AD_VP', 'SALARY': '17000', 'COMMISSION_PCT': ' - ', 'MANAGER_ID': '100', 'DEPARTMENT_ID': '90'}, {'EMPLOYEE_ID': '102', 'LAST_NAME': 'De Haan', 'EMAIL': 'LDEHAAN', 'PHONE_NUMBER': '515.123.4569', 'HIRE_DATE': '13-JAN-01', 'JOB_ID': 'AD_VP', 'SALARY': '17000', 'COMMISSION_PCT': ' - ', 'MANAGER_ID': '100', 'DEPARTMENT_ID': '90'}, {'EMPLOYEE_ID': '103', 'LAST_NAME': 'Hunold', 'EMAIL': 'AHUNOLD', 'PHONE_NUMBER': '590.423.4567', 'HIRE_DATE': '03-JAN-06', 'JOB_ID': 'IT_PROG', 'SALARY': '9000', 'COMMISSION_PCT': ' - ', 'MANAGER_ID': '102', 'DEPARTMENT_ID': '60'}, {'EMPLOYEE_ID': '104', 'LAST_NAME': 'Ernst', 'EMAIL': 'BERNST', 'PHONE_NUMBER': '590.423.4568', 'HIRE_DATE': '21-MAY-07', 'JOB_ID': 'IT_PROG', 'SALARY': '6000', 'COMMISSION_PCT': ' - ', 'MANAGER_ID': '103', 'DEPARTMENT_ID': '60'}, {'EMPLOYEE_ID': '105', 'LAST_NAME': 'Austin', 'EMAIL': 'DAUSTIN', 'PHONE_NUMBER': '590.423.4569', 'HIRE_DATE': '25-JUN-05', 'JOB_ID': 'IT_PROG', 'SALARY': '4800', 'COMMISSION_PCT': ' - ', 'MANAGER_ID': '103', 'DEPARTMENT_ID': '60'}], 'removed': [{'EMPLOYEE_ID': '198', 'FIRST_NAME': 'Donald', 'LAST_NAME': 'OConnell', 'EMAIL': 'DOCONNEL', 'PHONE_NUMBER': '650.507.9833', 'HIRE_DATE': '21-JUN-07', 'JOB_ID': 'SH_CLERK', 'SALARY': '2600', 'COMMISSION_PCT': ' - ', 'MANAGER_ID': '124', 'DEPARTMENT_ID': '50'}, {'EMPLOYEE_ID': '199', 'FIRST_NAME': 'Douglas', 'LAST_NAME': 'Grant', 'EMAIL': 'DGRANT', 'PHONE_NUMBER': '650.507.9844', 'HIRE_DATE': '13-JAN-08', 'JOB_ID': 'SH_CLERK', 'SALARY': '2600', 'COMMISSION_PCT': ' - ', 'MANAGER_ID': '124', 'DEPARTMENT_ID': '50'}, {'EMPLOYEE_ID': '200', 'FIRST_NAME': 'Jennifer', 'LAST_NAME': 'Whalen', 'EMAIL': 'JWHALEN', 'PHONE_NUMBER': '515.123.4444', 'HIRE_DATE': '17-SEP-03', 'JOB_ID': 'AD_ASST', 'SALARY': '4400', 'COMMISSION_PCT': ' - ', 'MANAGER_ID': '101', 'DEPARTMENT_ID': '10'}, {'EMPLOYEE_ID': '201', 'FIRST_NAME': 'Michael', 'LAST_NAME': 'Hartstein', 'EMAIL': 'MHARTSTE', 'PHONE_NUMBER': '515.123.5555', 'HIRE_DATE': '17-FEB-04', 'JOB_ID': 'MK_MAN', 'SALARY': '13000', 'COMMISSION_PCT': ' - ', 'MANAGER_ID': '100', 'DEPARTMENT_ID': '20'}, {}], 'changed': [], 'columns_added': [], 'columns_removed': ['FIRST_NAME']}


csv_file = "/home/alex/Desktop/Change-Detection-System-Examples/version_1_files/employee.csv"
import csv

import csv
def fitem(item):
    item=item.strip()
    try:
        item=float(item)
    except ValueError:
        pass
    return item

with open(csv_file, 'r') as csvin:
    reader=csv.DictReader(csvin)
    data={k.strip():[fitem(v)] for k,v in next(reader).items()}
    for line in reader:
        for k,v in line.items():
            k=k.strip()
            data[k].append(fitem(v))

csv_tuples = []
for k,v in data.items():
    for value in v:
        csv_tuples.append((k,value))


def format_csv_changes(csv_diff):
    output_changes = defaultdict(dict)
    output_changes["insert"] = defaultdict(dict)
    output_changes["delete"] = defaultdict(dict)
    change_id = 0
    # process output from csv diff library
    for change_type, related_changes in csv_diff.items():
        for changes in related_changes:
            if isinstance(changes, dict):
                for data_reference, change_reason in changes.items():
                    if (data_reference, change_reason) not in csv_tuples:
                        # print("delete", data_reference, change_reason)
                        if change_type == "added":
                            output_changes["insert"][change_id] = {
                                "data_reference": data_reference,
                                "change_reason": change_reason
                            }
                        else:
                            output_changes["delete"][change_id] = {
                                "data_reference": data_reference,
                                "change_reason": change_reason
                            }
                        change_id += 1
                    else:
                        pass
                        # print("delete", data_reference, change_reason)
            else:
                if isinstance(changes, str):
                    structural_reference = "Columns"
                    if change_type == "columns_added":
                        output_changes["insert"][change_id] = {
                            "structural_reference": structural_reference,
                            "change_reason": changes,
                        }
                    else:
                        output_changes["delete"][change_id] = {
                            "structural": structural_reference,
                            "change_reason": changes,
                        }
                    change_id += 1

format_csv_changes(dic)