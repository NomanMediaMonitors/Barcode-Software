"""
Configuration settings for Barcode Software
"""

# MySQL Database settings
DATABASE_CONFIG = {
    "host": "172.168.100.215",
    "user": "dev",
    "password": "master",
    "database": "barcode_system",
    "port": 3306,
}

# Barcode settings
BARCODE_TYPE = "code128"  # Options: code128, code39, ean13, qrcode
BARCODE_PREFIX = "PKG"    # Prefix for generated codes

# Label settings (in mm for TSC TE200)
# 2-column sticker layout: full page 4.25" wide, each sticker 2" x 1.5"
LABEL_WIDTH = 108   # Full page width: 4.25 inches = 108mm
LABEL_HEIGHT = 38   # Sticker height: 1.5 inches = 38mm
LABEL_GAP = 3       # Vertical gap between label rows
STICKER_WIDTH = 51  # Individual sticker width: 2 inches = 51mm
STICKER_GAP = 3     # Horizontal gap between 2 stickers (0.125" = 3mm)

# Printer specifications (from driver/hardware)
# These values define the physical capabilities of the printer
PRINTER_SPECS = {
    # Resolution
    "x_resolution_dpi": 203,       # Printer X Resolution: 203 dpi
    "y_resolution_dpi": 203,       # Printer Y Resolution: 203 dpi
    "dots_per_mm": 8,              # 203 dpi = ~8 dots/mm

    # Media dimensions (in inches)
    "min_media_width_in": 0.20,    # Minimum Media Width
    "min_media_length_in": 0.20,   # Minimum Media Length
    "max_media_width_in": 4.41,    # Maximum Media Width
    "max_media_length_in": 110.00, # Maximum Media Length
    "printable_width_in": 4.25,    # Printable Width
    "unprintable_width_in": 0.00,  # Unprintable Width

    # Media dimensions (in mm, converted)
    "max_media_width_mm": 112,     # 4.41 in = ~112mm
    "printable_width_mm": 108,     # 4.25 in = ~108mm

    # Orientation and loading
    "paper_loading": "center",     # Paper Loading: Center
    "natural_orientation": 180,    # Natural Orientation: 180°

    # Features
    "mirror_image": True,          # Mirror Image: Supported
    "negative_image": True,        # Negative Image: Supported
    "color": "monochrome",         # Color: Monochrome

    # Drawing capabilities
    "line_thickness_max": 9999,    # Line Thickness Maximum: 9999 dots
    "box_thickness_max": 9999,     # Box Thickness Maximum: 9999 dots
    "circles_supported": False,    # Circles: Not Supported
    "ellipses_supported": False,   # Ellipses: Not Supported

    # Optimizations
    "max_copies": 999999999,       # Maximum Copies
    "serialization": True,         # Serialization: Supported
    "format_mode": True,           # Format Mode: Supported
    "graphics_caching": True,      # Graphics Caching: Supported
}

# Printer settings for TSC TE200
# Configured for 2-column sticker layout (full page width)
PRINTER_SETTINGS = {
    "name": "TSC TE200",
    "port": "USB",  # Can be COM port like "COM3" or "USB"
    "speed": 4,     # Print speed (1-6)
    "density": 8,   # Print density (0-15)
    "width": 864,   # Full page width in dots (8 dots/mm × 108mm)
    "height": 304,  # Label height in dots (8 dots/mm × 38mm)
    "direction": 0, # Print direction (0 for 180° natural orientation printers)
    "mirror": 0,    # Mirror mode (0=normal, 1=mirror)
    "sticker_width_dots": 408,  # Single sticker: 51mm × 8 = 408 dots
    "sticker_gap_dots": 24,     # Gap: 3mm × 8 = 24 dots
}

# Date format for timestamps
DATE_FORMAT = "%Y%m%d%H%M%S"
SHORT_DATE_FORMAT = "%Y-%m-%d %H:%M"
