"""Module principal pour le jeu de Casino Flask."""
import sqlite3
from flask import Flask, render_template, request, redirect, url_for

DATABASE = 'casino_v2.db'
app = Flask(__name__)

def connexion_database():
    """Établit une connexion à la base de données SQLite."""
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

@app.route("/")
def home():
    """Affiche la page d'accueil avec les utilisateurs."""
    connexion = connexion_database()
    users = connexion.execute("SELECT * FROM users").fetchall()
    connexion.close()
    return render_template("index.html", users=users)

@app.route("/login", methods=["POST"])
def login():
    """Gère la redirection après soumission du formulaire de login."""
    return redirect(url_for("choix"))

@app.route("/choix")
def choix():
    """Affiche la page de sélection des jeux."""
    return render_template("choix.html")

@app.route('/jouer-au-blackjack')
def blackjack():
    """Affiche la page du Blackjack."""
    return render_template('blackjack.html')

@app.route('/jouer-a-la-roulette', methods=['GET', 'POST'])
def roulette():
    """Gère les mises de la roulette."""
    if request.method == 'POST':
        amount = request.form.get('amount')
        # On utilise print pour justifier l'existence de la variable amount
        print(f"La mise est de : {amount}")
    return render_template('roulette.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)