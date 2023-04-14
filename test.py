from xmldiff import main, formatting
import xml.etree.ElementTree as ET
from collections import defaultdict

import requests
version_1 = "https://raw.githubusercontent.com/kg-construct/rml-test-cases/master/test-cases/RMLTC0001a-XML/student.xml"
version_2 = "https://raw.githubusercontent.com/kg-construct/rml-test-cases/master/test-cases/RMLTC0009a-XML/student.xml"
version_1 = "https://raw.githubusercontent.com/alex-randles/Change-Detection-System-Examples/main/version_1_files/student.xml"
version_2 = "https://raw.githubusercontent.com/alex-randles/Change-Detection-System-Examples/main/version_2_files/student.xml"
version_1 = requests.get(version_1).text
version_2 = requests.get(version_2).text
def detect_xml_changes(version_1, version_2):
    # detect differences between XML file versions
    diff = main.diff_texts(
        version_1,
        version_2,
        formatter=formatting.XMLFormatter())
    # output difference to XML file
    diff_text = open("diff.xml", "w+")
    diff_text.write(diff)
    diff_text.close()
    format_XML_changes()

def format_XML_changes():
    tree = ET.parse("diff.xml")
    root = tree.getroot()
    # print(ET.tostring(tree, encoding='unicode'))
    # exit()
    insert_tag = "{http://namespaces.shoobx.com/diff}insert"
    result = ""
    results = defaultdict(list)
    # print([elem.text for elem in root.iter() if elem.tag == "ID"])
    # print([elem.text for elem in root.iter() if elem.tag == "Sport"])
    # print([elem.text for elem in root.iter() if elem.tag == "Name"])
    # exit()
    excluded_tags = ["{http://namespaces.shoobx.com/diff}insert", "{http://namespaces.shoobx.com/diff}delete"]
    for elem in tree.iter():
         print(elem.tag, elem.text)


detect_xml_changes(version_1, version_2)























exit()
import MySQLdb


# Open database connection ( If database is not created don't give dbname)
db = MySQLdb.connect("localhost","root","", "test" )

# prepare a cursor object using cursor() method
cursor = db.cursor()

# For creating create db
# Below line  is hide your warning
# create db here....
cursor.execute("create database IF NOT EXISTS test")

cursor.execute("create table IF NOT EXISTS people (ID varchar(70),FNAME varchar(20));")



from flask import Flask, render_template, request
from flask_mysqldb import MySQL

app = Flask(__name__)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'test'

mysql = MySQL(app)


@app.route('/form')
def form():
    return render_template('form.html')


@app.route('/', methods=['POST', 'GET'])
def login():
    if request.method == 'GET':
        name = "request.form['name']"
        age = "request.form['age']"
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO people VALUES ('1', '2')")
        mysql.connection.commit()
        cursor.close()
        return f"Done!!"


app.run(host='localhost', port=5000)