import random
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

class BlackjackGame:
    def __init__(self):
        suits = ['C', 'D', 'H', 'S']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        self.deck = [f"{r}{s}" for r in ranks for s in suits]
        random.shuffle(self.deck)
        self.player_hand = [self.deck.pop(), self.deck.pop()]
        self.dealer_hand = [self.deck.pop(), self.deck.pop()]
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

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_game():
    global game_counter
    game_counter += 1
    new_game = BlackjackGame()
    games[game_counter] = new_game

    return jsonify({
        "game_id": game_counter,
        "player_hand": new_game.player_hand,
        "dealer_visible_card": new_game.dealer_hand[0],
        "player_score": new_game.calculate_score(new_game.player_hand)
    })

@app.route('/game/<int:game_id>/hit', methods=['POST'])
def hit(game_id):
    game = games.get(game_id)
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
    game = games.get(game_id)
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