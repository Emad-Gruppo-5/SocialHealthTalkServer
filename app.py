import base64
import datetime
import uuid
from flask import Flask, json, request, jsonify, make_response
from functools import wraps
import jwt
import psycopg2
import smtplib

# LEGENDA
# RUOLI:
#       2 - ADMIN (DOTTORE SPECIALE)
#        1 - PAZIENTE
#         2 - DOTTORE
#          3 - VOLONTARIO
#           4 - FAMILIARE


gmail_user = 'socialhealthtalkbot@gmail.com'
gmail_password = 'gruppoemad5'

app = Flask(__name__)

db = psycopg2.connect(dbname='mydb', user='postgres', host='localhost', password='root')
app.config["SECRET_KEY"] = "secretkey"

def get_role(x):
    if x==1:
        user='paziente'
    elif x==2:
        user='dottore'
    elif x==3:
        user='volontario'
    elif x==4:
        user='familiare'
    else:
        user = 'no role'
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
    
    role=1
    row=None
    print("\n\nDATI:\n" + str(data))
    cod_fiscale = data["cod_fiscale"]
    password = data["password"]
    print("\n COD_FISCALE: " + cod_fiscale + "\nPASSWORD: " + password)
    cursor = db.cursor()

    while not row:
        user = get_role(role)
        query = "SELECT * FROM public." + user + " WHERE cod_fiscale='" + cod_fiscale + "' AND password='" + password + "';"
        print(query)
        cursor.execute(query)
        row = cursor.fetchone()
        print("\nROW:\n",row)
        role+=1
        if row:
            token = jwt.encode({'cod_fiscale' : cod_fiscale}, app.config['SECRET_KEY'], algorithm="HS256")
            print(jwt.decode(token, app.config["SECRET_KEY"]))
            resp = {}
            resp["cod_fiscale"] = row[0]
            resp["role"] =  row[2]
            resp["nome"] = row[3]
            resp["cognome"] = row[4]
            resp["num_cellulare"] = row[5]
            resp["email"] = row[6]
            if row[2] == 1:
                resp["tipologia_chat"] = row[7]
            elif row[2] == 2:
                resp["specializzazione"] = row[7]
            resp["token"] = token.decode('utf-8')
            cursor.close()
            print(json.dumps(resp))
            return make_response(resp, 200)
        elif role==5:
            resp = jsonify('User with cod_fiscale=' + cod_fiscale + ' not found')
            cursor.close()
            return make_response(resp, 500)


#############################################################
#                                                           #
#                          ADMIN                            #
#                                                           #
#############################################################


# Restituisce la lista degli utenti associati al ruolo passato. 
# Importante passare il ruolo giusto per costruire la query corretta.
# PARAMETRI DA PASSARE: - role
@app.route("/lista_attori", methods = ['POST'])
#@token_required
def getlista():
    data = request.get_json()
    user = get_role(data['role'])
    if user == 'no role':
        resp = jsonify("role " + str(data['role']) + " doesn't exist")
        return resp
    cursor = db.cursor()
    query = "SELECT cod_fiscale, nome, cognome FROM public." + user + ";"
    print(query)
    cursor.execute(query)
    rows = cursor.fetchall()
    if rows:
        resp = []
        for row in rows:
            resp.append({"cod_fiscale":row[0], "nome":row[1], "cognome":row[2]})
        cursor.close()
        return json.dumps(resp)
    else:
        resp = jsonify("No user found with role " + str(data['role']))
        return resp

# Restituisce dati profilo
# PARAMETRI DA PASSARE: - role, - cod_fiscale
@app.route("/dati_profilo", methods = ['POST'])
#@token_required
def getprofilo():
    data = request.get_json()
    user = get_role(data['role'])
    cursor = db.cursor()
    query = "SELECT * FROM public." + user + " WHERE cod_fiscale='" + data['cod_fiscale'] + "';"
    print(query)
    cursor.execute(query)
    rows = cursor.fetchone()
    if rows:
        resp = { "cod_fiscale": rows[0], "role": str(rows[2]), "nome": rows[3], "cognome":rows[4], "num_cellulare": str(rows[5]), "email":rows[6]}
        if data['role']==1:
            resp["tipologia_chat"] = rows[7]
            resp["eta"] = rows[8]
            resp["note"] = rows[9]
            resp["sesso"] = rows[10]
            resp["titolo_studio"] = rows[11]
        elif data['role']==2:
            resp["specializzazione"] = rows[7]
        elif data['role']==3:
            resp["ammonizioni"] = rows[7]
        cursor.close()
        return resp
    else:
        resp = jsonify('No user found with cod_fiscale ' + data['cod_fiscale'])
        return resp


