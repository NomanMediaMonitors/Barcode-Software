"""
TSC TE200 Printer Integration Module
Uses TSPL (TSC Printer Language) commands for direct printing
"""

import os
import sys
import subprocess
from typing import Optional, Tuple
from PIL import Image
import tempfile

from config import PRINTER_SETTINGS


class TSCPrinter:
    """
    TSC TE200 Printer controller using TSPL commands

    Supports:
    - Direct USB printing (Windows/Linux)
    - Network printing
    - Raw TSPL command sending
    """

    def __init__(self, printer_name: str = None, port: str = None):
        """
        Initialize printer connection

        Args:
            printer_name: Printer name as installed in OS
            port: Serial port (COM3, /dev/usb/lp0, etc.) or "USB"
        """
        self.printer_name = printer_name or PRINTER_SETTINGS.get("name", "TSC TE200")
        self.port = port or PRINTER_SETTINGS.get("port", "USB")
        self.width = PRINTER_SETTINGS.get("width", 400)
        self.height = PRINTER_SETTINGS.get("height", 240)
        self.speed = PRINTER_SETTINGS.get("speed", 4)
        self.density = PRINTER_SETTINGS.get("density", 8)

    def _get_tspl_header(self) -> str:
        """Generate TSPL header commands"""
        commands = [
            f"SIZE {self.width/8} mm, {self.height/8} mm",  # Label size
            f"GAP 3 mm, 0 mm",  # Gap between labels
            f"SPEED {self.speed}",  # Print speed
            f"DENSITY {self.density}",  # Print density
            "DIRECTION 1,0",  # Print direction
            "CLS",  # Clear buffer
        ]
        return "\n".join(commands)

    def generate_tspl_barcode(self, barcode_data: str, x: int = 50, y: int = 50,
                               barcode_type: str = "128",
                               height: int = 80, human_readable: int = 1,
                               rotation: int = 0, narrow: int = 2,
                               wide: int = 2) -> str:
        """
        Generate TSPL command for barcode

        Args:
            barcode_data: Data to encode
            x, y: Position in dots
            barcode_type: "128" for Code128, "39" for Code39, "EAN13", etc.
            height: Barcode height in dots
            human_readable: 0=no text, 1=align left, 2=center, 3=right
            rotation: 0, 90, 180, 270 degrees
            narrow: Narrow bar width
            wide: Wide bar width
        """
        return f'BARCODE {x},{y},"{barcode_type}",{height},{human_readable},{rotation},{narrow},{wide},"{barcode_data}"'

    def generate_tspl_qrcode(self, data: str, x: int = 50, y: int = 50,
                              ecc_level: str = "M", cell_width: int = 6,
                              mode: str = "A", rotation: int = 0) -> str:
        """
        Generate TSPL command for QR code

        Args:
            data: Data to encode
            x, y: Position in dots
            ecc_level: Error correction (L, M, Q, H)
            cell_width: Size of each cell (1-10)
            mode: A=auto, M=manual
            rotation: 0, 90, 180, 270
        """
        return f'QRCODE {x},{y},{ecc_level},{cell_width},{mode},{rotation},"{data}"'

    def generate_tspl_text(self, text: str, x: int = 10, y: int = 10,
                           font: str = "3", rotation: int = 0,
                           x_mult: int = 1, y_mult: int = 1) -> str:
        """
        Generate TSPL command for text

        Args:
            text: Text to print
            x, y: Position in dots
            font: Font selection (1-5 for built-in, or font name)
            rotation: 0, 90, 180, 270
            x_mult, y_mult: Multiplication factors for size
        """
        return f'TEXT {x},{y},"{font}",{rotation},{x_mult},{y_mult},"{text}"'

    def generate_label_tspl(self, barcode_data: str, product_name: str,
                            location_name: str, packer_name: str,
                            use_qrcode: bool = False) -> str:
        """
        Generate complete TSPL commands for a label

        Args:
            barcode_data: Data for barcode
            product_name: Product name to display
            location_name: Destination name
            packer_name: Packer name
            use_qrcode: Use QR code instead of Code128
        """
        commands = [self._get_tspl_header()]

        # Product name at top
        commands.append(self.generate_tspl_text(
            f"Product: {product_name[:25]}",  # Truncate if too long
            x=10, y=10, font="3", x_mult=1, y_mult=1
        ))

        # Barcode in middle
        if use_qrcode:
            commands.append(self.generate_tspl_qrcode(
                barcode_data, x=130, y=40, cell_width=4
            ))
        else:
            commands.append(self.generate_tspl_barcode(
                barcode_data, x=30, y=50, height=70, human_readable=2
            ))

        # Destination
        commands.append(self.generate_tspl_text(
            f"Dest: {location_name[:20]}",
            x=10, y=160, font="2", x_mult=1, y_mult=1
        ))

        # Packer
        commands.append(self.generate_tspl_text(
            f"Packed: {packer_name[:15]}",
            x=10, y=185, font="2", x_mult=1, y_mult=1
        ))

        # Print command
        commands.append("PRINT 1,1")  # Print 1 copy

        return "\n".join(commands)

    def _send_to_printer_windows(self, tspl_commands: str) -> bool:
        """Send TSPL commands to printer on Windows"""
        try:
            import win32print
            import win32api

            # Get printer handle
            printer_handle = win32print.OpenPrinter(self.printer_name)
            try:
                # Start document
                win32print.StartDocPrinter(printer_handle, 1, ("Barcode Label", None, "RAW"))
                try:
                    win32print.StartPagePrinter(printer_handle)
                    win32print.WritePrinter(printer_handle, tspl_commands.encode('utf-8'))
                    win32print.EndPagePrinter(printer_handle)
                finally:
                    win32print.EndDocPrinter(printer_handle)
            finally:
                win32print.ClosePrinter(printer_handle)
            return True
        except ImportError:
            print("Warning: win32print not available. Install pywin32 for Windows printing.")
            return False
        except Exception as e:
            print(f"Windows printing error: {e}")
            return False

    def _send_to_printer_linux(self, tspl_commands: str) -> bool:
        """Send TSPL commands to printer on Linux"""
        try:
            # Try using lp command
            process = subprocess.Popen(
                ['lp', '-d', self.printer_name, '-o', 'raw'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate(input=tspl_commands.encode('utf-8'))

            if process.returncode != 0:
                # Try direct device writing
                if os.path.exists('/dev/usb/lp0'):
                    with open('/dev/usb/lp0', 'wb') as printer:
                        printer.write(tspl_commands.encode('utf-8'))
                    return True
                print(f"Linux printing error: {stderr.decode()}")
                return False
            return True
        except Exception as e:
            print(f"Linux printing error: {e}")
            return False

    def _send_to_serial(self, tspl_commands: str) -> bool:
        """Send TSPL commands via serial port"""
        try:
            import serial

            with serial.Serial(self.port, 9600, timeout=5) as ser:
                ser.write(tspl_commands.encode('utf-8'))
                ser.flush()
            return True
        except ImportError:
            print("Warning: pyserial not available. Install with: pip install pyserial")
            return False
        except Exception as e:
            print(f"Serial printing error: {e}")
            return False

    def print_label(self, barcode_data: str, product_name: str,
                    location_name: str, packer_name: str,
                    use_qrcode: bool = False, copies: int = 1) -> bool:
        """
        Print a label with barcode

        Args:
            barcode_data: Data for barcode
            product_name: Product name
            location_name: Destination
            packer_name: Packer name
            use_qrcode: Use QR code instead of Code128
            copies: Number of copies

        Returns:
            True if successful
        """
        # Generate TSPL commands
        tspl = self.generate_label_tspl(
            barcode_data, product_name, location_name, packer_name, use_qrcode
        )

        # Modify print command for copies
        if copies > 1:
            tspl = tspl.replace("PRINT 1,1", f"PRINT {copies},1")

        # Send to printer based on platform
        if sys.platform == 'win32':
            return self._send_to_printer_windows(tspl)
        elif self.port.startswith('COM') or self.port.startswith('/dev/tty'):
            return self._send_to_serial(tspl)
        else:
            return self._send_to_printer_linux(tspl)

    def print_image(self, image: Image.Image, x: int = 0, y: int = 0) -> bool:
        """
        Print a PIL Image directly to the printer

        Args:
            image: PIL Image to print
            x, y: Position offset
        """
        # Convert to monochrome
        if image.mode != '1':
            image = image.convert('1')

        # Generate TSPL BITMAP command
        width = image.width
        height = image.height
        width_bytes = (width + 7) // 8

        # Get bitmap data
        bitmap_data = []
        for row in range(height):
            row_data = []
            for col_byte in range(width_bytes):
                byte = 0
                for bit in range(8):
                    col = col_byte * 8 + bit
                    if col < width:
                        pixel = image.getpixel((col, row))
                        if pixel == 0:  # Black pixel
                            byte |= (1 << (7 - bit))
                row_data.append(byte)
            bitmap_data.extend(row_data)

        # Generate TSPL commands
        commands = [
            self._get_tspl_header(),
            f"BITMAP {x},{y},{width_bytes},{height},1,",
        ]

        tspl = "\n".join(commands)
        tspl_bytes = tspl.encode('utf-8') + bytes(bitmap_data) + b"\nPRINT 1,1\n"

        # Save to temp file and print
        with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as f:
            f.write(tspl_bytes)
            temp_path = f.name

        try:
            if sys.platform == 'win32':
                return self._send_to_printer_windows(tspl_bytes.decode('latin-1'))
            else:
                return self._send_to_printer_linux(tspl_bytes.decode('latin-1'))
        finally:
            os.unlink(temp_path)

    def save_tspl_file(self, barcode_data: str, product_name: str,
                       location_name: str, packer_name: str,
                       filename: str, use_qrcode: bool = False) -> str:
        """
        Save TSPL commands to file for manual printing

        Useful for testing or printing via other methods
        """
        tspl = self.generate_label_tspl(
            barcode_data, product_name, location_name, packer_name, use_qrcode
        )

        if not filename.endswith('.tspl'):
            filename += '.tspl'

        with open(filename, 'w') as f:
            f.write(tspl)

        return filename

    def test_print(self) -> bool:
        """Print a test label"""
        return self.print_label(
            barcode_data="TEST-LABEL-001",
            product_name="Test Product",
            location_name="Test Location",
            packer_name="Test Packer"
        )

    @staticmethod
    def list_printers() -> list:
        """List available printers on the system"""
        printers = []

        if sys.platform == 'win32':
            try:
                import win32print
                printers = [p[2] for p in win32print.EnumPrinters(2)]
            except ImportError:
                pass
        else:
            try:
                result = subprocess.run(
                    ['lpstat', '-p'],
                    capture_output=True, text=True
                )
                for line in result.stdout.split('\n'):
                    if line.startswith('printer '):
                        name = line.split()[1]
                        printers.append(name)
            except Exception:
                pass

        return printers


def print_barcode_label(barcode_data: str, product_name: str,
                        location_name: str, packer_name: str,
                        copies: int = 1, use_qrcode: bool = False) -> bool:
    """
    Convenience function to print a barcode label

    Args:
        barcode_data: Data to encode in barcode
        product_name: Product name to display
        location_name: Destination location
        packer_name: Name of packer
        copies: Number of copies to print
        use_qrcode: Use QR code instead of Code128

    Returns:
        True if printing was successful
    """
    printer = TSCPrinter()
    return printer.print_label(
        barcode_data, product_name, location_name,
        packer_name, use_qrcode, copies
    )


if __name__ == "__main__":
    # Test printer functionality
    printer = TSCPrinter()

    # List available printers
    print("Available printers:", printer.list_printers())

    # Generate sample TSPL file
    filepath = printer.save_tspl_file(
        barcode_data="LOC01-BAG01-PKR01-20240115",
        product_name="Leather Bag",
        location_name="NYC Warehouse",
        packer_name="John Smith",
        filename="sample_label.tspl"
    )
    print(f"Sample TSPL saved to: {filepath}")
