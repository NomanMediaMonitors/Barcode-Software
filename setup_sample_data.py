"""
Setup script to initialize sample data for the Barcode Software
Run this once to populate your database with sample products, locations, and packers
"""

import database as db


def setup_sample_data():
    """Initialize database with sample data"""

    print("Setting up sample data...")

    # ============== PRODUCTS (3 items) ==============
    products = [
        ("BAG01", "Leather Bag Type A", "Premium leather handbag"),
        ("BAG02", "Canvas Bag Type B", "Durable canvas tote bag"),
        ("WAL01", "Leather Wallet", "Genuine leather wallet"),
    ]

    print("\nAdding products...")
    for code, name, desc in products:
        try:
            db.add_product(code, name, desc)
            print(f"  Added: {code} - {name}")
        except Exception as e:
            print(f"  Skipped: {code} (already exists)")

    # ============== LOCATIONS (8 destinations) ==============
    locations = [
        ("LOC01", "New York Warehouse", "123 Main St, New York, NY 10001"),
        ("LOC02", "Los Angeles Hub", "456 West Blvd, Los Angeles, CA 90001"),
        ("LOC03", "Chicago Distribution", "789 North Ave, Chicago, IL 60601"),
        ("LOC04", "Houston Facility", "321 South St, Houston, TX 77001"),
        ("LOC05", "Miami Center", "654 Beach Rd, Miami, FL 33101"),
        ("LOC06", "Seattle Store", "987 Pine St, Seattle, WA 98101"),
        ("LOC07", "Boston Branch", "147 Harbor Way, Boston, MA 02101"),
        ("LOC08", "Denver Depot", "258 Mountain Rd, Denver, CO 80201"),
    ]

    print("\nAdding locations...")
    for code, name, addr in locations:
        try:
            db.add_location(code, name, addr)
            print(f"  Added: {code} - {name}")
        except Exception as e:
            print(f"  Skipped: {code} (already exists)")

    # ============== PACKERS ==============
    packers = [
        ("PKR01", "John Smith"),
        ("PKR02", "Jane Doe"),
        ("PKR03", "Mike Johnson"),
        ("PKR04", "Sarah Williams"),
        ("PKR05", "David Brown"),
    ]

    print("\nAdding packers...")
    for code, name in packers:
        try:
            db.add_packer(code, name)
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
    print(f"  Packers:   {len(db.get_all_packers())}")

    print("\nYou can now run the application with: python app.py")


if __name__ == "__main__":
    setup_sample_data()
