# ============================================================
# Regression test for the ontology_tags ->/->> operator bug.
# With `->` the JSONB filter fails to match; with `->>` it works.
# Requires the seeded test DB (see backend/schema/seed_test.sql).
# ============================================================
import pytest
from fastapi.testclient import TestClient
from backend.api.main import app

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


def test_vegan_filter_returns_only_vegan(client):
    resp = client.get("/products/search?vegan=true&lang=en")
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) >= 1, "vegan filter returned nothing — operator likely broken"
    for r in results:
        assert r["ontology_tags"].get("vegan") is True


def test_vegan_filter_excludes_nonvegan(client):
    resp = client.get("/products/search?vegan=true&lang=en")
    gtins = {r["gtin"] for r in resp.json()["results"]}
    assert "7610000100001" not in gtins, "non-vegan milk leaked into vegan=true results"


def test_unfiltered_search_includes_nonvegan(client):
    resp = client.get("/products/search?q=milk&lang=en")
    gtins = {r["gtin"] for r in resp.json()["results"]}
    assert "7610000100001" in gtins
