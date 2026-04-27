"""
Application Casino
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
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'casino_v2.db')
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "mobility-bronze-strife-overreach-calorie-vigorous")

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
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "font-src 'self' data:; "
        "navigate-to 'self'; "
        "media-src 'self'; "
    )

    response.headers["Content-Security-Policy"] = csp_rules
    response.headers["Referrer-Policy"] = "no-referrer"
    return response

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
        self.status = "en_cours"  # en_cours, bust, terminé

    def calculate_score(self, hand):
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

    def is_blackjack(self, hand):
        return len(hand) == 2 and self.calculate_score(hand) == 21

    def hit(self):
        if self.status != "en_cours":
            return
        self.player_hand.append(self.deck.pop())
        if self.calculate_score(self.player_hand) > 21:
            self.status = "bust"

    def dealer_play(self):
        # Dealer tire jusqu'à 17 (classique)
        while self.calculate_score(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deck.pop())

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

def get_user_balance(username):
    user = read_db_log_in(username)
    try:
        return int(user['balance'])
    except:
        return 1000

def set_user_balance(username, new_balance):
    with connexion_database() as conn:
        conn.execute(
            "UPDATE users SET balance = ? WHERE username = ?;",
            (new_balance, username)
        )
        conn.commit()

# --- RÉSOLUTION D'UNE PARTIE DE BLACKJACK ---
def resolve_blackjack_game(game: BlackjackGame, username: str, player_busted=False):
    """
    Calcule le résultat, met à jour la balance, renvoie un dict JSON.
    Logique de gain alignée sur la roulette :
      - gain = montant total retourné (0, mise, 2*mise, 2.5*mise)
      - new_balance = balance - mise + gain
    """
    bet = game.bet
    balance = get_user_balance(username)

    player_score = game.calculate_score(game.player_hand)
    dealer_score = game.calculate_score(game.dealer_hand)

    # Par défaut
    result = "Perdu !"
    gain = 0

    if player_busted:
        # Joueur a bust, le croupier ne tire pas forcément plus
        result = "Perdu !"
        gain = 0
    else:
        # Cas blackjack naturels
        player_bj = game.is_blackjack(game.player_hand)
        dealer_bj = game.is_blackjack(game.dealer_hand)

        if player_bj and dealer_bj:
            result = "Égalité !"
            gain = bet  # on rend la mise
        elif player_bj:
            result = "Blackjack !"
            gain = int(bet * 2.5)  # 3:2
        else:
            # Pas de blackjack naturel, on compare les scores
            if dealer_score > 21:
                result = "Gagné !"
                gain = bet * 2
            elif dealer_score > player_score:
                result = "Perdu !"
                gain = 0
            elif dealer_score < player_score:
                result = "Gagné !"
                gain = bet * 2
            else:
                result = "Égalité !"
                gain = bet

    new_balance = balance - bet + gain
    set_user_balance(username, new_balance)

    return {
        "player_hand": game.player_hand,
        "player_score": player_score,
        "dealer_hand": game.dealer_hand,
        "dealer_score": dealer_score,
        "result": result,
        "gain": gain,
        "new_balance": new_balance
    }

# --- ROUTES ---

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
    return redirect(url_for("home"))

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
    user = read_db_log_in(session['username'])
    try:
        user_balance = user['balance']
    except:
        user_balance = 1000
    return render_template("choix.html", balance=user_balance)

@app.route('/jouer-au-blackjack')
@login_required
def blackjack():
    user = read_db_log_in(session['username'])
    try:
        user_balance = user['balance']
    except:
        user_balance = 1000
    return render_template('blackjack.html', balance=user_balance)

@app.route('/jouer-a-la-roulette')
@login_required
def roulette():
    user = read_db_log_in(session['username'])
    try:
        user_balance = user['balance']
    except:
        user_balance = 1000
    return render_template('roulette.html', balance=user_balance)

# --- API BLACKJACK ---

@app.route('/start', methods=['POST'])
@login_required
def start_game():
    global GAME_COUNTER
    data = request.get_json() or {}
    try:
        bet = int(data.get('bet', 0))
    except:
        return jsonify({"error": "Mise invalide"}), 400
    if bet <= 0:
        return jsonify({"error": "Mise > 0"}), 400

    # Vérifier la balance
    balance = get_user_balance(session['username'])
    if bet > balance:
        return jsonify({"error": "Balance insuffisante"}), 403

    GAME_COUNTER += 1
    new_game = BlackjackGame(bet)
    GAMES[GAME_COUNTER] = new_game

    player_score = new_game.calculate_score(new_game.player_hand)

    # Vérifier blackjack naturel dès le début
    if new_game.is_blackjack(new_game.player_hand):
        # Le croupier retourne sa main et on résout
        new_game.dealer_play()  # pour gérer le cas où le croupier a aussi blackjack
        result_data = resolve_blackjack_game(new_game, session['username'])
        # On ajoute l'id de partie pour cohérence
        result_data["game_id"] = GAME_COUNTER
        return jsonify(result_data)

    # Sinon, partie en cours
    return jsonify({
        "game_id": GAME_COUNTER,
        "player_hand": new_game.player_hand,
        "player_score": player_score,
        "dealer_visible_card": new_game.dealer_hand[0]
    })

csrf.exempt(start_game)

@app.route("/game/<int:game_id>/hit", methods=["POST"])
@login_required
def blackjack_hit(game_id):
    game = GAMES.get(game_id)
    if not game:
        return jsonify({"error": "Partie introuvable"}), 404

    if game.status != "en_cours":
        # On renvoie juste l'état actuel
        return jsonify({
            "player_hand": game.player_hand,
            "player_score": game.calculate_score(game.player_hand),
            "dealer_visible_card": game.dealer_hand[0]
        })

    game.hit()
    player_score = game.calculate_score(game.player_hand)

    if game.status == "bust":
        # Joueur bust → partie perdue
        # On peut révéler la main du croupier sans qu'il tire
        result_data = resolve_blackjack_game(game, session['username'], player_busted=True)
        result_data["status"] = "Bust!"
        return jsonify(result_data)

    # Sinon, partie continue
    return jsonify({
        "player_hand": game.player_hand,
        "player_score": player_score,
        "dealer_visible_card": game.dealer_hand[0]
    })

csrf.exempt(blackjack_hit)

@app.route("/game/<int:game_id>/stand", methods=["POST"])
@login_required
def blackjack_stand(game_id):
    game = GAMES.get(game_id)
    if not game:
        return jsonify({"error": "Partie introuvable"}), 404

    if game.status != "en_cours":
        # Partie déjà terminée
        return jsonify({"error": "Partie déjà terminée"}), 400

    # Le joueur s'arrête, le croupier joue
    game.dealer_play()
    result_data = resolve_blackjack_game(game, session['username'])
    return jsonify(result_data)

csrf.exempt(blackjack_stand)

# --- API BALANCE GLOBALE ---

@app.route('/api/balance')
@login_required
def get_balance():
    user = read_db_log_in(session['username'])
    try:
        balance = user['balance']
    except:
        balance = 1000
    return jsonify({"balance": balance})

csrf.exempt(get_balance)

# --- API ROULETTE ---

@app.route("/api/roulette/spin", methods=["POST"])
@login_required
def roulette_spin():
    data = request.get_json() or {}

    bet_type = data.get("type")
    bet_value = data.get("value")
    amount = data.get("amount")

    try:
        amount = int(amount)
    except:
        return jsonify({"error": "Mise invalide"}), 400

    user = read_db_log_in(session['username'])
    try:
        balance = int(user['balance'])
    except:
        balance = 1000

    if amount <= 0:
        return jsonify({"error": "Mise invalide"}), 400

    if balance < amount:
        return jsonify({"error": "Balance insuffisante"}), 403

    numero = SECURE_GEN.randint(0, 36)
    if numero == 0:
        couleur = "vert"
    elif numero in ROUGE_NUMBERS:
        couleur = "rouge"
    else:
        couleur = "noir"

    result = "perdu"
    gain = 0

    if bet_type == "color":
        if bet_value == couleur:
            result = "gagné"
            gain = amount * 2

    elif bet_type == "number":
        try:
            if int(bet_value) == numero:
                result = "gagné"
                gain = amount * 36
        except:
            pass

    elif bet_type == "parity":
        if numero != 0:
            if bet_value == "pair" and numero % 2 == 0:
                result = "gagné"
                gain = amount * 2
            elif bet_value == "impair" and numero % 2 == 1:
                result = "gagné"
                gain = amount * 2

    new_balance = balance - amount + gain

    with connexion_database() as conn:
        conn.execute(
            "UPDATE users SET balance = ? WHERE username = ?;",
            (new_balance, session['username'])
        )
        conn.commit()

    return jsonify({
        "numero": numero,
        "couleur": couleur,
        "result": result,
        "gain": gain,
        "new_balance": new_balance
    })

csrf.exempt(roulette_spin)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False)
