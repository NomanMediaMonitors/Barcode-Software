"""
Configuration settings for Barcode Software
"""

# Database settings
DATABASE_PATH = "barcode_data.db"

# Barcode settings
BARCODE_TYPE = "code128"  # Options: code128, code39, ean13, qrcode
BARCODE_PREFIX = "PKG"    # Prefix for generated codes

# Label settings (in mm for TSC TE200)
LABEL_WIDTH = 50
LABEL_HEIGHT = 30
LABEL_GAP = 3

# Printer settings for TSC TE200
PRINTER_SETTINGS = {
    "name": "TSC TE200",
    "port": "USB",  # Can be COM port like "COM3" or "USB"
    "speed": 4,     # Print speed (1-6)
    "density": 8,   # Print density (0-15)
    "width": 400,   # Label width in dots (8 dots/mm)
    "height": 240,  # Label height in dots
}

# Date format for timestamps
DATE_FORMAT = "%Y%m%d%H%M%S"
SHORT_DATE_FORMAT = "%Y-%m-%d %H:%M"
