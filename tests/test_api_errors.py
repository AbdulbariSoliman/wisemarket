# ============================================================
# WISEMARKET — API ERROR HANDLING & CORS TESTS
# No database needed: these check that every route returns a clean
# JSON error (never a raw 500) when the database is not reachable.
# ============================================================
import pytest
from fastapi.testclient import TestClient

from backend.api.main import app

GET_ROUTES = [
    "/products/search?q=milk",
    "/products/7610000100001",
    "/products/7610000100001/nutrition",
    "/prices/compare/7610000100001",
    "/prices/history/7610000100001",
    "/prices/latest/7610000100001",
    "/promotions",
    "/analyze/7610000100001",
]
POST_ROUTES = [
    ("/basket/calculate", {"items": [{"gtin": "7610000100001", "quantity": 1}]}),
    ("/scan", {"barcode": "7610000100001"}),
]

DB_SETUPS = {
    "missing_config": {"SUPABASE_URL": None, "SUPABASE_KEY": None},
    "unreachable":    {"SUPABASE_URL": "http://127.0.0.1:9", "SUPABASE_KEY": "test-key"},
}


@pytest.fixture(params=list(DB_SETUPS), ids=list(DB_SETUPS))
def client_without_db(request, monkeypatch):
    for name, value in DB_SETUPS[request.param].items():
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.mark.parametrize("path", GET_ROUTES)
def test_get_routes_return_clean_error_without_db(client_without_db, path):
    r = client_without_db.get(path)
    assert r.status_code in (502, 503), r.text
    assert r.json()["detail"] in ("Database unavailable", "Database query failed")


@pytest.mark.parametrize("path, body", POST_ROUTES)
def test_post_routes_return_clean_error_without_db(client_without_db, path, body):
    r = client_without_db.post(path, json=body)
    assert r.status_code in (422, 502, 503), r.text
    assert "detail" in r.json()


def test_health_works_without_db(client_without_db):
    r = client_without_db.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_cors_allows_local_frontend():
    with TestClient(app) as c:
        r = c.options(
            "/agent/query",
            headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
        )
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_blocks_unknown_origin():
    with TestClient(app) as c:
        r = c.options(
            "/agent/query",
            headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
        )
    assert "access-control-allow-origin" not in r.headers
