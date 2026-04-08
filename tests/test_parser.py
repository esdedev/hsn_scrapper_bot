import pytest
from src.parser import parse_product_page


MOCK_HTML_SINGLE_VARIANT = """
<div class="product-info-main">
    <h1 class="page-title">Evowhey Protein 2.0</h1>
    <div class="product-info-price">
        <span class="price-wrapper" data-price-type="finalPrice">
            <span class="price">35,90&nbsp;€</span>
        </span>
        <span class="price-wrapper" data-price-type="oldPrice">
            <span class="price">44,90&nbsp;€</span>
        </span>
    </div>
    <div class="swatch-attribute" data-attribute-code="formato">
        <div class="swatch-option selected" data-option-label="2 Kg">2 Kg</div>
    </div>
</div>
"""

MOCK_HTML_MULTIPLE_VARIANTS = """
<div class="product-info-main">
    <h1 class="page-title">Evowhey Protein 2.0</h1>
    <div class="product-info-price">
        <span class="price-wrapper" data-price-type="finalPrice">
            <span class="price">35,90&nbsp;€</span>
        </span>
        <span class="price-wrapper" data-price-type="oldPrice">
            <span class="price">44,90&nbsp;€</span>
        </span>
    </div>
    <div class="swatch-attribute" data-attribute-code="formato">
        <div class="swatch-option selected" data-option-label="2 Kg">2 Kg</div>
        <div class="swatch-option" data-option-label="500 g">500 g</div>
        <div class="swatch-option" data-option-label="3 Kg">3 Kg</div>
    </div>
</div>
"""


def test_parse_single_variant():
    results = parse_product_page(MOCK_HTML_SINGLE_VARIANT)
    assert len(results) == 1
    assert results[0]["variant"] == "2 Kg"
    assert results[0]["price"] == 35.90
    assert results[0]["original_price"] == 44.90
    assert results[0]["discount_pct"] > 0


def test_parse_extracts_discount():
    results = parse_product_page(MOCK_HTML_SINGLE_VARIANT)
    expected_discount = round((1 - 35.90 / 44.90) * 100, 1)
    assert results[0]["discount_pct"] == pytest.approx(expected_discount, abs=0.2)


def test_parse_no_original_price():
    html = """
    <div class="product-info-main">
        <h1 class="page-title">Test Product</h1>
        <div class="product-info-price">
            <span class="price-wrapper" data-price-type="finalPrice">
                <span class="price">20,00&nbsp;€</span>
            </span>
        </div>
        <div class="swatch-attribute" data-attribute-code="formato">
            <div class="swatch-option selected" data-option-label="500 g">500 g</div>
        </div>
    </div>
    """
    results = parse_product_page(html)
    assert results[0]["price"] == 20.00
    assert results[0]["original_price"] is None
    assert results[0]["discount_pct"] is None
