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
    all_prices = {}  # {product_name: [price_entries]}

    for product in products:
        name = product["name"]
        url = product["url"]
        logger.info(f"Scraping: {name}")

        product_id = upsert_product(conn, name, url)
        price_data = scrape_product(url, timeout_ms=timeout_ms)

        if not price_data:
            logger.warning(f"No prices found for {name}")
            continue

        all_prices[name] = price_data

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

        alerts = check_alerts(conn, product_id, name, price_data, threshold, comparison_days)
        all_alerts.extend(alerts)

    # Always send a price summary
    if all_prices and bot_token and chat_id:
        summary = _build_summary(all_prices, now)
        try:
            send_telegram_message(bot_token, chat_id, summary)
            logger.info("Summary sent to Telegram")
        except Exception as e:
            logger.error(f"Failed to send summary: {e}")

    # Send individual alerts for price drops
    if all_alerts and bot_token and chat_id:
        for alert in all_alerts:
            msg = format_alert_message(alert)
            logger.info(f"Sending alert: {alert['product_name']} ({alert['variant']})")
            try:
                send_telegram_message(bot_token, chat_id, msg)
            except Exception as e:
                logger.error(f"Failed to send Telegram alert: {e}")

    logger.info(f"Done. {len(all_prices)} products scraped, {len(all_alerts)} alerts sent.")
    conn.close()


def _build_summary(all_prices: dict, now: datetime) -> str:
    ts = now.strftime("%d/%m/%Y %H:%M UTC")
    lines = [f"Precios HSN ({ts})\n"]
    for name, entries in all_prices.items():
        lines.append(name)
        for e in entries:
            line = f"  {e['variant']}: {e['price']:.2f} EUR"
            if e.get("original_price"):
                line += f" (PVPR {e['original_price']:.2f} EUR)"
            if e.get("discount_pct"):
                line += f" -{e['discount_pct']:.0f}%"
            lines.append(line)
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    run()
