from html.parser import HTMLParser


def parse_price(price_text: str) -> float | None:
    """Convert a price string like '35,90 €' to a float like 35.90."""
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


def parse_product_page(html: str) -> list[dict]:
    """Extract price data from an HSN product page HTML string.

    Returns a list of dicts with keys: variant, price, original_price, discount_pct.
    For static HTML (no JS), only the currently selected variant is returned.
    """

    class PriceExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.final_price = None
            self.old_price = None
            self.variants = []
            self._in_price_span = False
            self._current_price_type = None

        def handle_starttag(self, tag, attrs):
            attrs_dict = dict(attrs)
            if tag == "span" and attrs_dict.get("data-price-type") == "finalPrice":
                self._current_price_type = "final"
            elif tag == "span" and attrs_dict.get("data-price-type") == "oldPrice":
                self._current_price_type = "old"
            elif (
                tag == "span"
                and "price" in attrs_dict.get("class", "")
                and self._current_price_type
            ):
                self._in_price_span = True
            elif tag == "div" and "swatch-option" in attrs_dict.get("class", ""):
                label = attrs_dict.get("data-option-label", "")
                if label:
                    self.variants.append(label)

        def handle_endtag(self, tag):
            if tag == "span" and self._in_price_span:
                self._in_price_span = False
                self._current_price_type = None

        def handle_data(self, data):
            if self._in_price_span:
                price = parse_price(data)
                if price is not None:
                    if self._current_price_type == "final":
                        self.final_price = price
                    elif self._current_price_type == "old":
                        self.old_price = price

    extractor = PriceExtractor()
    extractor.feed(html)

    if not extractor.variants:
        extractor.variants = ["default"]

    selected_variant = extractor.variants[0]

    results = []
    if extractor.final_price is not None:
        discount = None
        if extractor.old_price and extractor.old_price > 0:
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
