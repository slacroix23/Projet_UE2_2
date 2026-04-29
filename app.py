"""
Application Casino - Projet UE2-2 - Projet UE2-2
"""
import os
import random
import sqlite3
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from flask_wtf.csrf import CSRFProtect
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'casino_v2.db')
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "mobility-bronze-strife-overreach-calorie-vigorous")

# 1. Initialise SocketIO sans CSRF (on ajoute check_cors=False pour le test)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode=None)

# 2. Configure CSRF pour le reste de l'app
app.config["WTF_CSRF_ENABLED"] = True
csrf = CSRFProtect(app)


# --- CONSTANTES ---
ROUGE_NUMBERS = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
NOIR_NUMBERS = {2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35}
SECURE_GEN = random.SystemRandom()

# --- SÉCURITÉ & HEADERS ---
@app.after_request
def apply_security_headers(response):
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.socket.io; " 
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self' ws://127.0.0.1:5000 http://127.0.0.1:5000; "
        "font-src 'self' data:;"
    )
    response.headers["Referrer-Policy"] = "no-referrer"
    return response

# --- LOGIQUE CHAT (SOCKET.IO) ---
@socketio.on('send_message')
def handle_send_message(data):
    username = session.get('username', 'Anonyme')
    payload = data.get('payload', '')
    # On renvoie à tout le monde
    socketio.emit('new_message', {
        'user': username,
        'payload': payload
    })

# --- DÉCORATEUR ---
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return decorated

# --- LOGIQUE BLACKJACK (CLASSES) ---
class BlackjackGame:
    def __init__(self, bet):
        ranks = ['2','3','4','5','6','7','8','9','10','J','Q','K','A']
        suits = ['C','D','H','S']
        self.deck = [f"{r}{s}" for r in ranks for s in suits] # Correction ici
        SECURE_GEN.shuffle(self.deck)

        self.player_hand = [self.deck.pop(), self.deck.pop()]
        self.dealer_hand = [self.deck.pop(), self.deck.pop()]
        self.bet = bet
        self.status = "en_cours"
        self.status = "en_cours"

    def calculate_score(self, hand):
        score, aces = 0, 0
        values = {
            '2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,
            '10':10,'J':10,'Q':10,'K':10,'A':11
        }
        for card in hand:
            rank = card[:-1]
            score += values[rank]
            if rank == "A":
                aces += 1
        while score > 21 and aces:
            score -= 10
            aces -= 1
        return score

    def is_blackjack(self, hand):
        return len(hand) == 2 and self.calculate_score(hand) == 21

    def hit(self):
        if self.status == "en_cours":
            self.player_hand.append(self.deck.pop())
            if self.calculate_score(self.player_hand) > 21:
                self.status = "bust"

    def dealer_play(self):
        while self.calculate_score(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deck.pop())

GAMES = {}
GAME_COUNTER = 0

# --- BASE DE DONNÉES ---
def connexion_database():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

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
        return int(user["balance"])
    except:
        return 1000

def set_user_balance(username, new_balance):
    with connexion_database() as conn:
        conn.execute("UPDATE users SET balance = ? WHERE username = ?;", (new_balance, username))
        conn.commit()

# --- RÉSOLUTION BLACKJACK ---
def resolve_blackjack_game(game, username, player_busted=False):
    bet = game.bet
    balance = get_user_balance(username)

    player_score = game.calculate_score(game.player_hand)
    dealer_score = game.calculate_score(game.dealer_hand)

    result = "Perdu !"
    gain = 0

    if player_busted:
        result = "Perdu !"
        gain = 0
    else:
        player_bj = game.is_blackjack(game.player_hand)
        dealer_bj = game.is_blackjack(game.dealer_hand)

        if player_bj and dealer_bj:
            result = "Égalité !"
            gain = bet
        elif player_bj:
            result = "Blackjack !"
            gain = int(bet * 2.5)
        else:
            if dealer_score > 21:
                result = "Gagné !"
                gain = bet * 2
            elif dealer_score > player_score:
                result = "Perdu !"
            elif dealer_score < player_score:
                result = "Gagné !"
                gain = bet * 2
            else:
                result = "Égalité !"
                gain = bet

    new_balance = balance - bet + gain
    set_user_balance(username, new_balance)

    # Fin de partie
    game.status = "terminé"
    for gid, g in list(GAMES.items()):
        if g is game:
            del GAMES[gid]

    return {
        "player_hand": game.player_hand,
        "player_score": player_score,
        "dealer_hand": game.dealer_hand,
        "dealer_score": dealer_score,
        "result": result,
        "gain": gain,
        "new_balance": new_balance,
        "status": "finished"
    }

# --- ROUTES ---
@app.route("/")
def home():
    return render_template("index.html")

