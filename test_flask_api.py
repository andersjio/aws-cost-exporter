from urllib import response
import pytest
from aws_cost_exporter2 import get_flask_app

@pytest.fixture
def app():
    app = get_flask_app()
    yield app
    # teardown here

@pytest.fixture
def client(app):
    return app.test_client()

def test_can_get_health(client):
    response = client.get('/health')
    assert response.status_code == 200

def test_can_get_metrics(client):
    response = client.get('/metrics')
    assert response.status_code == 200

def test_redirect_to_metrics(client):
    response = client.get('/')
    assert response.status_code == 302

def test_can_get_metrics_with_trailing_slash(client):
    response = client.get('/metrics/')
    assert response.status_code == 200