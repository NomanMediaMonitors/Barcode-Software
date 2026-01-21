"""
Setup script to initialize sample data for the Barcode Software
Run this once to populate your database with sample products and locations

Requires MySQL server running at 172.168.100.215
"""

import sys
import database as db
from config import DATABASE_CONFIG


def setup_sample_data():
    """Initialize database with sample data"""

    print("=" * 50)
    print("Barcode Software - Database Setup")
    print("=" * 50)

    # Test connection first
    print(f"\nConnecting to MySQL server at {DATABASE_CONFIG['host']}...")
    success, message = db.test_connection()

    if not success:
        print(f"ERROR: {message}")
        print("\nPlease check:")
        print("  1. MySQL server is running")
        print("  2. Network connectivity to 172.168.100.215")
        print("  3. User 'dev' has proper permissions")
        sys.exit(1)

    print("Connection successful!")
    print("\nInitializing database tables...")
    db.init_database()

    print("\nSetting up sample data...")

    # ============== PRODUCTS ==============
    # Format: (code, name, description)
    products = [
        ("WALT BLCK", "WALLET BLACK", "Premium black leather wallet"),
        ("WALT BRWN", "WALLET BROWN", "Premium brown leather wallet"),
        ("WALT TAN", "WALLET TAN", "Premium tan leather wallet"),
        ("4PCS BLCK", "4PC SET BLACK", "4-piece luggage set in black"),
        ("4PCS BRWN", "4PC SET BROWN", "4-piece luggage set in brown"),
        ("4PCS TAN", "4PC SET TAN", "4-piece luggage set in tan"),
        ("LAPB NVYB", "LAPTOP BAG NAVY BLUE", "Navy blue laptop bag"),
    ]

    print("\nAdding products...")
    for code, name, desc in products:
        try:
            db.add_product(code, name, desc)
            print(f"  Added: {code} - {name}")
        except Exception as e:
            print(f"  Skipped: {code} (already exists)")

    # ============== LOCATIONS (8 destinations) ==============
    # Format: (city_code, city_name, address)
    locations = [
        ("ISB", "Islamabad", "Islamabad, Pakistan"),
        ("SAR", "Sargodha", "Sargodha, Pakistan"),
        ("HYD", "Hyderabad", "Hyderabad, Pakistan"),
        ("HOK", "H.O.Karachi", "Head Office Karachi, Pakistan"),
        ("JEH", "Jehlum", "Jehlum, Pakistan"),
        ("KAR", "Karachi", "Karachi, Pakistan"),
        ("LHR", "Lahore", "Lahore, Pakistan"),
        ("MUL", "Multan", "Multan, Pakistan"),
    ]

    print("\nAdding locations...")
    for code, name, addr in locations:
        try:
            db.add_location(code, name, addr)
            print(f"  Added: {code} - {name}")
        except Exception as e:
            print(f"  Skipped: {code} (already exists)")

    print("\n" + "="*50)
    print("Sample data setup complete!")
    print("="*50)

    # Display summary
    print(f"\nSummary:")
    print(f"  Products:  {len(db.get_all_products())}")
    print(f"  Locations: {len(db.get_all_locations())}")

    print("\nDelivery Codes available: 1A, 1B, 1C, 2A, 2B, 2C, 3A, 3B")
    print("\nBarcode format: LOCATION-PRODUCT-SERIAL")
    print("Example: ISB-WALT BLCK-0001")

    print("\nYou can now run the application with: python app.py")


if __name__ == "__main__":
    setup_sample_data()
