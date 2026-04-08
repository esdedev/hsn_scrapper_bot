# HSN Protein Price Scraper — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python scraper that tracks HSN protein prices every 6h, stores history in SQLite, and sends Telegram alerts on price drops.

**Architecture:** Playwright scrapes product pages → parser extracts prices/variants → SQLite stores history → alert engine compares against 7-day average → Telegram bot sends notifications and handles interactive commands. Cron triggers the scrape; bot runs as separate 24/7 process. Both deploy via Docker Compose.

**Tech Stack:** Python 3.12, Playwright (Chromium), SQLite, python-telegram-bot, PyYAML, pytest

---

## File Map

| File | Responsibility |
|------|---------------|
| `config.yaml` | Product URLs, Telegram credentials, scraper/alert settings |
| `requirements.txt` | Python dependencies |
| `.gitignore` | Ignore `data/`, venv, __pycache__ |
| `src/__init__.py` | Package marker |
| `src/config.py` | Load and validate config.yaml |
| `src/db.py` | SQLite schema init, inserts, queries |
| `src/scraper.py` | Playwright: visit URLs, wait for prices, return raw HTML |
| `src/parser.py` | Extract price data from rendered HTML |
| `src/alerts.py` | Compare new prices vs 7-day average, build alert messages |
| `src/bot.py` | Telegram bot: commands (/precios, /historico, /alerta, /productos) |
| `main.py` | Entry point: load config → scrape → store → check alerts → send |
| `tests/test_db.py` | Tests for DB operations |
| `tests/test_parser.py` | Tests for price extraction with mock HTML |
| `tests/test_alerts.py` | Tests for alert detection logic |
| `tests/test_config.py` | Tests for config loading |
| `Dockerfile` | Multi-stage build with Playwright+Chromium |
| `docker-compose.yml` | bot + scraper services, ./data volume |

---

### Task 1: Project scaffolding

