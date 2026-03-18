# ============================================================
# WISEMARKET — AGENT SERVICE
# ============================================================
# Intent detection → DB queries → LLM refiner
# Personalised by user_preferences + user_chat_history
# ============================================================
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from backend.api.db import get_supabase_client
from backend.config.stores import PUBLIC_STORES
from backend.services.llm_client import (
    build_messages,
    build_messages_with_history,
    call_intent,
    call_refiner,
)

logger = logging.getLogger(__name__)

# ── Intent definitions ────────────────────────────────────────

INTENTS = [
    "find_product",      # find me oat milk / show me vegan pasta
    "check_dietary",     # is this halal / can I eat this
    "price_check",       # where is milk cheapest / price of salmon
    "compare_stores",    # migros vs coop for pasta
    "basket_advice",     # what is cheapest for my list
    "scan_lookup",       # barcode / GTIN lookup
    "nutrition_query",   # how much protein in chicken / nutri score
    "promotion_search",  # what is on sale / any deals today
    "general",           # anything else
]

DIETARY_KEYWORDS = {
    "halal":       ["halal", "حلال"],
    "vegan":       ["vegan", "vegan", "végane", "vegano", "plant-based"],
    "vegetarian":  ["vegetarian", "vegetarisch", "végétarien", "vegetariano"],
    "gluten_free": ["gluten", "glutenfrei", "sans gluten", "senza glutine", "coeliac"],
    "lactose_free":["lactose", "laktose", "dairy free", "laktosefrei"],
    "organic":     ["organic", "bio", "biologisch", "biologique", "biologico"],
    "low_sugar":   ["sugar", "zucker", "sucre", "zucchero", "diabetic"],
    "high_protein":["protein", "proteinreich", "protéine", "proteina"],
    "nut_free":    ["nut", "nuss", "noix", "noce", "peanut"],
}

STORE_KEYWORDS = {s: s for s in PUBLIC_STORES}


# ── User profile loader ───────────────────────────────────────

