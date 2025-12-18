from flask import Flask, render_template, jsonify
import sqlite3
import os

DATABASE = 'casino_v2.db'

def connexion_database():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

app = Flask(__name__)

@app.route("/")
def home():
    connexion = connexion_database()
    users = connexion.execute("SELECT * FROM users").fetchall()
    connexion.close()
    
    return render_template("index.html", users = users)

#@app.route("/api/balance")
#def get_balance():
 #   conn = sqlite3.connect("casino.db")
  #  cursor = conn.cursor()
   # cursor.execute("SELECT balance FROM users WHERE id = 1")  # exemple
    #balance = cursor.fetchone()[0]
    #conn.close()
    #return jsonify({"balance": balance})

if __name__ == "__main__":
    app.run(debug=True)
