import datetime
from flask import Flask, json, request, jsonify, make_response
from functools import wraps
import jwt
import psycopg2

# LEGENDA
# RUOLI:
#       2 - ADMIN (DOTTORE SPECIALE)
#        1 - PAZIENTE
#         2 - DOTTORE
#          3 - VOLONTARIO
#           4 - FAMILIARE


app = Flask(__name__)

db = psycopg2.connect(dbname='mydb', user='postgres', host='localhost', password='root')


def get_role(x):
    if x==1:
        user='paziente'
    elif x==2:
        user='dottore'
    elif x==3:
        user='volontario'
    elif x==4:
        user='familiare'
    return user

# Token Check
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


# Controllo accesso utente
@app.route("/login", methods=['POST'])
def login():
    data = request.get_json()
    print("\n\nDATI:\n" + str(data))
    cod_fiscale = data["cod_fiscale"]
    password = data["password"]
    print("\n COD_FISCALE: " + cod_fiscale + "\nPASSWORD: " + password)
    cursor = db.cursor()
    query = "SELECT * FROM public.paziente, public.dottore, public.familiare, public.volontario WHERE cod_fiscale='" + cod_fiscale + "' AND password='" + password + "';"
    print(query)
    cursor.execute(query)
    row = cursor.fetchone()
    if row:
        token = jwt.encode({'cod_fiscale' : cod_fiscale}, app.config['SECRET_KEY'], algorithm="HS256")
        print(jwt.decode(token, app.config["SECRET_KEY"]))
        resp = {}
        resp["role"] =  row['role']
        resp["token"] = token.decode('utf-8')
        resp["cod_fiscale"] = row['cod_fiscale']
        cursor.close()
        print(json.dumps(resp))
        return resp
    else:
        resp = jsonify('User with cod_fiscale=%s not found', cod_fiscale)
        return resp


#############################################################
#                                                           #
#                          ADMIN                            #
#                                                           #
#############################################################


# Restituisce la lista degli utenti associati al ruolo passato. 
# Importante passare il ruolo giusto per costruire la query corretta.
# PARAMETRI DA PASSARE: - role
@app.route("/admin/lista_attori", methods = ['POST'])
#@token_required
def getlista():
    data = request.get_json()
    user = get_role(data['role'])
    cursor = db.cursor()
    query = "SELECT cod_fiscale, nome, cognome FROM public." + user + ";"
    print(query)
    cursor.execute(query)
    rows = cursor.fetchall()
    if rows:
        resp = json.dumps(rows)
        cursor.close()
        return resp
    else:
        resp = jsonify("No user found with role " + str(data['role']))
        return resp

# Restituisce dati profilo
# PARAMETRI DA PASSARE: - role, - cod_fiscale
@app.route("/admin/dati_profilo", methods = ['POST'])
#@token_required
def getprofilo():
    data = request.get_json()
    user = get_role(data['role'])
    cursor = db.cursor()
    query = "SELECT * FROM public." + user + " WHERE cod_fiscale='" + data['cod_fiscale'] + "';"
    print(query)
    cursor.execute(query)
    rows = cursor.fetchall()
    if rows:
        resp = json.dumps(rows)
        cursor.close()
        return resp
    else:
        resp = jsonify('No user found with cod_fiscale ' + data['cod_fiscale'])
        return resp


