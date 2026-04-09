# HSN Price Tracker

Scraper automatico de precios de proteinas de [HSN Store](https://www.hsnstore.com/) con alertas por Telegram.

Monitoriza precios cada 6 horas, almacena historico en SQLite, y avisa cuando detecta bajadas de precio significativas.

## Arquitectura

```
docker compose up -d
  |
  ├── hsn_bot        Bot de Telegram (24/7, escucha comandos)
  └── hsn_scrapper   Scraper con cron (cada 6h)
                       ├── Playwright + Chromium headless
                       ├── Scrape de precios por variante de peso
                       ├── Almacena en SQLite (data/hsn_prices.db)
                       ├── Compara con media de 7 dias
                       └── Envia resumen + alertas a Telegram
```

Ambos servicios comparten la base de datos SQLite via volumen Docker.

## Requisitos

- Docker y Docker Compose
- Bot de Telegram (crear con [@BotFather](https://t.me/BotFather))
- Grupo de Telegram donde anadir el bot (el chat_id del grupo es un numero negativo)

## Setup

1. Clonar el repositorio:
```bash
git clone <url-del-repo>
cd hsn_scrapper
```

2. Crear fichero `.env` a partir del ejemplo:
```bash
cp .env.example .env
```

3. Editar `.env` con tus credenciales:
```
TELEGRAM_BOT_TOKEN=tu-token-de-botfather
TELEGRAM_CHAT_ID=-123456789
```

4. Arrancar:
```bash
docker compose up -d --build
```

El scraper ejecutara un scrape inicial al arrancar y luego cada 6 horas via cron.

## Comandos del Bot

| Comando | Descripcion |
|---------|-------------|
| `/precios` | Precios actuales de todos los productos |
| `/historico <producto>` | Estadisticas de los ultimos 30 dias (min/max/media) |
| `/alerta [%]` | Ver o cambiar el umbral de alerta de bajada de precio |
| `/productos` | Lista de productos monitorizados |
| `/help` | Ayuda |

## Configuracion

Editar `config.yaml`:

```yaml
scraper:
  interval_hours: 6      # Frecuencia del cron (cambiar tambien en cron/scraper-cron)
  timeout_seconds: 30     # Timeout de Playwright por pagina

alerts:
  default_threshold_pct: 5   # Alerta si el precio baja >5% vs media
  comparison_days: 7         # Dias para calcular la media de comparacion

products:
  - name: "Evowhey Protein"
    url: "https://www.hsnstore.com/marcas/sport-series/evowhey-protein"
```

### Anadir un producto nuevo

Anadir una entrada en `products` de `config.yaml` con el nombre y la URL de la pagina del producto en HSN. Reiniciar el scraper:

```bash
docker compose restart hsn_scrapper
```

El scraper detecta automaticamente todas las variantes de peso de cada producto.

## Estructura del proyecto

```
hsn_scrapper/
├── src/
│   ├── bot.py          Bot de Telegram (comandos)
│   ├── scraper.py      Scraping con Playwright
│   ├── parser.py       Parseo de precios y descuentos
│   ├── alerts.py       Deteccion de bajadas de precio
│   ├── db.py           SQLite (schema, queries)
│   └── config.py       Carga de config.yaml + env vars
├── tests/              Tests unitarios (pytest)
├── cron/scraper-cron   Crontab (cada 6 horas)
├── main.py             Orquestador: scrape -> store -> alert -> send
├── config.yaml         Configuracion de productos y umbrales
├── docker-compose.yml  2 servicios: bot + scraper
├── Dockerfile          Imagen base Playwright + cron
└── .env.example        Plantilla de variables de entorno
```

## Tests

```bash
pip install -r requirements.txt
pytest
```
