# pylint: disable=redefined-outer-name
"""Module de tests unitaires pour l'application Casino."""
import pytest
from app import app  # On importe l'application, on ne la recopie pas !

@pytest.fixture
def client():
    """Crée un client de test pour Flask."""
    with app.test_client() as client_test:
        yield client_test

def test_home_page(client):
    """Vérifie que la page d'accueil s'affiche."""
    response = client.get('/')
    assert response.status_code == 200 #nosec

def test_choix_page(client):
    """Vérifie que la page de choix s'affiche."""
    response = client.get('/choix')
    assert response.status_code == 200 # nosec
