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
