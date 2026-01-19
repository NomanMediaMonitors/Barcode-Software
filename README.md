# Barcode Generation Software for TSC TE200

A complete barcode generation and printing solution for inventory management with embedded metadata tracking.

## Features

- **Barcode Generation**: Support for Code128 and QR codes
- **Metadata Embedding**: Encode destination, product, and packer information
- **Direct Printing**: Native support for TSC TE200 thermal printer via TSPL commands
- **Data Management**: SQLite database for products, locations, and packers
- **History Tracking**: Complete audit trail of all printed labels
- **Statistics**: Daily packing statistics by worker

## Barcode Data Format

Each barcode encodes the following information:
```
{LOCATION_CODE}-{PRODUCT_CODE}-{PACKER_CODE}-{TIMESTAMP}

Example: LOC01-BAG01-PKR03-20240115143022
```

This allows you to:
- Track which destination each package is going to
- Identify the product
- Know who packed the order
- Record when it was packed

## Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.in
```

Required packages:
- `python-barcode` - Barcode generation
- `qrcode` - QR code generation
- `Pillow` - Image processing
- `pyserial` - Serial port communication (optional, for direct printer connection)
- `reportlab` - PDF generation (optional)

For Windows direct printing, also install:
```bash
pip install pywin32
```

### 2. Setup Sample Data (Optional)

```bash
python setup_sample_data.py
```

This will create:
- 3 sample products (2 bags, 1 wallet)
- 8 sample locations
- 5 sample packers

### 3. Run the Application

```bash
python app.py
```

## Usage

### Main Workflow

1. **Select Product** - Choose from your product catalog
2. **Select Destination** - Pick the shipping location
3. **Select Packer** - Identify who is packing
4. **Choose Barcode Type** - Code128 (1D) or QR Code (2D)
5. **Preview** - See the label before printing
6. **Print** - Send to TSC TE200 printer

### Managing Data

#### Products Tab
- Add new products with code, name, and description
- Delete products you no longer need

#### Locations Tab
- Add shipping destinations with code, name, and address
- Your 8 locations are pre-configured

#### Packers Tab
- Add/remove packers
- Toggle active status (inactive packers won't appear in dropdown)

#### History Tab
- View all printed labels
- See daily statistics per packer
- Export history to CSV

## Printer Setup

### TSC TE200 Configuration

1. **USB Connection (Recommended)**
   - Install TSC printer drivers from [TSC website](https://www.tscprinters.com/)
   - Connect printer via USB
   - The software will auto-detect the printer

2. **Serial Connection**
   - Edit `config.py` and set the port:
   ```python
   PRINTER_SETTINGS = {
       "port": "COM3",  # Windows
       # or
       "port": "/dev/ttyUSB0",  # Linux
   }
   ```

3. **Label Size**
   - Default: 50mm x 30mm with 3mm gap
   - Adjust in `config.py`:
   ```python
   LABEL_WIDTH = 50   # mm
   LABEL_HEIGHT = 30  # mm
   LABEL_GAP = 3      # mm
   ```

### If Printer Not Available

The software can:
- **Save as Image**: Export labels as PNG/JPG for other printers
- **Save as TSPL**: Export raw printer commands for manual sending

## Project Structure

```
Barcode-Software/
├── app.py                 # Main GUI application
├── barcode_generator.py   # Barcode/QR code generation
├── database.py            # SQLite database operations
├── printer.py             # TSC TE200 printer integration
├── config.py              # Configuration settings
├── setup_sample_data.py   # Sample data initialization
├── requirements.in        # Python dependencies
├── barcode_data.db        # SQLite database (created on first run)
└── barcodes/              # Generated barcode images
```

## Configuration

Edit `config.py` to customize:

```python
# Barcode settings
BARCODE_TYPE = "code128"  # or "qrcode"

# Label dimensions (mm)
LABEL_WIDTH = 50
LABEL_HEIGHT = 30

# Printer settings
PRINTER_SETTINGS = {
    "name": "TSC TE200",
    "port": "USB",
    "speed": 4,      # 1-6
    "density": 8,    # 0-15
}
```

## Scanning Barcodes

When you scan the generated barcode, you'll get a string like:
```
LOC01-BAG01-PKR03-20240115143022
```

Your receiving system can parse this to extract:
- `LOC01` - Destination location code
- `BAG01` - Product code
- `PKR03` - Packer ID
- `20240115143022` - Timestamp (Jan 15, 2024, 2:30:22 PM)

## Troubleshooting

### Printer Not Detected
1. Check USB connection
2. Install TSC drivers
3. Verify printer is set as default (or update config.py)

### Barcode Won't Scan
1. Increase print density in config.py
2. Clean print head
3. Try QR code instead of Code128

### Database Errors
1. Delete `barcode_data.db` to reset
2. Run `setup_sample_data.py` again

## License

MIT License - Feel free to modify for your needs.
