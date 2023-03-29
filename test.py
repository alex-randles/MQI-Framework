from modules.detect_changes import  *

csv_file_1 = "https://raw.githubusercontent.com/kg-construct/" \
             "rml-test-cases/master/test-cases/RMLTC0002a-CSV/student.csv"
csv_file_2 = "https://raw.githubusercontent.com/kg-construct/" \
             "rml-test-cases/master/test-cases/RMLTC0009a-CSV/student.csv"
form_details = {
    'CSV_URL_1': "https://raw.githubusercontent.com/kg-construct/rml-test-cases/master/test-cases/RMLTC0002a-CSV/student.csv",
    'CSV_URL_2': "https://raw.githubusercontent.com/alex-randles/Change-Detection-System-Examples/main/manipulated_file/student-v2.csv",
    'insert-threshold': '10', 'delete-threshold': '0',
    'move-threshold': '5555', 'datatype-threshold': '0',
    'merge-threshold': '47474747', 'update-threshold': '0',
    'detection-end': '2022-07-10',
    'email-address': 'alexrandles0@gmail.com',
    "user-id": "2",
}
cd = DetectChanges(user_id=2, form_details=form_details)