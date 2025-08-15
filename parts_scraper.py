# parts_all_scraper.py
import asyncio
import csv
import re
import subprocess
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright, TimeoutError as PWTimeoutError

START_URL = "https://www.riderawrr.com/collection/parts"
OUTFILE = Path("parts_all.csv")
HEADLESS = True

PRICE_RE = re.compile(r"\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?")
SKU_RE   = re.compile(r"\bSKU[:\s-]*([A-Za-z0-9\-._/]+)\b", re.I)
OOS_RE   = re.compile(r"\b(out\s*of\s*stock|sold\s*out|unavailable)\b", re.I)

async def ensure_browser_then_launch(p):
    try:
        return await p.chromium.launch(headless=HEADLESS)
    except Exception as e:
        if "Executable doesn't exist" in str(e):
            print("→ Playwright browsers missing. Installing Chromium…")
            subprocess.run(["playwright", "install", "chromium"], check=True)
            return await p.chromium.launch(headless=HEADLESS)
        raise

async def click_load_more_until_done(page):
    """Click any visible ‘Load more’ until it disappears."""
    import re as _re
    while True:
        candidates = [
            page.get_by_role("button", name=_re.compile(r"load more", _re.I)),
            page.get_by_text(_re.compile(r"^\s*load more\s*$", _re.I)),
            page.locator("css=button:has-text('Load More')"),
            page.locator("css=a:has-text('Load More')"),
            page.locator("css=[data-action='load-more']"),
        ]
        target = None
        for loc in candidates:
            if await loc.count():
                target = loc.first
                break
        if not target:
            break
        try:
            await target.click(timeout=2000)
            await page.wait_for_timeout(900)
        except PWTimeoutError:
            break

async def scroll_to_bottom_until_idle(page, max_rounds=10):
    """Fallback for infinite-scroll grids: scroll down until page height stabilizes."""
    prev_h = 0
    same = 0
    for _ in range(max_rounds):
        h = await page.evaluate("() => document.body.scrollHeight")
        await page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(800)
        h2 = await page.evaluate("() => document.body.scrollHeight")
        if h2 == h == prev_h:
            same += 1
        else:
            same = 0
        prev_h = h2
        if same >= 2:
            break

def looks_like_product(href: str) -> bool:
    if not href:
        return False
    # Accept relative or absolute; look for /product or /products path segment
    path = urlparse(href).path.lower()
    return "/product" in path

async def collect_product_links_from_collection(page):
    """Return a de-duped list of absolute product URLs from the collection grid."""
    anchors = page.locator("a[href]")
    n = await anchors.count()
    links = set()
    for i in range(n):
        href = await anchors.nth(i).get_attribute("href")
        if looks_like_product(href):
            links.add(urljoin(START_URL, href))
    return sorted(links)

async def scrape_product(ctx, url: str):
    """Open a product page and extract title, price, sku, availability."""
    page = await ctx.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded")
        # Title: prefer <h1>, fall back to <meta property="og:title">
        title = ""
        h1 = page.locator("h1")
        if await h1.count():
            t = await h1.first.text_content()
            if t:
                title = " ".join(t.split())
        if not title:
            og = page.locator('meta[property="og:title"]')
            if await og.count():
                t = await og.first.get_attribute("content")
                if t:
                    title = " ".join(t.split())

        # Price: look for a visible element with a $ pattern; fallback to page text
        price = ""
        price_el = page.locator("*:text-matches('\\$\\s*\\d{1,3}(?:,\\d{3})*(?:\\.\\d{2})?')")
        if await price_el.count():
            ptxt = await price_el.first.text_content()
            if ptxt:
                m = PRICE_RE.search(ptxt)
                if m:
                    price = m.group(0)
        if not price:
            content = await page.content()
            m = PRICE_RE.search(content or "")
            if m:
                price = m.group(0)

        # Availability: look for OOS words in visible text; otherwise assume "In stock"
        availability = "In stock"
        text = (await page.text_content("body")) or ""
        if OOS_RE.search(text):
            availability = "Out of stock"

        # SKU (best effort)
        sku = ""
        m = SKU_RE.search(text)
        if m:
            sku = m.group(1)

        return {
            "title": title or "Unknown",
            "price": price,
            "sku": sku,
            "availability": availability,
            "url": url,
        }
    finally:
        await page.close()

def write_csv(rows, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["title", "price", "sku", "availability", "url"])
        w.writeheader()
        w.writerows(rows)

async def main():
    async with async_playwright() as p:
        browser = await ensure_browser_then_launch(p)
        ctx = await browser.new_context()

        page = await ctx.new_page()
        print(f"→ Opening {START_URL}")
        await page.goto(START_URL, wait_until="domcontentloaded")

        # Load everything available
        print("→ Expanding product list (Load more / scroll)…")
        await click_load_more_until_done(page)
        await scroll_to_bottom_until_idle(page)

        print("→ Collecting product links…")
        links = await collect_product_links_from_collection(page)
        print(f"→ Found {len(links)} product links")

        # Visit each product page and scrape details
        rows = []
        for idx, url in enumerate(links, 1):
            print(f"  [{idx}/{len(links)}] {url}")
            try:
                row = await scrape_product(ctx, url)
                rows.append(row)
            except Exception as e:
                print(f"   ! Error scraping {url}: {e}")

        rows.sort(key=lambda r: (r["title"].lower(), r["url"]))
        write_csv(rows, OUTFILE)
        print(f"✓ Wrote {len(rows)} items to {OUTFILE.resolve()}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())