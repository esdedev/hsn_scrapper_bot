# HSN Protein Price Scraper — Design Spec

## Overview

Scraper de precios de proteinas de HSN Store que se ejecuta cada 6 horas, almacena historico en SQLite, y envia alertas via Telegram cuando detecta bajadas de precio configurables.

## Objetivos

- Trackear precios de productos whey/proteina de HSN Store cada 6h
- Detectar ofertas automaticamente comparando con la media de los ultimos 7 dias
- Notificar via Telegram bot cuando el precio baja mas de un umbral configurable (defecto: 7%)
- Consultar estadisticas (precios actuales, historico, minimos) desde Telegram
- Despliegue en Docker en un mini PC Linux corriendo 24/7

## Arquitectura

```
┌─────────────┐    ┌──────────┐    ┌──────────────┐    ┌──────────┐
│  Playwright  │───>│  Parser  │───>│   SQLite DB   │───>│ Telegram │
│  (scraper)   │    │ (extrae  │    │  (historico   │    │   Bot    │
│  cada 6h     │    │  precios)│    │   precios)    │    │ (alertas)│
└─────────────┘    └──────────┘    └──────────────┘    └──────────┘
```

4 modulos:
1. **Scraper** — Playwright headless Chromium visita cada URL de producto
2. **Parser** — Extrae precio actual, precio original, % descuento, variantes de peso
3. **Storage** — SQLite local en `./data/hsn_prices.db`
4. **Bot Telegram** — Alertas automaticas + comandos interactivos

## Productos a trackear

URLs configuradas en `config.yaml`. Productos activos inicialmente:

| Producto | URL |
|----------|-----|
| Evowhey Protein | https://www.hsnstore.com/marcas/sport-series/evowhey-protein |
| Proteina de Soja Aislada 2.0 | https://www.hsnstore.com/marcas/essential-series/proteina-de-soja-aislada-2-0 |
| Proteina de Guisante Aislada 2.0 | https://www.hsnstore.com/marcas/essential-series/proteina-de-guisante-aislada-2-0 |

Productos comentados (inactivos) en config:

| Producto | URL |
|----------|-----|
| Evolate 2.0 | https://www.hsnstore.com/marcas/sport-series/evolate-2-0-whey-isolate-cfm |
| Evopro | https://www.hsnstore.com/marcas/sport-series/evopro-mezcla-proteinas-premium-digezyme |
| Evohydro 2.0 | https://www.hsnstore.com/marcas/sport-series/evohydro-2-0-hydro-whey |
| Evoexcel 2.0 | https://www.hsnstore.com/marcas/sport-series/evoexcel-2-0-whey-protein-isolate-concentrate |

Cada producto puede tener multiples variantes de peso (500g, 1kg, 2kg, 3kg). El scraper detecta automaticamente todas las variantes disponibles.

## Base de datos (SQLite)

Fichero: `./data/hsn_prices.db`

### Tabla `products`

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| id | INTEGER PK | Auto-increment |
| name | TEXT NOT NULL | Nombre del producto |
| url | TEXT NOT NULL UNIQUE | URL de HSN |
| active | BOOLEAN DEFAULT 1 | Si se scrapea o no |

### Tabla `prices`

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| id | INTEGER PK | Auto-increment |
| product_id | INTEGER FK | Referencia a products.id |
| variant | TEXT NOT NULL | Peso (500g, 1kg, 2kg...) |
| price | REAL NOT NULL | Precio actual en EUR |
| original_price | REAL | Precio sin descuento (tachado) |
| discount_pct | REAL | Porcentaje de descuento |
| scraped_at | DATETIME NOT NULL | Timestamp UTC de la lectura |

Indice compuesto en `(product_id, variant, scraped_at)` para queries de historico.

### Tabla `settings`

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| key | TEXT PK | Clave de configuracion |
| value | TEXT NOT NULL | Valor |

Almacena el umbral de alerta y el chat_id de Telegram.

## Bot de Telegram

### Comandos

| Comando | Descripcion |
|---------|-------------|
| `/precios` | Precios actuales de todos los productos activos |
| `/historico <producto>` | Precio medio, minimo y maximo ultimos 30 dias |
| `/alerta <porcentaje>` | Configura umbral de bajada (defecto: 7%) |
| `/productos` | Lista productos trackeados y su estado |

### Alertas automaticas

Despues de cada scrape, se compara el precio nuevo con la media de los ultimos 7 dias. Si la bajada supera el umbral configurado, se envia:

```
Oferta detectada!
Evowhey Protein (2kg)
Precio: 35,90 EUR (antes 44,90 EUR)
Descuento: -20%
Media 7 dias: 42,50 EUR
Minimo historico: 34,90 EUR
```

### Flujo de alertas

1. `main.py` ejecuta el scrape
2. Inserta precios nuevos en SQLite
3. `alerts.py` compara con media de 7 dias
4. Si bajada > umbral, envia mensaje via `python-telegram-bot` (no requiere que el bot este corriendo como servidor)

## Estructura del proyecto

```
hsn_scrapper/
├── config.yaml              # URLs de productos + settings
├── requirements.txt         # Dependencias Python
├── Dockerfile               # Multi-stage, imagen minima
├── docker-compose.yml       # Orquesta bot + cron scraper
├── .gitignore               # Incluye data/
├── main.py                  # Entry point: ejecuta scrape + alertas
├── src/
│   ├── scraper.py           # Playwright: visita URLs, extrae precios
│   ├── parser.py            # Parsea HTML y extrae datos estructurados
│   ├── db.py                # SQLite: init, insert, queries
│   ├── bot.py               # Telegram bot: comandos + alertas
│   └── alerts.py            # Logica de deteccion de ofertas
└── data/                    # .gitignore'd, volumen Docker
    └── hsn_prices.db        # SQLite (se crea automaticamente)
```

## Docker

### Imagen

- Base: `python:3.12-slim`
- Solo instala Chromium para Playwright (sin Firefox/WebKit)
- Multi-stage build para minimizar peso
- Peso estimado: ~300-400MB

### docker-compose.yml

Dos servicios:
- **bot** — Telegram bot corriendo 24/7 (`python src/bot.py`)
- **scraper** — Cron cada 6h ejecuta `python main.py`

### Volumen

```yaml
volumes:
  - ./data:/app/data
```

`./data/` esta en `.gitignore`. La carpeta existe en el proyecto pero su contenido no se versiona.

### Ejecucion

```bash
docker compose up -d      # Arranca todo
docker compose logs -f    # Ver logs
```

## Dependencias Python

- `playwright` — scraping con headless Chromium
- `python-telegram-bot` — bot de Telegram + envio de alertas desde el cron
- `pyyaml` — lectura de config.yaml

## Configuracion

### config.yaml

```yaml
telegram:
  bot_token: ""        # Token del bot de Telegram
  chat_id: ""          # Chat ID donde enviar alertas

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

## Notas tecnicas

- Los precios en HSN se cargan dinamicamente con JavaScript, por eso se usa Playwright en vez de requests+BeautifulSoup
- La API REST de Magento (`/rest/V1/products`) requiere autenticacion, no es viable
- El scraper debe esperar a que los precios se rendericen en el DOM antes de extraerlos
- Se usa SQLite por simplicidad y porque el volumen de datos es minimo (~4 lecturas/dia por producto)
