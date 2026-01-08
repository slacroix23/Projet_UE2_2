# pylint: disable=redefined-outer-name
"""Module de tests unitaires pour l'application Casino."""
import pytest
from app import app 

@pytest.fixture
def client():
    """Crée un client de test pour Flask avec configuration sécurisée."""
    app.config['TESTING'] = True
    # On ajoute # nosec car c'est une clé de test, pas une vraie clé secrète
    app.config['SECRET_KEY'] = 'test-secret-key'  # nosec
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client_test:
        yield client_test

def test_home_page(client):
    """Vérifie que la page d'accueil s'affiche (Code 200)."""
    response = client.get('/')
    # On ajoute # nosec car l'usage de assert est standard dans les tests
    assert response.status_code == 200  # nosec

def test_choix_page_redirects_unauthenticated(client):
    """Vérifie que /choix redirige vers l'accueil si non connecté."""
    response = client.get('/choix')
    assert response.status_code == 302  # nosec

def test_choix_page_authenticated(client):
    """Vérifie que la page de choix s'affiche après connexion simulée."""
    with client.session_transaction() as sess:
        sess['username'] = 'testuser'
    
    response = client.get('/choix')
    assert response.status_code == 200  # nosec
    