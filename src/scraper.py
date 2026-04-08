import logging
from playwright.sync_api import sync_playwright

from src.parser import parse_price

logger = logging.getLogger(__name__)


def scrape_product(url: str, timeout_ms: int = 30000) -> list[dict]:
    """Scrape all weight-variant prices from an HSN product page.

    Uses Playwright to render the page, clicks each variant button,
    and collects the updated price after each click.

    Returns a list of dicts with keys: variant, price, original_price, discount_pct.
    """
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

            page.wait_for_selector(
                "[data-price-type='finalPrice'] .price, .price-wrapper .price",
                timeout=timeout_ms,
            )

            variant_buttons = page.query_selector_all(
                "[data-attribute-code='formato'] .swatch-option, "
                ".swatch-attribute .swatch-option"
            )

            if not variant_buttons:
                price_text = _get_price_text(page, "finalPrice")
                old_price_text = _get_price_text(page, "oldPrice")
                price = parse_price(price_text)
                old_price = parse_price(old_price_text)
                discount = None
                if price and old_price and old_price > 0:
                    discount = round((1 - price / old_price) * 100, 1)
                if price:
                    results.append(
                        {
                            "variant": "default",
                            "price": price,
                            "original_price": old_price,
                            "discount_pct": discount,
                        }
                    )
            else:
                for btn in variant_buttons:
                    label = (
                        btn.get_attribute("data-option-label")
                        or btn.inner_text().strip()
                    )
                    btn.click()
                    page.wait_for_timeout(500)

                    price_text = _get_price_text(page, "finalPrice")
                    old_price_text = _get_price_text(page, "oldPrice")
                    price = parse_price(price_text)
                    old_price = parse_price(old_price_text)
                    discount = None
                    if price and old_price and old_price > 0:
                        discount = round((1 - price / old_price) * 100, 1)
                    if price:
                        results.append(
                            {
                                "variant": label,
                                "price": price,
                                "original_price": old_price,
                                "discount_pct": discount,
                            }
                        )

                    logger.info(f"  {label}: {price}€ (was {old_price}€)")

        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
        finally:
            browser.close()

    return results


def _get_price_text(page, price_type: str) -> str | None:
    """Extract the text content of a price element by its data-price-type attribute."""
    el = page.query_selector(f"[data-price-type='{price_type}'] .price")
    if el:
        return el.inner_text()
    return None
