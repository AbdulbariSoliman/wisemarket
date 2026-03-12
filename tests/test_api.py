import pytest
from fastapi.testclient import TestClient
from backend.api.main import app


@pytest.fixture(scope="session")
def client():
    # scope="session" means lifespan runs once
    # for all tests — loads ontology and services
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


def test_root(client):
    # Confirms API is alive and responding
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "WiseMarket API is running"}


def test_health(client):
    # Confirms all services loaded correctly at startup
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"
    assert data["services"]["ontology_data"] is True
    assert data["services"]["parser"] is True
    assert data["services"]["router"] is True
    assert data["services"]["matcher"] is True
    assert data["services"]["decision_engine"] is True


def test_analyze_invalid_gtin_letters(client):
    # GTIN must be numbers only - letters must return 422
    response = client.get("/analyze/ABCDEFGHIJKLM")
    assert response.status_code == 422


def test_analyze_invalid_gtin_short(client):
    # GTIN must be 8, 13, or 14 digits - 3 digits must return 422
    response = client.get("/analyze/123")
    assert response.status_code == 422


def test_analyze_missing_product(client):
    # Valid GTIN format but product does not exist - must return 404
    response = client.get("/analyze/9999999999999")
    assert response.status_code == 404


def test_analyze_invalid_gtin_wrong_length(client):
    # 11 digits is not a valid GTIN length - must return 422
    response = client.get("/analyze/12345678901")
    assert response.status_code == 422


def test_analyze_lang_param_default(client):
    # No lang param should default to en gracefully
    response = client.get("/analyze/9999999999999")
    assert response.status_code == 404


def test_analyze_lang_param_de(client):
    # German language param must be accepted
    response = client.get("/analyze/9999999999999?lang=de")
    assert response.status_code == 404


def test_analyze_lang_param_invalid(client):
    # Invalid language must be rejected with 422
    response = client.get("/analyze/9999999999999?lang=xx")
    assert response.status_code == 422


def test_admin_stats_no_key(client):
    # Admin route without key must be rejected
    response = client.get("/admin/stats")
    assert response.status_code == 422


def test_admin_stats_wrong_key(client):
    # Admin route with wrong key must return 403
    response = client.get("/admin/stats", headers={"x-admin-key": "wrongkey"})
    assert response.status_code == 403


def test_admin_stats_correct_key(client):
    # Admin route with correct key must return 200 with store data
    import os
    key = os.environ.get("ADMIN_API_KEY", "")
    response = client.get("/admin/stats", headers={"x-admin-key": key})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "stores" in data
    assert "public_stores" in data


def test_admin_health_correct_key(client):
    # Admin health with correct key must return 200
    import os
    key = os.environ.get("ADMIN_API_KEY", "")
    response = client.get("/admin/health", headers={"x-admin-key": key})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["admin_key_set"] is True
