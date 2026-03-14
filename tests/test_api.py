import os
import pytest
from fastapi.testclient import TestClient
from backend.api.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture(scope="session")
def admin_key():
    key = os.environ.get("ADMIN_API_KEY", "")
    if not key:
        pytest.skip("ADMIN_API_KEY not set in environment")
    return key


# ── Root & Health ─────────────────────────────────────────────

def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "WiseMarket API v2 is running"}


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "2.0.0"
    assert data["services"]["ontology"] is True
    assert data["services"]["parser"] is True
    assert data["services"]["router"] is True
    assert data["services"]["matcher"] is True
    assert data["services"]["decision_engine"] is True
    assert "public_stores" in data
    assert "migros" in data["public_stores"]
    assert "lidl" in data["public_stores"]


# ── Analyze endpoint ──────────────────────────────────────────

def test_analyze_invalid_gtin_letters(client):
    assert client.get("/analyze/ABCDEFGHIJKLM").status_code == 422

def test_analyze_invalid_gtin_short(client):
    assert client.get("/analyze/123").status_code == 422

def test_analyze_invalid_gtin_wrong_length(client):
    assert client.get("/analyze/12345678901").status_code == 422

def test_analyze_missing_product(client):
    assert client.get("/analyze/9999999999999").status_code == 404

def test_analyze_lang_de(client):
    assert client.get("/analyze/9999999999999?lang=de").status_code == 404

def test_analyze_lang_invalid(client):
    assert client.get("/analyze/9999999999999?lang=xx").status_code == 422

def test_analyze_real_product(client):
    response = client.get("/analyze/7610000100001?lang=en")
    assert response.status_code == 200
    data = response.json()
    assert data["gtin"] == "7610000100001"
    assert data["category"] == "dairy"
    assert "verdicts" in data
    assert "packages" in data["verdicts"]
    assert isinstance(data["verdicts"]["packages"], list)
    assert data["price"]["amount"] is not None
    assert data["price"]["currency"] == "CHF"


# ── Products ──────────────────────────────────────────────────

def test_products_search_returns_results(client):
    response = client.get("/products/search?q=milk&lang=en")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] > 0
    names = [r["name"].lower() for r in data["results"] if r["name"]]
    assert any("milk" in n for n in names)

def test_products_search_store_filter(client):
    response = client.get("/products/search?store=migros")
    assert response.status_code == 200
    for r in response.json()["results"]:
        assert r["store"] == "migros"

def test_products_search_vegan_filter(client):
    response = client.get("/products/search?vegan=true")
    assert response.status_code == 200
    for r in response.json()["results"]:
        assert r["ontology_tags"].get("vegan") is True

def test_products_search_halal_filter(client):
    response = client.get("/products/search?halal=true")
    assert response.status_code == 200
    for r in response.json()["results"]:
        assert r["ontology_tags"].get("halal") is True

