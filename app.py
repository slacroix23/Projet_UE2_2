"""Module principal de l'application Casino."""
import sqlite3
from flask import Flask, render_template, request, redirect, url_for

DATABASE = 'casino_v2.db'
app = Flask(__name__)

def connexion_database():
    """Crée une connexion à la base de données SQLite."""
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

@app.route("/")
def home():
    """Affiche la page d'accueil."""
    connexion = connexion_database()
    users = connexion.execute("SELECT * FROM users").fetchall()
    connexion.close()
    return render_template("index.html", users=users)

@app.route("/login", methods=["POST"])
def login():
    """Gère la connexion des utilisateurs."""
    # On utilise request.form pour éviter l'alerte 'unused-variable'
    if request.form.get("username"):
        return redirect(url_for("choix"))
    return redirect(url_for("home"))

@app.route("/choix")
def choix():
    """Affiche la page de choix du jeu."""
    return render_template("choix.html")

@app.route('/jouer-au-blackjack')
def blackjack():
    """Affiche la page de blackjack."""
    return render_template('blackjack.html')

@app.route('/jouer-a-la-roulette', methods=['GET', 'POST'])
def roulette():
    """Gère la logique de la roulette."""
    if request.method == 'POST':
        amount = request.form.get('amount')
        print(f"Mise : {amount}")  # Utilisation de la variable
    return render_template('roulette.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)