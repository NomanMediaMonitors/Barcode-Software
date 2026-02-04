import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from PIL import Image, ImageTk
import os

import database as db
from barcode_generator import BarcodeGenerator
from printer import TSCPrinter, print_barcode_label
from config import SHORT_DATE_FORMAT

# Try to import reportlab for PDF export
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.units import inch, mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


# Color scheme
COLORS = {
    "bg": "#0d1117",
    "card": "#161b22",
    "border": "#30363d",
    "primary": "#238636",
    "primary_hover": "#2ea043",
    "danger": "#da3633",
    "warning": "#d29922",
    "text": "#e6edf3",
    "text_dim": "#7d8590",
    "input_bg": "#0d1117",
    "accent": "#58a6ff",
}

# Delivery codes
DELIVERY_CODES = ["1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B"]

# City codes mapping
CITY_CODES = {
    "ISB": "Islamabad",
    "SAR": "Sargodha",
    "HYD": "Hyderabad",
    "HOK": "H.O.Karachi",
    "JEH": "Jehlum",
    "KAR": "Karachi",
    "LHR": "Lahore",
    "MUL": "Multan",
}

# Product codes mapping
PRODUCT_CODES = {
    "WALT BLCK": "WALLET BLACK",
    "WALT BRWN": "WALLET BROWN",
    "WALT TAN": "WALLET TAN",
    "4PCS BLCK": "4PC SET BLACK",
    "4PCS BRWN": "4PC SET BROWN",
    "4PCS TAN": "4PC SET TAN",
    "LAPB NVYB": "LAPTOP BAG NAVY BLUE",
}

# Carton capacity per product type (items per carton)
CARTON_CAPACITIES = {
    "WALT": 150,      # Wallet - 150 per carton
    "4PCS": 80,       # 4PC Set - 80 per carton
    "LAPB": 12,       # Laptop Bag - 12 per carton
}

def get_carton_capacity(product_code):
    """Get carton capacity for a product based on its code prefix."""
    for prefix, capacity in CARTON_CAPACITIES.items():
        if product_code.startswith(prefix):
            return capacity
    return 100  # Default capacity

def get_product_type(product_code):
    """Get product type prefix for grouping (WALT, 4PCS, LAPB, or OTHER)."""
    for prefix in CARTON_CAPACITIES.keys():
        if product_code.startswith(prefix):
            return prefix
    return "OTHER"

def pack_cartons_smart(cart_items):
    """Pack items into cartons with smart mixing.

    Strategy:
    1. Group items by product type (WALT, 4PCS, LAPB, etc.)
    2. For each type, first fill complete cartons with single products
    3. Collect remaining items that don't fill a complete carton
    4. Mix remaining items of same type into shared cartons

    Returns list of carton dicts, each containing:
    - items: list of {product_code, product_name, start_serial, end_serial, quantity, location_code}
    - capacity: carton capacity
    - total_quantity: total items in carton
    - is_mixed: True if carton contains multiple products
    """
    from collections import defaultdict

    # Group cart items by product type
    items_by_type = defaultdict(list)
    for item in cart_items:
        product_type = get_product_type(item['product']['code'])
        items_by_type[product_type].append(item)

    all_cartons = []

    for product_type, items in items_by_type.items():
        capacity = get_carton_capacity(items[0]['product']['code'])
        remainders = []  # Items that don't fill a complete carton

        # Process each item - fill complete cartons first
        for item in items:
            product_code = item['product']['code']
            product_name = item['product']['name']
            location_code = item['location']['code']
            start_serial = item['start_serial']
            end_serial = item['end_serial']

            current_serial = start_serial

            # Fill complete cartons with this single product
            while current_serial <= end_serial:
                remaining_qty = end_serial - current_serial + 1

                if remaining_qty >= capacity:
                    # Full carton with single product
                    carton_end = current_serial + capacity - 1
                    all_cartons.append({
                        'items': [{
                            'product_code': product_code,
                            'product_name': product_name,
                            'start_serial': current_serial,
                            'end_serial': carton_end,
                            'quantity': capacity,
                            'location_code': location_code
                        }],
                        'capacity': capacity,
                        'total_quantity': capacity,
                        'is_mixed': False,
                        'product_type': product_type
                    })
                    current_serial = carton_end + 1
                else:
                    # Remainder - save for mixing
                    remainders.append({
                        'product_code': product_code,
                        'product_name': product_name,
                        'start_serial': current_serial,
                        'end_serial': end_serial,
                        'quantity': remaining_qty,
                        'location_code': location_code
                    })
                    break

        # Now pack remainders into mixed cartons
        if remainders:
            current_carton_items = []
            current_carton_qty = 0

            for remainder in remainders:
                remaining_to_pack = remainder['quantity']
                current_start = remainder['start_serial']

                while remaining_to_pack > 0:
                    space_in_carton = capacity - current_carton_qty

                    if remaining_to_pack <= space_in_carton:
                        # Fits in current carton
                        current_carton_items.append({
                            'product_code': remainder['product_code'],
                            'product_name': remainder['product_name'],
                            'start_serial': current_start,
                            'end_serial': current_start + remaining_to_pack - 1,
                            'quantity': remaining_to_pack,
                            'location_code': remainder['location_code']
                        })
                        current_carton_qty += remaining_to_pack
                        remaining_to_pack = 0
                    else:
                        # Fill current carton, continue with next
                        if space_in_carton > 0:
                            current_carton_items.append({
                                'product_code': remainder['product_code'],
                                'product_name': remainder['product_name'],
                                'start_serial': current_start,
                                'end_serial': current_start + space_in_carton - 1,
                                'quantity': space_in_carton,
                                'location_code': remainder['location_code']
                            })
                            current_start += space_in_carton
                            remaining_to_pack -= space_in_carton

                        # Save current carton and start new one
                        is_mixed = len(current_carton_items) > 1 or (
                            len(current_carton_items) == 1 and
                            current_carton_items[0]['quantity'] < capacity
                        )
                        all_cartons.append({
                            'items': current_carton_items,
                            'capacity': capacity,
                            'total_quantity': capacity,
                            'is_mixed': len(set(i['product_code'] for i in current_carton_items)) > 1,
                            'product_type': product_type
                        })
                        current_carton_items = []
                        current_carton_qty = 0

            # Don't forget the last partial carton
            if current_carton_items:
                all_cartons.append({
                    'items': current_carton_items,
                    'capacity': capacity,
                    'total_quantity': current_carton_qty,
                    'is_mixed': len(set(i['product_code'] for i in current_carton_items)) > 1,
                    'product_type': product_type
                })

    return all_cartons


