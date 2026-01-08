import os
import random
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, jsonify, session,session
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect

load_dotenv()
# --- CONFIGURATION ET CONSTANTES ---
DATABASE = 'casino_v2.db'
app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY")

# Activation de la protection CSRF
csrf = CSRFProtect(app)
app.config["WTF_CSRF_ENABLED"] = True

@app.after_request
def apply_security_headers(response):
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self';"
    )
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
    return response


# Générateur sécurisé pour les jeux (B311) et pour corriger le bug shuffle
SECURE_GEN = random.SystemRandom()

# --- LE VIGILE (À mettre avant les routes) ---
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
        suits = ['C', 'D', 'H', 'S']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
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

def write_db(name, password):
    connexion = connexion_database()
    db_write=connexion.execute("INSERT INTO users (username, hash) VALUES (?, ?);",[name,password])
    connexion.commit()
    connexion.close()
    return db_write
# --- ROUTES NAVIGATION ---

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/register", methods=["POST"])
def register():
    new_username = request.form.get("username")
    new_password = request.form.get("password")
    if new_username and new_password:
        hashed = generate_password_hash(new_password)
        write_db(new_username, hashed)
    return redirect(url_for("home"))

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"].strip()
    password = request.form["password"]
    db_user = read_db_log_in(username)

    if db_user and check_password_hash(db_user["hash"], password):
        session['username'] = username # On mémorise l'utilisateur !
        return redirect(url_for("choix"))
    
    return redirect(url_for("croissantage"))

@app.route("/choix")
@login_required
def choix():
    return render_template("choix.html")

@app.route("/croissantage")
def croissantage():
    return render_template("croissantage.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# Routes de jeu protégées
@app.route('/jouer-au-blackjack')
@login_required
def blackjack():
    return render_template('blackjack.html')

@app.route('/jouer-a-la-roulette')
@login_required
def roulette():
    return render_template('roulette.html')

# --- ROUTES API JEUX ---

@app.route('/start', methods=['POST'])
def start_game():
    """Initialise une nouvelle partie de Blackjack."""
    global GAME_COUNTER  # pylint: disable=global-statement
    data = request.get_json() or {}

    try:
        bet = int(data.get('bet', 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Mise invalide"}), 400

    if bet <= 0:
        return jsonify({"error": "La mise doit être supérieure à 0"}), 400

    GAME_COUNTER += 1
    new_game = BlackjackGame(bet)
    GAMES[GAME_COUNTER] = new_game
    
    return jsonify({
        "game_id": GAME_COUNTER,
        "player_hand": new_game.player_hand,
        "dealer_visible_card": new_game.dealer_hand[0],
        "player_score": new_game.calculate_score(new_game.player_hand),
        "bet": new_game.bet
    })

@app.route('/game/<int:game_id>/hit', methods=['POST'])
def hit(game_id):
    """Le joueur demande une carte supplémentaire."""
    game = GAMES.get(game_id)
    if not game or game.status != "en_cours":
        return jsonify({"error": "Partie introuvable"}), 404

    game.player_hand.append(game.deck.pop())
    score = game.calculate_score(game.player_hand)
    
    if score > 21:
        game.status = "termine"
        return jsonify({
            "player_hand": game.player_hand,
            "player_score": score,
            "status": "Bust!"
        })

    return jsonify({
        "player_hand": game.player_hand,
        "player_score": score,
        "status": "en_cours"
    })

@app.route('/game/<int:game_id>/stand', methods=['POST'])
def stand(game_id):
    """Le joueur s'arrête et laisse le croupier jouer."""
    game = GAMES.get(game_id)
    if not game or game.status != "en_cours":
        return jsonify({"error": "Action impossible"}), 400

    player_score = game.calculate_score(game.player_hand)
    dealer_score = game.calculate_score(game.dealer_hand)

    while dealer_score < 17:
        game.dealer_hand.append(game.deck.pop())
        dealer_score = game.calculate_score(game.dealer_hand)

    if dealer_score > 21 or player_score > dealer_score:
        result, gain = "Gagné !", game.bet * 2
    elif player_score < dealer_score:
        result, gain = "Perdu !", 0
    else:
        result, gain = "Égalité !", game.bet

    game.status = "termine"
    return jsonify({
        "result": result,
        "dealer_hand": game.dealer_hand,
        "dealer_score": dealer_score,
        "gain": gain
    })

@app.route("/api/roulette/spin", methods=["POST"])
def roulette_spin():
    """Gère un tour de roulette et calcule les gains."""
    data = request.get_json() or {}
    bet_type = data.get("type")
    bet_value = data.get("value")
    amount = float(data.get("amount", 0))

    # Aléatoire sécurisé (B311)
    numero = SECURE_GEN.randint(0, 36)
    couleur = "vert" if numero == 0 else "rouge" if numero in ROUGE else "noir"

    gain = 0
    if bet_type == "color" and bet_value == couleur:
        gain = amount * 2
    elif bet_type == "number" and str(bet_value) == str(numero):
        gain = amount * 36
    elif bet_type == "parity" and numero != 0:
        is_even = numero % 2 == 0
        if (bet_value == "pair" and is_even) or (bet_value == "impair" and not is_even):
            gain = amount * 2

    return jsonify({
        "numero": numero,
        "couleur": couleur,
        "gain": gain,
        "result": "gagné" if gain > 0 else "perdu"
    })

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000, debug=False)