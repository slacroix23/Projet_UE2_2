import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_loading(client):
    response = client.get('/')
    assert response.status_code == 200

def test_choix_loading(client):
    response = client.get('/choix')
    assert response.status_code == 200

def test_blackjack_loading(client):
    response = client.get('/jouer-au-blackjack')
    assert response.status_code == 200

def test_roulette_loading(client):
    response = client.get('/jouer-a-la-roulette')
    assert response.status_code == 200

def test_roulette_post_bet(client):
    """Teste l'envoi d'une mise sur la bonne route"""
    response = client.post('/jouer-a-la-roulette', data={
        'amount': '10',
        'choice': 'red'
    }, follow_redirects=True)
    # Si tu as une erreur 405 ici, regarde l'étape 2 ci-dessous
    assert response.status_code == 200