def setup_styles():
    """Configure ttk styles"""
    style = ttk.Style()
    try:
        style.theme_use('clam')
    except:
        pass

    # Base
    style.configure(".", background=COLORS["card"], foreground=COLORS["text"], font=("Segoe UI", 10))

    # Frames
    style.configure("TFrame", background=COLORS["bg"])
    style.configure("Card.TFrame", background=COLORS["card"])

    # Labels
    style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"])
    style.configure("Card.TLabel", background=COLORS["card"])
    style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))
    style.configure("Header.TLabel", font=("Segoe UI", 11, "bold"))
    style.configure("Dim.TLabel", foreground=COLORS["text_dim"])
    style.configure("Accent.TLabel", foreground=COLORS["accent"])
    style.configure("Success.TLabel", foreground=COLORS["primary"])

    # Buttons
    style.configure("TButton", background=COLORS["border"], foreground=COLORS["text"],
                   padding=(16, 8), font=("Segoe UI", 10))
    style.map("TButton", background=[("active", COLORS["border"])])

    style.configure("Primary.TButton", background=COLORS["primary"], foreground="white")
    style.map("Primary.TButton", background=[("active", COLORS["primary_hover"])])

    style.configure("Danger.TButton", background=COLORS["danger"], foreground="white")
    style.map("Danger.TButton", background=[("active", "#f85149")])

    # Entry
    style.configure("TEntry", fieldbackground=COLORS["input_bg"], foreground=COLORS["text"], padding=8)

    # Combobox
    style.configure("TCombobox", fieldbackground=COLORS["input_bg"], background=COLORS["card"],
                   foreground=COLORS["text"], padding=8)
    style.map("TCombobox", fieldbackground=[("readonly", COLORS["input_bg"])])

    # Checkbutton
    style.configure("TCheckbutton", background=COLORS["bg"], foreground=COLORS["text"])
    style.configure("Card.TCheckbutton", background=COLORS["card"])

    # Radiobutton
    style.configure("TRadiobutton", background=COLORS["card"], foreground=COLORS["text"])

    # Notebook
    style.configure("TNotebook", background=COLORS["bg"], borderwidth=0)
    style.configure("TNotebook.Tab", background=COLORS["card"], foreground=COLORS["text_dim"],
                   padding=(20, 10), font=("Segoe UI", 10))
    style.map("TNotebook.Tab", background=[("selected", COLORS["border"])],
             foreground=[("selected", COLORS["text"])])

    # Treeview
    style.configure("Treeview", background=COLORS["input_bg"], foreground=COLORS["text"],
                   fieldbackground=COLORS["input_bg"], rowheight=28, font=("Segoe UI", 9))
    style.configure("Treeview.Heading", background=COLORS["card"], foreground=COLORS["text"],
                   font=("Segoe UI", 9, "bold"))
    style.map("Treeview", background=[("selected", COLORS["primary"])])

    # LabelFrame
    style.configure("TLabelframe", background=COLORS["card"])
    style.configure("TLabelframe.Label", background=COLORS["card"], foreground=COLORS["accent"],
                   font=("Segoe UI", 10, "bold"))

    # Spinbox
    style.configure("TSpinbox", fieldbackground=COLORS["input_bg"], background=COLORS["card"],
                   foreground=COLORS["text"], padding=8)

    # Separator
    style.configure("TSeparator", background=COLORS["border"])


class BarcodeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Barcode Generator")
        self.root.geometry("1200x800")
        self.root.minsize(1100, 700)
        self.root.configure(bg=COLORS["bg"])

        setup_styles()

        self.barcode_gen = BarcodeGenerator()
        self.printer = TSCPrinter()
        self.current_label_image = None
        self.cart_items = []

        self._create_menu()
        self._create_ui()
        self._refresh_all_data()

    def _create_menu(self):
        menubar = tk.Menu(self.root, bg=COLORS["card"], fg=COLORS["text"],
                         activebackground=COLORS["primary"], activeforeground="white")
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0, bg=COLORS["card"], fg=COLORS["text"],
                           activebackground=COLORS["primary"])
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export History", command=self._export_history)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        settings_menu = tk.Menu(menubar, tearoff=0, bg=COLORS["card"], fg=COLORS["text"],
                               activebackground=COLORS["primary"])
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Printer Setup", command=self._show_printer_setup)

        help_menu = tk.Menu(menubar, tearoff=0, bg=COLORS["card"], fg=COLORS["text"],
                           activebackground=COLORS["primary"])
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)

    def _create_ui(self):
        # Main container
        main = ttk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Left side - Controls
        left_panel = ttk.Frame(main, width=400)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15))
        left_panel.pack_propagate(False)

        self._create_delivery_section(left_panel)
        self._create_product_section(left_panel)

        # Right side - Tabs
        right_panel = ttk.Frame(main)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(right_panel)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self._create_cart_tab()
        self._create_products_tab()
        self._create_locations_tab()
        self._create_history_tab()

    def _create_delivery_section(self, parent):
        """Create delivery code selection section"""
        frame = tk.Frame(parent, bg=COLORS["card"], padx=20, pady=20)
        frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(frame, text="Delivery Settings", font=("Segoe UI", 14, "bold"),
                bg=COLORS["card"], fg=COLORS["text"]).pack(anchor=tk.W)

        tk.Label(frame, text="Select delivery code for all cart items",
                font=("Segoe UI", 9), bg=COLORS["card"], fg=COLORS["text_dim"]).pack(anchor=tk.W, pady=(2, 15))

        # Delivery Code dropdown
        tk.Label(frame, text="Delivery Code", font=("Segoe UI", 10, "bold"),
                bg=COLORS["card"], fg=COLORS["text"]).pack(anchor=tk.W)
        self.delivery_var = tk.StringVar(value=DELIVERY_CODES[0])
        self.delivery_combo = ttk.Combobox(frame, textvariable=self.delivery_var, state="readonly", width=35,
                                           values=DELIVERY_CODES)
        self.delivery_combo.pack(fill=tk.X, pady=(5, 15))

        # Destination dropdown
        tk.Label(frame, text="Destination", font=("Segoe UI", 10, "bold"),
                bg=COLORS["card"], fg=COLORS["text"]).pack(anchor=tk.W)
        self.location_var = tk.StringVar()
        self.location_combo = ttk.Combobox(frame, textvariable=self.location_var, state="readonly", width=35)
        self.location_combo.pack(fill=tk.X, pady=(5, 0))

        # Display current delivery info
        self.delivery_info_label = tk.Label(frame, text="",
                                            font=("Consolas", 11, "bold"), bg=COLORS["card"], fg=COLORS["accent"])
        self.delivery_info_label.pack(anchor=tk.W, pady=(10, 0))

        # Update info when delivery code changes
        self.delivery_combo.bind('<<ComboboxSelected>>', self._update_delivery_info)
        self.location_combo.bind('<<ComboboxSelected>>', self._update_delivery_info)

    def _update_delivery_info(self, event=None):
        """Update delivery info display"""
        delivery = self.delivery_var.get()
        location = self.location_var.get()
        if delivery and location:
            loc_code = location.split(" - ")[0] if " - " in location else location
            self.delivery_info_label.config(text=f"Code: {delivery} | Dest: {loc_code}")

    def _create_product_section(self, parent):
        """Create product selection section"""
        frame = tk.Frame(parent, bg=COLORS["card"], padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="Add Product", font=("Segoe UI", 14, "bold"),
                bg=COLORS["card"], fg=COLORS["text"]).pack(anchor=tk.W)

        tk.Label(frame, text="Select product and quantity to add to cart",
                font=("Segoe UI", 9), bg=COLORS["card"], fg=COLORS["text_dim"]).pack(anchor=tk.W, pady=(2, 15))

        # Product dropdown
        tk.Label(frame, text="Product", font=("Segoe UI", 10, "bold"),
                bg=COLORS["card"], fg=COLORS["text"]).pack(anchor=tk.W)
        self.product_var = tk.StringVar()
        self.product_combo = ttk.Combobox(frame, textvariable=self.product_var, state="readonly", width=35)
        self.product_combo.pack(fill=tk.X, pady=(5, 15))

        # Quantity
        qty_frame = tk.Frame(frame, bg=COLORS["card"])
        qty_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(qty_frame, text="Quantity", font=("Segoe UI", 10, "bold"),
                bg=COLORS["card"], fg=COLORS["text"]).pack(side=tk.LEFT)

        self.quantity_var = tk.StringVar(value="1")
        qty_spin = ttk.Spinbox(qty_frame, from_=1, to=1000, textvariable=self.quantity_var, width=8)
        qty_spin.pack(side=tk.RIGHT)

        # Serial customization section
        serial_frame = tk.Frame(frame, bg=COLORS["card"])
        serial_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(serial_frame, text="Serial Range", font=("Segoe UI", 10, "bold"),
                bg=COLORS["card"], fg=COLORS["text"]).pack(anchor=tk.W)

        self.custom_serial_var = tk.BooleanVar(value=False)
        custom_check = tk.Checkbutton(serial_frame, text="Custom starting serial",
                                      variable=self.custom_serial_var,
                                      bg=COLORS["card"], fg=COLORS["text"],
                                      selectcolor=COLORS["input_bg"],
                                      activebackground=COLORS["card"],
                                      command=self._toggle_custom_serial)
        custom_check.pack(anchor=tk.W, pady=(5, 5))

        self.serial_start_frame = tk.Frame(serial_frame, bg=COLORS["card"])
        self.serial_start_frame.pack(fill=tk.X)

        tk.Label(self.serial_start_frame, text="Start from:",
                bg=COLORS["card"], fg=COLORS["text_dim"]).pack(side=tk.LEFT)

        self.serial_start_var = tk.StringVar(value="1")
        self.serial_start_entry = tk.Entry(self.serial_start_frame, textvariable=self.serial_start_var,
                                           bg=COLORS["input_bg"], fg=COLORS["text"],
                                           insertbackground=COLORS["text"], border=0, width=10,
                                           state="disabled")
        self.serial_start_entry.pack(side=tk.LEFT, padx=(10, 0), ipady=5, ipadx=5)

        # Serial preview
        self.serial_preview_label = tk.Label(serial_frame, text="Serials: 0001 - 0001",
                                             font=("Segoe UI", 9), bg=COLORS["card"], fg=COLORS["text_dim"])
        self.serial_preview_label.pack(anchor=tk.W, pady=(5, 0))

        # Update preview when quantity or serial changes
        self.quantity_var.trace_add("write", self._update_serial_preview)
        self.serial_start_var.trace_add("write", self._update_serial_preview)

        # Add to Cart button
        add_btn = tk.Button(frame, text="+ Add to Cart", font=("Segoe UI", 11, "bold"),
                           bg=COLORS["primary"], fg="white", activebackground=COLORS["primary_hover"],
                           activeforeground="white", border=0, padx=20, pady=12, cursor="hand2",
                           command=self._add_to_cart)
        add_btn.pack(fill=tk.X, pady=(15, 0))

    def _toggle_custom_serial(self):
        """Toggle custom serial entry"""
        if self.custom_serial_var.get():
            self.serial_start_entry.config(state="normal")
        else:
            self.serial_start_entry.config(state="disabled")
            self.serial_start_var.set("1")
        self._update_serial_preview()

    def _update_serial_preview(self, *args):
        """Update serial range preview"""
        try:
            qty = int(self.quantity_var.get())
            start = int(self.serial_start_var.get()) if self.custom_serial_var.get() else 1
            end = start + qty - 1
            self.serial_preview_label.config(text=f"Serials: {start:04d} - {end:04d}")
        except ValueError:
            self.serial_preview_label.config(text="Serials: Invalid input")

    def _create_cart_tab(self):
        """Create cart/items tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Cart  ")

        # Cart header
        header = tk.Frame(tab, bg=COLORS["card"], padx=15, pady=15)
        header.pack(fill=tk.X)

        tk.Label(header, text="Items in Cart", font=("Segoe UI", 14, "bold"),
                bg=COLORS["card"], fg=COLORS["text"]).pack(side=tk.LEFT)

        btn_frame = tk.Frame(header, bg=COLORS["card"])
        btn_frame.pack(side=tk.RIGHT)

        delivery_note_btn = tk.Button(btn_frame, text="Delivery Note", font=("Segoe UI", 9),
                              bg=COLORS["accent"], fg="white", border=0, padx=12, pady=6,
                              cursor="hand2", command=self._export_delivery_note)
        delivery_note_btn.pack(side=tk.LEFT, padx=(0, 10))

        export_pdf_btn = tk.Button(btn_frame, text="Carton PDFs", font=("Segoe UI", 9),
                              bg=COLORS["warning"], fg="white", border=0, padx=12, pady=6,
                              cursor="hand2", command=self._export_cart_pdf)
        export_pdf_btn.pack(side=tk.LEFT, padx=(0, 10))

        clear_btn = tk.Button(btn_frame, text="Clear All", font=("Segoe UI", 9),
                             bg=COLORS["danger"], fg="white", border=0, padx=12, pady=6,
                             cursor="hand2", command=self._clear_cart)
        clear_btn.pack(side=tk.LEFT, padx=(0, 10))

        print_btn = tk.Button(btn_frame, text="Print All", font=("Segoe UI", 10, "bold"),
                             bg=COLORS["primary"], fg="white", border=0, padx=15, pady=8,
                             cursor="hand2", command=self._print_all_cart)
        print_btn.pack(side=tk.LEFT)

        # Cart info
        info_frame = tk.Frame(tab, bg=COLORS["card"], padx=15, pady=10)
        info_frame.pack(fill=tk.X)

        self.cart_info_label = tk.Label(info_frame, text="Delivery: -- | Destination: --",
                                        font=("Segoe UI", 11, "bold"), bg=COLORS["card"], fg=COLORS["accent"])
        self.cart_info_label.pack(side=tk.LEFT)

        # Cart list
        list_frame = tk.Frame(tab, bg=COLORS["bg"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        columns = ("product", "serial_range", "qty", "barcode_preview")
        self.cart_tree = ttk.Treeview(list_frame, columns=columns, show="headings")

        self.cart_tree.heading("product", text="Product")
        self.cart_tree.heading("serial_range", text="Serial Range")
        self.cart_tree.heading("qty", text="Qty")
        self.cart_tree.heading("barcode_preview", text="Barcode Preview")

        self.cart_tree.column("product", width=200)
        self.cart_tree.column("serial_range", width=120)
        self.cart_tree.column("qty", width=60)
        self.cart_tree.column("barcode_preview", width=250)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.cart_tree.yview)
        self.cart_tree.configure(yscrollcommand=scrollbar.set)

        self.cart_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Remove button
        remove_btn = tk.Button(tab, text="Remove Selected", font=("Segoe UI", 10),
                              bg=COLORS["border"], fg=COLORS["text"], border=0, padx=15, pady=8,
                              cursor="hand2", command=self._remove_from_cart)
        remove_btn.pack(pady=(0, 15))

    def _create_products_tab(self):
        """Create products management tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Products  ")

        # Add form
        form_frame = tk.Frame(tab, bg=COLORS["card"], padx=20, pady=15)
        form_frame.pack(fill=tk.X, padx=15, pady=15)

        tk.Label(form_frame, text="Add Product", font=("Segoe UI", 12, "bold"),
                bg=COLORS["card"], fg=COLORS["text"]).grid(row=0, column=0, sticky=tk.W, columnspan=7)

        tk.Label(form_frame, text="Code:", bg=COLORS["card"], fg=COLORS["text"]).grid(row=1, column=0, pady=10, padx=(0, 5))
        self.new_product_code = tk.Entry(form_frame, bg=COLORS["input_bg"], fg=COLORS["text"],
                                        insertbackground=COLORS["text"], border=0, width=12)
        self.new_product_code.grid(row=1, column=1, pady=10, padx=(0, 15), ipady=5, ipadx=5)

        tk.Label(form_frame, text="Name:", bg=COLORS["card"], fg=COLORS["text"]).grid(row=1, column=2, pady=10, padx=(0, 5))
        self.new_product_name = tk.Entry(form_frame, bg=COLORS["input_bg"], fg=COLORS["text"],
                                        insertbackground=COLORS["text"], border=0, width=25)
        self.new_product_name.grid(row=1, column=3, pady=10, padx=(0, 15), ipady=5, ipadx=5)

        tk.Label(form_frame, text="Description:", bg=COLORS["card"], fg=COLORS["text"]).grid(row=1, column=4, pady=10, padx=(0, 5))
        self.new_product_desc = tk.Entry(form_frame, bg=COLORS["input_bg"], fg=COLORS["text"],
                                        insertbackground=COLORS["text"], border=0, width=30)
        self.new_product_desc.grid(row=1, column=5, pady=10, padx=(0, 15), ipady=5, ipadx=5)

        add_btn = tk.Button(form_frame, text="Add", bg=COLORS["primary"], fg="white",
                           border=0, padx=15, pady=5, cursor="hand2", command=self._add_product)
        add_btn.grid(row=1, column=6, pady=10)

        # List
        list_frame = tk.Frame(tab, bg=COLORS["bg"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        columns = ("code", "name", "description", "created")
        self.products_tree = ttk.Treeview(list_frame, columns=columns, show="headings")

        for col, width in [("code", 100), ("name", 200), ("description", 300), ("created", 150)]:
            self.products_tree.heading(col, text=col.title())
            self.products_tree.column(col, width=width)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.products_tree.yview)
        self.products_tree.configure(yscrollcommand=scrollbar.set)

        self.products_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        tk.Button(tab, text="Delete Selected", bg=COLORS["danger"], fg="white",
                 border=0, padx=15, pady=8, cursor="hand2", command=self._delete_product).pack(pady=(0, 15))

    def _create_locations_tab(self):
        """Create locations management tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Locations  ")

        # Add form
        form_frame = tk.Frame(tab, bg=COLORS["card"], padx=20, pady=15)
        form_frame.pack(fill=tk.X, padx=15, pady=15)

        tk.Label(form_frame, text="Add Location", font=("Segoe UI", 12, "bold"),
                bg=COLORS["card"], fg=COLORS["text"]).grid(row=0, column=0, sticky=tk.W, columnspan=7)

        tk.Label(form_frame, text="Code:", bg=COLORS["card"], fg=COLORS["text"]).grid(row=1, column=0, pady=10, padx=(0, 5))
        self.new_location_code = tk.Entry(form_frame, bg=COLORS["input_bg"], fg=COLORS["text"],
                                         insertbackground=COLORS["text"], border=0, width=12)
        self.new_location_code.grid(row=1, column=1, pady=10, padx=(0, 15), ipady=5, ipadx=5)

        tk.Label(form_frame, text="Name:", bg=COLORS["card"], fg=COLORS["text"]).grid(row=1, column=2, pady=10, padx=(0, 5))
        self.new_location_name = tk.Entry(form_frame, bg=COLORS["input_bg"], fg=COLORS["text"],
                                         insertbackground=COLORS["text"], border=0, width=25)
        self.new_location_name.grid(row=1, column=3, pady=10, padx=(0, 15), ipady=5, ipadx=5)

        tk.Label(form_frame, text="Address:", bg=COLORS["card"], fg=COLORS["text"]).grid(row=1, column=4, pady=10, padx=(0, 5))
        self.new_location_addr = tk.Entry(form_frame, bg=COLORS["input_bg"], fg=COLORS["text"],
                                         insertbackground=COLORS["text"], border=0, width=30)
        self.new_location_addr.grid(row=1, column=5, pady=10, padx=(0, 15), ipady=5, ipadx=5)

        add_btn = tk.Button(form_frame, text="Add", bg=COLORS["primary"], fg="white",
                           border=0, padx=15, pady=5, cursor="hand2", command=self._add_location)
        add_btn.grid(row=1, column=6, pady=10)

        # List
        list_frame = tk.Frame(tab, bg=COLORS["bg"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        columns = ("code", "name", "address", "created")
        self.locations_tree = ttk.Treeview(list_frame, columns=columns, show="headings")

        for col, width in [("code", 100), ("name", 200), ("address", 300), ("created", 150)]:
            self.locations_tree.heading(col, text=col.title())
            self.locations_tree.column(col, width=width)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.locations_tree.yview)
        self.locations_tree.configure(yscrollcommand=scrollbar.set)

        self.locations_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        tk.Button(tab, text="Delete Selected", bg=COLORS["danger"], fg="white",
                 border=0, padx=15, pady=8, cursor="hand2", command=self._delete_location).pack(pady=(0, 15))

    def _create_history_tab(self):
        """Create history tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  History  ")

        # Stats
        stats_frame = tk.Frame(tab, bg=COLORS["card"], padx=20, pady=15)
        stats_frame.pack(fill=tk.X, padx=15, pady=15)

        tk.Label(stats_frame, text="Today's Statistics", font=("Segoe UI", 12, "bold"),
                bg=COLORS["card"], fg=COLORS["text"]).pack(anchor=tk.W)

        self.stats_label = tk.Label(stats_frame, text="Loading...", font=("Segoe UI", 10),
                                   bg=COLORS["card"], fg=COLORS["text_dim"])
        self.stats_label.pack(anchor=tk.W, pady=(5, 0))

        # List
        list_frame = tk.Frame(tab, bg=COLORS["bg"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        columns = ("barcode", "product", "location", "delivery", "qty", "created")
        self.history_tree = ttk.Treeview(list_frame, columns=columns, show="headings")

        for col, width in [("barcode", 220), ("product", 150), ("location", 100), ("delivery", 80), ("qty", 50), ("created", 140)]:
            self.history_tree.heading(col, text=col.title())
            self.history_tree.column(col, width=width)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)

        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        tk.Button(tab, text="Refresh", bg=COLORS["border"], fg=COLORS["text"],
                 border=0, padx=15, pady=8, cursor="hand2", command=self._refresh_history).pack(pady=(0, 15))

    # ==================== CART FUNCTIONS ====================

    def _add_to_cart(self):
        """Add item to cart"""
        if not self.product_var.get():
            messagebox.showwarning("Warning", "Please select a product")
            return
        if not self.location_var.get():
            messagebox.showwarning("Warning", "Please select a destination")
            return
        if not self.delivery_var.get():
            messagebox.showwarning("Warning", "Please select a delivery code")
            return

        product = self._get_selected_product()
        location = self._get_selected_location()
        delivery_code = self.delivery_var.get()

        try:
            qty = int(self.quantity_var.get())
            start_serial = int(self.serial_start_var.get()) if self.custom_serial_var.get() else 1
        except ValueError:
            messagebox.showwarning("Warning", "Invalid quantity or serial number")
            return

        end_serial = start_serial + qty - 1

        # Generate barcode preview
        barcode_preview = f"{location['code']}-{product['code']}-{start_serial:04d}"

        item = {
            "product": product,
            "location": location,
            "delivery_code": delivery_code,
            "quantity": qty,
            "start_serial": start_serial,
            "end_serial": end_serial
        }
        self.cart_items.append(item)
        self._refresh_cart()

        # Reset quantity and serial
        self.quantity_var.set("1")
        self.serial_start_var.set("1")
        self.custom_serial_var.set(False)
        self._toggle_custom_serial()

    def _refresh_cart(self):
        """Refresh cart display"""
        self.cart_tree.delete(*self.cart_tree.get_children())

        delivery_code = self.delivery_var.get()
        location = self.location_var.get()
        loc_code = location.split(" - ")[0] if location and " - " in location else "--"

        self.cart_info_label.config(text=f"Delivery: {delivery_code} | Destination: {loc_code}")

        for i, item in enumerate(self.cart_items):
            serial_range = f"{item['start_serial']:04d} - {item['end_serial']:04d}"
            barcode_preview = f"{item['location']['code']}-{item['product']['code']}-{item['start_serial']:04d}"

            self.cart_tree.insert("", tk.END, values=(
                f"{item['product']['code']} - {item['product']['name']}",
                serial_range,
                item['quantity'],
                barcode_preview
            ), tags=(str(i),))

    def _remove_from_cart(self):
        """Remove selected item from cart"""
        selection = self.cart_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an item to remove")
            return

        indices = [int(self.cart_tree.item(s)['tags'][0]) for s in selection]
        for i in sorted(indices, reverse=True):
            del self.cart_items[i]
        self._refresh_cart()

    def _clear_cart(self):
        """Clear all items from cart"""
        if self.cart_items and messagebox.askyesno("Confirm", "Clear all items from cart?"):
            self.cart_items = []
            self._refresh_cart()

    def _export_cart_pdf(self):
        """Export cart items to PDF"""
        if not self.cart_items:
            messagebox.showwarning("Warning", "Cart is empty")
            return

        if not REPORTLAB_AVAILABLE:
            messagebox.showerror("Error", "PDF export requires reportlab library.\n\nInstall with: pip install reportlab")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")],
            initialfile=f"cart_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )

        if filename:
            self._generate_pdf(filename)
            messagebox.showinfo("Success", f"Cart exported to PDF:\n{filename}")

    def _generate_pdf(self, filename):
        """Generate PDF from cart items - organized by cartons for packing.

        Each carton gets its own page showing:
        - Carton label (e.g., 1A/1, 1A/2)
        - Product info
        - Serial numbers that go in that carton

        Carton capacities:
        - WALLET: 300 per carton
        - 4PC SET: 50 per carton
        - LAPTOP BAG: 15 per carton
        """
        from reportlab.platypus import PageBreak

        doc = SimpleDocTemplate(filename, pagesize=A4,
                               rightMargin=30, leftMargin=30,
                               topMargin=30, bottomMargin=30)

        elements = []
        styles = getSampleStyleSheet()

        # Get delivery info
        delivery_code = self.delivery_var.get()
        location = self._get_selected_location()
        loc_name = location['name'] if location else "--"
        loc_code = location['code'] if location else "--"

        # Styles
        carton_title_style = ParagraphStyle(
            'CartonTitle',
            parent=styles['Heading1'],
            fontSize=48,
            spaceAfter=10,
            alignment=1,  # Center
            textColor=colors.HexColor('#000000')
        )

        dest_style = ParagraphStyle(
            'Destination',
            parent=styles['Heading2'],
            fontSize=24,
            spaceAfter=5,
            alignment=1,
            textColor=colors.HexColor('#333333')
        )

        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=14,
            spaceAfter=20,
            alignment=1,
            textColor=colors.HexColor('#666666')
        )

        info_style = ParagraphStyle(
            'Info',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=5,
            alignment=1
        )

        product_style = ParagraphStyle(
            'Product',
            parent=styles['Normal'],
            fontSize=16,
            spaceBefore=15,
            spaceAfter=5,
            alignment=1
        )

        serial_style = ParagraphStyle(
            'Serial',
            parent=styles['Normal'],
            fontSize=14,
            spaceAfter=3,
            alignment=1,
            textColor=colors.HexColor('#444444')
        )

        serial_range_style = ParagraphStyle(
            'SerialRange',
            parent=styles['Normal'],
            fontSize=20,
            spaceBefore=10,
            spaceAfter=10,
            alignment=1,
            textColor=colors.HexColor('#000000')
        )

        # Use smart packing to fill cartons efficiently and mix remainders
        cartons = pack_cartons_smart(self.cart_items)
        total_cartons = len(cartons)

        # Style for mixed carton indicator
        mixed_style = ParagraphStyle(
            'Mixed',
            parent=styles['Normal'],
            fontSize=14,
            spaceBefore=5,
            spaceAfter=5,
            alignment=1,
            textColor=colors.HexColor('#cc6600')
        )

        # Generate a page for each carton
        for i, carton in enumerate(cartons):
            carton_number = i + 1
            carton_label = f"{delivery_code}/{carton_number}"

            # Large carton label at top
            elements.append(Spacer(1, 50))
            elements.append(Paragraph(f"<b>{carton_label}</b>", carton_title_style))
            elements.append(Spacer(1, 20))

            # Destination
            elements.append(Paragraph(f"{loc_name}", dest_style))
            elements.append(Paragraph(f"Destination Code: {loc_code}", subtitle_style))

            elements.append(Spacer(1, 30))

            # Carton info
            elements.append(Paragraph(f"Carton {carton_number} of {total_cartons}", info_style))
            elements.append(Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d')}", info_style))

            # Show mixed carton indicator if applicable
            if carton['is_mixed']:
                elements.append(Spacer(1, 10))
                elements.append(Paragraph("<b>** MIXED CARTON **</b>", mixed_style))

            elements.append(Spacer(1, 20))

            # Total quantity for carton
            elements.append(Paragraph(f"Total Quantity: <b>{carton['total_quantity']}</b> items", info_style))

            elements.append(Spacer(1, 20))

            # Product info - show all items in carton
            for item_idx, item in enumerate(carton['items']):
                if item_idx > 0:
                    elements.append(Spacer(1, 15))

                elements.append(Paragraph(f"<b>{item['product_name']}</b>", product_style))
                elements.append(Paragraph(f"({item['product_code']})", serial_style))
                elements.append(Paragraph(f"Qty: <b>{item['quantity']}</b>", info_style))

                # Serial range
                elements.append(Paragraph(
                    f"Serial: <b>{item['start_serial']:04d} - {item['end_serial']:04d}</b>",
                    serial_style
                ))

                # Barcode format preview
                barcode_start = f"{item['location_code']}-{item['product_code']}-{item['start_serial']:04d}"
                barcode_end = f"{item['location_code']}-{item['product_code']}-{item['end_serial']:04d}"
                elements.append(Paragraph(f"{barcode_start} to {barcode_end}", info_style))

            # Add page break if not last carton
            if i < len(cartons) - 1:
                elements.append(PageBreak())

        # Build PDF
        doc.build(elements)

    def _export_delivery_note(self):
        """Export a complete delivery note summary PDF"""
        if not self.cart_items:
            messagebox.showwarning("Warning", "Cart is empty")
            return

        if not REPORTLAB_AVAILABLE:
            messagebox.showerror("Error", "PDF export requires reportlab library.\n\nInstall with: pip install reportlab")
            return

        delivery_code = self.delivery_var.get()
        filename = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")],
            initialfile=f"delivery_note_{delivery_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )

        if filename:
            self._generate_delivery_note_pdf(filename)
            messagebox.showinfo("Success", f"Delivery note exported to PDF:\n{filename}")

    def _generate_delivery_note_pdf(self, filename):
        """Generate a complete delivery note PDF with all details.

        Shows complete summary of the delivery including:
        - Delivery code and destination
        - All products with quantities and serial ranges
        - Carton breakdown for each product
        - Total cartons needed
        """
        doc = SimpleDocTemplate(filename, pagesize=A4,
                               rightMargin=30, leftMargin=30,
                               topMargin=30, bottomMargin=30)

        elements = []
        styles = getSampleStyleSheet()

        # Get delivery info
        delivery_code = self.delivery_var.get()
        location = self._get_selected_location()
        loc_name = location['name'] if location else "--"
        loc_code = location['code'] if location else "--"

        # Styles
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontSize=36,
            spaceAfter=5,
            alignment=1,
            textColor=colors.HexColor('#000000')
        )

        dest_style = ParagraphStyle(
            'Destination',
            parent=styles['Heading2'],
            fontSize=24,
            spaceAfter=10,
            alignment=1,
            textColor=colors.HexColor('#333333')
        )

        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=5,
            alignment=1,
            textColor=colors.HexColor('#666666')
        )

        section_style = ParagraphStyle(
            'Section',
            parent=styles['Heading2'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#238636')
        )

        info_style = ParagraphStyle(
            'Info',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=5
        )

        # Title - Delivery Note
        elements.append(Paragraph(f"<b>DELIVERY NOTE</b>", title_style))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(f"<b>{delivery_code}</b>", title_style))
        elements.append(Spacer(1, 20))

        # Destination
        elements.append(Paragraph(f"{loc_name}", dest_style))
        elements.append(Paragraph(f"Destination Code: {loc_code}", subtitle_style))
        elements.append(Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", subtitle_style))

        elements.append(Spacer(1, 30))

        # Use smart packing to calculate cartons with mixing
        cartons = pack_cartons_smart(self.cart_items)
        total_items = sum(item['quantity'] for item in self.cart_items)
        total_cartons = len(cartons)

        # Build product summary for the product details table
        product_summary = []
        for item in self.cart_items:
            product_code = item['product']['code']
            product_name = item['product']['name']
            qty = item['quantity']
            capacity = get_carton_capacity(product_code)

            product_summary.append({
                'name': product_name,
                'code': product_code,
                'quantity': qty,
                'capacity': capacity,
                'start_serial': item['start_serial'],
                'end_serial': item['end_serial'],
                'location_code': item['location']['code']
            })

        # Count mixed cartons
        mixed_cartons = sum(1 for c in cartons if c['is_mixed'])

        # Summary Table
        elements.append(Paragraph("Summary", section_style))

        summary_data = [
            ['Total Items', str(total_items)],
            ['Total Cartons', str(total_cartons)],
            ['Mixed Cartons', str(mixed_cartons)],
            ['Delivery Code', delivery_code],
            ['Destination', f"{loc_code} - {loc_name}"],
        ]
        summary_table = Table(summary_data, colWidths=[150, 300])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
            ('PADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(summary_table)

        # Products Detail Section
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("Product Details", section_style))

        # Product table header
        product_data = [['Product', 'Qty', 'Per Carton', 'Serial Range']]

        for prod in product_summary:
            serial_range = f"{prod['start_serial']:04d} - {prod['end_serial']:04d}"
            product_data.append([
                f"{prod['name']}\n({prod['code']})",
                str(prod['quantity']),
                str(prod['capacity']),
                serial_range
            ])

        product_table = Table(product_data, colWidths=[180, 60, 80, 130])
        product_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#238636')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(product_table)

        # Carton Breakdown Section
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("Carton Breakdown", section_style))

        carton_data = [['Carton', 'Product(s)', 'Quantity', 'Serial Range(s)']]

        for carton_idx, carton in enumerate(cartons):
            carton_label = f"{delivery_code}/{carton_idx + 1}"

            if carton['is_mixed']:
                # Mixed carton - show all products
                products_str = "MIXED:\n" + "\n".join(
                    f"{item['product_code']}" for item in carton['items']
                )
                qty_str = "\n".join(str(item['quantity']) for item in carton['items'])
                serial_str = "\n".join(
                    f"{item['start_serial']:04d}-{item['end_serial']:04d}"
                    for item in carton['items']
                )
            else:
                # Single product carton
                item = carton['items'][0]
                products_str = item['product_code']
                qty_str = str(item['quantity'])
                serial_str = f"{item['start_serial']:04d} - {item['end_serial']:04d}"

            carton_data.append([
                carton_label,
                products_str,
                qty_str,
                serial_str
            ])

        carton_table = Table(carton_data, colWidths=[70, 130, 60, 120])
        carton_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#333333')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(carton_table)

        # Footer note
        elements.append(Spacer(1, 30))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=10,
            alignment=1,
            textColor=colors.HexColor('#888888')
        )
        elements.append(Paragraph(
            f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            footer_style
        ))

        # Build PDF
        doc.build(elements)

    def _print_all_cart(self):
        """Print all items in cart - prints 2 different stickers per pass to save sticker paper"""
        if not self.cart_items:
            messagebox.showwarning("Warning", "Cart is empty")
            return

        if not self.delivery_var.get():
            messagebox.showwarning("Warning", "Please select a delivery code")
            return

        delivery_code = self.delivery_var.get()
        success_count = 0
        fail_count = 0

        # Collect all barcodes to print
        all_barcodes = []
        for item in self.cart_items:
            for serial in range(item['start_serial'], item['end_serial'] + 1):
                barcode_data = f"{item['location']['code']}-{item['product']['code']}-{serial:04d}"
                all_barcodes.append({
                    'barcode': barcode_data,
                    'product_name': item['product']['name'],
                    'location_name': item['location']['name'],
                    'product_id': item['product']['id'],
                    'location_id': item['location']['id']
                })

        # Print in pairs (2 different stickers per pass)
        i = 0
        while i < len(all_barcodes):
            left_item = all_barcodes[i]
            right_item = all_barcodes[i + 1] if i + 1 < len(all_barcodes) else None

            # Print label with 2 different barcodes (or just 1 if odd number)
            success, _ = self.printer.print_label(
                left_item['barcode'],
                left_item['product_name'],
                left_item['location_name'],
                delivery_code,
                False,  # Code128
                1,
                right_item['barcode'] if right_item else None
            )

            if success:
                # Save left barcode to history
                db.save_barcode_history(
                    left_item['barcode'],
                    left_item['product_id'],
                    left_item['location_id'],
                    delivery_code,
                    1
                )
                success_count += 1

                # Save right barcode to history if exists
                if right_item:
                    db.save_barcode_history(
                        right_item['barcode'],
                        right_item['product_id'],
                        right_item['location_id'],
                        delivery_code,
                        1
                    )
                    success_count += 1
            else:
                fail_count += 1
                if right_item:
                    fail_count += 1

            # Move to next pair
            i += 2

        # Clear cart and refresh
        self.cart_items = []
        self._refresh_cart()
        self._refresh_history()

        if fail_count == 0:
            messagebox.showinfo("Success", f"Printed {success_count} labels")
        else:
            messagebox.showwarning("Partial Success", f"Printed {success_count} labels, {fail_count} failed")

    # ==================== HELPER FUNCTIONS ====================

    def _get_selected_product(self):
        code = self.product_var.get().split(" - ")[0]
        for p in db.get_all_products():
            if p['code'] == code:
                return dict(p)
        return None

    def _get_selected_location(self):
        code = self.location_var.get().split(" - ")[0]
        for l in db.get_all_locations():
            if l['code'] == code:
                return dict(l)
        return None

    # ==================== CRUD FUNCTIONS ====================

    def _add_product(self):
        code = self.new_product_code.get().strip()
        name = self.new_product_name.get().strip()
        desc = self.new_product_desc.get().strip()

        if not code or not name:
            messagebox.showwarning("Warning", "Code and Name required")
            return

        try:
            db.add_product(code, name, desc)
            self._refresh_products()
            self.new_product_code.delete(0, tk.END)
            self.new_product_name.delete(0, tk.END)
            self.new_product_desc.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _delete_product(self):
        selection = self.products_tree.selection()
        if not selection:
            return
        if messagebox.askyesno("Confirm", "Delete product?"):
            code = self.products_tree.item(selection[0])['values'][0]
            for p in db.get_all_products():
                if p['code'] == code:
                    db.delete_product(p['id'])
                    break
            self._refresh_products()

    def _add_location(self):
        code = self.new_location_code.get().strip()
        name = self.new_location_name.get().strip()
        addr = self.new_location_addr.get().strip()

        if not code or not name:
            messagebox.showwarning("Warning", "Code and Name required")
            return

        try:
            db.add_location(code, name, addr)
            self._refresh_locations()
            self.new_location_code.delete(0, tk.END)
            self.new_location_name.delete(0, tk.END)
            self.new_location_addr.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _delete_location(self):
        selection = self.locations_tree.selection()
        if not selection:
            return
        if messagebox.askyesno("Confirm", "Delete location?"):
            code = self.locations_tree.item(selection[0])['values'][0]
            for l in db.get_all_locations():
                if l['code'] == code:
                    db.delete_location(l['id'])
                    break
            self._refresh_locations()

    # ==================== REFRESH FUNCTIONS ====================

    def _refresh_combos(self):
        products = db.get_all_products()
        self.product_combo['values'] = [f"{p['code']} - {p['name']}" for p in products]

        locations = db.get_all_locations()
        self.location_combo['values'] = [f"{l['code']} - {l['name']}" for l in locations]

    def _refresh_products(self):
        self.products_tree.delete(*self.products_tree.get_children())
        for p in db.get_all_products():
            self.products_tree.insert("", tk.END, values=(
                p['code'], p['name'], p['description'] or "", p['created_at']
            ))
        self._refresh_combos()

    def _refresh_locations(self):
        self.locations_tree.delete(*self.locations_tree.get_children())
        for l in db.get_all_locations():
            self.locations_tree.insert("", tk.END, values=(
                l['code'], l['name'], l['address'] or "", l['created_at']
            ))
        self._refresh_combos()

    def _refresh_history(self):
        stats = db.get_location_stats()
        if stats:
            text = " | ".join([f"{s['location_name']}: {int(s['total_items'])} items" for s in stats])
        else:
            text = "No labels printed today"
        self.stats_label.config(text=text)

        self.history_tree.delete(*self.history_tree.get_children())
        for h in db.get_barcode_history():
            # delivery_code is stored in packer_name field for now
            delivery = h.get('packer_name') or h.get('delivery_code') or "-"
            self.history_tree.insert("", tk.END, values=(
                h['barcode_data'], h['product_name'] or "-", h['location_name'] or "-",
                delivery, h['quantity'], h['created_at']
            ))

    def _refresh_all_data(self):
        self._refresh_products()
        self._refresh_locations()
        self._refresh_history()

    # ==================== DIALOGS ====================

    def _export_history(self):
        filename = filedialog.asksaveasfilename(defaultextension=".csv",
                                                filetypes=[("CSV", "*.csv")])
        if filename:
            history = db.get_barcode_history(limit=10000)
            with open(filename, 'w') as f:
                f.write("Barcode,Product,Location,Delivery,Qty,Created\n")
                for h in history:
                    delivery = h.get('packer_name') or h.get('delivery_code') or "-"
                    f.write(f"{h['barcode_data']},{h['product_name']},{h['location_name']},"
                           f"{delivery},{h['quantity']},{h['created_at']}\n")
            messagebox.showinfo("Success", f"Exported to {filename}")

    def _show_printer_setup(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Printer Setup")
        dialog.geometry("500x400")
        dialog.configure(bg=COLORS["bg"])
        dialog.transient(self.root)

        frame = tk.Frame(dialog, bg=COLORS["bg"], padx=30, pady=30)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="Printer Configuration", font=("Segoe UI", 16, "bold"),
                bg=COLORS["bg"], fg=COLORS["text"]).pack(anchor=tk.W)

        tk.Label(frame, text=f"\nConfigured: {self.printer.printer_name}",
                bg=COLORS["bg"], fg=COLORS["text"]).pack(anchor=tk.W)
        tk.Label(frame, text=f"Port: {self.printer.port}",
                bg=COLORS["bg"], fg=COLORS["text"]).pack(anchor=tk.W)

        detected = self.printer.find_tsc_printer()
        tk.Label(frame, text=f"\nDetected TSC: {detected or 'None'}",
                bg=COLORS["bg"], fg=COLORS["primary"] if detected else COLORS["text_dim"]).pack(anchor=tk.W)

        tk.Label(frame, text="\nEdit config.py to change settings",
                bg=COLORS["bg"], fg=COLORS["text_dim"]).pack(anchor=tk.W, pady=(20, 0))

        tk.Button(frame, text="Close", bg=COLORS["border"], fg=COLORS["text"],
                 border=0, padx=20, pady=8, command=dialog.destroy).pack(pady=30)

    def _show_about(self):
        messagebox.showinfo("About",
            "Barcode Generator v3.0\n\n"
            "Features:\n"
            "- Serial-based barcode generation\n"
            "- Delivery code assignment\n"
            "- PDF and CSV export\n"
            "- TSC TE200 support\n\n"
            "Format: LOCATION-PRODUCT-SERIAL")


def main():
    root = tk.Tk()
    app = BarcodeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
