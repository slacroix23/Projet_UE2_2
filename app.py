from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import hashlib

DATABASE = 'casino_v2.db'

def connexion_database():
    db = sqlite3.connect(DATABASE)
    #lecture de la base de donnée par colonnes
    db.row_factory = sqlite3.Row
    return db

def read_db():
    connexion = connexion_database()
    #recupération de toute la table users
    db_read = connexion.execute(f"SELECT * FROM users;").fetchall() 
    connexion.close()
    return db_read


def read_db_log_in(name):
    connexion = connexion_database()
    #recupération du bon user uniquement
    db_read_log = connexion.execute("SELECT * FROM users WHERE username = ?;", [name]).fetchone() 
    connexion.close()
    return db_read_log


app = Flask(__name__)

@app.route("/")
def home():
    users = read_db()
    #envoi vers index.html
    return render_template("index.html", users = users)

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"].strip()
    password = request.form["password"]
    hashed_password = hashlib.sha1(password.encode()).hexdigest()
    db = read_db_log_in(username)

    if db is None:
       return redirect(url_for("croissantage"))
    
    if username == db["username"] :
        if db["hash"] == hashed_password :
            return redirect(url_for("choix"))
        else:
            return redirect(url_for("croissantage"))
    else : 
        return redirect(url_for("croissantage"))


            


@app.route("/choix")
def choix():
    db = read_db()
    return render_template("choix.html", users = db)

@app.route("/croissantage")
def croissantage():
    return render_template("croissantage.html")


if __name__ == "__main__":
    app.run(debug=True)
