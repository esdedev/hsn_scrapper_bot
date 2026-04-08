import logging
from playwright.sync_api import sync_playwright

from src.parser import parse_price, parse_discount

logger = logging.getLogger(__name__)


def scrape_product(url: str, timeout_ms: int = 30000) -> list[dict]:
    """Scrape the current price from an HSN product page.

    HSN uses Alpine.js (Hyva theme). The actual product price is in a
    .price-box that contains a .tag__discount element (distinguishing it
    from per-serving/per-100g price boxes). Prices are rendered by Alpine.js
    so we read innerText of visible elements, not data attributes.

    Returns one result per product (the currently selected size/flavor).
    """
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            page.wait_for_timeout(2000)

            result = _read_main_price(page)
            if result:
                results.append(result)
                logger.info(f"  {result['variant']}: {result['price']}€ "
                            f"(was {result.get('original_price')}€, "
                            f"-{result.get('discount_pct')}%)")
            else:
                logger.warning("  Could not extract price")

        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
        finally:
            browser.close()

    return results


def _read_main_price(page) -> dict | None:
    """Extract the main product price from the page.

    Strategy: Find the price-box that contains a .tag__discount (the actual
    product price, not per-serving prices). Read visible text via innerText.
    Also detect the currently selected size from the page.
    """
    data = page.evaluate("""() => {
        const main = document.querySelector('.product-info-main') || document;

        // Find the main product price box — the one with the discount tag
        // (per-serving and per-100g boxes don't have discount tags)
        let priceBox = null;
        for (const pb of main.querySelectorAll('.price-box')) {
            if (pb.closest('.product-info-wrapper')) continue;
            if (pb.querySelector('.tag__discount')) {
                priceBox = pb;
                break;
            }
        }

        // Fallback: find any price-box not inside .price-related-pdp
        if (!priceBox) {
            for (const pb of main.querySelectorAll('.price-box')) {
                if (pb.closest('.product-info-wrapper')) continue;
                if (pb.closest('.price-related-pdp')) continue;
                const text = pb.innerText;
                if (text && text.includes('€')) {
                    priceBox = pb;
                    break;
                }
            }
        }

        if (!priceBox) return null;

        // Read the final (discounted) price — .primary-price innerText
        let finalPriceText = null;
        const primaryEls = priceBox.querySelectorAll('.primary-price');
        for (const el of primaryEls) {
            const text = el.innerText.trim();
            if (text && text.includes('€')) {
                finalPriceText = text;
                break;
            }
        }

        // Read the old (strikethrough) price
        let oldPriceText = null;
        const oldEls = priceBox.querySelectorAll('.line-through');
        for (const el of oldEls) {
            const text = el.innerText.trim();
            if (text && text.includes('€') && text.length < 30) {
                oldPriceText = text;
                break;
            }
        }

        // Read discount tag
        let discountText = null;
        const discountEl = priceBox.querySelector('.tag__discount');
        if (discountEl) discountText = discountEl.innerText.trim();

        // Detect currently selected size/format
        // Look for format info in product options or title
        let variant = 'default';

        // Check super_attribute selects for a size-like selected option
        for (const s of main.querySelectorAll('select[name^="super_attribute"]')) {
            const selected = s.options[s.selectedIndex];
            if (selected && selected.value) {
                // Check if any option text mentions weight
                const hasWeightOpts = Array.from(s.options).some(
                    o => /\\d+\\s*(g|kg)/i.test(o.text)
                );
                if (hasWeightOpts && /\\d+\\s*(g|kg)/i.test(selected.text)) {
                    variant = selected.text.trim();
                    break;
                }
            }
        }

        // Fallback: extract weight from product title
        if (variant === 'default') {
            const h1 = main.querySelector('h1');
            if (h1) {
                const match = h1.textContent.match(/(\\d+\\s*(g|kg|Kg))/i);
                if (match) variant = match[1];
            }
        }

        return { finalPriceText, oldPriceText, discountText, variant };
    }""")

    if not data or not data["finalPriceText"]:
        return None

    final_price = parse_price(data["finalPriceText"])
    if not final_price:
        return None

    old_price = parse_price(data["oldPriceText"])

    discount = parse_discount(data["discountText"])
    if discount is None and old_price and old_price > 0:
        discount = round((1 - final_price / old_price) * 100, 1)

    return {
        "variant": data.get("variant", "default"),
        "price": final_price,
        "original_price": old_price,
        "discount_pct": discount,
    }
