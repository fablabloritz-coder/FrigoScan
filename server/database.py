"""
FrigoScan — Module base de données SQLite.
Gestion de la connexion, création du schéma et helpers CRUD.
"""

import sqlite3
import json
import os
from datetime import datetime, date
from pathlib import Path

DB_DIR = Path(__file__).parent / "data"
DB_PATH = DB_DIR / "frigoscan.db"


def get_db() -> sqlite3.Connection:
    """Retourne une connexion SQLite avec row_factory = Row."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def dict_from_row(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return dict(row)


def rows_to_list(rows: list[sqlite3.Row]) -> list[dict]:
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Schéma
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barcode TEXT UNIQUE,
    name TEXT NOT NULL,
    brand TEXT,
    image_url TEXT,
    category TEXT,
    nutrition_json TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fridge_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    name TEXT NOT NULL,
    barcode TEXT,
    image_url TEXT,
    category TEXT DEFAULT 'autre',
    quantity REAL DEFAULT 1,
    unit TEXT DEFAULT 'unité',
    dlc DATE,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    nutrition_json TEXT DEFAULT '{}',
    status TEXT DEFAULT 'active',
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS consumption_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fridge_item_id INTEGER,
    product_name TEXT NOT NULL,
    category TEXT,
    quantity REAL DEFAULT 1,
    unit TEXT DEFAULT 'unité',
    consumed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_name TEXT DEFAULT 'Famille'
);

CREATE TABLE IF NOT EXISTS recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    ingredients_json TEXT DEFAULT '[]',
    instructions TEXT,
    prep_time INTEGER DEFAULT 0,
    cook_time INTEGER DEFAULT 0,
    servings INTEGER DEFAULT 4,
    source_url TEXT,
    image_url TEXT,
    tags_json TEXT DEFAULT '[]',
    diet_tags_json TEXT DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS weekly_menu (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_start DATE NOT NULL,
    day_of_week INTEGER NOT NULL,
    meal_type TEXT NOT NULL DEFAULT 'lunch',
    recipe_id INTEGER,
    recipe_title TEXT,
    notes TEXT,
    servings INTEGER DEFAULT 4,
    is_pinned INTEGER DEFAULT 0,
    recipe_data_json TEXT,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id)
);

CREATE TABLE IF NOT EXISTS shopping_list (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    category TEXT DEFAULT 'autre',
    quantity REAL DEFAULT 1,
    unit TEXT DEFAULT 'unité',
    is_purchased INTEGER DEFAULT 0,
    source TEXT DEFAULT 'manual',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS stock_minimums (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL UNIQUE,
    category TEXT DEFAULT 'autre',
    min_quantity REAL DEFAULT 1,
    unit TEXT DEFAULT 'unité'
);

CREATE TABLE IF NOT EXISTS banned_recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL UNIQUE,
    image_url TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

DEFAULT_SETTINGS = {
    "theme": "light",
    "language": "fr",
    "nb_persons": "4",
    "diets": "[]",
    "allergens": "[]",
    "shopping_frequency": "7",
    "scan_interval": "2",
    "scan_beep": "true",
    "scan_beep_volume": "0.5",
    "default_camera": "",
    "webcam_resolution": "1280x720",
    "recipe_prefer_dlc": "true",
    "recipe_prefer_seasonal": "true",
    "menu_mode": "after_shopping",
    "auto_save": "true",
    "notifications_enabled": "false",
    "dashboard_widgets": '["scan","manual","fridge","recipes","menu","seasonal","shopping","stats"]',
}


def init_db():
    """Crée les tables et insère les réglages par défaut si absents."""
    conn = get_db()
    try:
        conn.executescript(SCHEMA_SQL)
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )
        # Migration : ajouter is_pinned si absent
        try:
            conn.execute("ALTER TABLE weekly_menu ADD COLUMN is_pinned INTEGER DEFAULT 0")
            conn.commit()
        except Exception:
            pass  # Colonne déjà existante
        # Migration : ajouter recipe_data_json si absent
        try:
            conn.execute("ALTER TABLE weekly_menu ADD COLUMN recipe_data_json TEXT")
            conn.commit()
        except Exception:
            pass  # Colonne déjà existante
        conn.commit()
    finally:
        conn.close()


def backup_db(dest_path: str | None = None) -> str:
    """Crée une copie de sauvegarde de la base."""
    if dest_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_path = str(DB_DIR / f"frigoscan_backup_{ts}.db")
    import shutil
    shutil.copy2(str(DB_PATH), dest_path)
    return dest_path


def reset_db():
    """Supprime et recrée la base (double confirmation côté client)."""
    if DB_PATH.exists():
        os.remove(str(DB_PATH))
    init_db()
