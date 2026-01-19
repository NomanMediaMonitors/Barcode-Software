"""
Database module for managing products, locations, packers, and barcode history
Uses MySQL database
"""

import mysql.connector
from mysql.connector import Error
from datetime import datetime
from typing import Optional
from config import DATABASE_CONFIG


def get_connection():
    """Get MySQL database connection"""
    try:
        conn = mysql.connector.connect(
            host=DATABASE_CONFIG["host"],
            user=DATABASE_CONFIG["user"],
            password=DATABASE_CONFIG["password"],
            database=DATABASE_CONFIG["database"],
            port=DATABASE_CONFIG.get("port", 3306)
        )
        return conn
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        raise


def get_connection_without_db():
    """Get MySQL connection without selecting database (for initial setup)"""
    try:
        conn = mysql.connector.connect(
            host=DATABASE_CONFIG["host"],
            user=DATABASE_CONFIG["user"],
            password=DATABASE_CONFIG["password"],
            port=DATABASE_CONFIG.get("port", 3306)
        )
        return conn
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        raise


def init_database():
    """Initialize database with required tables"""
    # First, create database if not exists
    try:
        conn = get_connection_without_db()
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DATABASE_CONFIG['database']}")
        conn.commit()
        cursor.close()
        conn.close()
    except Error as e:
        print(f"Error creating database: {e}")
        raise

    # Now connect to the database and create tables
    conn = get_connection()
    cursor = conn.cursor()

    # Products table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INT AUTO_INCREMENT PRIMARY KEY,
            code VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')

    # Locations table (8 destinations)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS locations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            code VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL,
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')

    # Packers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS packers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            code VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL,
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')

    # Barcode history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS barcode_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            barcode_data VARCHAR(100) NOT NULL,
            product_id INT,
            location_id INT,
            packer_id INT,
            quantity INT DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL,
            FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE SET NULL,
            FOREIGN KEY (packer_id) REFERENCES packers(id) ON DELETE SET NULL,
            INDEX idx_created_at (created_at),
            INDEX idx_packer_id (packer_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')

    conn.commit()
    cursor.close()
    conn.close()
    print("Database initialized successfully!")


def row_to_dict(cursor, row):
    """Convert a row to dictionary using cursor description"""
    if row is None:
        return None
    columns = [col[0] for col in cursor.description]
    return dict(zip(columns, row))


def rows_to_dicts(cursor, rows):
    """Convert multiple rows to list of dictionaries"""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in rows]


# ============== PRODUCT FUNCTIONS ==============

def add_product(code: str, name: str, description: str = "") -> int:
    """Add a new product"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (code, name, description) VALUES (%s, %s, %s)",
        (code.upper(), name, description)
    )
    conn.commit()
    product_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return product_id


def get_all_products():
    """Get all products"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products ORDER BY name")
    rows = cursor.fetchall()
    products = rows_to_dicts(cursor, rows)
    cursor.close()
    conn.close()
    return products


def get_product_by_id(product_id: int):
    """Get product by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
    row = cursor.fetchone()
    product = row_to_dict(cursor, row)
    cursor.close()
    conn.close()
    return product


def update_product(product_id: int, code: str = None, name: str = None, description: str = None):
    """Update a product"""
    conn = get_connection()
    cursor = conn.cursor()

    updates = []
    values = []

    if code is not None:
        updates.append("code = %s")
        values.append(code.upper())
    if name is not None:
        updates.append("name = %s")
        values.append(name)
    if description is not None:
        updates.append("description = %s")
        values.append(description)

    if updates:
        values.append(product_id)
        cursor.execute(
            f"UPDATE products SET {', '.join(updates)} WHERE id = %s",
            tuple(values)
        )
        conn.commit()

    cursor.close()
    conn.close()


def delete_product(product_id: int):
    """Delete a product"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
    conn.commit()
    cursor.close()
    conn.close()


# ============== LOCATION FUNCTIONS ==============

def add_location(code: str, name: str, address: str = "") -> int:
    """Add a new location/destination"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO locations (code, name, address) VALUES (%s, %s, %s)",
        (code.upper(), name, address)
    )
    conn.commit()
    location_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return location_id


def get_all_locations():
    """Get all locations"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM locations ORDER BY name")
    rows = cursor.fetchall()
    locations = rows_to_dicts(cursor, rows)
    cursor.close()
    conn.close()
    return locations


