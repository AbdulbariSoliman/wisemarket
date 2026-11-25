"""Production entry point: React app at /, API at /api (backend/api/serve.py)."""
import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>WiseMarket</html>")
    (dist / "assets" / "app-123.js").write_text("console.log(1)")
    (tmp_path / "secret.txt").write_text("do not serve")
    monkeypatch.setenv("FRONTEND_DIST", str(dist))
    import backend.api.serve as serve
    serve = importlib.reload(serve)
    with TestClient(serve.app) as c:
        yield c


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_api_is_mounted_under_api(client):
    r = client.get("/api/")
    assert r.status_code == 200 and "application/json" in r.headers["content-type"]


def test_client_side_routes_get_index_html(client):
    for path in ("/", "/product/3017620422003", "/basket"):
        r = client.get(path)
        assert r.status_code == 200 and "WiseMarket" in r.text


def test_assets_are_served_with_long_cache(client):
    r = client.get("/assets/app-123.js")
    assert r.text == "console.log(1)"
    assert "immutable" in r.headers["cache-control"]


def test_no_files_outside_dist(client):
    r = client.get("/..%2Fsecret.txt")
    assert "do not serve" not in r.text
