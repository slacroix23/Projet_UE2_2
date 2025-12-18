from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

DATABASE = 'casino_v2.db'

def connexion_database():
    db = sqlite3.connect(DATABASE)
    #lecture de la base de donnée par colonnes
    db.row_factory = sqlite3.Row
    return db

app = Flask(__name__)

@app.route("/")
def home():
    connexion = connexion_database()
    #recupération de toute la table users
    users = connexion.execute("SELECT * FROM users").fetchall()
    connexion.close()
    #envoi vers index.html
    return render_template("index.html", users = users)

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]
    # logique de login ici
    return redirect(url_for("choix"))

@app.route("/choix")
def choix():
    return render_template("choix.html")


if __name__ == "__main__":
    app.run(debug=True)
