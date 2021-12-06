import datetime
from flask import Flask, json, request, jsonify, make_response
from flask_mysqldb import MySQLdb, MySQL
from functools import wraps
import jwt

app = Flask(__name__)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'mydb'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)

app.config['SECRET_KEY'] = "secretkey"

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.args.get('token')
        if not token:
            return jsonify({'message':'Token is missing!'}), 403
        try:
            data = jwt.decode(token, app.config["SECRET_KEY"])
        except:
            return jsonify({'message':'Token is invalid'}), 403
        return f(*args, **kwargs)
    return decorated
# @app.route("/login", methods=['POST'])
# def login():
#     data = request.get_json()
#     print("\n\nDATI:\n" + str(data))
#     cod_fiscale = data["cod_fiscale"]
#     password = data["password"]
#     print("\n COD_FISCALE: " + cod_fiscale + "\nPASSWORD: " + password)
#     cursor = mysql.connection.cursor()
#     query = "SELECT * FROM mydb.user AS U WHERE U.cod_fiscale='" + cod_fiscale + "';"
#     print(query)
#     cursor.execute(query)
#     row = json.dumps(cursor.fetchone())
#     if row:
#         resp = "data:" + row
#         resp+=(", status: 200")
#         cursor.close()
#         print(json.dumps(resp))
#         return resp
#     else:
#         resp = jsonify('User with cod_fiscale=%s not found', cod_fiscale)
#         resp+=(", status: 500")
#         return resp
        
@app.route("/login", methods=['GET'])
def login():
    cod_fiscale = request.args.get("cod_fiscale")
    password = request.args.get("password")
    print("\n COD_FISCALE: " + cod_fiscale + "\nPASSWORD: " + password)
    cursor = mysql.connection.cursor()
    query = "SELECT * FROM mydb.user AS U WHERE U.cod_fiscale='" + cod_fiscale + "';"
    print(query)
    cursor.execute(query)
    row = cursor.fetchone()
    print(row)
    if row:
        token = jwt.encode({'cod_fiscale' : cod_fiscale}, app.config['SECRET_KEY'], algorithm="HS256")
        print(jwt.decode(token, app.config["SECRET_KEY"]))
        resp = {}
        resp["role"] =  row['role']
        resp["token"] = token.decode('utf-8')
        cursor.close()
        print(json.dumps(resp))
        return resp
    else:
        resp = jsonify('User with cod_fiscale=%s not found', cod_fiscale)
        return resp


@app.route("/")
def prova():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM mydb.user")
    row = cur.fetchone()
    print(json.dumps(row))
    return json.dumps(row)

@app.route("/prova")
def index():
    return "ciao"


@app.route("/f/prova")
@token_required
def prova_familiare():
    return jsonify({'message':'Solo coloro che hanno il token possono visualizzare il messaggio'})