import pytest
from src.parser import parse_product_page, parse_price, parse_discount


# Realistic mock HTML matching HSN's Hyva/Alpine.js theme
MOCK_HTML_WITH_DISCOUNT = """
<div class="price-box">
    <div class="old-price flex items-center">
        <span class="tag tag__discount uppercase font-bold">-34%</span>
        <span class="price text-primary-middle text-em line-through flex items-center">17,90&nbsp;€</span>
    </div>
    <div class="final-price inline-block flex">
        <span class="price text-display-bold title-3 font-extrabold primary-price text-hsn-red">11,76&nbsp;€</span>
    </div>
    <div class="swatch-option selected" data-option-label="500 g">500 g</div>
</div>
"""

MOCK_HTML_NO_DISCOUNT = """
<div class="price-box">
    <div class="final-price inline-block flex">
        <span class="price text-display-bold title-3 font-extrabold primary-price">20,00&nbsp;€</span>
    </div>
    <div class="swatch-option selected" data-option-label="1 Kg">1 Kg</div>
</div>
"""

MOCK_HTML_MULTIPLE_VARIANTS = """
<div class="price-box">
    <span class="tag tag__discount uppercase font-bold">-20%</span>
    <span class="price text-primary-middle text-em line-through">44,90&nbsp;€</span>
    <span class="price text-display-bold primary-price">35,90&nbsp;€</span>
    <div class="swatch-option selected" data-option-label="2 Kg">2 Kg</div>
    <div class="swatch-option" data-option-label="500 g">500 g</div>
    <div class="swatch-option" data-option-label="3 Kg">3 Kg</div>
</div>
"""


def test_parse_price_european_format():
    assert parse_price("11,76\xa0€") == 11.76
    assert parse_price("17,90 €") == 17.90
    assert parse_price("1.234,56€") == 1234.56
    assert parse_price("") is None
    assert parse_price(None) is None


def test_parse_discount_text():
    assert parse_discount("-34%") == 34.0
    assert parse_discount("-20%") == 20.0
    assert parse_discount("") is None
    assert parse_discount(None) is None


def test_parse_with_discount():
    results = parse_product_page(MOCK_HTML_WITH_DISCOUNT)
    assert len(results) == 1
    assert results[0]["variant"] == "500 g"
    assert results[0]["price"] == 11.76
    assert results[0]["original_price"] == 17.90
    assert results[0]["discount_pct"] == 34.0


def test_parse_no_original_price():
    results = parse_product_page(MOCK_HTML_NO_DISCOUNT)
    assert len(results) == 1
    assert results[0]["variant"] == "1 Kg"
    assert results[0]["price"] == 20.00
    assert results[0]["original_price"] is None
    assert results[0]["discount_pct"] is None


def test_parse_detects_variants():
    results = parse_product_page(MOCK_HTML_MULTIPLE_VARIANTS)
    assert len(results) == 1
    assert results[0]["variant"] == "2 Kg"
    assert results[0]["price"] == 35.90
    assert results[0]["original_price"] == 44.90
    assert results[0]["discount_pct"] == 20.0