# Crea utente. Importante passare il ruolo giusto per costruire la query corretta
@app.route("/crea_utente", methods = ['POST'])
#@token_required
def create_user():
    data = request.get_json()
    cursor = db.cursor()
    print("\n")
    print(data)
    print("\n")
    if data['role'] == 1: #PAZIENTE [1]
        query = "INSERT INTO public.paziente (cod_fiscale, password, role, nome, cognome, num_cellulare, email, tipologia_chat, eta, sesso, titolo_studio) VALUES ('" 
        query += data["cod_fiscale"] + "', 'admin', " + str(1) + ", '" + data["nome"] + "', '" + data["cognome"] + "', " 
        query += str(data["num_cellulare"]) + ", '" + data["email"] + "', " + str(data["tipologia_chat"]) + ", '" + str(data["eta"]) + "', '" + str(data["sesso"]) + "', '" + str(data["titolo_studio"]) + "');"
    elif data['role'] == 2: #DOTTORE [2]
        query = "INSERT INTO public.dottore (cod_fiscale, password, role, nome, cognome, num_cellulare, email, specializzazione) VALUES ('" 
        query += data["cod_fiscale"] + "', 'admin', " + str(2) + ", '" + data["nome"] + "', '" + data["cognome"] + "', " 
        query += str(data["num_cellulare"]) + ", '" + data["email"] + "', '" + data["specializzazione"] + "');"
    elif data['role'] == 3: #VOLONTARIO [3]
        query = "INSERT INTO public.volontario (cod_fiscale, password, role, nome, cognome, num_cellulare, email, ammonizioni) VALUES ('" 
        query += data["cod_fiscale"] + "', 'admin', " + str(3) + ", '" + data["nome"] + "', '" + data["cognome"] + "', " 
        query += str(data["num_cellulare"]) + ", '" + data["email"] + "', " + str(0) + ");"
    elif data['role'] == 4: #FAMILIARE [4]
        query = "INSERT INTO public.familiare (cod_fiscale, password, role, nome, cognome, num_cellulare, email) VALUES ('" 
        query += data["cod_fiscale"] + "', 'admin', " + str(4) + ", '" + data["nome"] + "', '" + data["cognome"] + "', " 
        query += str(data["num_cellulare"]) + ", '" + data["email"] + "');"  

    print(query)

    try:
        cursor.execute(query)
        db.commit()
        status = jsonify({"statusCode" : 200, "body": 'User inserted'})
    except psycopg2.errors.UniqueViolation as e:
        status = jsonify({"statusCode" : 500, "body" : 'Error: User not inserted - ' + str(e)})
    finally:
        cursor.close()
    return status
    
# Elimina utente. Importante passare codice fiscale e role giusti per costruire la query corretta
# PARAMETRI DA PASSARE: - role, - cod_fiscale
@app.route("/elimina_utente", methods = ['POST'])
#@token_required
def delete_user():
    data = request.get_json()
    cursor = db.cursor()

    user = get_role(data['role'])

    try:
        cursor.execute("DELETE FROM public." + user + " WHERE cod_fiscale='" + data["cod_fiscale"] + "';")
        db.commit()
        status = jsonify({"statusCode" : 200, "body": 'User deleted'})
    except psycopg2.IntegrityError as e:
        status = jsonify({"statusCode" : 500, "body" : 'Error: User not deleted - ' + str(e)})
    finally:
        cursor.close()
    return status

# Modifica utente. Importante passare il ruolo giusto per costruire la query corretta
# PARAMETRI DA PASSARE: - role, - cod_fiscale, - num_cellulare, - email, ?- tipologia_chat
@app.route("/modifica_utente", methods = ['POST'])
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
@app.route("/associa_attore", methods = ['POST'])
#@token_required
def associa_attore():
    data = request.get_json()
    cursor = db.cursor()
    
    user = get_role(int(data['role']))
    query = "INSERT INTO public." + user + "_paziente (paziente_cod_fiscale, " + user + "_cod_fiscale) "
    query += "VALUES ('" + data['paziente_cod_fiscale'] + "', '" + data["user_cod_fiscale"] + "');"

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
@app.route("/rimuovi_associazione", methods = ['POST'])
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



