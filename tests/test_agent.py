# ============================================================
# WISEMARKET — AGENT TESTS
# Logic tests: the LLM and database tools are replaced with fakes,
# so these run without any API key or database.
# Integration tests (marked) run the agent against the seeded DB.
# ============================================================
import re

import pytest

import backend.services.agent as agent
import backend.services.llm_client as llm


# ── Fake LLM ──────────────────────────────────────────────────

INTENT_RULES = [
    (r"cheap|price|kostet", "price_check"),
    (r"sale|deal|aktion", "promotion_search"),
    (r"halal|vegan|gluten", "check_dietary"),
    (r"protein|calorie", "nutrition_query"),
    (r"find|show|zeig", "find_product"),
]


def _fake_llm(extract_fails=False):
    def fake_call(model, messages, max_tokens=500, temperature=0.3):
        system, user = messages[0]["content"], messages[-1]["content"]
        if "intent classifier" in system:
            for pattern, intent in INTENT_RULES:
                if re.search(pattern, user, re.I):
                    return intent
            return "general"
        if "Extract only the product name" in system:
            if extract_fails:
                raise RuntimeError("LLM unavailable")
            words = agent._search_words(user)
            return words[-1] if words else user
        return "OK"
    return fake_call


@pytest.fixture
def fake_llm(monkeypatch):
    monkeypatch.setattr(llm, "_call", _fake_llm())


@pytest.fixture
def no_user(monkeypatch):
    monkeypatch.setattr(agent, "_load_user_profile", lambda uid: None)
    monkeypatch.setattr(agent, "_load_chat_history", lambda uid, limit=6: [])


# ── Search word extraction ────────────────────────────────────

@pytest.mark.parametrize("text, expected", [
    ("show me spaghetti", ["spaghetti"]),
    ("find vegan pasta", ["pasta"]),
    ("is the chicken halal", ["chicken"]),
    ("Zeig mir Haferdrink", ["haferdrink"]),
    ("où est le lait moins cher", ["lait"]),
    ("hackfleisch pasta tomaten", ["hackfleisch", "pasta", "tomaten"]),
])
def test_search_words_removes_filler(text, expected):
    assert agent._search_words(text) == expected


def test_extract_search_term_falls_back_without_llm(monkeypatch):
    monkeypatch.setattr(llm, "_call", _fake_llm(extract_fails=True))
    assert agent._extract_search_term("show me spaghetti", "en") == "spaghetti"


# ── Routing: the DB is searched with the product name, not the sentence ──

@pytest.mark.parametrize("question, intent", [
    ("show me spaghetti", "find_product"),
    ("is the spaghetti vegan", "check_dietary"),
])
def test_find_and_dietary_search_by_product_name(monkeypatch, fake_llm, no_user, question, intent):
    seen = {}

    def fake_find(query, dietary, store, profile, lang):
        seen["query"] = query
        return {"products": [{"gtin": "1", "name_en": "Spaghetti"}], "count": 1}

    monkeypatch.setattr(agent, "_agent_find_product", fake_find)
    result = agent.run_agent(question)
    assert result["intent"] == intent
    assert seen["query"] == "spaghetti"
    assert len(result["products"]) == 1


def test_nutrition_searches_by_product_name(monkeypatch, fake_llm, no_user):
    seen = {}

    def fake_find(query, dietary, store, profile, lang):
        seen["query"] = query
        return {"products": [{"gtin": "123"}], "count": 1}

    monkeypatch.setattr(agent, "_agent_find_product", fake_find)
    monkeypatch.setattr(agent, "_agent_nutrition", lambda gtin, store: {"nutrition": {"protein_g": 23}})
    result = agent.run_agent("how much protein in chicken")
    assert result["intent"] == "nutrition_query"
    assert seen["query"] == "chicken"
    assert result["data"]["nutrition"]["protein_g"] == 23


def test_promotion_intent_is_handled(monkeypatch, fake_llm, no_user):
    monkeypatch.setattr(
        agent, "_agent_promotions",
        lambda store, lang: {"promotions": [{"gtin": "1", "discount_pct": 20}], "count": 1},
    )
    result = agent.run_agent("any deals today")
    assert result["intent"] == "promotion_search"
    assert result["data"]["count"] == 1


@pytest.mark.parametrize("lang, word", [("en", "unavailable"), ("de", "nicht verfügbar")])
def test_database_error_returns_friendly_message(monkeypatch, fake_llm, no_user, lang, word):
    def broken(*args, **kwargs):
        raise ConnectionError("database down")

    monkeypatch.setattr(agent, "_agent_find_product", broken)
    result = agent.run_agent("show me milk", lang=lang)
    assert word in result["response"]
    assert result["products"] == []
    assert result["data"] == {"error": "database_unavailable"}


# ── Integration: real seeded database, fake LLM ───────────────

@pytest.mark.integration
@pytest.mark.parametrize("question, lang, expected_name", [
    ("show me spaghetti", "en", "Spaghetti 500g"),
    ("is the chicken halal", "en", "Halal Chicken Breast"),
    ("Zeig mir Haferdrink", "de", "Oat Drink 1L"),
])
def test_agent_finds_seeded_products(fake_llm, no_user, question, lang, expected_name):
    result = agent.run_agent(question, lang=lang)
    assert expected_name in [p.get("name_en") for p in result["products"]]


@pytest.mark.integration
def test_agent_price_check_returns_all_stores(fake_llm, no_user):
    result = agent.run_agent("where is milk cheapest")
    assert result["intent"] == "price_check"
    assert {p["store"] for p in result["products"]} == {"migros", "coop", "aldi"}
