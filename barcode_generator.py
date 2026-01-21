"""
Barcode generation module supporting Code128, Code39, and QR codes
"""

import os
from datetime import datetime
from io import BytesIO
from typing import Optional, Tuple

import barcode
from barcode.writer import ImageWriter
import qrcode
from PIL import Image, ImageDraw, ImageFont

from config import BARCODE_TYPE, BARCODE_PREFIX, DATE_FORMAT


class BarcodeGenerator:
    """Generate barcodes with embedded metadata"""

    def __init__(self, output_dir: str = "barcodes"):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def generate_barcode_data(self, location_code: str, product_code: str,
                               serial: int) -> str:
        """
        Generate the data string to be encoded in the barcode

        Format: {LOCATION}-{PRODUCT}-{SERIAL}
        Example: ISB-WALT BLCK-0001
        """
        barcode_data = f"{location_code}-{product_code}-{serial:04d}"
        return barcode_data

    def parse_barcode_data(self, barcode_data: str) -> dict:
        """
        Parse barcode data back into components

        Returns dict with: location_code, product_code, serial
        """
        parts = barcode_data.rsplit("-", 1)  # Split from right to handle product codes with spaces
        if len(parts) == 2:
            location_product = parts[0]
            serial = parts[1]
            # Split location from product (first dash)
            loc_parts = location_product.split("-", 1)
            if len(loc_parts) == 2:
                return {
                    "location_code": loc_parts[0],
                    "product_code": loc_parts[1],
                    "serial": serial
                }
        return {"raw": barcode_data}

    def generate_code128(self, data: str, include_text: bool = True) -> Image.Image:
        """Generate Code128 barcode image"""
        code128 = barcode.get_barcode_class('code128')

        # Configure writer options
        writer = ImageWriter()
        options = {
            'module_width': 0.4,
            'module_height': 15.0,
            'font_size': 10,
            'text_distance': 5.0,
            'quiet_zone': 6.5,
            'write_text': include_text
        }

        # Generate barcode
        barcode_instance = code128(data, writer=writer)

        # Write to BytesIO buffer
        buffer = BytesIO()
        barcode_instance.write(buffer, options=options)
        buffer.seek(0)

        # Return as PIL Image
        return Image.open(buffer)

    def generate_code39(self, data: str, include_text: bool = True) -> Image.Image:
        """Generate Code39 barcode image"""
        code39 = barcode.get_barcode_class('code39')

        writer = ImageWriter()
        options = {
            'module_width': 0.4,
            'module_height': 15.0,
            'font_size': 10,
            'text_distance': 5.0,
            'quiet_zone': 6.5,
            'write_text': include_text
        }

        barcode_instance = code39(data, writer=writer, add_checksum=False)

        buffer = BytesIO()
        barcode_instance.write(buffer, options=options)
        buffer.seek(0)

        return Image.open(buffer)

    def generate_qrcode(self, data: str, box_size: int = 10,
                        border: int = 4) -> Image.Image:
        """Generate QR code image"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=box_size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)

        return qr.make_image(fill_color="black", back_color="white")

    def generate_barcode(self, data: str, barcode_type: str = None) -> Image.Image:
        """
        Generate barcode based on type

        Args:
            data: Data to encode
            barcode_type: Type of barcode (code128, code39, qrcode)
        """
        if barcode_type is None:
            barcode_type = BARCODE_TYPE

        barcode_type = barcode_type.lower()

        if barcode_type == "code128":
            return self.generate_code128(data)
        elif barcode_type == "code39":
            return self.generate_code39(data)
        elif barcode_type in ("qrcode", "qr"):
            return self.generate_qrcode(data)
        else:
            raise ValueError(f"Unsupported barcode type: {barcode_type}")

    def create_label(self, barcode_data: str, product_name: str,
                     location_name: str, delivery_code: str,
                     barcode_type: str = None,
                     label_size: Tuple[int, int] = (400, 300)) -> Image.Image:
        """
        Create a complete label with barcode and text information

        Args:
            barcode_data: Data to encode in barcode
            product_name: Product name to display
            location_name: Destination location name
            delivery_code: Delivery code to display
            barcode_type: Type of barcode
            label_size: Label size in pixels (width, height)
        """
        width, height = label_size

        # Create white background
        label = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(label)

        # Try to use a nice font, fall back to default
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
            font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
        except (OSError, IOError):
            font_large = ImageFont.load_default()
            font_medium = font_large
            font_small = font_large

        # Generate barcode
        barcode_img = self.generate_barcode(barcode_data, barcode_type)

        # Resize barcode to fit
        barcode_max_width = width - 40
        barcode_max_height = height - 100

        barcode_ratio = min(
            barcode_max_width / barcode_img.width,
            barcode_max_height / barcode_img.height
        )
        new_size = (
            int(barcode_img.width * barcode_ratio),
            int(barcode_img.height * barcode_ratio)
        )
        barcode_img = barcode_img.resize(new_size, Image.Resampling.LANCZOS)

        # Calculate positions
        barcode_x = (width - barcode_img.width) // 2
        barcode_y = 50

        # Paste barcode (handle both RGB and RGBA)
        if barcode_img.mode == 'RGBA':
            label.paste(barcode_img, (barcode_x, barcode_y), barcode_img)
        else:
            label.paste(barcode_img, (barcode_x, barcode_y))

        # Draw text information
        y_offset = 10

        # Product name at top
        draw.text((10, y_offset), f"Product: {product_name}", font=font_large, fill='black')

        # Location and delivery code at bottom
        bottom_y = barcode_y + barcode_img.height + 10
        draw.text((10, bottom_y), f"Dest: {location_name}", font=font_medium, fill='black')
        draw.text((10, bottom_y + 18), f"Delivery: {delivery_code}", font=font_medium, fill='black')

        # Timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        draw.text((width - 120, bottom_y + 18), timestamp, font=font_small, fill='gray')

        return label

    def save_barcode(self, image: Image.Image, filename: str) -> str:
        """Save barcode image to file"""
        if not filename.endswith(('.png', '.jpg', '.bmp')):
            filename += '.png'

        filepath = os.path.join(self.output_dir, filename)
        image.save(filepath)
        return filepath

    def generate_and_save(self, location_code: str, product_code: str,
                          serial: int, product_name: str,
                          location_name: str, delivery_code: str,
                          barcode_type: str = None) -> Tuple[str, str, Image.Image]:
        """
        Complete workflow: generate barcode data, create label, and save

        Returns:
            Tuple of (barcode_data, filepath, image)
        """
        # Generate barcode data
        barcode_data = self.generate_barcode_data(
            location_code, product_code, serial
        )

        # Create label
        label = self.create_label(
            barcode_data, product_name, location_name,
            delivery_code, barcode_type
        )

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{product_code}_{location_code}_{serial:04d}_{timestamp}.png"

        # Save
        filepath = self.save_barcode(label, filename)

        return barcode_data, filepath, label


# Convenience function
def create_barcode(location_code: str, product_code: str, serial: int,
                   product_name: str = "", location_name: str = "",
                   delivery_code: str = "", barcode_type: str = "code128") -> Tuple[str, Image.Image]:
    """
    Quick function to create a barcode label

    Returns:
        Tuple of (barcode_data, label_image)
    """
    generator = BarcodeGenerator()

    barcode_data = generator.generate_barcode_data(
        location_code, product_code, serial
    )

    label = generator.create_label(
        barcode_data,
        product_name or product_code,
        location_name or location_code,
        delivery_code or "1A",
        barcode_type
    )

    return barcode_data, label


if __name__ == "__main__":
    # Test barcode generation
    gen = BarcodeGenerator()

    # Test data with new format: LOCATION-PRODUCT-SERIAL
    barcode_data, filepath, img = gen.generate_and_save(
        location_code="ISB",
        product_code="WALT BLCK",
        serial=1,
        product_name="WALLET BLACK",
        location_name="Islamabad",
        delivery_code="1A"
    )

    print(f"Generated barcode: {barcode_data}")
    print(f"Saved to: {filepath}")
