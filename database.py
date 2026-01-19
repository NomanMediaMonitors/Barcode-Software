"""
Database module for managing products, locations, packers, and barcode history
"""

import sqlite3
from datetime import datetime
from typing import Optional
from config import DATABASE_PATH


def get_connection():
    """Get database connection with row factory"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize database with required tables"""
    conn = get_connection()
    cursor = conn.cursor()

    # Products table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Locations table (8 destinations)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL,
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Packers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS packers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL,
            active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Barcode history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS barcode_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode_data VARCHAR(100) NOT NULL,
            product_id INTEGER,
            location_id INTEGER,
            packer_id INTEGER,
            quantity INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (location_id) REFERENCES locations(id),
            FOREIGN KEY (packer_id) REFERENCES packers(id)
        )
    ''')

    conn.commit()
    conn.close()


# ============== PRODUCT FUNCTIONS ==============

def add_product(code: str, name: str, description: str = "") -> int:
    """Add a new product"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (code, name, description) VALUES (?, ?, ?)",
        (code.upper(), name, description)
    )
    conn.commit()
    product_id = cursor.lastrowid
    conn.close()
    return product_id


def get_all_products():
    """Get all products"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products ORDER BY name")
    products = cursor.fetchall()
    conn.close()
    return products


def get_product_by_id(product_id: int):
    """Get product by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = cursor.fetchone()
    conn.close()
    return product


def delete_product(product_id: int):
    """Delete a product"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()


# ============== LOCATION FUNCTIONS ==============

def add_location(code: str, name: str, address: str = "") -> int:
    """Add a new location/destination"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO locations (code, name, address) VALUES (?, ?, ?)",
        (code.upper(), name, address)
    )
    conn.commit()
    location_id = cursor.lastrowid
    conn.close()
    return location_id


def get_all_locations():
    """Get all locations"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM locations ORDER BY name")
    locations = cursor.fetchall()
    conn.close()
    return locations


def get_location_by_id(location_id: int):
    """Get location by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM locations WHERE id = ?", (location_id,))
    location = cursor.fetchone()
    conn.close()
    return location


def delete_location(location_id: int):
    """Delete a location"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM locations WHERE id = ?", (location_id,))
    conn.commit()
    conn.close()


# ============== PACKER FUNCTIONS ==============

def add_packer(code: str, name: str) -> int:
    """Add a new packer"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO packers (code, name) VALUES (?, ?)",
        (code.upper(), name)
    )
    conn.commit()
    packer_id = cursor.lastrowid
    conn.close()
    return packer_id


def get_all_packers(active_only: bool = True):
    """Get all packers"""
    conn = get_connection()
    cursor = conn.cursor()
    if active_only:
        cursor.execute("SELECT * FROM packers WHERE active = 1 ORDER BY name")
    else:
        cursor.execute("SELECT * FROM packers ORDER BY name")
    packers = cursor.fetchall()
    conn.close()
    return packers


def get_packer_by_id(packer_id: int):
    """Get packer by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM packers WHERE id = ?", (packer_id,))
    packer = cursor.fetchone()
    conn.close()
    return packer


def toggle_packer_active(packer_id: int):
    """Toggle packer active status"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE packers SET active = NOT active WHERE id = ?",
        (packer_id,)
    )
    conn.commit()
    conn.close()


def delete_packer(packer_id: int):
    """Delete a packer"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM packers WHERE id = ?", (packer_id,))
    conn.commit()
    conn.close()


# ============== BARCODE HISTORY FUNCTIONS ==============

def save_barcode_history(barcode_data: str, product_id: int,
                         location_id: int, packer_id: int,
                         quantity: int = 1) -> int:
    """Save barcode generation to history"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO barcode_history
           (barcode_data, product_id, location_id, packer_id, quantity)
           VALUES (?, ?, ?, ?, ?)""",
        (barcode_data, product_id, location_id, packer_id, quantity)
    )
    conn.commit()
    history_id = cursor.lastrowid
    conn.close()
    return history_id


def get_barcode_history(limit: int = 100):
    """Get recent barcode history with details"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            bh.id,
            bh.barcode_data,
            bh.quantity,
            bh.created_at,
            p.code as product_code,
            p.name as product_name,
            l.code as location_code,
            l.name as location_name,
            pk.code as packer_code,
            pk.name as packer_name
        FROM barcode_history bh
        LEFT JOIN products p ON bh.product_id = p.id
        LEFT JOIN locations l ON bh.location_id = l.id
        LEFT JOIN packers pk ON bh.packer_id = pk.id
        ORDER BY bh.created_at DESC
        LIMIT ?
    ''', (limit,))
    history = cursor.fetchall()
    conn.close()
    return history


def get_history_by_packer(packer_id: int, limit: int = 50):
    """Get barcode history for a specific packer"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            bh.*,
            p.name as product_name,
            l.name as location_name
        FROM barcode_history bh
        LEFT JOIN products p ON bh.product_id = p.id
        LEFT JOIN locations l ON bh.location_id = l.id
        WHERE bh.packer_id = ?
        ORDER BY bh.created_at DESC
        LIMIT ?
    ''', (packer_id, limit))
    history = cursor.fetchall()
    conn.close()
    return history


def get_daily_stats(date: Optional[str] = None):
    """Get daily packing statistics"""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            pk.name as packer_name,
            COUNT(*) as total_labels,
            SUM(bh.quantity) as total_items
        FROM barcode_history bh
        JOIN packers pk ON bh.packer_id = pk.id
        WHERE DATE(bh.created_at) = ?
        GROUP BY bh.packer_id
        ORDER BY total_items DESC
    ''', (date,))
    stats = cursor.fetchall()
    conn.close()
    return stats


# Initialize database on import
init_database()