# Crea utente. Importante passare il ruolo giusto per costruire la query corretta
@app.route("/admin/crea_utente", methods = ['POST'])
#@token_required
def create_user():
    data = request.get_json()
    cursor = db.cursor()
    print("\n")
    print(data)
    print("\n")
    if data['role']==1: #PAZIENTE [1]
        query = "INSERT INTO public.paziente (cod_fiscale, password, role, nome, cognome, num_cellulare, email, tipologia_chat) VALUES ('" 
        query+= data["cod_fiscale"] + "', 'admin', " + str(1) + ", '" + data["nome"] + "', '" + data["cognome"] + "', " 
        query+= str(data["num_cellulare"]) + ", '" + data["email"] + "', " + str(data["tipologia_chat"]) + ");"
    elif data['role']==2: #DOTTORE [2]
        query = "INSERT INTO public.dottore (cod_fiscale, password, role, nome, cognome, num_cellulare, email, specializzazione) VALUES ('" 
        query+= data["cod_fiscale"] + "', 'admin', " + str(2) + ", '" + data["nome"] + "', '" + data["cognome"] + "', " 
        query+= str(data["num_cellulare"]) + ", '" + data["email"] + "', '" + data["specializzazione"] + "');"
    elif data['role']==3: #VOLONTARIO [3]
        query = "INSERT INTO public.volontario (cod_fiscale, password, role, nome, cognome, num_cellulare, email, ammonizioni) VALUES ('" 
        query+= data["cod_fiscale"] + "', 'admin', " + str(3) + ", '" + data["nome"] + "', '" + data["cognome"] + "', " 
        query+= str(data["num_cellulare"]) + ", '" + data["email"] + "', " + str(0) + ");"
    elif data['role']==4: #FAMILIARE [4]
        query = "INSERT INTO public.familiare (cod_fiscale, password, role, nome, cognome, num_cellulare, email) VALUES ('" 
        query+= data["cod_fiscale"] + "', 'admin', " + str(4) + ", '" + data["nome"] + "', '" + data["cognome"] + "', " 
        query+= str(data["num_cellulare"]) + ", '" + data["email"] + "');"
    print("\n")    

    print(query)

    try:
        cursor.execute(query)
        db.commit()
        status = jsonify('User inserted')
    except psycopg2.IntegrityError as e:
        status = jsonify('Error: User not inserted - ', str(e))
    finally:
        cursor.close()
    return status
    
# Elimina utente. Importante passare codice fiscale e role giusti per costruire la query corretta
# PARAMETRI DA PASSARE: - role, - cod_fiscale
@app.route("/admin/elimina_utente", methods = ['POST'])
#@token_required
def delete_user():
    data = request.get_json()
    cursor = db.cursor()

    user = get_role(data['role'])

    try:
        cursor.execute("DELETE FROM public." + user + " WHERE cod_fiscale='" + data["cod_fiscale"] + "';")
        db.commit()
        status = jsonify('User deleted')
    except psycopg2.IntegrityError as e:
        status = jsonify('Error: User not deleted - ', str(e))
    finally:
        cursor.close()
    return status

# Modifica utente. Importante passare il ruolo giusto per costruire la query corretta
# PARAMETRI DA PASSARE: - role, - cod_fiscale, - num_cellulare, - email, ?- tipologia_chat
@app.route("/admin/modifica_utente", methods = ['POST'])
#@token_required
def update_user():
    data = request.get_json()
    cursor = db.cursor()
    user = get_role(data['role'])
    print("\n")
    print(data)
    print("\n")

    query = "UPDATE public." + user + " SET num_cellulare=" + str(data["num_cellulare"]) + ", email='" + data["email"] + "'"  

    if data['role']==1: #PAZIENTE [1]
        query += ", tipologia_chat=" + str(data["tipologia_chat"]) 
    
    query += " WHERE cod_fiscale='" + data['cod_fiscale'] + "';"
    
    print("\n")    

    print(query)

    try:
        cursor.execute(query)
        db.commit()
        status = jsonify('User updated')
    except psycopg2.IntegrityError as e:
        status = jsonify('Error: User not updated - ', str(e))
    finally:
        cursor.close()
    return status

