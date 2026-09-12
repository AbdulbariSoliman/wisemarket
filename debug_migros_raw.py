# ============================================================
# WISEMARKET - DEBUG: dump raw Migros API response
# ============================================================
import asyncio
import json
from playwright.async_api import async_playwright

SEARCH_TERM = "rindsburger"


async def main():
    results = []

    async def handle_response(response):
        if 'product-display/public/v4/product-cards' in response.url and response.status == 200:
            try:
                data = await response.json()
                if isinstance(data, list):
                    results.extend(data)
            except Exception:
                pass

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="de-CH",
        )
        page = await context.new_page()
        page.on('response', handle_response)

        await page.goto(f"https://www.migros.ch/de/search?query={SEARCH_TERM}", timeout=20000, wait_until="networkidle")
        await page.wait_for_timeout(2000)

        await browser.close()

    print(f"Got {len(results)} raw product entries.\n")

    for i, item in enumerate(results[:2]):
        print(f"===== RAW PRODUCT {i+1} =====")
        print(json.dumps(item, indent=2, ensure_ascii=False))
        print()

    print("===== 'offer' section for all results =====")
    for i, item in enumerate(results):
        title = item.get("title") or item.get("name") or "?"
        offer = item.get("offer") or {}
        print(f"[{i}] {title}")
        print(json.dumps(offer, indent=2, ensure_ascii=False))
        print()


if __name__ == "__main__":
    asyncio.run(main())