@app.route('/test')
def page_test():
    print(" >>> JE SERS LA PAGE TEST ACTUELLEMENT <<< ") # Regarde ton terminal !
    username = session.get('username', 'Invité')
    user = read_db_log_in(username)
    balance = user['balance'] if user else 0
    return render_template('test.html', balance=balance)

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"].strip()
    password = request.form["password"]
    db_user = read_db_log_in(username)
    if db_user and check_password_hash(db_user["hash"], password):
        session["username"] = username
        return redirect(url_for("choix"))
    return redirect(url_for("home"))

@app.route("/register", methods=["POST"])
def register():
    u = request.form.get("username")
    p = request.form.get("password")
    if u and p:
        write_db(u, generate_password_hash(p))
    return redirect(url_for("home"))

@app.route("/choix")
@login_required
def choix():
    balance = get_user_balance(session["username"])
    return render_template("choix.html", balance=balance)

@app.route("/jouer-au-blackjack")
@login_required
def blackjack():
    balance = get_user_balance(session["username"])
    return render_template("blackjack.html", balance=balance)

@app.route("/jouer-a-la-roulette")
@login_required
def roulette():
    balance = get_user_balance(session["username"])
    return render_template("roulette.html", balance=balance)

# --- API BLACKJACK ---
@app.route("/start", methods=["POST"])
@login_required
def start_game():
    global GAME_COUNTER
    data = request.get_json() or {}
    try:
        bet = int(data.get("bet", 0))
    except:
        return jsonify({"error": "Mise invalide"}), 400

    if bet <= 0:
        return jsonify({"error": "Mise > 0"}), 400

    balance = get_user_balance(session["username"])
    if bet > balance:
        return jsonify({"error": "Balance insuffisante"}), 403

    GAME_COUNTER += 1
    game = BlackjackGame(bet)
    GAMES[GAME_COUNTER] = game

    player_score = game.calculate_score(game.player_hand)

    # Blackjack naturel
    if game.is_blackjack(game.player_hand):
        dealer_score = game.calculate_score(game.dealer_hand)
        gain = int(bet * 2.5)
        new_balance = balance - bet + gain
        set_user_balance(session["username"], new_balance)

        game.status = "terminé"
        GAMES.pop(GAME_COUNTER, None)

        return jsonify({
            "game_id": GAME_COUNTER,
            "player_hand": game.player_hand,
            "player_score": player_score,
            "dealer_hand": game.dealer_hand,
            "dealer_score": dealer_score,
            "result": "Blackjack !",
            "gain": gain,
            "new_balance": new_balance,
            "status": "finished"
        })

    return jsonify({
        "game_id": GAME_COUNTER,
        "player_hand": game.player_hand,
        "player_score": player_score,
        "dealer_visible_card": game.dealer_hand[0]
    })

csrf.exempt(start_game)

@app.route("/game/<int:game_id>/hit", methods=["POST"])
@login_required
def blackjack_hit(game_id):
    game = GAMES.get(game_id)
    if not game:
        return jsonify({"error": "Partie introuvable"}), 404

    if game.status != "en_cours":
        return jsonify({"error": "Partie déjà terminée"}), 400

    game.hit()
    player_score = game.calculate_score(game.player_hand)

    # Bust
    if player_score > 21:
        result = resolve_blackjack_game(game, session["username"], player_busted=True)
        return jsonify(result)

    # 21 en 3+ cartes → victoire immédiate
    if player_score == 21:
        game.dealer_play()
        result = resolve_blackjack_game(game, session["username"])
        return jsonify(result)

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
        return jsonify({"error": "Partie déjà terminée"}), 400

    game.dealer_play()
    result = resolve_blackjack_game(game, session["username"])
    return jsonify(result)

csrf.exempt(blackjack_stand)

# --- API BALANCE ---
@app.route("/api/balance")
@login_required
def get_balance():
    return jsonify({"balance": get_user_balance(session["username"])})

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

    balance = get_user_balance(session["username"])
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

    if bet_type == "color" and bet_value == couleur:
        gain = amount * 2
        result = "gagné"
    elif bet_type == "number":
        try:
            if int(bet_value) == numero:
                gain = amount * 36
                result = "gagné"
        except:
            pass
    elif bet_type == "parity" and numero != 0:
        if bet_value == "pair" and numero % 2 == 0:
            gain = amount * 2
            result = "gagné"
        elif bet_value == "impair" and numero % 2 == 1:
            gain = amount * 2
            result = "gagné"

    new_balance = balance - amount + gain
    set_user_balance(session["username"], new_balance)

    return jsonify({
        "numero": numero,
        "couleur": couleur,
        "result": result,
        "gain": gain,
        "new_balance": new_balance
    })

csrf.exempt(roulette_spin)

if __name__ == "__main__":
    # IMPORTANT : Utiliser socketio.run pour que le chat fonctionne
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)