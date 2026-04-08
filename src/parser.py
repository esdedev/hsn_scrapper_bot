import re
from html.parser import HTMLParser


def parse_price(price_text: str) -> float | None:
    """Convert a price string like '11,76 €' or '17,90\xa0€' to a float."""
    if not price_text:
        return None
    cleaned = (
        price_text.replace("\xa0", "")
        .replace("€", "")
        .replace("\u202f", "")
        .strip()
    )
    # European format: 1.234,56 -> remove dots, replace comma with dot
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return None


def parse_discount(text: str) -> float | None:
    """Extract discount percentage from text like '-34%'."""
    if not text:
        return None
    match = re.search(r"(\d+(?:[.,]\d+)?)", text.replace(",", "."))
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def parse_product_page(html: str) -> list[dict]:
    """Extract price data from HSN product page HTML (Hyva/Alpine.js theme).

    HSN uses Alpine.js. Prices are in:
    - Final price: <span class="... primary-price ...">11,76 €</span>
    - Old price: <span class="... line-through ...">17,90 €</span>
    - Discount: <span class="tag tag__discount ...">-34%</span>
    - Variants: <div class="swatch-option" data-option-label="2 Kg">
    """

    class PriceExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.final_price = None
            self.old_price = None
            self.discount_pct = None
            self.variants = []
            self._in_primary_price = False
            self._in_old_price = False
            self._in_discount_tag = False

        def handle_starttag(self, tag, attrs):
            attrs_dict = dict(attrs)
            classes = attrs_dict.get("class", "")
            if tag == "span" and "primary-price" in classes:
                self._in_primary_price = True
            elif tag == "span" and "line-through" in classes:
                self._in_old_price = True
            elif tag == "span" and "tag__discount" in classes:
                self._in_discount_tag = True
            elif tag == "div" and "swatch-option" in classes:
                label = attrs_dict.get("data-option-label", "")
                if label:
                    self.variants.append(label)

        def handle_endtag(self, tag):
            if tag == "span":
                self._in_primary_price = False
                self._in_old_price = False
                self._in_discount_tag = False

        def handle_data(self, data):
            if self._in_primary_price and self.final_price is None:
                price = parse_price(data)
                if price is not None:
                    self.final_price = price
            elif self._in_old_price and self.old_price is None:
                price = parse_price(data)
                if price is not None:
                    self.old_price = price
            elif self._in_discount_tag and self.discount_pct is None:
                self.discount_pct = parse_discount(data)

    extractor = PriceExtractor()
    extractor.feed(html)

    if not extractor.variants:
        extractor.variants = ["default"]

    selected_variant = extractor.variants[0]

    results = []
    if extractor.final_price is not None:
        discount = extractor.discount_pct
        if discount is None and extractor.old_price and extractor.old_price > 0:
            discount = round(
                (1 - extractor.final_price / extractor.old_price) * 100, 1
            )
        results.append(
            {
                "variant": selected_variant,
                "price": extractor.final_price,
                "original_price": extractor.old_price,
                "discount_pct": discount,
            }
        )

    return results
