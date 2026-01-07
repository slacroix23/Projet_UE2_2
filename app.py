"""Module principal de l'application Casino Flask."""
import sqlite3
import hashlib
import random
from flask import Flask, render_template, request, redirect, url_for, jsonify, jsonify

DATABASE = 'casino_v2.db'
app = Flask(__name__)

# --- LOGIQUE DU BLACKJACK ---
class BlackjackGame:
    def __init__(self, bet): # On ajoute bet ici
        suits = ['C', 'D', 'H', 'S']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        self.deck = [f"{r}{s}" for r in ranks for s in suits]
        random.shuffle(self.deck)
        self.player_hand = [self.deck.pop(), self.deck.pop()]
        self.dealer_hand = [self.deck.pop(), self.deck.pop()]
        self.bet = bet  # On mémorise la mise pour ce jeu
        self.status = "en_cours"
    
    def calculate_score(self, hand):
        score = 0
        aces = 0
        values = {'2':2, '3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, '10':10, 'J':10, 'Q':10, 'K':10, 'A':11}
        for card in hand:
            rank = card[:-1]
            score += values[rank]
            if rank == 'A': aces += 1
        while score > 21 and aces:
            score -= 10
            aces -= 1
        return score

games = {}
game_counter = 0

# --- FONCTIONS BASE DE DONNÉES ---
def connexion_database():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def read_db():
    connexion = connexion_database()
    db_read = connexion.execute("SELECT * FROM users;").fetchall()
    connexion.close()
    return db_read

def read_db_log_in(name):
    connexion = connexion_database()
    db_read_log = connexion.execute("SELECT * FROM users WHERE username = ?;", [name]).fetchone()
    connexion.close()
    return db_read_log

# --- ROUTES NAVIGATION ---
@app.route("/")
def home():
    users = read_db()
    return render_template("index.html", users=users)

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"].strip()
    password = request.form["password"]
    hashed_password = hashlib.sha1(password.encode()).hexdigest()
    db = read_db_log_in(username)

    if db is None:
        return redirect(url_for("croissantage"))
    
    if username == db["username"] :
        if db["hash"] == hashed_password:
            return redirect(url_for("choix"))
        else:
            return redirect(url_for("croissantage"))
    else: 
        return redirect(url_for("croissantage"))


@app.route("/choix")
def choix():
    return render_template("choix.html")

@app.route("/croissantage")
def croissantage():
    return render_template("croissantage.html")

@app.route('/jouer-au-blackjack')
def blackjack():
    # Assure-toi que ton fichier HTML s'appelle bien blackjack.html dans /templates
    return render_template('blackjack.html')

# --- ROUTES API JEU (Ce qui manquait !) ---

@app.route('/start', methods=['POST'])
def start_game():
    global game_counter
    data = request.get_json()
    
    # On récupère la mise depuis le JavaScript
    try:
        bet = int(data.get('bet', 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Mise invalide"}), 400

    if bet <= 0:
        return jsonify({"error": "La mise doit être supérieure à 0"}), 400

    game_counter += 1
    new_game = BlackjackGame(bet)
    games[game_counter] = new_game
    return jsonify({
        "game_id": game_counter,
        "player_hand": new_game.player_hand,
        "dealer_visible_card": new_game.dealer_hand[0],
        "player_score": new_game.calculate_score(new_game.player_hand),
        "bet": new_game.bet
    })

@app.route('/game/<int:game_id>/hit', methods=['POST'])
def hit(game_id):
    game = games.get(game_id)
    if not game: return jsonify({"error": "Inexistant"}), 404
    game.player_hand.append(game.deck.pop())
    score = game.calculate_score(game.player_hand)
    status = "Bust!" if score > 21 else "en_cours"
    return jsonify({"player_hand": game.player_hand, "player_score": score, "status": status})

@app.route('/game/<int:game_id>/stand', methods=['POST'])
def stand(game_id):
    game = games.get(game_id)
    if not game: return jsonify({"error": "Inexistant"}), 404
    
    player_score = game.calculate_score(game.player_hand)
    dealer_score = game.calculate_score(game.dealer_hand)
    
    while dealer_score < 17:
        game.dealer_hand.append(game.deck.pop())
        dealer_score = game.calculate_score(game.dealer_hand)
    
    gain = 0
    if dealer_score > 21 or player_score > dealer_score:
        result = "Gagné !"
        gain = game.bet * 2
    elif player_score < dealer_score:
        result = "Perdu !"
        gain = 0
    else:
        result = "Égalité ! "
        gain = game.bet
    
    return jsonify({
        "result": result, 
        "dealer_hand": game.dealer_hand, 
        "dealer_score": dealer_score,
        "gain": gain
    })
    

@app.route('/jouer-a-la-roulette')
def roulette():
    # Cette fonction correspond à url_for('roulette')
    return render_template('roulette.html')

@app.route("/api/roulette/spin", methods=["POST"])
def roulette_spin():
    from flask import request, jsonify
    import random

    ROUGE = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
    NOIR = {2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35}

    data = request.get_json()
    bet_type = data.get("type")
    bet_value = data.get("value")
    amount = float(data.get("amount", 0))

    numero = random.randint(0, 36)
    couleur = "vert" if numero == 0 else "rouge" if numero in ROUGE else "noir"

    gain = 0
    result_type = "perdu"

    if bet_type == "color" and bet_value == couleur:
        gain = amount * 2
        result_type = "gagné"

    elif bet_type == "number" and str(bet_value) == str(numero):
        gain = amount * 36
        result_type = "gagné"

    elif bet_type == "parity" and numero != 0:
        if bet_value == "pair" and numero % 2 == 0:
            gain = amount * 2
            result_type = "gagné"
        elif bet_value == "impair" and numero % 2 == 1:
            gain = amount * 2
            result_type = "gagné"

    return jsonify({
        "numero": numero,
        "couleur": couleur,
        "gain": gain,
        "result": result_type
    })

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True) # nosec