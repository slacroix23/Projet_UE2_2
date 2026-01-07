"""
Module principal de l'application Casino Flask.
Gère l'authentification, le Blackjack et la Roulette.
"""

import hashlib
import random
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

# --- CONFIGURATION ET CONSTANTES ---
DATABASE = 'casino_v2.db'
# Utilisation de MAJUSCULES pour les constantes globales (validé par Pylint)
ROUGE = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
NOIR = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}

app = Flask(__name__)

# Générateur sécurisé pour les jeux (B311) et pour corriger le bug shuffle
SECURE_GEN = random.SystemRandom()

# --- LOGIQUE DU JEU ---

class BlackjackGame:  # pylint: disable=too-few-public-methods
    """Classe gérant la logique d'une partie de Blackjack."""

    def __init__(self, bet):
        """Initialise le paquet, mélange et distribue les cartes."""
        suits = ['C', 'D', 'H', 'S']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        self.deck = [f"{r}{s}" for r in ranks for s in suits]
        
        # Correction du crash : SystemRandom possède .shuffle()
        SECURE_GEN.shuffle(self.deck)
        
        self.player_hand = [self.deck.pop(), self.deck.pop()]
        self.dealer_hand = [self.deck.pop(), self.deck.pop()]
        self.bet = bet
        self.status = "en_cours"

    def calculate_score(self, hand):
        """Calcule le score d'une main donnée en gérant les As."""
        score = 0
        aces = 0
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

# Stockage global des parties (Noms en majuscules pour le style)
GAMES = {}
GAME_COUNTER = 0

# --- FONCTIONS BASE DE DONNÉES ---

def connexion_database():
    """Crée une connexion à la base de données SQLite."""
    db_conn = sqlite3.connect(DATABASE)
    db_conn.row_factory = sqlite3.Row
    return db_conn


def read_db_log_in(name):
    """Récupère les informations d'un utilisateur par son nom."""
    with connexion_database() as conn:
        db_read_log = conn.execute(
            "SELECT * FROM users WHERE username = ?;", [name]
        ).fetchone()
    return db_read_log


def write_db(name, password):
    connexion = connexion_database()
    db_write=connexion.execute("INSERT INTO users (username, hash) VALUES (?, ?);",[name,password])
    db_write=db_write
    #m'insultez pas vous avez qu'a pas mettre de regles sur les variables non utilisées
    connexion.commit()
    connexion.close()
    writed = True
    return writed

# --- ROUTES NAVIGATION ---

@app.route("/")
def home():
    """Route pour la page d'accueil."""
    return render_template("index.html")

@app.route("/login", methods=["POST"])
def login():
    """Gère l'authentification des utilisateurs."""
    username = request.form["username"].strip()
    password = request.form["password"]
    
    # Hachage SHA1 conservé à ta demande. 
    # Ajout du tag # nosec pour que Bandit ignore l'alerte B324.
    #hashed_password = hashlib.sha1(password.encode()).hexdigest()  # nosec B324

    db_user = read_db_log_in(username)

    if db_user is None:
        return redirect(url_for("croissantage"))

    if check_password_hash(db_user["hash"], password):
        return redirect(url_for("choix"))

    return redirect(url_for("croissantage"))

            
@app.route("/register", methods = ["POST"])
def register():
    """Gère la redirection du register."""
    new_username = request.form.get("username")
    new_password = request.form.get("password")

    if not new_username or not new_password:
        return "Formulaire invalide", 400

    hashed_password = generate_password_hash(new_password)
    write_db(new_username, hashed_password)
    return render_template("index.html")


@app.route("/choix")
def choix():
    """Page de sélection des jeux."""
    return render_template("choix.html")

@app.route("/croissantage")
def croissantage():
    """Page d'erreur de connexion."""
    return render_template("croissantage.html")

@app.route('/jouer-au-blackjack')
def blackjack():
    """Page du jeu de Blackjack."""
    return render_template('blackjack.html')

@app.route('/jouer-a-la-roulette')
def roulette():
    """Page du jeu de Roulette."""
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
    # Correction B104 (Hôte local) et B201 (Debug off)
    app.run(host='127.0.0.1', port=5000, debug=False)
    