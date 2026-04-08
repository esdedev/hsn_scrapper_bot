import os
import pytest
from src.config import load_config


def test_load_config_reads_yaml(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "TEST_TOKEN")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
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
