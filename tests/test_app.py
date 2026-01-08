# pylint: disable=redefined-outer-name
"""Module de tests unitaires pour l'application Casino."""
import pytest
from app import app 

@pytest.fixture
def client():
    """Crée un client de test pour Flask avec configuration sécurisée."""
    # On force l'application en mode test
    app.config['TESTING'] = True
    # On définit une clé secrète pour éviter l'erreur "RuntimeError: A secret key is required"
    app.config['SECRET_KEY'] = 'test-secret-key'
    # On désactive la protection CSRF uniquement pour les tests unitaires
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client_test:
        yield client_test

def test_home_page(client):
    """Vérifie que la page d'accueil s'affiche (Code 200)."""
    response = client.get('/')
    assert response.status_code == 200

def test_choix_page_redirects_unauthenticated(client):
    """Vérifie que /choix redirige vers l'accueil si non connecté (Code 302)."""
    response = client.get('/choix')
    # Comme tu as @login_required, l'accès anonyme doit être rejeté
    assert response.status_code == 302

def test_choix_page_authenticated(client):
    """Vérifie que la page de choix s'affiche après connexion simulée."""
    with client.session_transaction() as sess:
        sess['username'] = 'testuser'
    
    response = client.get('/choix')
    assert response.status_code == 200
    