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
                "avg_price": round(avg, 2),
                "comparison_days": comparison_days,
                "min_historic": min_historic,
            })
    return alerts


def format_alert_message(alert: dict) -> str:
    days = alert.get("comparison_days", 7)
    lines = [
        "OFERTA DETECTADA",
        "",
        f"<b>{alert['product_name']} ({alert['variant']})</b>",
        "",
        f"Precio: <b>{alert['price']:.2f} EUR</b>",
    ]
    if alert.get("original_price"):
        lines.append(f"PVPR: <s>{alert['original_price']:.2f} EUR</s>")
    lines.append("")
    lines.append(f"Bajada vs media {days}d: <b>-{alert['drop_pct']:.1f}%</b>")
    if alert.get("discount_pct"):
        lines.append(f"Descuento HSN: -{alert['discount_pct']:.0f}%")
    lines.append(f"Media {days} dias: {alert['avg_price']:.2f} EUR")
    if alert.get("min_historic") is not None:
        lines.append(f"Minimo historico: {alert['min_historic']:.2f} EUR")
    return "\n".join(lines)
