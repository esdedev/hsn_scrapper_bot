import sqlite3
from datetime import datetime, timezone, timedelta


def init_db(db_path: str = "data/hsn_prices.db") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            active BOOLEAN NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL REFERENCES products(id),
            variant TEXT NOT NULL,
            price REAL NOT NULL,
            original_price REAL,
            discount_pct REAL,
            scraped_at DATETIME NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_prices_lookup
        ON prices(product_id, variant, scraped_at);

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)
    conn.commit()
    return conn


def upsert_product(conn: sqlite3.Connection, name: str, url: str) -> int:
    row = conn.execute("SELECT id FROM products WHERE url = ?", (url,)).fetchone()
    if row:
        conn.execute("UPDATE products SET name = ? WHERE url = ?", (name, url))
        conn.commit()
        return row[0]
    cursor = conn.execute(
        "INSERT INTO products (name, url) VALUES (?, ?)", (name, url)
    )
    conn.commit()
    return cursor.lastrowid


def insert_price(
    conn: sqlite3.Connection,
    product_id: int,
    variant: str,
    price: float,
    original_price: float | None,
    discount_pct: float | None,
    scraped_at: datetime,
) -> None:
    conn.execute(
        """INSERT INTO prices (product_id, variant, price, original_price, discount_pct, scraped_at)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (product_id, variant, price, original_price, discount_pct, scraped_at.isoformat()),
    )
    conn.commit()


def get_active_products(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT id, name, url FROM products WHERE active = 1"
    ).fetchall()
    return [{"id": r["id"], "name": r["name"], "url": r["url"]} for r in rows]


def get_latest_prices(conn: sqlite3.Connection, product_id: int) -> list[dict]:
    rows = conn.execute(
        """SELECT variant, price, original_price, discount_pct, scraped_at
        FROM prices
        WHERE product_id = ?
        AND scraped_at = (
            SELECT MAX(p2.scraped_at) FROM prices p2
            WHERE p2.product_id = prices.product_id AND p2.variant = prices.variant
        )
        ORDER BY variant""",
        (product_id,),
    ).fetchall()
    return [
        {
            "variant": r["variant"],
            "price": r["price"],
            "original_price": r["original_price"],
            "discount_pct": r["discount_pct"],
            "scraped_at": r["scraped_at"],
        }
        for r in rows
    ]


def get_average_price(
    conn: sqlite3.Connection, product_id: int, variant: str, days: int = 7
) -> float | None:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    row = conn.execute(
        """SELECT AVG(price) as avg_price FROM prices
        WHERE product_id = ? AND variant = ? AND scraped_at >= ?""",
        (product_id, variant, since),
    ).fetchone()
    return row["avg_price"] if row and row["avg_price"] is not None else None


def get_min_price(
    conn: sqlite3.Connection, product_id: int, variant: str
) -> float | None:
    row = conn.execute(
        "SELECT MIN(price) as min_price FROM prices WHERE product_id = ? AND variant = ?",
        (product_id, variant),
    ).fetchone()
    return row["min_price"] if row and row["min_price"] is not None else None


def get_price_stats(
    conn: sqlite3.Connection, product_id: int, variant: str, days: int = 30
) -> dict:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    row = conn.execute(
        """SELECT MIN(price) as min, MAX(price) as max, AVG(price) as avg
        FROM prices
        WHERE product_id = ? AND variant = ? AND scraped_at >= ?""",
        (product_id, variant, since),
    ).fetchone()
    return {
        "min": row["min"],
        "max": row["max"],
        "avg": row["avg"],
    }


def get_setting(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?",
        (key, value, value),
    )
    conn.commit()
