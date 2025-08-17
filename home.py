# home.py
from playwright.sync_api import sync_playwright
import re

URL = "https://www.riderawrr.com/collection/parts"

def slug_to_title(href: str) -> str:
    try:
        slug = href.rstrip("/").split("/")[-1]
        return " ".join(part.capitalize() for part in slug.replace("-", " ").split())
    except Exception:
        return ""

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)  # set False to watch
    page = browser.new_page()
    page.goto(URL, wait_until="domcontentloaded")

    # Wait until real products (with data-stock) are present
    page.wait_for_function(
        """() => Array.from(document.querySelectorAll('smootify-product'))
                      .some(el => el.getAttribute('data-stock') !== null)""",
        timeout=60000
    )

    # ---- Load everything: try 'Load More' + scroll until count stops growing ----
    def try_click_load_more():
        try:
            btn = page.get_by_role("button", name=re.compile(r"load\\s*more", re.I))
            if btn.count() > 0:
                btn.first.click(timeout=2000)
                return True
        except Exception:
            pass
        return False

    last = -1
    stable_iters = 0
    for _ in range(50):
        # click load-more if present
        clicked = try_click_load_more()
        page.wait_for_timeout(800)

        # scroll to bottom to trigger lazy load
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(900)

        # small jiggle to kick observers
        page.evaluate("window.scrollBy(0, -200)")
        page.wait_for_timeout(200)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(300)

        count_now = page.locator("smootify-product").count()
        if count_now == last:
            stable_iters += 1
        else:
            stable_iters = 0
        last = count_now

        if stable_iters >= 3 and not clicked:
            break

    all_products = page.locator("smootify-product")
    total_all = all_products.count()

    # Keep only canonical parts: cards with a link to /product/...
    parts = all_products.filter(has=page.locator('a[product="url"][href^="/product/"]'))
    total_parts = parts.count()

    #print(f"Total smootify-product in DOM: {total_all}")
    #print(f"Parts candidates (with /product/ link): {total_parts}")

    seen_handles = set()
    oos_names = []

    for i in range(total_parts):
        prod = parts.nth(i)

        # Skip search widget if present
        if (prod.get_attribute("data-id") or "").strip().lower() == "search":
            continue

        # Unique handle (href)
        link = prod.locator('a[product="url"]')
        if link.count() == 0:
            continue
        href = (link.first.get_attribute("href") or "").strip()
        if not href.startswith("/product/"):
            continue
        if href in seen_handles:
            continue
        seen_handles.add(href)

        # Title: tag -> link text/attrs -> slug
        title_loc = prod.locator('h5[product="title"].product-title, h5.product-title, [product="title"]')
        name = ""
        if title_loc.count() > 0:
            try:
                name = (title_loc.inner_text() or "").strip()
            except Exception:
                name = ""
        if not name:
            try:
                name = (link.first.inner_text() or "").strip()
            except Exception:
                name = ""
        if not name:
            name = (link.first.get_attribute("aria-label") or link.first.get_attribute("title") or "").strip()
        if not name:
            name = slug_to_title(href)
        if not name:
            continue

        # ---- Availability (attributes only; robust) ----
        classes = (prod.get_attribute("class") or "").lower()
        stock_s = (prod.get_attribute("data-stock") or "").strip()

        is_oos = (
            "is-not-available" in classes
            or "is-currently-out-of-stock" in classes
            or stock_s == "0"
        )
        if is_oos:
            oos_names.append(name)

    oos_unique_sorted = sorted(dict.fromkeys(oos_names))
    #print(f"\nUnique parts found: {len(seen_handles)}")
    #print(f"Out of stock (unique parts): {len(oos_unique_sorted)}")
    # for n in oos_unique_sorted:
    #     print("-", n)

    browser.close()






