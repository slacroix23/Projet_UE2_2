"""Module gérant la logique du jeu de Blackjack."""
import random
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

class BlackjackGame:
    """Classe représentant une partie de Blackjack."""
    
    def __init__(self, bet=0):
        """Initialise le paquet, les mains et la mise."""
        suits = ['C', 'D', 'H', 'S']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        self.deck = [f"{r}{s}" for r in ranks for s in suits]
        random.shuffle(self.deck)
        self.player_hand = [self.deck.pop(), self.deck.pop()]
        self.dealer_hand = [self.deck.pop(), self.deck.pop()]
        self.bet = bet
        self.status = "en_cours"

    def calculate_score(self, hand):
        """Calcule le score d'une main en gérant la valeur des As."""
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
        
        # Gestion de l'As (vaut 1 au lieu de 11 si on dépasse 21)
        while score > 21 and aces:
            score -= 10
            aces -= 1
        return score

# Stockage des parties en mémoire (Noms en MAJUSCULES pour Ruff/Pylint)
GAMES = {}
GAME_COUNTER = 0

@app.route('/')
def home():
    """Route pour la page d'accueil."""
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_game():
    """Initialise une nouvelle partie."""
    global GAME_COUNTER  # Utilisation du nom en majuscule
    
    # Récupération optionnelle de la mise si ton JS l'envoie
    data = request.get_json() or {}
    bet = data.get('bet', 0)

    GAME_COUNTER += 1
    new_game = BlackjackGame(bet=bet)
    GAMES[GAME_COUNTER] = new_game

    return jsonify({
        "game_id": GAME_COUNTER,
        "player_hand": new_game.player_hand,
        "dealer_visible_card": new_game.dealer_hand[0],
        "player_score": new_game.calculate_score(new_game.player_hand)
    })

@app.route('/game/<int:game_id>/hit', methods=['POST'])
def hit(game_id):
    """Le joueur tire une carte."""
    game = GAMES.get(game_id)  # Utilisation de GAMES
    if not game or game.status != "en_cours":
        return jsonify({"error": "Partie introuvable"}), 400
    
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
        "player_score": score
    })

@app.route('/game/<int:game_id>/stand', methods=['POST'])
def stand(game_id):
    """Le joueur s'arrête, le croupier joue."""
    game = GAMES.get(game_id)  # Utilisation de GAMES
    if not game or game.status != "en_cours":
        return jsonify({"error": "Action impossible"}), 400
    
    player_score = game.calculate_score(game.player_hand)
    dealer_score = game.calculate_score(game.dealer_hand)

    while dealer_score < 17:
        game.dealer_hand.append(game.deck.pop())
        dealer_score = game.calculate_score(game.dealer_hand)

    if dealer_score > 21 or player_score > dealer_score:
        result = "Gagné !"
    elif player_score < dealer_score:
        result = "Perdu !"
    else:
        result = "Égalité !"

    game.status = "termine"
    return jsonify({
        "result": result,
        "dealer_hand": game.dealer_hand,
        "dealer_score": dealer_score
    })    

if __name__ == '__main__':
    app.run(debug=True)