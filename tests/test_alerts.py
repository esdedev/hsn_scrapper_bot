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
    for i in range(7):
        insert_price(db, pid, "2kg", 40.0, 50.0, 20.0, now - timedelta(days=i + 1))
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
    new_prices = [{"variant": "2kg", "price": 34.0, "original_price": 50.0, "discount_pct": 32.0}]
    alerts = check_alerts(db, pid, "Evowhey", new_prices, threshold_pct=7, comparison_days=7)
    assert len(alerts) == 1
    assert alerts[0]["avg_7d"] == pytest.approx(40.0, abs=0.1)
    assert alerts[0]["min_historic"] == 38.0
