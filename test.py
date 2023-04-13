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