# scrape_oos/home.py
from playwright.sync_api import sync_playwright
import re, csv, os

URL = "https://www.riderawrr.com/collection/parts"
OUTPUT_CSV = "oos_products.csv"

def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(URL, wait_until="domcontentloaded")

    # --- Keep clicking "Load more" and scrolling until nothing new shows up ---
    def try_click_load_more():
        try:
            btn = page.get_by_role("button", name=re.compile(r"load\s*more", re.I))
            if btn.count() > 0 and btn.first.is_visible() and btn.first.is_enabled():
                btn.first.click()
                return True
        except Exception:
            pass
        return False

    last = -1
    stable_iters = 0
    for _ in range(60):
        clicked = try_click_load_more()
        page.wait_for_timeout(600)

        # Scroll to trigger lazy load
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(800)

        count_now = page.locator("smootify-product").count()
        stable_iters = stable_iters + 1 if count_now == last else 0
        last = count_now

        if stable_iters >= 3 and not clicked:
            break

    # --- Extract product info ---
    products = page.locator("smootify-product")
    total = products.count()

    oos_rows = []  # list of (name, sku)
    for i in range(total):
        prod = products.nth(i)

        stock_raw = norm(prod.get_attribute("data-stock"))
        if stock_raw.isdigit() and int(stock_raw) == 0:
            # Try to get name
            title_loc = prod.locator('h5[product="title"].product-title, h5.product-title, [product="title"]')
            name = ""
            if title_loc.count() > 0:
                name = norm(title_loc.inner_text())
            else:
                # fallback: link text
                link = prod.locator('a[product="url"]')
                if link.count() > 0:
                    name = norm(link.first.inner_text())
            if not name:
                continue

            # Get SKU
            sku = ""
            sku_loc = prod.locator('[variant="sku"]')
            if sku_loc.count() > 0:
                sku = norm(sku_loc.inner_text())

            oos_rows.append((name, sku))

    # Deduplicate & sort by (name, sku)
    oos_rows = sorted(set(oos_rows), key=lambda x: (x[0].lower(), x[1].lower()))

    # --- NEW: Filter to ensure no duplicate SKUs (keeps first seen non-empty SKU) ---
    filtered = []
    seen_skus = set()
    for name, sku in oos_rows:
        key = (sku or "").strip().lower()
        if key:
            if key in seen_skus:
                continue
            seen_skus.add(key)
        filtered.append((name, sku))
    oos_rows = filtered
    # -------------------------------------------------------------------------------

    # Print summary
    print(f"Total products found: {total}")
    print(f"Out of stock products: {len(oos_rows)}")
    for name, sku in oos_rows:
        print(f"- {name} ({sku})" if sku else f"- {name}")

    # Write CSV
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["product_name", "sku"])
        writer.writerows(oos_rows)

    print(f"\nWrote CSV to: {os.path.abspath(OUTPUT_CSV)}")

    browser.close()