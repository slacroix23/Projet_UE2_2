from flask import Flask, render_template, jsonify
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

if __name__ == "__main__":
    app.run(debug=True)
