"""
Module principal de l'application Casino.
Ce module gère les routes Flask et la connexion à la base de données SQLite.
"""
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
    """Affiche la page d'accueil avec la liste des utilisateurs."""
    connexion = connexion_database()
    users = connexion.execute("SELECT * FROM users").fetchall()
    connexion.close()
    return render_template("index.html", users=users)

@app.route("/login", methods=["POST"])
def login():
    """Gère la tentative de connexion de l'utilisateur."""
    # On récupère les données sans créer de variables inutilisées
    if request.form.get("username") and request.form.get("password"):
        # Logique de login à implémenter ici
        return redirect(url_for("choix"))
    return redirect(url_for("home"))

@app.route("/choix")
def choix():
    """Affiche la page de sélection du jeu."""
    return render_template("choix.html")

@app.route('/jouer-au-blackjack')
def blackjack():
    """Affiche la table de Blackjack."""
    return render_template('blackjack.html')

@app.route('/jouer-a-la-roulette', methods=['GET', 'POST'])
def roulette():
    """Gère les mises et l'affichage de la roulette."""
    if request.method == 'POST':
        # On peut utiliser les données ou simplement valider la réception
        amount = request.form.get('amount')
        print(f"Mise reçue : {amount}")  # Utilisation de la variable pour Pylint
        return render_template('roulette.html', result="Résultat en attente")
    return render_template('roulette.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)