**Files:**
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `config.yaml`
- Create: `src/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Initialize git repo**

```bash
cd /path/to/hsn_scrapper
git init
```

- [ ] **Step 2: Create .gitignore**

```gitignore
data/*
!data/.gitkeep
__pycache__/
*.pyc
.venv/
venv/
*.egg-info/
.pytest_cache/
```

- [ ] **Step 3: Create requirements.txt**

```
playwright==1.52.0
python-telegram-bot==21.11
pyyaml==6.0.2
pytest==8.3.5
pytest-asyncio==0.25.3
```

- [ ] **Step 4: Create config.yaml**

```yaml
telegram:
  bot_token: ""
  chat_id: ""

scraper:
  interval_hours: 6
  timeout_seconds: 30

alerts:
  default_threshold_pct: 7
  comparison_days: 7

products:
  - name: "Evowhey Protein"
    url: "https://www.hsnstore.com/marcas/sport-series/evowhey-protein"
  - name: "Proteina de Soja Aislada 2.0"
    url: "https://www.hsnstore.com/marcas/essential-series/proteina-de-soja-aislada-2-0"
  - name: "Proteina de Guisante Aislada 2.0"
    url: "https://www.hsnstore.com/marcas/essential-series/proteina-de-guisante-aislada-2-0"
  # - name: "Evolate 2.0"
  #   url: "https://www.hsnstore.com/marcas/sport-series/evolate-2-0-whey-isolate-cfm"
  # - name: "Evopro"
  #   url: "https://www.hsnstore.com/marcas/sport-series/evopro-mezcla-proteinas-premium-digezyme"
  # - name: "Evohydro 2.0"
  #   url: "https://www.hsnstore.com/marcas/sport-series/evohydro-2-0-hydro-whey"
  # - name: "Evoexcel 2.0"
  #   url: "https://www.hsnstore.com/marcas/sport-series/evoexcel-2-0-whey-protein-isolate-concentrate"
```

- [ ] **Step 5: Create package markers**

```python
# src/__init__.py
# (empty)
```

```python
# tests/__init__.py
# (empty)
```

- [ ] **Step 6: Create data directory with .gitkeep**

```bash
mkdir -p data
touch data/.gitkeep
```

- [ ] **Step 7: Install dependencies and Playwright browser**

```bash
python -m venv .venv
source .venv/bin/activate  # Linux
pip install -r requirements.txt
playwright install chromium
```

- [ ] **Step 8: Commit**

```bash
git add .gitignore requirements.txt config.yaml src/__init__.py tests/__init__.py data/.gitkeep
git commit -m "chore: project scaffolding with dependencies and config"
```

---

### Task 2: Config loader

**Files:**
- Create: `src/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
import os
import tempfile
import pytest
from src.config import load_config


def test_load_config_reads_yaml(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("""
telegram:
  bot_token: "TEST_TOKEN"
  chat_id: "12345"

scraper:
  interval_hours: 6
  timeout_seconds: 30

alerts:
  default_threshold_pct: 7
  comparison_days: 7

products:
  - name: "Test Product"
    url: "https://example.com/product"
""")
    config = load_config(str(cfg_file))
    assert config["telegram"]["bot_token"] == "TEST_TOKEN"
    assert config["telegram"]["chat_id"] == "12345"
    assert config["scraper"]["timeout_seconds"] == 30
    assert config["alerts"]["default_threshold_pct"] == 7
    assert len(config["products"]) == 1
    assert config["products"][0]["name"] == "Test Product"


def test_load_config_filters_active_products(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("""
telegram:
  bot_token: ""
  chat_id: ""

scraper:
  interval_hours: 6
  timeout_seconds: 30

alerts:
  default_threshold_pct: 7
  comparison_days: 7

products:
  - name: "Active Product"
    url: "https://example.com/active"
  - name: "Another Active"
    url: "https://example.com/another"
""")
    config = load_config(str(cfg_file))
    assert len(config["products"]) == 2


def test_load_config_missing_file():
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/config.yaml")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_config.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'src.config'`

- [ ] **Step 3: Write implementation**

```python
# src/config.py
import yaml
from pathlib import Path


def load_config(path: str = "config.yaml") -> dict:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_config.py -v
```

Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add src/config.py tests/test_config.py
git commit -m "feat: config loader with yaml parsing"
```

---

### Task 3: Database module

**Files:**
- Create: `src/db.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_db.py
import sqlite3
from datetime import datetime, timezone, timedelta
import pytest
from src.db import (
    init_db,
    upsert_product,
    insert_price,
    get_active_products,
    get_latest_prices,
    get_price_stats,
    get_average_price,
    get_min_price,
    get_setting,
    set_setting,
)


@pytest.fixture
def db(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = init_db(db_path)
    yield conn
    conn.close()


def test_init_db_creates_tables(db):
    cursor = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = [row[0] for row in cursor.fetchall()]
    assert "products" in tables
    assert "prices" in tables
    assert "settings" in tables


def test_upsert_product_insert(db):
    product_id = upsert_product(db, "Evowhey", "https://hsn.com/evowhey")
    assert product_id is not None
    row = db.execute("SELECT name, url, active FROM products WHERE id = ?", (product_id,)).fetchone()
    assert row[0] == "Evowhey"
    assert row[1] == "https://hsn.com/evowhey"
    assert row[2] == 1


def test_upsert_product_existing(db):
    id1 = upsert_product(db, "Evowhey", "https://hsn.com/evowhey")
    id2 = upsert_product(db, "Evowhey Updated", "https://hsn.com/evowhey")
    assert id1 == id2
    row = db.execute("SELECT name FROM products WHERE id = ?", (id1,)).fetchone()
    assert row[0] == "Evowhey Updated"


def test_insert_price(db):
    pid = upsert_product(db, "Evowhey", "https://hsn.com/evowhey")
    now = datetime.now(timezone.utc)
    insert_price(db, pid, "2kg", 35.90, 44.90, 20.0, now)
    row = db.execute("SELECT variant, price, original_price, discount_pct FROM prices WHERE product_id = ?", (pid,)).fetchone()
    assert row[0] == "2kg"
    assert row[1] == 35.90
    assert row[2] == 44.90
    assert row[3] == 20.0


def test_get_active_products(db):
    upsert_product(db, "Active", "https://hsn.com/active")
    pid2 = upsert_product(db, "Inactive", "https://hsn.com/inactive")
    db.execute("UPDATE products SET active = 0 WHERE id = ?", (pid2,))
    db.commit()
    products = get_active_products(db)
    assert len(products) == 1
    assert products[0]["name"] == "Active"


def test_get_latest_prices(db):
    pid = upsert_product(db, "Evowhey", "https://hsn.com/evowhey")
    now = datetime.now(timezone.utc)
    old = now - timedelta(hours=6)
    insert_price(db, pid, "2kg", 40.00, 44.90, 10.0, old)
    insert_price(db, pid, "2kg", 35.90, 44.90, 20.0, now)
    insert_price(db, pid, "1kg", 22.00, 25.00, 12.0, now)
    latest = get_latest_prices(db, pid)
    assert len(latest) == 2
    prices_by_variant = {p["variant"]: p for p in latest}
    assert prices_by_variant["2kg"]["price"] == 35.90
    assert prices_by_variant["1kg"]["price"] == 22.00


def test_get_average_price(db):
    pid = upsert_product(db, "Evowhey", "https://hsn.com/evowhey")
    now = datetime.now(timezone.utc)
    for i in range(4):
        ts = now - timedelta(days=i)
        insert_price(db, pid, "2kg", 40.0 + i, 50.0, 0.0, ts)
    avg = get_average_price(db, pid, "2kg", days=7)
    assert avg == pytest.approx(41.5, abs=0.01)


def test_get_min_price(db):
    pid = upsert_product(db, "Evowhey", "https://hsn.com/evowhey")
    now = datetime.now(timezone.utc)
    insert_price(db, pid, "2kg", 40.0, 50.0, 0.0, now - timedelta(days=10))
    insert_price(db, pid, "2kg", 30.0, 50.0, 0.0, now - timedelta(days=5))
    insert_price(db, pid, "2kg", 35.0, 50.0, 0.0, now)
    assert get_min_price(db, pid, "2kg") == 30.0


def test_get_price_stats(db):
    pid = upsert_product(db, "Evowhey", "https://hsn.com/evowhey")
    now = datetime.now(timezone.utc)
    insert_price(db, pid, "2kg", 40.0, 50.0, 0.0, now - timedelta(days=2))
    insert_price(db, pid, "2kg", 30.0, 50.0, 0.0, now - timedelta(days=1))
    insert_price(db, pid, "2kg", 35.0, 50.0, 0.0, now)
    stats = get_price_stats(db, pid, "2kg", days=30)
    assert stats["min"] == 30.0
    assert stats["max"] == 40.0
    assert stats["avg"] == pytest.approx(35.0, abs=0.01)


def test_settings(db):
    set_setting(db, "alert_threshold", "7")
    assert get_setting(db, "alert_threshold") == "7"
    set_setting(db, "alert_threshold", "15")
    assert get_setting(db, "alert_threshold") == "15"
    assert get_setting(db, "nonexistent") is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_db.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'src.db'`

- [ ] **Step 3: Write implementation**

```python
# src/db.py
import sqlite3
from datetime import datetime, timezone, timedelta


def init_db(db_path: str = "data/hsn_prices.db") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            active BOOLEAN NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL REFERENCES products(id),
            variant TEXT NOT NULL,
            price REAL NOT NULL,
            original_price REAL,
            discount_pct REAL,
            scraped_at DATETIME NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_prices_lookup
        ON prices(product_id, variant, scraped_at);

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)
    conn.commit()
    return conn


def upsert_product(conn: sqlite3.Connection, name: str, url: str) -> int:
    row = conn.execute("SELECT id FROM products WHERE url = ?", (url,)).fetchone()
    if row:
        conn.execute("UPDATE products SET name = ? WHERE url = ?", (name, url))
        conn.commit()
        return row[0]
    cursor = conn.execute(
        "INSERT INTO products (name, url) VALUES (?, ?)", (name, url)
    )
    conn.commit()
    return cursor.lastrowid


def insert_price(
    conn: sqlite3.Connection,
    product_id: int,
    variant: str,
    price: float,
    original_price: float | None,
    discount_pct: float | None,
    scraped_at: datetime,
) -> None:
    conn.execute(
        """INSERT INTO prices (product_id, variant, price, original_price, discount_pct, scraped_at)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (product_id, variant, price, original_price, discount_pct, scraped_at.isoformat()),
    )
    conn.commit()


def get_active_products(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT id, name, url FROM products WHERE active = 1"
    ).fetchall()
    return [{"id": r["id"], "name": r["name"], "url": r["url"]} for r in rows]


def get_latest_prices(conn: sqlite3.Connection, product_id: int) -> list[dict]:
    rows = conn.execute(
        """SELECT variant, price, original_price, discount_pct, scraped_at
        FROM prices
        WHERE product_id = ?
        AND scraped_at = (
            SELECT MAX(p2.scraped_at) FROM prices p2
            WHERE p2.product_id = prices.product_id AND p2.variant = prices.variant
        )
        ORDER BY variant""",
        (product_id,),
    ).fetchall()
    return [
        {
            "variant": r["variant"],
            "price": r["price"],
            "original_price": r["original_price"],
            "discount_pct": r["discount_pct"],
            "scraped_at": r["scraped_at"],
        }
        for r in rows
    ]


def get_average_price(
    conn: sqlite3.Connection, product_id: int, variant: str, days: int = 7
) -> float | None:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    row = conn.execute(
        """SELECT AVG(price) as avg_price FROM prices
        WHERE product_id = ? AND variant = ? AND scraped_at >= ?""",
        (product_id, variant, since),
    ).fetchone()
    return row["avg_price"] if row and row["avg_price"] is not None else None


def get_min_price(
    conn: sqlite3.Connection, product_id: int, variant: str
) -> float | None:
    row = conn.execute(
        "SELECT MIN(price) as min_price FROM prices WHERE product_id = ? AND variant = ?",
        (product_id, variant),
    ).fetchone()
    return row["min_price"] if row and row["min_price"] is not None else None


def get_price_stats(
    conn: sqlite3.Connection, product_id: int, variant: str, days: int = 30
) -> dict:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    row = conn.execute(
        """SELECT MIN(price) as min, MAX(price) as max, AVG(price) as avg
        FROM prices
        WHERE product_id = ? AND variant = ? AND scraped_at >= ?""",
        (product_id, variant, since),
    ).fetchone()
    return {
        "min": row["min"],
        "max": row["max"],
        "avg": row["avg"],
    }


def get_setting(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?",
        (key, value, value),
    )
    conn.commit()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_db.py -v
```

Expected: 10 PASSED

- [ ] **Step 5: Commit**

```bash
git add src/db.py tests/test_db.py
git commit -m "feat: SQLite database module with products, prices, and settings"
```

---

### Task 4: Scraper + Parser (Playwright)

**Files:**
- Create: `src/scraper.py`
- Create: `src/parser.py`
- Create: `tests/test_parser.py`

**Note:** The scraper itself cannot be unit-tested easily since it depends on a live browser and the HSN website. We test the parser with mock HTML. The scraper is tested manually in Task 6.

- [ ] **Step 1: Write failing parser tests with mock HTML**

```python
# tests/test_parser.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_parser.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'src.parser'`

- [ ] **Step 3: Write parser implementation**

```python
# src/parser.py
import re


def parse_price(price_text: str) -> float | None:
    if not price_text:
        return None
    cleaned = price_text.replace("\xa0", "").replace("€", "").replace("\u202f", "").strip()
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return None


def parse_product_page(html: str) -> list[dict]:
    from html.parser import HTMLParser

    class PriceExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.final_price = None
            self.old_price = None
            self.variants = []
            self._in_final_price = False
            self._in_old_price = False
            self._in_price_span = False
            self._current_price_type = None

        def handle_starttag(self, tag, attrs):
            attrs_dict = dict(attrs)
            if tag == "span" and attrs_dict.get("data-price-type") == "finalPrice":
                self._current_price_type = "final"
            elif tag == "span" and attrs_dict.get("data-price-type") == "oldPrice":
                self._current_price_type = "old"
            elif tag == "span" and "price" in attrs_dict.get("class", "") and self._current_price_type:
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
            discount = round((1 - extractor.final_price / extractor.old_price) * 100, 1)
        results.append({
            "variant": selected_variant,
            "price": extractor.final_price,
            "original_price": extractor.old_price,
            "discount_pct": discount,
        })

    return results
```

- [ ] **Step 4: Run parser tests to verify they pass**

```bash
pytest tests/test_parser.py -v
```

Expected: 3 PASSED

- [ ] **Step 5: Write scraper module**

```python
# src/scraper.py
import logging
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)


def scrape_product(url: str, timeout_ms: int = 30000) -> list[dict]:
    """
    Visit a product URL with Playwright, click each weight variant,
    and collect prices for all variants.
    Returns list of dicts with: variant, price, original_price, discount_pct
    """
    from src.parser import parse_price

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

            # Wait for price to appear
            page.wait_for_selector(
                "[data-price-type='finalPrice'] .price, .price-wrapper .price",
                timeout=timeout_ms,
            )

            # Find weight/format variant buttons
            variant_buttons = page.query_selector_all(
                "[data-attribute-code='formato'] .swatch-option, "
                ".swatch-attribute .swatch-option"
            )

            if not variant_buttons:
                # Single variant or no swatch — grab current price
                price_text = _get_price_text(page, "finalPrice")
                old_price_text = _get_price_text(page, "oldPrice")
                price = parse_price(price_text)
                old_price = parse_price(old_price_text)
                discount = None
                if price and old_price and old_price > 0:
                    discount = round((1 - price / old_price) * 100, 1)
                if price:
                    results.append({
                        "variant": "default",
                        "price": price,
                        "original_price": old_price,
                        "discount_pct": discount,
                    })
            else:
                for btn in variant_buttons:
                    label = btn.get_attribute("data-option-label") or btn.inner_text().strip()
                    btn.click()
                    page.wait_for_timeout(500)  # Wait for price update

                    price_text = _get_price_text(page, "finalPrice")
                    old_price_text = _get_price_text(page, "oldPrice")
                    price = parse_price(price_text)
                    old_price = parse_price(old_price_text)
                    discount = None
                    if price and old_price and old_price > 0:
                        discount = round((1 - price / old_price) * 100, 1)
                    if price:
                        results.append({
                            "variant": label,
                            "price": price,
                            "original_price": old_price,
                            "discount_pct": discount,
                        })

                    logger.info(f"  {label}: {price}€ (was {old_price}€)")

        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
        finally:
            browser.close()

    return results


def _get_price_text(page, price_type: str) -> str | None:
    el = page.query_selector(f"[data-price-type='{price_type}'] .price")
    if el:
        return el.inner_text()
    return None
```

- [ ] **Step 6: Commit**

```bash
git add src/parser.py src/scraper.py tests/test_parser.py
git commit -m "feat: HTML parser and Playwright scraper for HSN product pages"
```

---

### Task 5: Alert engine

**Files:**
- Create: `src/alerts.py`
- Create: `tests/test_alerts.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_alerts.py
from datetime import datetime, timezone, timedelta
import pytest
from src.db import init_db, upsert_product, insert_price, set_setting
from src.alerts import check_alerts


@pytest.fixture
def db(tmp_path):
    from src.db import init_db
    conn = init_db(str(tmp_path / "test.db"))
    yield conn
    conn.close()


def test_alert_triggered_when_price_drops(db):
    pid = upsert_product(db, "Evowhey", "https://hsn.com/evowhey")
    now = datetime.now(timezone.utc)
    # Insert 7 days of prices at 40€
    for i in range(7):
        insert_price(db, pid, "2kg", 40.0, 50.0, 20.0, now - timedelta(days=i + 1))
    # New price at 35€ (12.5% drop)
    new_prices = [{"variant": "2kg", "price": 35.0, "original_price": 50.0, "discount_pct": 30.0}]
    alerts = check_alerts(db, pid, "Evowhey", new_prices, threshold_pct=7, comparison_days=7)
    assert len(alerts) == 1
    assert alerts[0]["variant"] == "2kg"
    assert alerts[0]["price"] == 35.0
    assert alerts[0]["drop_pct"] == pytest.approx(12.5, abs=0.1)


def test_no_alert_when_drop_below_threshold(db):
    pid = upsert_product(db, "Evowhey", "https://hsn.com/evowhey")
    now = datetime.now(timezone.utc)
    for i in range(7):
        insert_price(db, pid, "2kg", 40.0, 50.0, 20.0, now - timedelta(days=i + 1))
    # New price at 39€ (2.5% drop, below 7% threshold)
    new_prices = [{"variant": "2kg", "price": 39.0, "original_price": 50.0, "discount_pct": 22.0}]
    alerts = check_alerts(db, pid, "Evowhey", new_prices, threshold_pct=7, comparison_days=7)
    assert len(alerts) == 0


def test_no_alert_when_no_history(db):
    pid = upsert_product(db, "Evowhey", "https://hsn.com/evowhey")
    new_prices = [{"variant": "2kg", "price": 35.0, "original_price": 50.0, "discount_pct": 30.0}]
    alerts = check_alerts(db, pid, "Evowhey", new_prices, threshold_pct=7, comparison_days=7)
    assert len(alerts) == 0


def test_alert_includes_min_and_avg(db):
    pid = upsert_product(db, "Evowhey", "https://hsn.com/evowhey")
    now = datetime.now(timezone.utc)
    insert_price(db, pid, "2kg", 38.0, 50.0, 0.0, now - timedelta(days=5))
    insert_price(db, pid, "2kg", 42.0, 50.0, 0.0, now - timedelta(days=3))
    insert_price(db, pid, "2kg", 40.0, 50.0, 0.0, now - timedelta(days=1))
    # New price at 34€ (15% drop from avg 40)
    new_prices = [{"variant": "2kg", "price": 34.0, "original_price": 50.0, "discount_pct": 32.0}]
    alerts = check_alerts(db, pid, "Evowhey", new_prices, threshold_pct=7, comparison_days=7)
    assert len(alerts) == 1
    assert alerts[0]["avg_7d"] == pytest.approx(40.0, abs=0.1)
    assert alerts[0]["min_historic"] == 38.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_alerts.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'src.alerts'`

- [ ] **Step 3: Write implementation**

```python
# src/alerts.py
import sqlite3
from src.db import get_average_price, get_min_price


def check_alerts(
    conn: sqlite3.Connection,
    product_id: int,
    product_name: str,
    new_prices: list[dict],
    threshold_pct: float = 7,
    comparison_days: int = 7,
) -> list[dict]:
    alerts = []
    for entry in new_prices:
        variant = entry["variant"]
        price = entry["price"]

        avg = get_average_price(conn, product_id, variant, days=comparison_days)
        if avg is None:
            continue

        drop_pct = round((1 - price / avg) * 100, 1)
        if drop_pct >= threshold_pct:
            min_historic = get_min_price(conn, product_id, variant)
            alerts.append({
                "product_name": product_name,
                "variant": variant,
                "price": price,
                "original_price": entry.get("original_price"),
                "discount_pct": entry.get("discount_pct"),
                "drop_pct": drop_pct,
                "avg_7d": round(avg, 2),
                "min_historic": min_historic,
            })
    return alerts


def format_alert_message(alert: dict) -> str:
    msg = f"Oferta detectada!\n"
    msg += f"{alert['product_name']} ({alert['variant']})\n"
    msg += f"Precio: {alert['price']:.2f} EUR"
    if alert.get("original_price"):
        msg += f" (antes {alert['original_price']:.2f} EUR)"
    msg += f"\nBajada vs media 7d: -{alert['drop_pct']:.1f}%"
    if alert.get("discount_pct"):
        msg += f"\nDescuento HSN: -{alert['discount_pct']:.1f}%"
    msg += f"\nMedia 7 dias: {alert['avg_7d']:.2f} EUR"
    if alert.get("min_historic") is not None:
        msg += f"\nMinimo historico: {alert['min_historic']:.2f} EUR"
    return msg
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_alerts.py -v
```

Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add src/alerts.py tests/test_alerts.py
git commit -m "feat: alert engine with threshold detection and message formatting"
```

---

### Task 6: Main entry point

**Files:**
- Create: `main.py`

- [ ] **Step 1: Write main.py**

```python
# main.py
import logging
import sys
from datetime import datetime, timezone

from src.config import load_config
from src.db import init_db, upsert_product, insert_price, get_setting
from src.scraper import scrape_product
from src.alerts import check_alerts, format_alert_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def send_telegram_message(bot_token: str, chat_id: str, text: str) -> None:
    from telegram import Bot
    import asyncio

    async def _send():
        bot = Bot(token=bot_token)
        await bot.send_message(chat_id=chat_id, text=text)

    asyncio.run(_send())


def run():
    config = load_config()
    conn = init_db()

    bot_token = config["telegram"]["bot_token"]
    chat_id = config["telegram"]["chat_id"]
    timeout_ms = config["scraper"]["timeout_seconds"] * 1000
    default_threshold = config["alerts"]["default_threshold_pct"]
    comparison_days = config["alerts"]["comparison_days"]

    # Use user-configured threshold or default from config
    threshold_str = get_setting(conn, "alert_threshold")
    threshold = float(threshold_str) if threshold_str else default_threshold

    products = config["products"]
    now = datetime.now(timezone.utc)
    all_alerts = []

    for product in products:
        name = product["name"]
        url = product["url"]
        logger.info(f"Scraping: {name}")

        product_id = upsert_product(conn, name, url)
        price_data = scrape_product(url, timeout_ms=timeout_ms)

        if not price_data:
            logger.warning(f"No prices found for {name}")
            continue

        for entry in price_data:
            insert_price(
                conn,
                product_id,
                entry["variant"],
                entry["price"],
                entry.get("original_price"),
                entry.get("discount_pct"),
                now,
            )
            logger.info(f"  {entry['variant']}: {entry['price']}€")

        alerts = check_alerts(conn, product_id, name, price_data, threshold, comparison_days)
        all_alerts.extend(alerts)

    if all_alerts and bot_token and chat_id:
        for alert in all_alerts:
            msg = format_alert_message(alert)
            logger.info(f"Sending alert: {alert['product_name']} ({alert['variant']})")
            try:
                send_telegram_message(bot_token, chat_id, msg)
            except Exception as e:
                logger.error(f"Failed to send Telegram alert: {e}")
    elif all_alerts:
        logger.warning("Alerts detected but Telegram not configured")
        for alert in all_alerts:
            logger.info(format_alert_message(alert))

    logger.info(f"Done. {len(all_alerts)} alerts sent.")
    conn.close()


if __name__ == "__main__":
    run()
```

- [ ] **Step 2: Manual test — run scraper against live HSN**

```bash
python main.py
```

Expected: logs showing scraping each product, extracting variants and prices, inserting into DB. Check `data/hsn_prices.db` exists.

**Important:** This is where we verify that Playwright selectors actually work against the live HSN site. If selectors fail (no prices found), inspect the page manually with `playwright codegen https://www.hsnstore.com/marcas/sport-series/evowhey-protein` and update the selectors in `src/scraper.py`.

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: main entry point - scrape, store, and alert pipeline"
```

---

### Task 7: Telegram bot

**Files:**
- Create: `src/bot.py`

- [ ] **Step 1: Write bot.py**

```python
# src/bot.py
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from src.config import load_config
from src.db import (
    init_db,
    get_active_products,
    get_latest_prices,
    get_price_stats,
    get_setting,
    set_setting,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

config = load_config()
conn = init_db()


async def cmd_precios(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    products = get_active_products(conn)
    if not products:
        await update.message.reply_text("No hay productos activos.")
        return

    lines = []
    for p in products:
        latest = get_latest_prices(conn, p["id"])
        if not latest:
            lines.append(f"*{p['name']}*\nSin datos aun\n")
            continue
        lines.append(f"*{p['name']}*")
        for v in latest:
            line = f"  {v['variant']}: {v['price']:.2f} EUR"
            if v["original_price"]:
                line += f" (antes {v['original_price']:.2f} EUR)"
            if v["discount_pct"]:
                line += f" [-{v['discount_pct']:.0f}%]"
            lines.append(line)
        lines.append("")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_historico(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Uso: /historico <nombre_producto>")
        return

    query = " ".join(context.args).lower()
    products = get_active_products(conn)
    match = None
    for p in products:
        if query in p["name"].lower():
            match = p
            break

    if not match:
        names = ", ".join(p["name"] for p in products)
        await update.message.reply_text(f"Producto no encontrado. Disponibles: {names}")
        return

    latest = get_latest_prices(conn, match["id"])
    if not latest:
        await update.message.reply_text(f"Sin datos para {match['name']}")
        return

    lines = [f"*{match['name']}* (ultimos 30 dias)\n"]
    for v in latest:
        stats = get_price_stats(conn, match["id"], v["variant"], days=30)
        lines.append(f"  {v['variant']}:")
        lines.append(f"    Actual: {v['price']:.2f} EUR")
        if stats["min"] is not None:
            lines.append(f"    Min: {stats['min']:.2f} EUR")
            lines.append(f"    Max: {stats['max']:.2f} EUR")
            lines.append(f"    Media: {stats['avg']:.2f} EUR")
        lines.append("")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_alerta(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        current = get_setting(conn, "alert_threshold")
        if current is None:
            current = str(config["alerts"]["default_threshold_pct"])
        await update.message.reply_text(f"Umbral actual: {current}%\nUso: /alerta <porcentaje>")
        return

    try:
        threshold = float(context.args[0])
        if threshold <= 0 or threshold > 100:
            raise ValueError()
    except ValueError:
        await update.message.reply_text("Porcentaje invalido. Ejemplo: /alerta 15")
        return

    set_setting(conn, "alert_threshold", str(threshold))
    await update.message.reply_text(f"Umbral de alerta actualizado a {threshold}%")


async def cmd_productos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    products = get_active_products(conn)
    if not products:
        await update.message.reply_text("No hay productos configurados.")
        return

    lines = ["*Productos trackeados:*\n"]
    for p in products:
        lines.append(f"  - {p['name']}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


def main():
    bot_token = config["telegram"]["bot_token"]
    if not bot_token:
        logger.error("bot_token not configured in config.yaml")
        return

    app = Application.builder().token(bot_token).build()
    app.add_handler(CommandHandler("precios", cmd_precios))
    app.add_handler(CommandHandler("historico", cmd_historico))
    app.add_handler(CommandHandler("alerta", cmd_alerta))
    app.add_handler(CommandHandler("productos", cmd_productos))

    logger.info("Bot started. Listening for commands...")
    app.run_polling()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Manual test — start bot and test commands**

```bash
# First configure bot_token and chat_id in config.yaml
python src/bot.py
```

Test each command in Telegram: `/precios`, `/historico evowhey`, `/alerta`, `/alerta 10`, `/productos`

- [ ] **Step 3: Commit**

```bash
git add src/bot.py
git commit -m "feat: Telegram bot with /precios /historico /alerta /productos commands"
```

---

### Task 8: Docker setup

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `cron/scraper-cron`

- [ ] **Step 1: Create Dockerfile**

```dockerfile
# Dockerfile
FROM python:3.12-slim AS base

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    cron \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    playwright install --with-deps chromium

COPY src/ src/
COPY main.py .
COPY config.yaml .
```

- [ ] **Step 2: Create cron schedule file**

```bash
mkdir -p cron
```

```
# cron/scraper-cron
0 */6 * * * cd /app && python main.py >> /var/log/scraper.log 2>&1
```

- [ ] **Step 3: Create docker-compose.yml**

```yaml
# docker-compose.yml
services:
  bot:
    build: .
    command: python src/bot.py
    volumes:
      - ./data:/app/data
      - ./config.yaml:/app/config.yaml:ro
    restart: unless-stopped

  scraper:
    build: .
    command: >
      bash -c "
        cp /app/cron/scraper-cron /etc/cron.d/scraper-cron &&
        chmod 0644 /etc/cron.d/scraper-cron &&
        crontab /etc/cron.d/scraper-cron &&
        echo 'Cron started. Running initial scrape...' &&
        python main.py &&
        cron -f
      "
    volumes:
      - ./data:/app/data
      - ./config.yaml:/app/config.yaml:ro
      - ./cron:/app/cron:ro
    restart: unless-stopped
