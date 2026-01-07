"""Module principal de l'application Casino Flask."""
import sqlite3
import hashlib
import random
from flask import Flask, render_template, request, redirect, url_for, jsonify

DATABASE = 'casino_v2.db'
app = Flask(__name__)

def connexion_database():
    """Crée une connexion à la base de données SQLite."""
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def read_db():
    connexion = connexion_database()
    #recupération de toute la table users
    db_read = connexion.execute("SELECT * FROM users;").fetchall() 
    connexion.close()
    return db_read


def read_db_log_in(name):
    connexion = connexion_database()
    #recupération du bon user uniquement
    db_read_log = connexion.execute("SELECT * FROM users WHERE username = ?;", [name]).fetchone() 
    connexion.close()
    return db_read_log

@app.route("/")
def home():
    """Affiche la page d'accueil."""
    users = read_db()
    #envoi vers index.html
    return render_template("index.html", users = users)

@app.route("/login", methods=["POST"])
def login():
    """Gère la redirection du login."""
    username = request.form["username"].strip()
    password = request.form["password"]
    hashed_password = hashlib.sha1(password.encode()).hexdigest() # nosec
    db = read_db_log_in(username)

    if db is None:
        return redirect(url_for("croissantage"))
    
    if username == db["username"] :
        if db["hash"] == hashed_password:
            return redirect(url_for("choix"))
        else:
            return redirect(url_for("croissantage"))
    else: 
        return redirect(url_for("croissantage"))


@app.route("/choix")
def choix():
    """Affiche la page de sélection du jeu."""
    return render_template("choix.html")

@app.route("/croissantage")
def croissantage():
    return render_template("croissantage.html")

@app.route('/jouer-au-blackjack')
def blackjack():
    """Affiche la table de Blackjack."""
    return render_template('blackjack.html')

@app.route('/jouer-a-la-roulette', methods=['GET', 'POST'])
def roulette():
    """Gère la roulette."""
    if request.method == 'POST':
        amount = request.form.get('amount')
        print(f"Mise enregistrée : {amount}")
    return render_template('roulette.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True) # nosec
    

@app.route("/api/roulette/spin", methods=["POST"])
def roulette_spin():
    from flask import request, jsonify
    import random

    ROUGE = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
    NOIR = {2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35}

    data = request.get_json()
    bet_type = data.get("type")
    bet_value = data.get("value")
    amount = float(data.get("amount", 0))

    numero = random.randint(0, 36)
    couleur = "vert" if numero == 0 else "rouge" if numero in ROUGE else "noir"

    gain = 0
    result_type = "perdu"

    if bet_type == "color" and bet_value == couleur:
        gain = amount * 2
        result_type = "gagné"

    elif bet_type == "number" and str(bet_value) == str(numero):
        gain = amount * 36
        result_type = "gagné"

    elif bet_type == "parity" and numero != 0:
        if bet_value == "pair" and numero % 2 == 0:
            gain = amount * 2
            result_type = "gagné"
        elif bet_value == "impair" and numero % 2 == 1:
            gain = amount * 2
            result_type = "gagné"

    return jsonify({
        "numero": numero,
        "couleur": couleur,
        "gain": gain,
        "result": result_type
    })