def test_products_search_pagination(client):
    response = client.get("/products/search?limit=3&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) <= 3
    assert data["limit"] == 3

def test_products_get_by_gtin(client):
    response = client.get("/products/7610000100001")
    assert response.status_code == 200
    data = response.json()
    assert data["gtin"] == "7610000100001"
    assert len(data["stores"]) > 0
    assert "migros" in [s["store"] for s in data["stores"]]

def test_products_get_not_found(client):
    assert client.get("/products/9999999999999").status_code == 404

def test_products_nutrition(client):
    response = client.get("/products/7610000100001/nutrition")
    assert response.status_code == 200
    data = response.json()
    assert data["per_100g"]["energy_kcal"] is not None
    assert data["nutri_score"] in ("A","B","C","D","E")


# ── Prices ────────────────────────────────────────────────────

def test_prices_compare(client):
    response = client.get("/prices/compare/7610000100001")
    assert response.status_code == 200
    data = response.json()
    assert data["cheapest_store"] is not None
    prices = data["prices_chf"]
    assert prices[data["cheapest_store"]] == data["cheapest_price_chf"]
    for price in prices.values():
        assert price >= data["cheapest_price_chf"]

def test_prices_compare_not_found(client):
    assert client.get("/prices/compare/9999999999999").status_code == 404

def test_prices_history(client):
    response = client.get("/prices/history/7610000100001")
    assert response.status_code == 200
    assert isinstance(response.json()["history"], dict)

def test_prices_history_store_filter(client):
    response = client.get("/prices/history/7610000100001?store=migros")
    assert response.status_code == 200
    assert "migros" in response.json()["history"]
    assert "coop" not in response.json()["history"]

def test_prices_latest_no_duplicate_stores(client):
    response = client.get("/prices/latest/7610000100001")
    stores = [p["store"] for p in response.json()["prices"]]
    assert len(stores) == len(set(stores))


# ── Promotions ────────────────────────────────────────────────

def test_promotions_returns_list(client):
    response = client.get("/promotions")
    assert response.status_code == 200
    data = response.json()
    assert "promotions" in data
    assert "count" in data

def test_promotions_sorted_by_discount(client):
    response = client.get("/promotions?limit=10")
    discounts = [
        p["discount_pct"] for p in response.json()["promotions"]
        if p["discount_pct"] is not None
    ]
    assert discounts == sorted(discounts, reverse=True)

def test_promotions_store_filter(client):
    response = client.get("/promotions?store=migros")
    assert response.status_code == 200
    for p in response.json()["promotions"]:
        assert p["store"] == "migros"

def test_promotions_required_fields(client):
    for p in client.get("/promotions").json()["promotions"]:
        assert "gtin" in p
        assert "store" in p
        assert "promo_price_chf" in p
        assert "discount_pct" in p


# ── Basket ────────────────────────────────────────────────────

def test_basket_calculate(client):
    response = client.post("/basket/calculate", json={
        "items": [
            {"gtin": "7610000100001", "quantity": 2},
            {"gtin": "7610001100001", "quantity": 1}
        ],
        "lang": "en"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["items_count"] == 2
    assert data["cheapest_complete_store"] is not None
    assert len(data["item_breakdown"]) == 2

def test_basket_cheapest_is_actually_cheapest(client):
    response = client.post("/basket/calculate", json={
        "items": [{"gtin": "7610000100001", "quantity": 1}]
    })
    data = response.json()
    cheapest = data["cheapest_complete_store"]
    cheapest_total = data["cheapest_complete_total"]
    for store, total in data["store_totals_chf"].items():
        if total > 0:
            assert total >= cheapest_total

def test_basket_empty_rejected(client):
    assert client.post(
        "/basket/calculate", json={"items": []}
    ).status_code == 422


# ── Scan ──────────────────────────────────────────────────────

def test_scan_known_barcode(client):
    response = client.post("/scan", json={"barcode": "7610000100001", "lang": "en"})
    assert response.status_code == 200
    data = response.json()
    assert data["gtin"] == "7610000100001"
    assert len(data["products"]) > 0
    assert len(data["prices"]) > 0

def test_scan_unknown_barcode(client):
    assert client.post(
        "/scan", json={"barcode": "9999999999999"}
    ).status_code == 404

def test_scan_halal_product(client):
    response = client.post("/scan", json={"barcode": "7610000500001", "lang": "en"})
    assert response.status_code == 200
    for p in response.json()["products"]:
        assert p["ontology_tags"].get("halal") is True

def test_scan_no_duplicate_store_prices(client):
    response = client.post("/scan", json={"barcode": "7610000100001"})
    stores = [p["store"] for p in response.json()["prices"]]
    assert len(stores) == len(set(stores))


# ── Admin ─────────────────────────────────────────────────────

def test_admin_no_key_returns_403(client):
    assert client.get("/admin/stats").status_code == 403

def test_admin_wrong_key_returns_403(client):
    assert client.get(
        "/admin/stats", headers={"x-admin-key": "wrongkey"}
    ).status_code == 403

def test_admin_stats_correct_key(client, admin_key):
    response = client.get("/admin/stats", headers={"x-admin-key": admin_key})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "migros" in data["public_stores"]
    assert "lidl" in data["public_stores"]

def test_admin_health_correct_key(client, admin_key):
    response = client.get("/admin/health", headers={"x-admin-key": admin_key})
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "2.0.0"
    assert data["admin_key_set"] is True