# Recupera la lista delle domande fatte da un dottore ad un paziente
# in una certa data
# PARAMETRI DA PASSARE: - data, - cod_fiscale_paziente, - cod_fiscale_dottore
@app.route("/lista_domande", methods = ['GET'])
#@token_required
def getlistaDomande():
   data = request.get_json()
   cursor = db.cursor()
   query = "SELECT id_domanda, testo_domanda, testo_risposta, file_risposta, data_risposta FROM public.storico_domande"
   query += " WHERE cod_fiscale_paziente='" + data['cod_fiscale_paziente'] + "' AND cod_fiscale_dottore='" + data['cod_fiscale_dottore'];
   query += "' AND data_domanda='" + data['data_domanda'] + "' ;"
   print(query)
   cursor.execute(query)
   rows = cursor.fetchall()
   if rows:
       jsonOb = {}
       resp = []
       for row in rows:
           print(row)
           resp.append({"id_domanda":row[0], "testo_domanda":row[1], "testo_risposta":row[2], "file_risposta":row[3], "data_risposta":row[4]})
           print(resp)
       cursor.close()
       return make_response(json.dumps(resp, default=str), 200)
   else:
       resp = make_response(jsonify("Nessuna domanda trovata per " + str(data['cod_fiscale_paziente'])), 500)
       return resp



# Invia una mail e un sms a tutti i familiari e dottori associati scelti
# PARAMETRI DA PASSARE: 
@app.route("/alert", methods = ['POST'])
#@token_required
def sendAlerts():
    data = request.get_json()
    print(data)
    to = [] # è possibile inserire in to ["email1", "email2", ..]
    for val in data:
        to.append(val["email"])
    print(to)
    subject = "ALERT"
    body = "ALERT ALERT ALERT\nFUNZIONA"
    email_text = """\
    From: %s
    To: %s
    Subject: %s

    %s
    """ % (gmail_user, ", ".join(to), subject, body)
    try:
        smtp_server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        smtp_server.ehlo()
        smtp_server.login(gmail_user, gmail_password)
        smtp_server.sendmail(gmail_user, to, email_text)
        smtp_server.close()
        return make_response("Email sent successfully!", 200)
    except Exception as ex:
        return make_response("Something went wrong: " + ex, 500)



# Restituisce gli attori associati ad una figura:
# - Pazienti: Resituisce Familiari e Dottori associati
# - Dottori/Familiari/Volontari : Restituisce Pazienti associati
# PARAMETRI DA PASSARE: - role, - paziente_cod_fiscale
@app.route("/attori_associati", methods=['POST'])
#@token_required
def get_actors():
    data = request.get_json()
    cursor = db.cursor()
    user = get_role(data['role'])
    resp = {}


    if data['role']==1:
        try:
            query_fam = "SELECT f.cod_fiscale, f.nome, f.cognome FROM public.familiare_paziente as fp, public.familiare as f "
            query_fam += "WHERE paziente_cod_fiscale='" + data['cod_fiscale'] + "' AND fp.familiare_cod_fiscale = f.cod_fiscale;"
            print(query_fam + "\n")
            cursor.execute(query_fam)
            familiari=[]
            for row in cursor.fetchall():
                familiari.append({"cod_fiscale":row[0], "nome":row[1], "cognome":row[2]})
                
            print(familiari)
            resp["familiari"] = familiari 
            
            query_dot = "SELECT d.cod_fiscale, d.nome, d.cognome FROM public.dottore_paziente as dp, public.dottore as d "
            query_dot += "WHERE paziente_cod_fiscale='" + data['cod_fiscale'] + "' AND dp.dottore_cod_fiscale = d.cod_fiscale;"
            print(query_dot + "\n")
            cursor.execute(query_dot)
            dottori=[]
            for row in cursor.fetchall():
                dottori.append({"cod_fiscale":row[0], "nome":row[1], "cognome":row[2]})
            resp["dottori"] = dottori
            print(resp)
            
        except psycopg2.IntegrityError as e:
            resp = jsonify('Error: Select not done - ', str(e))
        finally:
            cursor.close()
            return json.dumps(resp)
    else:
        try:
            query = "SELECT p.cod_fiscale, p.nome, p.cognome FROM public." + user + "_paziente as up, public.paziente as p "
            query += "WHERE up." + user + "_cod_fiscale='" + data['cod_fiscale'] + "' AND up.paziente_cod_fiscale=p.cod_fiscale;"
            cursor.execute(query)
            print(query + "\n")
            pazienti = []
            for row in cursor.fetchall():
                pazienti.append({ "cod_fiscale": row[0], "nome": row[1], "cognome": row[2]})
            resp["pazienti"] = pazienti
        except psycopg2.IntegrityError as e:
            resp = jsonify('Error: Select not done - ', str(e))

        finally:
            cursor.close()
            return resp


