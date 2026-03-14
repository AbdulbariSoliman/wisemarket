# ============================================================
# WISEMARKET — STORE CONFIGURATION
# ============================================================
# Add new stores here. public=True means the store is live
# in the API. public=False means data exists but not yet
# exposed to end users.
# ============================================================

STORES = {
    "migros": {
        "public": True,
        "crawl_delay": 2,
        "base_url": "https://www.migros.ch",
        "scrape_type": "playwright",
    },
    "coop": {
        "public": True,
        "crawl_delay": 5,
        "base_url": "https://www.coop.ch",
        "scrape_type": "playwright",
    },
    "aldi": {
        "public": True,
        "crawl_delay": 3,
        "base_url": "https://www.aldi.ch",
        "scrape_type": "httpx_bs4",
    },
    "lidl": {
        "public": True,
        "crawl_delay": 3,
        "base_url": "https://www.lidl.ch",
        "scrape_type": "httpx_bs4",
    },
    "denner": {
        "public": False,
        "reason": "Pending scraper implementation",
        "base_url": "https://www.denner.ch",
        "scrape_type": "httpx_bs4",
    },
}

PUBLIC_STORES = [k for k, v in STORES.items() if v.get("public")]
ALL_STORES    = list(STORES.keys())
