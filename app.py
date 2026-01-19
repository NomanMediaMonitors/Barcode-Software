import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from PIL import Image, ImageTk
import os

import database as db
from barcode_generator import BarcodeGenerator
from printer import TSCPrinter, print_barcode_label
from config import SHORT_DATE_FORMAT


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
        self.current_carton = None
        self.cart_items = []  # Items to add to carton

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

        self._create_product_section(left_panel)
        self._create_carton_section(left_panel)

        # Right side - Tabs
        right_panel = ttk.Frame(main)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(right_panel)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self._create_cart_tab()
        self._create_lookup_tab()
        self._create_products_tab()
        self._create_locations_tab()
        self._create_packers_tab()
        self._create_history_tab()

    def _create_product_section(self, parent):
        """Create product selection section"""
        frame = tk.Frame(parent, bg=COLORS["card"], padx=20, pady=20)
        frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(frame, text="Add Product", font=("Segoe UI", 14, "bold"),
                bg=COLORS["card"], fg=COLORS["text"]).pack(anchor=tk.W)

        tk.Label(frame, text="Select product and quantity to add to carton",
                font=("Segoe UI", 9), bg=COLORS["card"], fg=COLORS["text_dim"]).pack(anchor=tk.W, pady=(2, 15))

        # Product dropdown
        tk.Label(frame, text="Product", font=("Segoe UI", 10, "bold"),
                bg=COLORS["card"], fg=COLORS["text"]).pack(anchor=tk.W)
        self.product_var = tk.StringVar()
        self.product_combo = ttk.Combobox(frame, textvariable=self.product_var, state="readonly", width=35)
        self.product_combo.pack(fill=tk.X, pady=(5, 15))

        # Location dropdown
        tk.Label(frame, text="Destination", font=("Segoe UI", 10, "bold"),
                bg=COLORS["card"], fg=COLORS["text"]).pack(anchor=tk.W)
        self.location_var = tk.StringVar()
        self.location_combo = ttk.Combobox(frame, textvariable=self.location_var, state="readonly", width=35)
        self.location_combo.pack(fill=tk.X, pady=(5, 15))

        # Packer dropdown
        tk.Label(frame, text="Packer", font=("Segoe UI", 10, "bold"),
                bg=COLORS["card"], fg=COLORS["text"]).pack(anchor=tk.W)
        self.packer_var = tk.StringVar()
        self.packer_combo = ttk.Combobox(frame, textvariable=self.packer_var, state="readonly", width=35)
        self.packer_combo.pack(fill=tk.X, pady=(5, 15))

        # Quantity
        qty_frame = tk.Frame(frame, bg=COLORS["card"])
        qty_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(qty_frame, text="Quantity", font=("Segoe UI", 10, "bold"),
                bg=COLORS["card"], fg=COLORS["text"]).pack(side=tk.LEFT)

        self.quantity_var = tk.StringVar(value="1")
        qty_spin = ttk.Spinbox(qty_frame, from_=1, to=100, textvariable=self.quantity_var, width=8)
        qty_spin.pack(side=tk.RIGHT)

        # Add to Cart button
        add_btn = tk.Button(frame, text="+ Add to Cart", font=("Segoe UI", 11, "bold"),
                           bg=COLORS["primary"], fg="white", activebackground=COLORS["primary_hover"],
                           activeforeground="white", border=0, padx=20, pady=12, cursor="hand2",
                           command=self._add_to_cart)
        add_btn.pack(fill=tk.X, pady=(5, 0))

    def _create_carton_section(self, parent):
        """Create carton control section"""
        frame = tk.Frame(parent, bg=COLORS["card"], padx=20, pady=20)
        frame.pack(fill=tk.X)

        # Header with checkbox
        header_frame = tk.Frame(frame, bg=COLORS["card"])
        header_frame.pack(fill=tk.X)

        tk.Label(header_frame, text="Carton", font=("Segoe UI", 14, "bold"),
                bg=COLORS["card"], fg=COLORS["text"]).pack(side=tk.LEFT)

        # Enable/Disable checkbox
        self.carton_enabled_var = tk.BooleanVar(value=True)
        self.carton_checkbox = tk.Checkbutton(
            header_frame, text="Enabled", variable=self.carton_enabled_var,
            bg=COLORS["card"], fg=COLORS["text"], selectcolor=COLORS["input_bg"],
            activebackground=COLORS["card"], activeforeground=COLORS["text"],
            font=("Segoe UI", 9), command=self._toggle_carton_mode
        )
        self.carton_checkbox.pack(side=tk.RIGHT)

        # Carton status
        self.carton_status_frame = tk.Frame(frame, bg=COLORS["card"])
        self.carton_status_frame.pack(fill=tk.X, pady=(10, 15))

        self.carton_status_label = tk.Label(self.carton_status_frame, text="No active carton",
                                            font=("Segoe UI", 10), bg=COLORS["card"], fg=COLORS["text_dim"])
        self.carton_status_label.pack(anchor=tk.W)

        self.carton_barcode_label = tk.Label(self.carton_status_frame, text="",
                                             font=("Consolas", 11, "bold"), bg=COLORS["card"], fg=COLORS["accent"])
        self.carton_barcode_label.pack(anchor=tk.W)

        self.carton_count_label = tk.Label(self.carton_status_frame, text="",
                                           font=("Segoe UI", 10), bg=COLORS["card"], fg=COLORS["primary"])
        self.carton_count_label.pack(anchor=tk.W)

        # Buttons
        btn_frame = tk.Frame(frame, bg=COLORS["card"])
        btn_frame.pack(fill=tk.X, pady=(5, 0))

        new_btn = tk.Button(btn_frame, text="New Carton", font=("Segoe UI", 10),
                           bg=COLORS["border"], fg=COLORS["text"], activebackground=COLORS["border"],
                           border=0, padx=15, pady=8, cursor="hand2", command=self._create_new_carton)
        new_btn.pack(side=tk.LEFT, padx=(0, 10))

        close_btn = tk.Button(btn_frame, text="Close & Print", font=("Segoe UI", 10, "bold"),
                             bg=COLORS["primary"], fg="white", activebackground=COLORS["primary_hover"],
                             border=0, padx=15, pady=8, cursor="hand2", command=self._close_and_print_carton)
        close_btn.pack(side=tk.LEFT)

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

        export_btn = tk.Button(btn_frame, text="Export CSV", font=("Segoe UI", 9),
                              bg=COLORS["accent"], fg="white", border=0, padx=12, pady=6,
                              cursor="hand2", command=self._export_cart)
        export_btn.pack(side=tk.LEFT, padx=(0, 10))

        clear_btn = tk.Button(btn_frame, text="Clear All", font=("Segoe UI", 9),
                             bg=COLORS["danger"], fg="white", border=0, padx=12, pady=6,
                             cursor="hand2", command=self._clear_cart)
        clear_btn.pack(side=tk.LEFT, padx=(0, 10))

        print_btn = tk.Button(btn_frame, text="Print All", font=("Segoe UI", 10, "bold"),
                             bg=COLORS["primary"], fg="white", border=0, padx=15, pady=8,
                             cursor="hand2", command=self._print_all_cart)
        print_btn.pack(side=tk.LEFT)

        # Cart list
        list_frame = tk.Frame(tab, bg=COLORS["bg"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        columns = ("product", "destination", "packer", "qty")
        self.cart_tree = ttk.Treeview(list_frame, columns=columns, show="headings")

        self.cart_tree.heading("product", text="Product")
        self.cart_tree.heading("destination", text="Destination")
        self.cart_tree.heading("packer", text="Packer")
        self.cart_tree.heading("qty", text="Qty")

        self.cart_tree.column("product", width=250)
        self.cart_tree.column("destination", width=200)
        self.cart_tree.column("packer", width=150)
        self.cart_tree.column("qty", width=60)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.cart_tree.yview)
        self.cart_tree.configure(yscrollcommand=scrollbar.set)

        self.cart_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Remove button
        remove_btn = tk.Button(tab, text="Remove Selected", font=("Segoe UI", 10),
                              bg=COLORS["border"], fg=COLORS["text"], border=0, padx=15, pady=8,
                              cursor="hand2", command=self._remove_from_cart)
        remove_btn.pack(pady=(0, 15))

    def _create_lookup_tab(self):
        """Create carton lookup tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Lookup Carton  ")

        # Search
        search_frame = tk.Frame(tab, bg=COLORS["card"], padx=20, pady=20)
        search_frame.pack(fill=tk.X, padx=15, pady=15)

        tk.Label(search_frame, text="Scan or Enter Carton Barcode", font=("Segoe UI", 12, "bold"),
                bg=COLORS["card"], fg=COLORS["text"]).pack(anchor=tk.W)

        input_frame = tk.Frame(search_frame, bg=COLORS["card"])
        input_frame.pack(fill=tk.X, pady=(15, 0))

        self.lookup_var = tk.StringVar()
        lookup_entry = tk.Entry(input_frame, textvariable=self.lookup_var, font=("Consolas", 14),
                               bg=COLORS["input_bg"], fg=COLORS["text"], insertbackground=COLORS["text"],
                               border=0, width=30)
        lookup_entry.pack(side=tk.LEFT, padx=(0, 10), ipady=10, ipadx=10)
        lookup_entry.bind('<Return>', lambda e: self._lookup_carton())

        lookup_btn = tk.Button(input_frame, text="Lookup", font=("Segoe UI", 10, "bold"),
                              bg=COLORS["primary"], fg="white", border=0, padx=20, pady=10,
                              cursor="hand2", command=self._lookup_carton)
        lookup_btn.pack(side=tk.LEFT)

        # Results
        results_frame = tk.Frame(tab, bg=COLORS["bg"])
        results_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        # Info panel
        info_frame = tk.Frame(results_frame, bg=COLORS["card"], padx=20, pady=15)
        info_frame.pack(fill=tk.X, pady=(0, 15))

        self.lookup_info = tk.Label(info_frame, text="Enter a carton barcode to see its contents",
                                   font=("Segoe UI", 10), bg=COLORS["card"], fg=COLORS["text_dim"],
                                   justify=tk.LEFT)
        self.lookup_info.pack(anchor=tk.W)

        # Contents
        columns = ("code", "product", "qty")
        self.lookup_tree = ttk.Treeview(results_frame, columns=columns, show="headings")

        self.lookup_tree.heading("code", text="Code")
        self.lookup_tree.heading("product", text="Product")
        self.lookup_tree.heading("qty", text="Quantity")

        self.lookup_tree.column("code", width=120)
        self.lookup_tree.column("product", width=300)
        self.lookup_tree.column("qty", width=100)

        self.lookup_tree.pack(fill=tk.BOTH, expand=True)

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

    def _create_packers_tab(self):
        """Create packers management tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Packers  ")

        # Add form
        form_frame = tk.Frame(tab, bg=COLORS["card"], padx=20, pady=15)
        form_frame.pack(fill=tk.X, padx=15, pady=15)

        tk.Label(form_frame, text="Add Packer", font=("Segoe UI", 12, "bold"),
                bg=COLORS["card"], fg=COLORS["text"]).grid(row=0, column=0, sticky=tk.W, columnspan=5)

        tk.Label(form_frame, text="Code:", bg=COLORS["card"], fg=COLORS["text"]).grid(row=1, column=0, pady=10, padx=(0, 5))
        self.new_packer_code = tk.Entry(form_frame, bg=COLORS["input_bg"], fg=COLORS["text"],
                                       insertbackground=COLORS["text"], border=0, width=12)
        self.new_packer_code.grid(row=1, column=1, pady=10, padx=(0, 15), ipady=5, ipadx=5)

        tk.Label(form_frame, text="Name:", bg=COLORS["card"], fg=COLORS["text"]).grid(row=1, column=2, pady=10, padx=(0, 5))
        self.new_packer_name = tk.Entry(form_frame, bg=COLORS["input_bg"], fg=COLORS["text"],
                                       insertbackground=COLORS["text"], border=0, width=25)
        self.new_packer_name.grid(row=1, column=3, pady=10, padx=(0, 15), ipady=5, ipadx=5)

        add_btn = tk.Button(form_frame, text="Add", bg=COLORS["primary"], fg="white",
                           border=0, padx=15, pady=5, cursor="hand2", command=self._add_packer)
        add_btn.grid(row=1, column=4, pady=10)

        # List
        list_frame = tk.Frame(tab, bg=COLORS["bg"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        columns = ("code", "name", "active", "created")
        self.packers_tree = ttk.Treeview(list_frame, columns=columns, show="headings")

        for col, width in [("code", 100), ("name", 200), ("active", 80), ("created", 150)]:
            self.packers_tree.heading(col, text=col.title())
            self.packers_tree.column(col, width=width)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.packers_tree.yview)
        self.packers_tree.configure(yscrollcommand=scrollbar.set)

        self.packers_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = tk.Frame(tab, bg=COLORS["bg"])
        btn_frame.pack(pady=(0, 15))

        tk.Button(btn_frame, text="Toggle Active", bg=COLORS["border"], fg=COLORS["text"],
                 border=0, padx=15, pady=8, cursor="hand2", command=self._toggle_packer).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Delete Selected", bg=COLORS["danger"], fg="white",
                 border=0, padx=15, pady=8, cursor="hand2", command=self._delete_packer).pack(side=tk.LEFT, padx=5)

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

        columns = ("barcode", "product", "location", "packer", "qty", "created")
        self.history_tree = ttk.Treeview(list_frame, columns=columns, show="headings")

        for col, width in [("barcode", 200), ("product", 150), ("location", 120), ("packer", 100), ("qty", 50), ("created", 140)]:
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
        if not self.packer_var.get():
            messagebox.showwarning("Warning", "Please select a packer")
            return

        product = self._get_selected_product()
        location = self._get_selected_location()
        packer = self._get_selected_packer()
        qty = int(self.quantity_var.get())

        item = {
            "product": product,
            "location": location,
            "packer": packer,
            "quantity": qty
        }
        self.cart_items.append(item)
        self._refresh_cart()

        # Reset quantity
        self.quantity_var.set("1")

    def _refresh_cart(self):
        """Refresh cart display"""
        self.cart_tree.delete(*self.cart_tree.get_children())
        for i, item in enumerate(self.cart_items):
            self.cart_tree.insert("", tk.END, values=(
                f"{item['product']['code']} - {item['product']['name']}",
                item['location']['name'],
                item['packer']['name'],
                item['quantity']
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

    def _export_cart(self):
        """Export cart items to CSV"""
        if not self.cart_items:
            messagebox.showwarning("Warning", "Cart is empty")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            initialfilename=f"cart_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )

        if filename:
            with open(filename, 'w') as f:
                f.write("Product Code,Product Name,Destination,Packer,Quantity\n")
                for item in self.cart_items:
                    f.write(f"{item['product']['code']},{item['product']['name']},"
                           f"{item['location']['name']},{item['packer']['name']},{item['quantity']}\n")
            messagebox.showinfo("Success", f"Cart exported to:\n{filename}")

    def _toggle_carton_mode(self):
        """Toggle carton mode on/off"""
        if self.carton_enabled_var.get():
            self.carton_status_frame.pack(fill=tk.X, pady=(10, 15))
            self._update_carton_display()
        else:
            # Disable carton mode
            if self.current_carton:
                if messagebox.askyesno("Close Carton?",
                    "Disabling carton mode will close the current carton.\nContinue?"):
                    db.close_carton(self.current_carton['id'])
                    self.current_carton = None
                else:
                    self.carton_enabled_var.set(True)
                    return
            self.carton_status_label.config(text="Carton mode disabled", fg=COLORS["text_dim"])
            self.carton_barcode_label.config(text="Products will print without carton tracking")
            self.carton_count_label.config(text="")

    def _print_all_cart(self):
        """Print all items in cart and optionally add to carton"""
        if not self.cart_items:
            messagebox.showwarning("Warning", "Cart is empty")
            return

        carton_mode = self.carton_enabled_var.get()

        # Create carton if enabled and none exists
        if carton_mode and not self.current_carton:
            first_item = self.cart_items[0]
            carton_id, barcode = db.create_carton(
                first_item['location']['id'],
                first_item['packer']['id'],
                ""
            )
            self.current_carton = db.get_carton_by_id(carton_id)
            self._update_carton_display()

        success_count = 0
        fail_count = 0

        for item in self.cart_items:
            # Generate barcode
            barcode_data = self.barcode_gen.generate_barcode_data(
                item['location']['code'],
                item['product']['code'],
                item['packer']['code']
            )

            # Print label
            success, _ = self.printer.print_label(
                barcode_data,
                item['product']['name'],
                item['location']['name'],
                item['packer']['name'],
                False,  # Code128
                item['quantity']
            )

            if success:
                # Save to history
                db.save_barcode_history(
                    barcode_data,
                    item['product']['id'],
                    item['location']['id'],
                    item['packer']['id'],
                    item['quantity']
                )

                # Add to carton only if carton mode enabled
                if carton_mode and self.current_carton:
                    db.add_product_to_carton(
                        self.current_carton['id'],
                        item['product']['id'],
                        item['quantity'],
                        barcode_data
                    )
                success_count += 1
            else:
                fail_count += 1

        # Clear cart and refresh
        self.cart_items = []
        self._refresh_cart()
        if carton_mode:
            self._update_carton_display()
        self._refresh_history()

        if fail_count == 0:
            if carton_mode:
                messagebox.showinfo("Success", f"Printed {success_count} labels and added to carton")
            else:
                messagebox.showinfo("Success", f"Printed {success_count} labels")
        else:
            messagebox.showwarning("Partial Success", f"Printed {success_count} labels, {fail_count} failed")

    # ==================== CARTON FUNCTIONS ====================

    def _create_new_carton(self):
        """Create a new carton"""
        if not self.carton_enabled_var.get():
            messagebox.showwarning("Warning", "Carton mode is disabled. Enable it first.")
            return

        if not self.location_var.get() or not self.packer_var.get():
            messagebox.showwarning("Warning", "Please select destination and packer first")
            return

        location = self._get_selected_location()
        packer = self._get_selected_packer()

        try:
            carton_id, barcode = db.create_carton(location['id'], packer['id'], "")
            self.current_carton = db.get_carton_by_id(carton_id)
            self._update_carton_display()
            messagebox.showinfo("Success", f"Carton created: {barcode}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create carton: {e}")

    def _update_carton_display(self):
        """Update carton status display"""
        if self.current_carton:
            self.carton_status_label.config(text="Active carton:", fg=COLORS["text"])
            self.carton_barcode_label.config(text=self.current_carton['barcode'])

            contents = db.get_carton_contents(self.current_carton['id'])
            total_qty = sum(c['quantity'] for c in contents)
            self.carton_count_label.config(text=f"{len(contents)} items, {total_qty} total")
        else:
            self.carton_status_label.config(text="No active carton", fg=COLORS["text_dim"])
            self.carton_barcode_label.config(text="")
            self.carton_count_label.config(text="")

    def _close_and_print_carton(self):
        """Close carton and print label"""
        if not self.current_carton:
            messagebox.showwarning("Warning", "No active carton")
            return

        contents = db.get_carton_contents(self.current_carton['id'])
        if not contents:
            if not messagebox.askyesno("Empty Carton", "Carton is empty. Close anyway?"):
                return

        db.close_carton(self.current_carton['id'])

        # Print carton label
        summary = db.get_carton_summary(self.current_carton['id'])
        summary_text = ", ".join([f"{s['product_code']}x{int(s['total_quantity'])}" for s in summary])

        success, msg = self.printer.print_label(
            self.current_carton['barcode'],
            f"CARTON: {summary_text[:25]}",
            self.current_carton['location_name'],
            self.current_carton['packer_name'],
            True,  # QR code
            1
        )

        barcode = self.current_carton['barcode']
        self.current_carton = None
        self._update_carton_display()

        if success:
            messagebox.showinfo("Success", f"Carton closed and printed\n\n{barcode}")
        else:
            messagebox.showwarning("Print Failed", f"Carton closed but print failed\n\n{barcode}")

    # ==================== LOOKUP FUNCTIONS ====================

    def _lookup_carton(self):
        """Lookup carton by barcode"""
        barcode = self.lookup_var.get().strip()
        if not barcode:
            messagebox.showwarning("Warning", "Enter a barcode")
            return

        carton = db.lookup_carton_by_barcode(barcode)
        if not carton:
            self.lookup_info.config(text=f"No carton found: {barcode}", fg=COLORS["danger"])
            self.lookup_tree.delete(*self.lookup_tree.get_children())
            return

        status = "OPEN" if carton['status'] == 'open' else "CLOSED"
        info = f"Barcode: {carton['barcode']}   |   Status: {status}   |   Destination: {carton['location_name']}   |   Packer: {carton['packer_name']}"
        self.lookup_info.config(text=info, fg=COLORS["text"])

        self.lookup_tree.delete(*self.lookup_tree.get_children())
        for s in carton['summary']:
            self.lookup_tree.insert("", tk.END, values=(
                s['product_code'],
                s['product_name'],
                int(s['total_quantity'])
            ))

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

    def _get_selected_packer(self):
        code = self.packer_var.get().split(" - ")[0]
        for p in db.get_all_packers():
            if p['code'] == code:
                return dict(p)
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

    def _add_packer(self):
        code = self.new_packer_code.get().strip()
        name = self.new_packer_name.get().strip()

        if not code or not name:
            messagebox.showwarning("Warning", "Code and Name required")
            return

        try:
            db.add_packer(code, name)
            self._refresh_packers()
            self.new_packer_code.delete(0, tk.END)
            self.new_packer_name.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _toggle_packer(self):
        selection = self.packers_tree.selection()
        if not selection:
            return
        code = self.packers_tree.item(selection[0])['values'][0]
        for p in db.get_all_packers(active_only=False):
            if p['code'] == code:
                db.toggle_packer_active(p['id'])
                break
        self._refresh_packers()

    def _delete_packer(self):
        selection = self.packers_tree.selection()
        if not selection:
            return
        if messagebox.askyesno("Confirm", "Delete packer?"):
            code = self.packers_tree.item(selection[0])['values'][0]
            for p in db.get_all_packers(active_only=False):
                if p['code'] == code:
                    db.delete_packer(p['id'])
                    break
            self._refresh_packers()

    # ==================== REFRESH FUNCTIONS ====================

    def _refresh_combos(self):
        products = db.get_all_products()
        self.product_combo['values'] = [f"{p['code']} - {p['name']}" for p in products]

        locations = db.get_all_locations()
        self.location_combo['values'] = [f"{l['code']} - {l['name']}" for l in locations]

        packers = db.get_all_packers(active_only=True)
        self.packer_combo['values'] = [f"{p['code']} - {p['name']}" for p in packers]

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

    def _refresh_packers(self):
        self.packers_tree.delete(*self.packers_tree.get_children())
        for p in db.get_all_packers(active_only=False):
            self.packers_tree.insert("", tk.END, values=(
                p['code'], p['name'], "Yes" if p['active'] else "No", p['created_at']
            ))
        self._refresh_combos()

    def _refresh_history(self):
        stats = db.get_daily_stats()
        if stats:
            text = " | ".join([f"{s['packer_name']}: {int(s['total_items'])} items" for s in stats])
        else:
            text = "No labels printed today"
        self.stats_label.config(text=text)

        self.history_tree.delete(*self.history_tree.get_children())
        for h in db.get_barcode_history():
            self.history_tree.insert("", tk.END, values=(
                h['barcode_data'], h['product_name'] or "-", h['location_name'] or "-",
                h['packer_name'] or "-", h['quantity'], h['created_at']
            ))

    def _refresh_all_data(self):
        self._refresh_products()
        self._refresh_locations()
        self._refresh_packers()
        self._refresh_history()

    # ==================== DIALOGS ====================

    def _export_history(self):
        filename = filedialog.asksaveasfilename(defaultextension=".csv",
                                                filetypes=[("CSV", "*.csv")])
        if filename:
            history = db.get_barcode_history(limit=10000)
            with open(filename, 'w') as f:
                f.write("Barcode,Product,Location,Packer,Qty,Created\n")
                for h in history:
                    f.write(f"{h['barcode_data']},{h['product_name']},{h['location_name']},"
                           f"{h['packer_name']},{h['quantity']},{h['created_at']}\n")
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
            "Barcode Generator v2.1\n\n"
            "Features:\n"
            "- Multi-product cart system\n"
            "- Automatic carton tracking\n"
            "- Batch printing\n"
            "- TSC TE200 support")


def main():
    root = tk.Tk()
    app = BarcodeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