# Crea una visita.
@app.route("/dottore/crea_visita", methods=['POST'])
# @token_required
def create_visita():
    data = request.get_json()
    cursor = db.cursor()
    print("\n")
    print(data)
    print("\n")
    query = "INSERT INTO public.visite (\"id visita\", ora, notifica, data, cod_fiscale_doc, cod_fiscale_pat) VALUES ('"
    query += data["id"] + "', '" + data["ora"] + "', '" + data["notifica"] + "', '" + data["data"] + "', '" + data[
        "cfdottore"] + "', '" + data["cfpaziente"] + "');"

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


# Restituisce la lista delle visite associati al paziente.
# PARAMETRI DA PASSARE: - paziente_cod_fiscare
@app.route("/paziente/getvisite", methods=['POST'])
# @token_required
def getvisite():
    data = request.get_json()
    cursor = db.cursor()
    try:
        query_fam = "SELECT v.\"id visita\", v.nome, v.cognome FROM public.visita_paziente as vp, public.visita as v "
        query_fam += "WHERE paziente_cod_fiscale='" + data[
            'paziente_cod_fiscale'] + "' AND vp.\"id visita\" = v.\"id visita\""
        cursor.execute(query_fam)
        print(query_fam + "\n")

        resp = {"visite": cursor.fetchall()}

    except psycopg2.IntegrityError as e:
        resp = jsonify('Error: Select not done - ', str(e))
    finally:
        cursor.close()
        return resp

# Inserisce domanda (fatta dal dottore) e risposta (data dal paziente) nello storico_domande
# PARAMETRI DA PASSARE: testo_risposta, data_domanda, data_risposta, cod_fiscale_paziente, cod_fiscale_dottore
@app.route("/aggiungi_domanda", methods = ['POST'])
#@token_required
def create_question():
   data = request.get_json()
   cursor = db.cursor()
   print(data)
   print("\n")
 
   query = "INSERT INTO public.storico_domande (testo_domanda, testo_risposta, data_domanda, data_risposta, cod_fiscale_paziente, cod_fiscale_dottore, audio) VALUES ('"
   query+= data["testo_domanda"] + "', '" + data["testo_risposta"] + "', '" + data["data_domanda"] + "', '"
   query+= data["data_risposta"] + "', '" + data["cod_fiscale_paziente"] + "', '" + data["cod_fiscale_dottore"] + "', audio='"+ data["audio"] + "'); "
 
   print("\n")   
 
   print(query)
 
   try:
       prova = cursor.execute(query)
       prova2 = db.commit()
       print(prova)
       print(prova2)
       status = make_response(jsonify('domanda inserita'), 200)
   except psycopg2.IntegrityError as e:
       status = make_response(jsonify('Error: domanda not inserted - ', str(e)), 500)
   finally:
       cursor.close()
   return status

 

# # Inserisce risposta audio.
# # PARAMETRI DA PASSARE: - audio, - id
# @app.route('/audiofile', methods=['POST'])
# def rispostaDomandeAudio():
#     content = request.get_json(silent=True)
#     print(type(content["audio"])) #This is type string
#     ans = base64.b64encode(bytes(content["audio"], 'utf-8'))
#     print(type(ans)) #This is type bytes
#     namefile = uuid.uuid4()
#     with open(namefile + ".webm", "wb") as fh:
#         fh.write(base64.b64decode(ans))
#     query = "UPDATE public.storico_domande SET audio='" + content[
#         "audio"] + "'"

#     query += " WHERE id_domanda='" + content['id'] + "';"

#     print("\n")

#     print(query)
    
#     cursor = db.cursor()

#     try:
#         cursor.execute(query)
#         db.commit()
#         status = jsonify('User updated')
#     except psycopg2.IntegrityError as e:
#         status = jsonify('Error: User not updated - ', str(e))
#     finally:
#         cursor.close()
#     return status


# # Inserisce risposta testuale.
# # PARAMETRI DA PASSARE: - role, - risposta, - idDomanda
# @app.route("/textrisposta", methods=['POST'])
# # @token_required
# def rispostaDomandeTesto():
#     data = request.get_json()
#     cursor = db.cursor()
#     user = get_role(data['role'])
#     print("\n")
#     print(data)
#     print("\n")

#     query = "UPDATE public.storico_domande SET testo_risposta='" + data[
#         "risposta"] + "'"

#     query += " WHERE id_domanda='" + data['id'] + "';"

#     print("\n")

#     print(query)

#     try:
#         cursor.execute(query)
#         db.commit()
#         status = jsonify('User updated')
#     except psycopg2.IntegrityError as e:
#         status = jsonify('Error: User not updated - ', str(e))
#     finally:
#         cursor.close()
#     return status