def get_location_by_id(location_id: int):
    """Get location by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM locations WHERE id = %s", (location_id,))
    row = cursor.fetchone()
    location = row_to_dict(cursor, row)
    cursor.close()
    conn.close()
    return location


def update_location(location_id: int, code: str = None, name: str = None, address: str = None):
    """Update a location"""
    conn = get_connection()
    cursor = conn.cursor()

    updates = []
    values = []

    if code is not None:
        updates.append("code = %s")
        values.append(code.upper())
    if name is not None:
        updates.append("name = %s")
        values.append(name)
    if address is not None:
        updates.append("address = %s")
        values.append(address)

    if updates:
        values.append(location_id)
        cursor.execute(
            f"UPDATE locations SET {', '.join(updates)} WHERE id = %s",
            tuple(values)
        )
        conn.commit()

    cursor.close()
    conn.close()


def delete_location(location_id: int):
    """Delete a location"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM locations WHERE id = %s", (location_id,))
    conn.commit()
    cursor.close()
    conn.close()


# ============== PACKER FUNCTIONS ==============

def add_packer(code: str, name: str) -> int:
    """Add a new packer"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO packers (code, name) VALUES (%s, %s)",
        (code.upper(), name)
    )
    conn.commit()
    packer_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return packer_id


def get_all_packers(active_only: bool = True):
    """Get all packers"""
    conn = get_connection()
    cursor = conn.cursor()
    if active_only:
        cursor.execute("SELECT * FROM packers WHERE active = TRUE ORDER BY name")
    else:
        cursor.execute("SELECT * FROM packers ORDER BY name")
    rows = cursor.fetchall()
    packers = rows_to_dicts(cursor, rows)
    cursor.close()
    conn.close()
    return packers


def get_packer_by_id(packer_id: int):
    """Get packer by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM packers WHERE id = %s", (packer_id,))
    row = cursor.fetchone()
    packer = row_to_dict(cursor, row)
    cursor.close()
    conn.close()
    return packer


def toggle_packer_active(packer_id: int):
    """Toggle packer active status"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE packers SET active = NOT active WHERE id = %s",
        (packer_id,)
    )
    conn.commit()
    cursor.close()
    conn.close()


def update_packer(packer_id: int, code: str = None, name: str = None, active: bool = None):
    """Update a packer"""
    conn = get_connection()
    cursor = conn.cursor()

    updates = []
    values = []

    if code is not None:
        updates.append("code = %s")
        values.append(code.upper())
    if name is not None:
        updates.append("name = %s")
        values.append(name)
    if active is not None:
        updates.append("active = %s")
        values.append(active)

    if updates:
        values.append(packer_id)
        cursor.execute(
            f"UPDATE packers SET {', '.join(updates)} WHERE id = %s",
            tuple(values)
        )
        conn.commit()

    cursor.close()
    conn.close()


def delete_packer(packer_id: int):
    """Delete a packer"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM packers WHERE id = %s", (packer_id,))
    conn.commit()
    cursor.close()
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
           VALUES (%s, %s, %s, %s, %s)""",
        (barcode_data, product_id, location_id, packer_id, quantity)
    )
    conn.commit()
    history_id = cursor.lastrowid
    cursor.close()
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
        LIMIT %s
    ''', (limit,))
    rows = cursor.fetchall()
    history = rows_to_dicts(cursor, rows)
    cursor.close()
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
        WHERE bh.packer_id = %s
        ORDER BY bh.created_at DESC
        LIMIT %s
    ''', (packer_id, limit))
    rows = cursor.fetchall()
    history = rows_to_dicts(cursor, rows)
    cursor.close()
    conn.close()
    return history


def get_history_by_date_range(start_date: str, end_date: str, limit: int = 1000):
    """Get barcode history for a date range"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            bh.*,
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
        WHERE DATE(bh.created_at) BETWEEN %s AND %s
        ORDER BY bh.created_at DESC
        LIMIT %s
    ''', (start_date, end_date, limit))
    rows = cursor.fetchall()
    history = rows_to_dicts(cursor, rows)
    cursor.close()
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
        WHERE DATE(bh.created_at) = %s
        GROUP BY bh.packer_id, pk.name
        ORDER BY total_items DESC
    ''', (date,))
    rows = cursor.fetchall()
    stats = rows_to_dicts(cursor, rows)
    cursor.close()
    conn.close()
    return stats


def get_location_stats(date: Optional[str] = None):
    """Get daily statistics by location"""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            l.code as location_code,
            l.name as location_name,
            COUNT(*) as total_labels,
            SUM(bh.quantity) as total_items
        FROM barcode_history bh
        JOIN locations l ON bh.location_id = l.id
        WHERE DATE(bh.created_at) = %s
        GROUP BY bh.location_id, l.code, l.name
        ORDER BY total_items DESC
    ''', (date,))
    rows = cursor.fetchall()
    stats = rows_to_dicts(cursor, rows)
    cursor.close()
    conn.close()
    return stats


def test_connection():
    """Test database connection"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()
        return True, "Connection successful!"
    except Error as e:
        return False, f"Connection failed: {e}"


# Initialize database on import
if __name__ != "__main__":
    try:
        init_database()
    except Exception as e:
        print(f"Warning: Could not initialize database: {e}")
        print("Please ensure MySQL server is running and credentials are correct.")
