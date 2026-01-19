import os
import sys
import subprocess
import tempfile
from typing import Optional, Tuple, List
from PIL import Image

from config import PRINTER_SETTINGS


class TSCPrinter:

    def __init__(self, printer_name: str = None, port: str = None):
        self.printer_name = printer_name or PRINTER_SETTINGS.get("name", "TSC TE200")
        self.port = port or PRINTER_SETTINGS.get("port", "USB")
        self.width = PRINTER_SETTINGS.get("width", 400)
        self.height = PRINTER_SETTINGS.get("height", 240)
        self.speed = PRINTER_SETTINGS.get("speed", 4)
        self.density = PRINTER_SETTINGS.get("density", 8)
        # Direction: 0 for printers with 180° natural orientation, 1 for 0° orientation
        self.direction = PRINTER_SETTINGS.get("direction", 0)
        self.mirror = PRINTER_SETTINGS.get("mirror", 0)
        self._detected_printer = None
        self._last_error = None

    def get_last_error(self) -> Optional[str]:
        return self._last_error

    def _get_tspl_header(self) -> str:
        # TSPL syntax: no space before comma, integers only (not floats)
        width_mm = self.width // 8
        height_mm = self.height // 8
        commands = [
            f"SIZE {width_mm} mm,{height_mm} mm",
            "GAP 3 mm,0 mm",
            f"SPEED {self.speed}",
            f"DENSITY {self.density}",
            # DIRECTION n,m: n=0 for 180° natural orientation printers, n=1 for 0° orientation
            # m=0 for normal, m=1 for mirror
            f"DIRECTION {self.direction},{self.mirror}",
            "CLS",
        ]
        # TSPL requires CRLF line endings
        return "\r\n".join(commands)

    def generate_tspl_barcode(self, barcode_data: str, x: int = 50, y: int = 50,
                               barcode_type: str = "128", height: int = 80,
                               human_readable: int = 1, rotation: int = 0,
                               narrow: int = 2, wide: int = 2) -> str:
        return f'BARCODE {x},{y},"{barcode_type}",{height},{human_readable},{rotation},{narrow},{wide},"{barcode_data}"'

    def generate_tspl_qrcode(self, data: str, x: int = 50, y: int = 50,
                              ecc_level: str = "M", cell_width: int = 6,
                              mode: str = "A", rotation: int = 0) -> str:
        return f'QRCODE {x},{y},{ecc_level},{cell_width},{mode},{rotation},"{data}"'

    def generate_tspl_text(self, text: str, x: int = 10, y: int = 10,
                           font: str = "3", rotation: int = 0,
                           x_mult: int = 1, y_mult: int = 1) -> str:
        return f'TEXT {x},{y},"{font}",{rotation},{x_mult},{y_mult},"{text}"'

    def generate_label_tspl(self, barcode_data: str, product_name: str,
                            location_name: str, packer_name: str,
                            use_qrcode: bool = False) -> str:
        commands = [self._get_tspl_header()]

        # Product name at top
        commands.append(self.generate_tspl_text(
            f"Product: {product_name[:25]}",
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
        commands.append("PRINT 1,1")

        # TSPL requires CRLF line endings, plus trailing CRLF to flush buffer
        return "\r\n".join(commands) + "\r\n"

    @staticmethod
    def list_printers() -> List[str]:
        """List available printers on the system"""
        printers = []

        if sys.platform == 'win32':
            try:
                import win32print
                printers = [p[2] for p in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]
            except ImportError:
                # Fallback: use wmic command
                try:
                    result = subprocess.run(
                        ['wmic', 'printer', 'get', 'name'],
                        capture_output=True, text=True, shell=True
                    )
                    for line in result.stdout.split('\n'):
                        line = line.strip()
                        if line and line != 'Name':
                            printers.append(line)
                except Exception:
                    pass
        else:
            try:
                result = subprocess.run(
                    ['lpstat', '-p'], capture_output=True, text=True
                )
                for line in result.stdout.split('\n'):
                    if line.startswith('printer '):
                        printers.append(line.split()[1])
            except Exception:
                pass

        return printers

    def find_tsc_printer(self) -> Optional[str]:
        """Auto-detect TSC printer from available printers"""
        if self._detected_printer:
            return self._detected_printer

        printers = self.list_printers()
        tsc_keywords = ['TSC', 'TE200', 'TE-200', 'TE 200', 'TTP', 'TDP']

        for printer in printers:
            printer_upper = printer.upper()
            for keyword in tsc_keywords:
                if keyword in printer_upper:
                    self._detected_printer = printer
                    return printer

        for printer in printers:
            if printer.upper() == self.printer_name.upper():
                self._detected_printer = printer
                return printer

        return self.printer_name

    def is_tsc_printer_available(self) -> bool:
        printers = self.list_printers()
        tsc_keywords = ['TSC', 'TE200', 'TE-200', 'TE 200', 'TTP', 'TDP']

        for printer in printers:
            printer_upper = printer.upper()
            for keyword in tsc_keywords:
                if keyword in printer_upper:
                    return True

        return self.printer_name in printers

    def _send_via_win32print(self, tspl_commands: str, printer_name: str) -> bool:
        try:
            import win32print

            handle = win32print.OpenPrinter(printer_name)
            try:
                win32print.StartDocPrinter(handle, 1, ("Barcode Label", None, "RAW"))
                try:
                    win32print.StartPagePrinter(handle)
                    # TSC printers expect ASCII encoding, not UTF-8
                    win32print.WritePrinter(handle, tspl_commands.encode('ascii', errors='replace'))
                    win32print.EndPagePrinter(handle)
                finally:
                    win32print.EndDocPrinter(handle)
                return True
            finally:
                win32print.ClosePrinter(handle)
        except ImportError:
            self._last_error = "pywin32 not installed. Run: pip install pywin32"
            return False
        except Exception as e:
            self._last_error = f"win32print error: {e}"
            return False

    def _send_via_file_copy(self, tspl_commands: str, printer_name: str) -> bool:
        try:
            # Use binary mode with ASCII encoding to preserve CRLF line endings
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.prn', delete=False) as f:
                f.write(tspl_commands.encode('ascii', errors='replace'))
                temp_file = f.name

            try:
                computer = os.environ.get('COMPUTERNAME', 'localhost')
                printer_path = f"\\\\{computer}\\{printer_name}"

                result = subprocess.run(
                    f'copy /b "{temp_file}" "{printer_path}"',
                    shell=True, capture_output=True, text=True
                )

                if result.returncode == 0:
                    return True
                else:
                    self._last_error = f"File copy failed: {result.stderr}"
                    return False
            finally:
                os.unlink(temp_file)
        except Exception as e:
            self._last_error = f"File copy error: {e}"
            return False

    def _send_via_usb_port(self, tspl_commands: str) -> bool:
        """Send directly to USB port (requires knowing the port)"""
        usb_ports = ['USB001', 'USB002', 'USB003']

        for port in usb_ports:
            try:
                port_path = f"\\\\.\\{port}"
                with open(port_path, 'wb') as f:
                    # TSC printers expect ASCII encoding, not UTF-8
                    f.write(tspl_commands.encode('ascii', errors='replace'))
                return True
            except Exception:
                continue

        linux_usb = ['/dev/usb/lp0', '/dev/usb/lp1', '/dev/lp0']
        for port in linux_usb:
            if os.path.exists(port):
                try:
                    with open(port, 'wb') as f:
                        # TSC printers expect ASCII encoding, not UTF-8
                        f.write(tspl_commands.encode('ascii', errors='replace'))
                    return True
                except Exception:
                    continue

        self._last_error = "No USB printer port found"
        return False

    def _send_via_serial(self, tspl_commands: str) -> bool:
        """Send via serial port"""
        try:
            import serial
            port = self.port if self.port.startswith('COM') else 'COM1'
            with serial.Serial(port, 9600, timeout=5) as ser:
                # TSC printers expect ASCII encoding, not UTF-8
                ser.write(tspl_commands.encode('ascii', errors='replace'))
                ser.flush()
            return True
        except ImportError:
            self._last_error = "pyserial not installed. Run: pip install pyserial"
            return False
        except Exception as e:
            self._last_error = f"Serial port error: {e}"
            return False

    def _send_via_lp(self, tspl_commands: str, printer_name: str) -> bool:
        """Send via lp command (Linux/Mac)"""
        try:
            process = subprocess.Popen(
                ['lp', '-d', printer_name, '-o', 'raw'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            # TSC printers expect ASCII encoding, not UTF-8
            _, stderr = process.communicate(input=tspl_commands.encode('ascii', errors='replace'))
            if process.returncode != 0:
                self._last_error = f"lp error: {stderr.decode()}"
                return False
            return True
        except Exception as e:
            self._last_error = f"lp command error: {e}"
            return False

    def print_label(self, barcode_data: str, product_name: str,
                    location_name: str, packer_name: str,
                    use_qrcode: bool = False, copies: int = 1) -> Tuple[bool, str]:
        self._last_error = None

        printer_name = self.find_tsc_printer()

        if not self.is_tsc_printer_available():
            available = self.list_printers()
            return False, (
                f"TSC printer '{printer_name}' not found!\n\n"
                f"Available printers:\n" +
                "\n".join(f"  - {p}" for p in available) +
                "\n\nPlease:\n"
                "1. Install TSC TE200 driver\n"
                "2. Or update 'name' in config.py PRINTER_SETTINGS"
            )

        tspl = self.generate_label_tspl(
            barcode_data, product_name, location_name, packer_name, use_qrcode
        )

        if copies > 1:
            tspl = tspl.replace("PRINT 1,1", f"PRINT {copies},1")

        methods = []

        if sys.platform == 'win32':
            methods = [
                ('Windows Spooler', lambda: self._send_via_win32print(tspl, printer_name)),
                ('File Copy', lambda: self._send_via_file_copy(tspl, printer_name)),
                ('Direct USB', lambda: self._send_via_usb_port(tspl)),
                ('Serial Port', lambda: self._send_via_serial(tspl)),
            ]
        else:
            methods = [
                ('LP Command', lambda: self._send_via_lp(tspl, printer_name)),
                ('Direct USB', lambda: self._send_via_usb_port(tspl)),
                ('Serial Port', lambda: self._send_via_serial(tspl)),
            ]

        errors = []
        for method_name, method_func in methods:
            try:
                if method_func():
                    return True, f"Printed via {method_name} to {printer_name}"
                if self._last_error:
                    errors.append(f"{method_name}: {self._last_error}")
            except Exception as e:
                errors.append(f"{method_name}: {str(e)}")

        error_msg = "All print methods failed:\n" + "\n".join(errors)
        return False, error_msg

    def save_tspl_file(self, barcode_data: str, product_name: str,
                       location_name: str, packer_name: str,
                       filename: str, use_qrcode: bool = False) -> str:
        tspl = self.generate_label_tspl(
            barcode_data, product_name, location_name, packer_name, use_qrcode
        )

        if not filename.endswith('.prn'):
            filename += '.prn'

        # Use binary mode with ASCII encoding to preserve CRLF line endings
        with open(filename, 'wb') as f:
            f.write(tspl.encode('ascii', errors='replace'))

        return filename

    def test_connection(self) -> Tuple[bool, str]:
        printer_name = self.find_tsc_printer()
        printers = self.list_printers()

        if not printers:
            return False, "No printers found on system"

        if printer_name in printers:
            return True, f"Printer '{printer_name}' found and available"

        # Check if any TSC printer exists
        tsc_found = [p for p in printers if 'TSC' in p.upper()]
        if tsc_found:
            return True, f"TSC printer found: {tsc_found[0]}"

        return False, f"Printer '{printer_name}' not found. Available: {', '.join(printers)}"


def print_barcode_label(barcode_data: str, product_name: str,
                        location_name: str, packer_name: str,
                        copies: int = 1, use_qrcode: bool = False) -> Tuple[bool, str]:

    printer = TSCPrinter()
    return printer.print_label(
        barcode_data, product_name, location_name,
        packer_name, use_qrcode, copies
    )


if __name__ == "__main__":
    printer = TSCPrinter()

    print("=== TSC TE200 Printer Test ===\n")

    # List printers
    printers = printer.list_printers()
    print(f"Available printers: {printers if printers else 'None found'}")

    # Find TSC printer
    tsc = printer.find_tsc_printer()
    print(f"Detected TSC printer: {tsc}")

    # Test connection
    success, msg = printer.test_connection()
    print(f"Connection test: {msg}")

    # Save sample file
    filepath = printer.save_tspl_file(
        barcode_data="LOC01-BAG01-PKR01-20240115",
        product_name="Leather Bag",
        location_name="NYC Warehouse",
        packer_name="John Smith",
        filename="sample_label"
    )
    print(f"\nSample TSPL saved to: {filepath}")
    print("You can manually print this file by copying it to your printer.")