def _load_user_profile(user_id: Optional[str]) -> Optional[Dict]:
    if not user_id:
        return None
    try:
        supabase = get_supabase_client()
        resp = (
            supabase.table("user_preferences")
            .select("*")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("Could not load user profile: %s", e)
        return None


def _load_chat_history(user_id: Optional[str], limit: int = 6) -> List[Dict]:
    if not user_id:
        return []
    try:
        supabase = get_supabase_client()
        resp = (
            supabase.table("user_chat_history")
            .select("input, response")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        history = []
        for row in reversed(resp.data):
            if row.get("input"):
                history.append({"role": "user", "content": row["input"]})
            if row.get("response"):
                history.append({"role": "assistant", "content": row["response"]})
        return history
    except Exception as e:
        logger.warning("Could not load chat history: %s", e)
        return []


# ── Intent detection ──────────────────────────────────────────

def _detect_intent(user_input: str, lang: str) -> str:
    system = """You are an intent classifier for a Swiss supermarket app.
Classify the user message into exactly one of these intents:
find_product, check_dietary, price_check, compare_stores,
basket_advice, scan_lookup, nutrition_query, promotion_search, general

Reply with ONLY the intent name. Nothing else."""

    messages = build_messages(system, user_input)
    try:
        result = call_intent(messages, max_tokens=20).strip().lower()
        for intent in INTENTS:
            if intent in result:
                return intent
    except Exception as e:
        logger.warning("Intent detection failed: %s", e)
    return "general"


def _extract_dietary_filters(text: str) -> Dict[str, bool]:
    text_lower = text.lower()
    filters = {}
    for tag, keywords in DIETARY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            filters[tag] = True
    return filters


def _extract_store(text: str) -> Optional[str]:
    text_lower = text.lower()
    for store in PUBLIC_STORES:
        if store in text_lower:
            return store
    return None


# ── DB query agents ───────────────────────────────────────────

def _extract_search_term(user_input: str, lang: str) -> str:
    """Extract the key product search term from natural language input."""
    system = """Extract only the product name from this shopping query.
Return 1-3 words only. Examples:
'show me halal chicken' -> chicken
'where is milk cheapest' -> milk
'find vegan pasta' -> pasta
'was kostet Milch' -> Milch
Reply with ONLY the product name, no quotes, no punctuation."""
    messages = build_messages(system, user_input)
    try:
        result = call_intent(messages, max_tokens=10).strip()
        result = result.strip()
        return result if len(result) > 1 else user_input
    except Exception:
        return user_input


def _agent_find_product(
    query: str,
    dietary: Dict,
    store: Optional[str],
    profile: Optional[Dict],
    lang: str,
) -> Dict:
    supabase = get_supabase_client()
    name_col = f"name_{lang}" if lang in ("en", "de", "fr", "it") else "name_en"

    q = (
        supabase.table("products")
        .select(
            "gtin, store, name_en, name_de, name_fr, name_it, "
            "brand, category, ontology_tags, allergens, "
            "nutrition_cache, pack_size_raw, image_url"
        )
        .eq("is_active", True)
        .in_("store", [store] if store else PUBLIC_STORES)
        .ilike(name_col, f"%{query}%")
    )

    # Apply dietary filters
    for tag, val in dietary.items():
        if val:
            q = q.eq(f"ontology_tags->>{tag}", "true")

    # Apply user preferences as soft filters
    if profile:
        for pref in ["halal", "vegan", "gluten_free", "lactose_free"]:
            if profile.get(pref) and pref not in dietary:
                q = q.eq(f"ontology_tags->>{pref}", "true")

    resp = q.limit(5).execute()
    return {"products": resp.data, "count": len(resp.data)}


def _agent_similar_products(
    category: Optional[str],
    dietary: Dict,
    profile: Optional[Dict],
    lang: str,
    exclude_gtins: List[str] = [],
    limit: int = 4,
) -> Dict:
    """
    Find similar products when exact search returns nothing.
    Matches by category + dietary tags.
    """
    supabase = get_supabase_client()

    q = (
        supabase.table("products")
        .select(
            "gtin, store, name_en, name_de, name_fr, name_it, "
            "brand, category, ontology_tags, pack_size_raw, image_url"
        )
        .eq("is_active", True)
        .in_("store", PUBLIC_STORES)
    )

    if category:
        q = q.eq("category", category)

    # Apply dietary filters
    for tag, val in dietary.items():
        if val:
            q = q.eq(f"ontology_tags->>{tag}", "true")

    # Apply user preferences
    if profile:
        for pref in ["halal", "vegan", "gluten_free"]:
            if profile.get(pref) and pref not in dietary:
                q = q.eq(f"ontology_tags->>{pref}", "true")

    resp = q.limit(limit * 3).execute()

    # Filter out already-seen GTINs
    results = [p for p in resp.data if p.get("gtin") not in exclude_gtins]

    # Deduplicate by GTIN (keep first store)
    seen = set()
    unique = []
    for p in results:
        if p["gtin"] not in seen:
            seen.add(p["gtin"])
            unique.append(p)

    return {"products": unique[:limit], "count": len(unique[:limit])}


def _agent_price_check(gtin: str, store: Optional[str]) -> Dict:
    supabase = get_supabase_client()
    resp = (
        supabase.table("store_price_snapshot")
        .select("*")
        .eq("gtin", gtin)
        .order("snapshot_date", desc=True)
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data else {}


def _agent_promotions(store: Optional[str], lang: str) -> Dict:
    supabase = get_supabase_client()
    name_col = f"name_{lang}" if lang in ("en", "de", "fr", "it") else "name_en"
    q = (
        supabase.table("product_prices")
        .select(
            "gtin, store, price_chf, original_price_chf, "
            "discount_pct, promotion_label, promotion_ends, "
            "products(name_en, name_de, name_fr, name_it, category)"
        )
        .eq("is_promotion", True)
        .in_("store", [store] if store else PUBLIC_STORES)
        .order("discount_pct", desc=True)
        .limit(5)
    )
    resp = q.execute()
    return {"promotions": resp.data, "count": len(resp.data)}


def _agent_nutrition(gtin: str, store: Optional[str]) -> Dict:
    supabase = get_supabase_client()
    q = (
        supabase.table("products")
        .select("id, name_en, store")
        .eq("gtin", gtin)
        .in_("store", [store] if store else PUBLIC_STORES)
        .limit(1)
    )
    prod = q.execute()
    if not prod.data:
        return {}
    product_id = prod.data[0]["id"]
    nutr = (
        supabase.table("nutrition_facts")
        .select("*")
        .eq("product_id", product_id)
        .limit(1)
        .execute()
    )
    return {
        "product": prod.data[0],
        "nutrition": nutr.data[0] if nutr.data else {},
    }


# ── System prompt builder ─────────────────────────────────────

def _build_system_prompt(
    profile: Optional[Dict],
    lang: str,
    user_name: Optional[str] = None,
) -> str:
    lang_names = {"en": "English", "de": "German", "fr": "French", "it": "Italian"}
    lang_name = lang_names.get(lang, "English")

    # Personal context
    if profile:
        prefs = []
        for tag in ["halal", "vegan", "vegetarian", "gluten_free",
                    "lactose_free", "keto", "low_sugar", "nut_allergy"]:
            if profile.get(tag):
                prefs.append(tag.replace("_", " "))
        pref_str = ", ".join(prefs) if prefs else "no specific dietary restrictions"
        stores = profile.get("preferred_stores") or []
        store_str = ", ".join(stores) if stores else "any store"
        budget = profile.get("max_price_chf")
        budget_str = f"CHF {budget}" if budget else "no fixed budget"
        name_str = f"The user's name is {user_name}. " if user_name else ""
    else:
        name_str = ""
        pref_str = "unknown"
        store_str = "any store"
        budget_str = "unknown"

    return f"""You are WiseMarket, a smart Swiss supermarket shopping assistant.
You help users find products, check dietary compatibility, compare prices, and shop smarter.
Switzerland has 4 languages — always respond in {lang_name}.

{name_str}User dietary profile: {pref_str}.
Preferred stores: {store_str}. Budget: {budget_str}.

Guidelines:
- Max 2-3 sentences. Be direct and warm.
- Always cite specific product names, prices in CHF, and store names
- Flag allergens and dietary conflicts clearly
- If exact product not found: say so in 1 sentence, then suggest alternatives
- Never guess ingredients — only use verified data provided to you
- If no data at all: say so in 1 sentence only"""


# ── Response composer ─────────────────────────────────────────

def _compose_and_refine(
    intent: str,
    data: Dict,
    user_input: str,
    system_prompt: str,
    history: List[Dict],
    lang: str,
) -> str:
    # Summarise DB data for the LLM
    data_summary = json.dumps(data, ensure_ascii=False, default=str)[:2000]

    user_msg = f"""User asked: {user_input}

Verified data from database:
{data_summary}

Based only on this data, give a helpful, warm, concise answer in the correct language.
Do not invent prices, ingredients, or product details not shown above."""

    messages = build_messages_with_history(system_prompt, history, user_msg)

    try:
        return call_refiner(messages, max_tokens=150)
    except Exception as e:
        logger.error("Refiner failed: %s", e)
        return "I'm sorry, I couldn't process your request right now. Please try again."


# ── Main agent entry point ────────────────────────────────────

def run_agent(
    user_input: str,
    lang: str = "en",
    user_id: Optional[str] = None,
    mode: str = "chat",
    store: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Main agent pipeline.

    Returns:
        response     : str  — final answer for the user
        intent       : str  — detected intent
        data         : dict — raw DB data used
        products     : list — products returned (if any)
    """
    # 1. Load user context
    profile  = _load_user_profile(user_id)
    history  = _load_chat_history(user_id)
    system   = _build_system_prompt(profile, lang)

    # 2. Detect intent
    intent = _detect_intent(user_input, lang)
    logger.info("Intent detected: %s", intent)

    # 3. Extract filters from input
    dietary = _extract_dietary_filters(user_input)
    detected_store = store or _extract_store(user_input)

    # 4. Route to correct DB agent
    data = {}
    products = []

    if intent == "find_product":
        data = _agent_find_product(
            user_input, dietary, detected_store, profile, lang
        )
        products = data.get("products", [])

    elif intent == "check_dietary":
        data = _agent_find_product(
            user_input, dietary, detected_store, profile, lang
        )
        products = data.get("products", [])

    elif intent in ("price_check", "compare_stores"):
        gtin_match = re.search(r'\b\d{8,14}\b', user_input)
        if gtin_match:
            data = _agent_price_check(gtin_match.group(), None)
        else:
            search_term = _extract_search_term(user_input, lang)
            prod_data = _agent_find_product(
                search_term, {}, None, profile, lang
            )
            if prod_data.get("products"):
                gtin = prod_data["products"][0].get("gtin")
                price_snapshot = _agent_price_check(gtin, None)
                data = {
                    "product":        prod_data["products"][0],
                    "cheapest_store": price_snapshot.get("cheapest_store"),
                    "cheapest_price": price_snapshot.get("cheapest_price"),
                    "all_prices":     price_snapshot.get("prices_chf", {}),
                    "per_100g":       price_snapshot.get("prices_per_100g", {}),
                    "spread_pct":     price_snapshot.get("price_spread_pct"),
                }
                products = prod_data["products"]
            else:
                data = {"message": "Product not found"}

    elif intent == "nutrition_query":
        gtin_match = re.search(r'\b\d{8,14}\b', user_input)
        if gtin_match:
            data = _agent_nutrition(gtin_match.group(), detected_store)
        else:
            prod_data = _agent_find_product(
                user_input, {}, detected_store, profile, lang
            )
            if prod_data.get("products"):
                gtin = prod_data["products"][0].get("gtin")
                data = _agent_nutrition(gtin, detected_store)
                products = prod_data["products"]

    elif intent == "scan_lookup":
        gtin_match = re.search(r'\b\d{8,14}\b', user_input)
        if gtin_match:
            supabase = get_supabase_client()
            resp = (
                supabase.table("products")
                .select("*")
                .eq("gtin", gtin_match.group())
                .in_("store", PUBLIC_STORES)
                .execute()
            )
            data = {"products": resp.data}
            products = resp.data

    # general intent — no DB query, LLM answers from context only

    # 5. Compose and refine answer
    response = _compose_and_refine(
        intent, data, user_input, system, history, lang
    )

    # 6. Save to chat history
    if user_id:
        try:
            supabase = get_supabase_client()
            supabase.table("user_chat_history").insert({
                "user_id":          user_id,
                "mode":             mode,
                "input":            user_input,
                "response":         response,
                "products_returned": [p.get("gtin") for p in products],
                "lang":             lang,
            }).execute()
        except Exception as e:
            logger.warning("Could not save chat history: %s", e)

    return {
        "response": response,
        "intent":   intent,
        "products": products,
        "data":     data,
    }


# ── Greeting generator ────────────────────────────────────────

def generate_greeting(
    user_id: Optional[str],
    lang: str = "en",
    user_name: Optional[str] = None,
) -> str:
    """
    Generate a personalised greeting when user opens the app.
    Uses profile to make it relevant.
    """
    profile = _load_user_profile(user_id)
    system  = _build_system_prompt(profile, lang, user_name)

    if profile and user_name:
        prefs = [
            tag.replace("_", " ")
            for tag in ["halal", "vegan", "vegetarian", "gluten_free"]
            if profile.get(tag)
        ]
        pref_hint = f"They prefer {', '.join(prefs)}." if prefs else ""
        user_msg = (
            f"Greet {user_name} personally. {pref_hint} "
            f"Make it warm, short (1-2 sentences), and offer to help them shop."
        )
    else:
        user_msg = (
            "Greet a new guest user. "
            "Welcome them to WiseMarket, 1-2 sentences, "
            "mention you can help find products, check dietary needs, compare prices."
        )

    messages = build_messages(system, user_msg)
    try:
        return call_refiner(messages, max_tokens=80)
    except Exception:
        greetings = {
            "en": "Welcome to WiseMarket! How can I help you shop smarter today?",
            "de": "Willkommen bei WiseMarket! Wie kann ich Ihnen heute helfen?",
            "fr": "Bienvenue sur WiseMarket! Comment puis-je vous aider?",
            "it": "Benvenuto su WiseMarket! Come posso aiutarti oggi?",
        }
        return greetings.get(lang, greetings["en"])