```

- [ ] **Step 4: Update Dockerfile to include cron directory**

Add before the last line of the Dockerfile:

```dockerfile
COPY cron/ cron/
```

Full Dockerfile:

```dockerfile
FROM python:3.12-slim AS base

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    cron \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    playwright install --with-deps chromium

COPY src/ src/
COPY main.py .
COPY config.yaml .
COPY cron/ cron/
```

- [ ] **Step 5: Test Docker build**

```bash
docker compose build
```

Expected: successful build, image size ~300-400MB

- [ ] **Step 6: Test Docker run**

```bash
docker compose up -d
docker compose logs -f
```

Expected: bot starts polling, scraper runs initial scrape then cron takes over

- [ ] **Step 7: Commit**

```bash
git add Dockerfile docker-compose.yml cron/
git commit -m "feat: Docker setup with bot and cron scraper services"
```

---

### Task 9: Run all tests and final verification

- [ ] **Step 1: Run full test suite**

```bash
pytest tests/ -v
```

Expected: all tests pass (test_config: 3, test_db: 10, test_parser: 3, test_alerts: 4 = 20 total)

- [ ] **Step 2: Run scraper manually end-to-end**

```bash
python main.py
```

Verify:
- Products are scraped successfully (check logs)
- `data/hsn_prices.db` contains rows in `products` and `prices` tables
- If Telegram is configured, alerts work

- [ ] **Step 3: Verify Docker**

```bash
docker compose build && docker compose up -d
docker compose logs bot
docker compose logs scraper
```

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: final verification - all tests pass, Docker works"
```
