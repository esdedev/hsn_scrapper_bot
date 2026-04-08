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
