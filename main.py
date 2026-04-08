# main.py
import logging
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