# Associa familiari/volontari/dottori a pazienti e non il contrario: che
# senso ha dare la possibilità di associare ambo i lati? Lato paziente
# ci sarà solo la visualizzazione dei familiari/dottori associati
# PARAMETRI DA PASSARE: - role(NON DEL PAZIENTE), - user_cod_fiscale(NON DEL PAZIENTE), - paziente_cod_fiscale
@app.route("/admin/associa_attore", methods = ['POST'])
#@token_required
def associa_attore():
    data = request.get_json()
    cursor = db.cursor()
    user = get_role(data['role'])
    user_cod_fiscale = user + "_cod_fiscale"
    query = "INSERT INTO public." + user + "_paziente (paziente_cod_fiscale, " + user + "_cod_fiscale) "
    query += "VALUES ('" + data['paziente_cod_fiscale'] + "', '" + data[user_cod_fiscale] + "');"

    print(query)

    try:
        cursor.execute(query)
        db.commit()
        status = jsonify('User associated')
    except psycopg2.IntegrityError as e:
        status = jsonify('Error: User not associated - ', str(e))
    finally:
        cursor.close()
    return status
    
# Rimuovi associazione attore_paziente
# PARAMETRI DA PASSARE: - role(NON DEL PAZIENTE), - user_cod_fiscale(NON DEL PAZIENTE), - paziente_cod_fiscale
@app.route("/admin/rimuovi_associazione", methods = ['POST'])
#@token_required
def rimuovi_associazione():
    data = request.get_json()
    cursor = db.cursor()
    user = get_role(data['role'])
    user_cod_fiscale = user + "_cod_fiscale"



    query = "DELETE FROM public." + user + "_paziente WHERE " + user + "_cod_fiscale='" + data[user_cod_fiscale]
    query += "' AND paziente_cod_fiscale='" + data['paziente_cod_fiscale'] + "';"

    print(query)

    try:
        cursor.execute(query)
        db.commit()
        status = jsonify('Association deleted')
    except psycopg2.IntegrityError as e:
        status = jsonify('Error: Association not deleted - ', str(e))
    finally:
        cursor.close()
    return status



# Restituisce gli attori associati ad una figura:
# - Pazienti: Resituisce Familiari e Dottori associati
# - Dottori/Familiari/Volontari : Restituisce Pazienti associati
# PARAMETRI DA PASSARE: - role, - paziente_cod_fiscale
@app.route("/admin/attori_associati", methods=['POST'])
#@token_required
def get_actors():
    data = request.get_json()
    cursor = db.cursor()
    user = get_role(data['role'])
    if data['role']==1:
        try:
            query_fam = "SELECT f.cod_fiscale, f.nome, f.cognome FROM public.familiare_paziente as fp, public.familiare as f "
            query_fam += "WHERE paziente_cod_fiscale='" + data['paziente_cod_fiscale'] + "' AND fp.familiare_cod_fiscale = f.cod_fiscale"
            cursor.execute(query_fam)
            print(query_fam + "\n")

            resp = { "familiari" : cursor.fetchall() }
            
            query_dot = "SELECT d.cod_fiscale, d.nome, d.cognome FROM public.dottore_paziente as dp, public.dottore as d "
            query_dot += "WHERE paziente_cod_fiscale='" + data['paziente_cod_fiscale'] + "' AND dp.dottore_cod_fiscale = d.cod_fiscale"
            cursor.execute(query_dot)
            
            resp.update({ "dottori": cursor.fetchall()})

            
        except psycopg2.IntegrityError as e:
            resp = jsonify('Error: Select not done - ', str(e))
        finally:
            cursor.close()
            return resp
    else:
        try:
            query = "SELECT u.cod_fiscale, u.nome, u.cognome FROM public." + user + "_paziente as up, public." + user + "as u "
            query += "WHERE paziente_cod_fiscale='" + data['paziente_cod_fiscale'] + "' AND up." + user + "_cod_fiscale = u.cod_fiscale"
            cursor.execute(query)
            print(query + "\n")
            resp = cursor.fetchall()

        except psycopg2.IntegrityError as e:
            resp = jsonify('Error: Select not done - ', str(e))

        finally:
            cursor.close()
            return resp




# @app.route("/")
# def prova():
#     cursor = db.cursor()
#     cursor.execute("SELECT * FROM public.paziente")
#     rows = cursor.fetchall()
#     print(rows)
#     return json.dumps(rows)

