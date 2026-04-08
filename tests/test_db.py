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
