import logging
from playwright.sync_api import sync_playwright

from src.parser import parse_price, parse_discount

logger = logging.getLogger(__name__)


def scrape_product(url: str, timeout_ms: int = 30000) -> list[dict]:
    """Scrape all size-variant prices from an HSN product page.

    HSN uses Alpine.js (Hyva theme). Size variants are <label> elements
    inside .weight-options. Clicking each one updates the main price.
    We click each size, wait for price update, and read the result.
    """
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            page.wait_for_timeout(2000)

            # Get list of size variant labels
            size_labels = page.evaluate("""() => {
                const main = document.querySelector('.product-info-main') || document;
                const container = main.querySelector('.weight-options');
                if (!container) return [];
                const labels = [];
                for (const label of container.querySelectorAll('label')) {
                    const text = label.innerText.trim();
                    if (text) labels.push(text);
                }
                return labels;
            }""")

            if not size_labels:
                # No size variants — read the single price
                result = _read_main_price(page)
                if result:
                    result["variant"] = "default"
                    results.append(result)
                    logger.info(f"  default: {result['price']}€")
                return results

            logger.info(f"  Found {len(size_labels)} sizes: {size_labels}")

            # Click each size label and read the updated price
            label_els = page.query_selector_all(".weight-options label")
            for i, label_el in enumerate(label_els):
                size_name = size_labels[i] if i < len(size_labels) else f"size_{i}"
                label_el.click()
                page.wait_for_timeout(1000)

                result = _read_main_price(page)
                if result:
                    result["variant"] = size_name
                    results.append(result)
                    logger.info(f"  {size_name}: {result['price']}€ "
                                f"(was {result.get('original_price')}€, "
                                f"-{result.get('discount_pct')}%)")

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

        return { finalPriceText, oldPriceText, discountText };
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
        "price": final_price,
        "original_price": old_price,
        "discount_pct": discount,
    }
