from flask import Flask, render_template, jsonify
import sqlite3

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/balance")
def get_balance():
    conn = sqlite3.connect("casino.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE id = 1")  # exemple
    balance = cursor.fetchone()[0]
    conn.close()
    return jsonify({"balance": balance})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
