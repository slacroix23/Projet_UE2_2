import os
import random
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# --- INITIALISATION ---
load_dotenv()
DATABASE = 'casino_v2.db'
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# --- CONSTANTES JEU ---
ROUGE = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
NOIR = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}

SECURE_GEN = random.SystemRandom()

# --- LE VIGILE ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# --- LOGIQUE BLACKJACK ---
class BlackjackGame:
    def __init__(self, bet):
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        suits = ['C', 'D', 'H', 'S']
        self.deck = [f"{r}{s}" for r in ranks for s in suits]
        SECURE_GEN.shuffle(self.deck)
        self.player_hand = [self.deck.pop(), self.deck.pop()]
        self.dealer_hand = [self.deck.pop(), self.deck.pop()]
        self.bet = bet
        self.status = "en_cours"

    def calculate_score(self, hand):
        score, aces = 0, 0
        values = {'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,'10':10,'J':10,'Q':10,'K':10,'A':11}
        for card in hand:
            rank = card[:-1]
            score += values[rank]
            if rank == 'A': aces += 1
        while score > 21 and aces:
            score -= 10
            aces -= 1
        return score

GAMES = {}
GAME_COUNTER = 0

# --- BASE DE DONNÉES ---
def connexion_database():
    db_conn = sqlite3.connect(DATABASE)
    db_conn.row_factory = sqlite3.Row
    return db_conn

def read_db_log_in(name):
    with connexion_database() as conn:
        return conn.execute("SELECT * FROM users WHERE username = ?;", [name]).fetchone()

def write_db(name, password_hash):
    with connexion_database() as conn:
        conn.execute("INSERT INTO users (username, hash) VALUES (?, ?);", [name, password_hash])
        conn.commit()

# --- ROUTES NAVIGATION ---

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"].strip()
    password = request.form["password"]
    db_user = read_db_log_in(username)
    if db_user and check_password_hash(db_user["hash"], password):
        session['username'] = username
        return redirect(url_for("choix"))
    return redirect(url_for("croissantage"))

@app.route("/register", methods=["POST"])
def register():
    new_username = request.form.get("username")
    new_password = request.form.get("password")
    if new_username and new_password:
        write_db(new_username, generate_password_hash(new_password))
    return redirect(url_for("home"))

@app.route("/choix")
@login_required
def choix():
    return render_template("choix.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/croissantage")
def croissantage():
    return render_template("croissantage.html")

# --- ROUTES API JEUX (Toutes protégées) ---

@app.route('/start', methods=['POST'])
@login_required
def start_game():
    global GAME_COUNTER
    data = request.get_json() or {}
    try:
        bet = int(data.get('bet', 0))
    except (ValueError, TypeError): return jsonify({"error": "Mise invalide"}), 400
    if bet <= 0: return jsonify({"error": "Mise > 0"}), 400
    
    GAME_COUNTER += 1
    new_game = BlackjackGame(bet)
    GAMES[GAME_COUNTER] = new_game
    return jsonify({
        "game_id": GAME_COUNTER,
        "player_hand": new_game.player_hand,
        "player_score": new_game.calculate_score(new_game.player_hand)
    })

@app.route('/game/<int:game_id>/hit', methods=['POST'])
@login_required
def hit(game_id):
    game = GAMES.get(game_id)
    if not game or game.status != "en_cours": return jsonify({"error": "Partie finie"}), 404
    game.player_hand.append(game.deck.pop())
    score = game.calculate_score(game.player_hand)
    if score > 21: game.status = "termine"
    return jsonify({"player_hand": game.player_hand, "player_score": score})

@app.route('/game/<int:game_id>/stand', methods=['POST'])
@login_required
def stand(game_id):
    game = GAMES.get(game_id)
    if not game or game.status != "en_cours": return jsonify({"error": "Action impossible"}), 400
    # ... (le reste de ta logique stand est bon)
    return jsonify({"result": "Calculé", "dealer_hand": game.dealer_hand})

@app.route("/api/roulette/spin", methods=["POST"])
@login_required
def roulette_spin():
    data = request.get_json() or {}
    amount = float(data.get("amount", 0))
    numero = SECURE_GEN.randint(0, 36)
    couleur = "vert" if numero == 0 else "rouge" if numero in ROUGE else "noir"
    return jsonify({"numero": numero, "couleur": couleur})

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000, debug=False)