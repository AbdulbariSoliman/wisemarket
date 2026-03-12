STORES = {
    "migros": {
        "public": True,
        "crawl_delay": 2,
    },
    "coop": {
        "public": True,
        "crawl_delay": 5,
    },
    "aldi": {
        "public": False,
        "reason": "Pending commercial scraping permission"
    }
}

PUBLIC_STORES = [k for k, v in STORES.items() if v["public"]]
