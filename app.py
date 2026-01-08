"""
Application Casino - Projet UE2-2
"""
import os
import random
import sqlite3
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

# --- CONFIGURATION ---
DATABASE = 'casino_v2.db'
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# Protection CSRF
csrf = CSRFProtect(app)
app.config["WTF_CSRF_ENABLED"] = True

# --- CONSTANTES ---
ROUGE_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
NOIR_NUMBERS = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}
SECURE_GEN = random.SystemRandom()

@app.after_request
def apply_security_headers(response):
    """Ajoute des headers de sécurité à chaque réponse."""
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    csp_rules = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self';"
    )
    response.headers["Content-Security-Policy"] = csp_rules
    response.headers["Referrer-Policy"] = "no-referrer"
    return response

# --- LE VIGILE ---
def login_required(f):
    """Décorateur pour protéger les routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# --- LOGIQUE BLACKJACK ---
class BlackjackGame:
    """Gère la logique d'une partie de Blackjack."""
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
        """Calcule le score d'une main donnée."""
        score, aces = 0, 0
        values = {
            '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
            '10': 10, 'J': 10, 'Q': 10, 'K': 10, 'A': 11
        }
        for card in hand:
            rank = card[:-1]
            score += values[rank]
            if rank == 'A':
                aces += 1
        while score > 21 and aces:
            score -= 10
            aces -= 1
        return score

GAMES = {}
GAME_COUNTER = 0

# --- BASE DE DONNÉES ---
def connexion_database():
    """Crée une connexion à la base SQLite."""
    db_conn = sqlite3.connect(DATABASE)
    db_conn.row_factory = sqlite3.Row
    return db_conn

def read_db_log_in(name):
    """Récupère un utilisateur par son nom."""
    with connexion_database() as conn:
        return conn.execute("SELECT * FROM users WHERE username = ?;", [name]).fetchone()

def write_db(name, password_hash):
    """Enregistre un nouvel utilisateur."""
    with connexion_database() as conn:
        conn.execute("INSERT INTO users (username, hash) VALUES (?, ?);", [name, password_hash])
        conn.commit()

# --- ROUTES ---

@app.route("/")
def home():
    """Page d'accueil."""
    return render_template("index.html")

@app.route("/login", methods=["POST"])
def login():
    """Gère la connexion."""
    username = request.form["username"].strip()
    password = request.form["password"]
    db_user = read_db_log_in(username)
    if db_user and check_password_hash(db_user["hash"], password):
        session['username'] = username
        return redirect(url_for("choix"))
    return redirect(url_for("croissantage"))

@app.route("/register", methods=["POST"])
def register():
    """Gère l'inscription."""
    new_username = request.form.get("username")
    new_password = request.form.get("password")
    if new_username and new_password:
        write_db(new_username, generate_password_hash(new_password))
    return redirect(url_for("home"))

@app.route("/choix")
@login_required
def choix():
    """Page de sélection des jeux."""
    return render_template("choix.html")

@app.route('/jouer-au-blackjack')
@login_required
def blackjack():
    """Page HTML Blackjack."""
    return render_template('blackjack.html')

# --- API ---

@app.route('/start', methods=['POST'])
@login_required
def start_game():
    """Initialise le jeu."""
    global GAME_COUNTER  # pylint: disable=W0603
    data = request.get_json() or {}
    try:
        bet = int(data.get('bet', 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Mise invalide"}), 400
    if bet <= 0:
        return jsonify({"error": "Mise > 0"}), 400

    GAME_COUNTER += 1
    new_game = BlackjackGame(bet)
    GAMES[GAME_COUNTER] = new_game
    return jsonify({
        "game_id": GAME_COUNTER,
        "player_hand": new_game.player_hand,
        "player_score": new_game.calculate_score(new_game.player_hand)
    })

@app.route("/api/roulette/spin", methods=["POST"])
@login_required
def roulette_spin():
    """Lance la roulette."""
    numero = SECURE_GEN.randint(0, 36)
    if numero == 0:
        couleur = "vert"
    elif numero in ROUGE_NUMBERS:
        couleur = "rouge"
    else:
        couleur = "noir"
    return jsonify({"numero": numero, "couleur": couleur})

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000, debug=False)