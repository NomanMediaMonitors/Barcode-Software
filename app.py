import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from PIL import Image, ImageTk
import os

import database as db
from barcode_generator import BarcodeGenerator
from printer import TSCPrinter, print_barcode_label
from config import SHORT_DATE_FORMAT


class ModernStyle:
    """Modern color scheme and styling"""
    # Colors
    BG_PRIMARY = "#1a1a2e"
    BG_SECONDARY = "#16213e"
    BG_CARD = "#0f3460"
    ACCENT = "#e94560"
    ACCENT_HOVER = "#ff6b6b"
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#a0a0a0"
    SUCCESS = "#00d26a"
    WARNING = "#ffc107"

    @classmethod
    def apply_theme(cls, root):
        """Apply modern dark theme"""
        style = ttk.Style()

        # Try to use clam theme as base (works well for customization)
        try:
            style.theme_use('clam')
        except:
            pass

        # Configure colors
        style.configure(".",
            background=cls.BG_SECONDARY,
            foreground=cls.TEXT_PRIMARY,
            fieldbackground=cls.BG_PRIMARY,
            font=("Segoe UI", 10)
        )

        # Frame styles
        style.configure("TFrame", background=cls.BG_SECONDARY)
        style.configure("Card.TFrame", background=cls.BG_CARD)

        # Label styles
        style.configure("TLabel",
            background=cls.BG_SECONDARY,
            foreground=cls.TEXT_PRIMARY,
            font=("Segoe UI", 10)
        )
        style.configure("Card.TLabel", background=cls.BG_CARD)
        style.configure("Title.TLabel",
            font=("Segoe UI", 18, "bold"),
            foreground=cls.TEXT_PRIMARY
        )
        style.configure("Subtitle.TLabel",
            font=("Segoe UI", 12),
            foreground=cls.TEXT_SECONDARY
        )
        style.configure("Header.TLabel",
            font=("Segoe UI", 11, "bold"),
            foreground=cls.TEXT_PRIMARY
        )
        style.configure("Success.TLabel", foreground=cls.SUCCESS)
        style.configure("Accent.TLabel", foreground=cls.ACCENT)

        # Button styles
        style.configure("TButton",
            background=cls.ACCENT,
            foreground=cls.TEXT_PRIMARY,
            font=("Segoe UI", 10, "bold"),
            padding=(20, 10)
        )
        style.map("TButton",
            background=[("active", cls.ACCENT_HOVER), ("pressed", cls.ACCENT)],
            foreground=[("active", cls.TEXT_PRIMARY)]
        )

        style.configure("Success.TButton", background=cls.SUCCESS)
        style.map("Success.TButton",
            background=[("active", "#00ff7f"), ("pressed", cls.SUCCESS)]
        )

        # Entry styles
        style.configure("TEntry",
            fieldbackground=cls.BG_PRIMARY,
            foreground=cls.TEXT_PRIMARY,
            insertcolor=cls.TEXT_PRIMARY,
            padding=8
        )

        # Combobox styles
        style.configure("TCombobox",
            fieldbackground=cls.BG_PRIMARY,
            background=cls.BG_CARD,
            foreground=cls.TEXT_PRIMARY,
            arrowcolor=cls.TEXT_PRIMARY,
            padding=8
        )
        style.map("TCombobox",
            fieldbackground=[("readonly", cls.BG_PRIMARY)],
            selectbackground=[("readonly", cls.ACCENT)]
        )

        # Checkbutton styles
        style.configure("TCheckbutton",
            background=cls.BG_SECONDARY,
            foreground=cls.TEXT_PRIMARY,
            font=("Segoe UI", 10)
        )
        style.configure("Card.TCheckbutton", background=cls.BG_CARD)

        # Radiobutton styles
        style.configure("TRadiobutton",
            background=cls.BG_SECONDARY,
            foreground=cls.TEXT_PRIMARY
        )
        style.configure("Card.TRadiobutton", background=cls.BG_CARD)

        # Notebook (tabs) styles
        style.configure("TNotebook", background=cls.BG_SECONDARY, borderwidth=0)
        style.configure("TNotebook.Tab",
            background=cls.BG_PRIMARY,
            foreground=cls.TEXT_SECONDARY,
            padding=(20, 10),
            font=("Segoe UI", 10)
        )
        style.map("TNotebook.Tab",
            background=[("selected", cls.BG_CARD)],
            foreground=[("selected", cls.TEXT_PRIMARY)],
            expand=[("selected", [1, 1, 1, 0])]
        )

        # Treeview styles
        style.configure("Treeview",
            background=cls.BG_PRIMARY,
            foreground=cls.TEXT_PRIMARY,
            fieldbackground=cls.BG_PRIMARY,
            rowheight=30,
            font=("Segoe UI", 9)
        )
        style.configure("Treeview.Heading",
            background=cls.BG_CARD,
            foreground=cls.TEXT_PRIMARY,
            font=("Segoe UI", 10, "bold")
        )
        style.map("Treeview",
            background=[("selected", cls.ACCENT)],
            foreground=[("selected", cls.TEXT_PRIMARY)]
        )

        # LabelFrame styles
        style.configure("TLabelframe",
            background=cls.BG_CARD,
            foreground=cls.TEXT_PRIMARY
        )
        style.configure("TLabelframe.Label",
            background=cls.BG_CARD,
            foreground=cls.ACCENT,
            font=("Segoe UI", 11, "bold")
        )

        # Spinbox
        style.configure("TSpinbox",
            fieldbackground=cls.BG_PRIMARY,
            background=cls.BG_CARD,
            foreground=cls.TEXT_PRIMARY,
            arrowcolor=cls.TEXT_PRIMARY,
            padding=8
        )

        # Scrollbar
        style.configure("TScrollbar",
            background=cls.BG_CARD,
            troughcolor=cls.BG_PRIMARY,
            arrowcolor=cls.TEXT_PRIMARY
        )

        # Set root background
        root.configure(bg=cls.BG_SECONDARY)


class BarcodeApp:
    """Main application window"""

    def __init__(self, root):
        self.root = root
        self.root.title("Barcode Generator Pro")
        self.root.geometry("1100x750")
        self.root.minsize(1000, 650)

        # Apply modern theme
        ModernStyle.apply_theme(root)

        # Initialize components
        self.barcode_gen = BarcodeGenerator()
        self.printer = TSCPrinter()
        self.current_label_image = None
        self.current_carton = None  # Current active carton

        # Create main UI
        self._create_menu()
        self._create_header()
        self._create_notebook()

        # Load initial data
        self._refresh_all_data()

    def _create_menu(self):
        menubar = tk.Menu(self.root, bg=ModernStyle.BG_PRIMARY, fg=ModernStyle.TEXT_PRIMARY,
                         activebackground=ModernStyle.ACCENT, activeforeground=ModernStyle.TEXT_PRIMARY)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0, bg=ModernStyle.BG_PRIMARY, fg=ModernStyle.TEXT_PRIMARY,
                           activebackground=ModernStyle.ACCENT)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export History", command=self._export_history)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0, bg=ModernStyle.BG_PRIMARY, fg=ModernStyle.TEXT_PRIMARY,
                               activebackground=ModernStyle.ACCENT)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Printer Setup", command=self._show_printer_setup)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0, bg=ModernStyle.BG_PRIMARY, fg=ModernStyle.TEXT_PRIMARY,
                           activebackground=ModernStyle.ACCENT)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)

    def _create_header(self):
        """Create app header"""
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill=tk.X, padx=20, pady=(15, 5))

        ttk.Label(header_frame, text="Barcode Generator Pro", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Label(header_frame, text="TSC TE200 Label Printer", style="Subtitle.TLabel").pack(side=tk.LEFT, padx=20)

    def _create_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        # Create tabs
        self._create_generate_tab()
        self._create_carton_lookup_tab()
        self._create_products_tab()
        self._create_locations_tab()
        self._create_packers_tab()
        self._create_history_tab()

    # ==================== GENERATE TAB ====================

    def _create_generate_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Generate & Pack  ")

        # Main container
        main_container = ttk.Frame(tab)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left panel - Form
        left_frame = ttk.LabelFrame(main_container, text="Label Information", padding=15)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # Product selection
        ttk.Label(left_frame, text="Product", style="Header.TLabel").grid(
            row=0, column=0, sticky=tk.W, pady=(0, 5)
        )
        self.product_var = tk.StringVar()
        self.product_combo = ttk.Combobox(
            left_frame, textvariable=self.product_var, state="readonly", width=35
        )
        self.product_combo.grid(row=1, column=0, sticky=tk.EW, pady=(0, 15))

        # Location selection
        ttk.Label(left_frame, text="Destination", style="Header.TLabel").grid(
            row=2, column=0, sticky=tk.W, pady=(0, 5)
        )
        self.location_var = tk.StringVar()
        self.location_combo = ttk.Combobox(
            left_frame, textvariable=self.location_var, state="readonly", width=35
        )
        self.location_combo.grid(row=3, column=0, sticky=tk.EW, pady=(0, 15))

        # Packer selection
        ttk.Label(left_frame, text="Packer", style="Header.TLabel").grid(
            row=4, column=0, sticky=tk.W, pady=(0, 5)
        )
        self.packer_var = tk.StringVar()
        self.packer_combo = ttk.Combobox(
            left_frame, textvariable=self.packer_var, state="readonly", width=35
        )
        self.packer_combo.grid(row=5, column=0, sticky=tk.EW, pady=(0, 15))

        # Barcode type and Quantity row
        options_frame = ttk.Frame(left_frame)
        options_frame.grid(row=6, column=0, sticky=tk.EW, pady=(0, 15))

        # Barcode type
        type_frame = ttk.Frame(options_frame)
        type_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(type_frame, text="Barcode Type", style="Header.TLabel").pack(anchor=tk.W)
        self.barcode_type_var = tk.StringVar(value="code128")
        barcode_frame = ttk.Frame(type_frame)
        barcode_frame.pack(anchor=tk.W, pady=(5, 0))
        ttk.Radiobutton(
            barcode_frame, text="Code 128", variable=self.barcode_type_var, value="code128"
        ).pack(side=tk.LEFT)
        ttk.Radiobutton(
            barcode_frame, text="QR Code", variable=self.barcode_type_var, value="qrcode"
        ).pack(side=tk.LEFT, padx=15)

        # Quantity
        qty_frame = ttk.Frame(options_frame)
        qty_frame.pack(side=tk.RIGHT)
        ttk.Label(qty_frame, text="Quantity", style="Header.TLabel").pack(anchor=tk.W)
        self.quantity_var = tk.StringVar(value="1")
        quantity_spin = ttk.Spinbox(
            qty_frame, from_=1, to=100, textvariable=self.quantity_var, width=8
        )
        quantity_spin.pack(anchor=tk.W, pady=(5, 0))

        # Separator
        ttk.Separator(left_frame, orient=tk.HORIZONTAL).grid(row=7, column=0, sticky=tk.EW, pady=15)

        # CARTON SECTION
        carton_section = ttk.Frame(left_frame)
        carton_section.grid(row=8, column=0, sticky=tk.EW)

        # Carton checkbox
        self.carton_enabled_var = tk.BooleanVar(value=False)
        self.carton_check = ttk.Checkbutton(
            carton_section,
            text="Add to Carton",
            variable=self.carton_enabled_var,
            command=self._toggle_carton_mode
        )
        self.carton_check.pack(anchor=tk.W)

        # Carton info frame (shown when checkbox is checked)
        self.carton_info_frame = ttk.Frame(left_frame)
        self.carton_info_frame.grid(row=9, column=0, sticky=tk.EW, pady=(10, 0))

        self.carton_status_label = ttk.Label(
            self.carton_info_frame,
            text="No active carton",
            style="Subtitle.TLabel"
        )
        self.carton_status_label.pack(anchor=tk.W)

        self.carton_barcode_label = ttk.Label(
            self.carton_info_frame,
            text="",
            style="Accent.TLabel"
        )
        self.carton_barcode_label.pack(anchor=tk.W)

        self.carton_count_label = ttk.Label(
            self.carton_info_frame,
            text="",
            style="Success.TLabel"
        )
        self.carton_count_label.pack(anchor=tk.W)

        # Carton buttons
        carton_btn_frame = ttk.Frame(self.carton_info_frame)
        carton_btn_frame.pack(anchor=tk.W, pady=(10, 0))

        ttk.Button(
            carton_btn_frame, text="New Carton", command=self._create_new_carton
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            carton_btn_frame, text="Close & Print Carton", command=self._close_and_print_carton,
            style="Success.TButton"
        ).pack(side=tk.LEFT)

        # Initially hide carton info
        self.carton_info_frame.grid_remove()

        # Buttons
        btn_frame = ttk.Frame(left_frame)
        btn_frame.grid(row=10, column=0, pady=(25, 0), sticky=tk.EW)

        ttk.Button(
            btn_frame, text="Preview", command=self._preview_label
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(
            btn_frame, text="Print Label", command=self._print_label,
            style="Success.TButton"
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(
            btn_frame, text="Save Image", command=self._save_label_image
        ).pack(side=tk.LEFT)

        # Configure grid weights
        left_frame.columnconfigure(0, weight=1)

        # Right panel - Preview
        right_frame = ttk.LabelFrame(main_container, text="Label Preview", padding=15)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.preview_canvas = tk.Canvas(
            right_frame, bg=ModernStyle.BG_PRIMARY, highlightthickness=0
        )
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)

        # Barcode data display
        self.barcode_data_var = tk.StringVar(value="Select options and click Preview")
        ttk.Label(
            right_frame, textvariable=self.barcode_data_var,
            font=("Consolas", 11), style="Accent.TLabel"
        ).pack(pady=(15, 0))

    def _toggle_carton_mode(self):
        """Toggle carton mode on/off"""
        if self.carton_enabled_var.get():
            self.carton_info_frame.grid()
            self._update_carton_display()
        else:
            self.carton_info_frame.grid_remove()

    def _create_new_carton(self):
        """Create a new carton"""
        if not self._validate_selection():
            return

        location = self._get_selected_location()
        packer = self._get_selected_packer()

        if not location or not packer:
            messagebox.showerror("Error", "Please select destination and packer first")
            return

        try:
            carton_id, barcode = db.create_carton(location['id'], packer['id'], "")
            self.current_carton = db.get_carton_by_id(carton_id)
            self._update_carton_display()
            messagebox.showinfo("Carton Created", f"New carton created!\n\nBarcode: {barcode}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not create carton: {e}")

    def _update_carton_display(self):
        """Update carton status display"""
        if self.current_carton:
            self.carton_status_label.config(text=f"Active Carton:")
            self.carton_barcode_label.config(text=self.current_carton['barcode'])

            contents = db.get_carton_contents(self.current_carton['id'])
            total_qty = sum(c['quantity'] for c in contents)
            self.carton_count_label.config(text=f"{len(contents)} items, {total_qty} total qty")
        else:
            self.carton_status_label.config(text="No active carton")
            self.carton_barcode_label.config(text="Click 'New Carton' to start packing")
            self.carton_count_label.config(text="")

    def _close_and_print_carton(self):
        """Close current carton and print its label"""
        if not self.current_carton:
            messagebox.showwarning("Warning", "No active carton to close")
            return

        contents = db.get_carton_contents(self.current_carton['id'])
        if not contents:
            if not messagebox.askyesno("Empty Carton", "This carton is empty. Close anyway?"):
                return

        # Close the carton
        db.close_carton(self.current_carton['id'])

        # Print carton label
        summary = db.get_carton_summary(self.current_carton['id'])
        summary_text = ", ".join([f"{s['product_code']}x{int(s['total_quantity'])}" for s in summary])

        success, message = self.printer.print_label(
            self.current_carton['barcode'],
            f"CARTON: {summary_text[:25]}",
            self.current_carton['location_name'],
            self.current_carton['packer_name'],
            True,  # QR code for cartons
            1
        )

        carton_barcode = self.current_carton['barcode']
        self.current_carton = None
        self._update_carton_display()

        if success:
            messagebox.showinfo("Success", f"Carton closed and label printed!\n\nBarcode: {carton_barcode}")
        else:
            messagebox.showwarning("Print Failed", f"Carton closed but print failed:\n{message}\n\nBarcode: {carton_barcode}")

    def _preview_label(self):
        if not self._validate_selection():
            return

        # Get selected values
        product = self._get_selected_product()
        location = self._get_selected_location()
        packer = self._get_selected_packer()

        if not all([product, location, packer]):
            messagebox.showerror("Error", "Please select all options")
            return

        # Generate barcode data
        barcode_data = self.barcode_gen.generate_barcode_data(
            location['code'], product['code'], packer['code']
        )

        # Create label image
        label_img = self.barcode_gen.create_label(
            barcode_data,
            product['name'],
            location['name'],
            packer['name'],
            self.barcode_type_var.get()
        )

        # Store for printing/saving
        self.current_label_image = label_img
        self.current_barcode_data = barcode_data
        self.current_product = product
        self.current_location = location
        self.current_packer = packer

        # Display preview
        self._display_preview(label_img)

        # Update barcode data display
        self.barcode_data_var.set(f"{barcode_data}")

    def _display_preview(self, image: Image.Image):
        # Resize to fit canvas
        self.preview_canvas.update_idletasks()
        canvas_width = self.preview_canvas.winfo_width() or 400
        canvas_height = self.preview_canvas.winfo_height() or 300

        ratio = min(canvas_width / image.width, canvas_height / image.height)
        new_size = (int(image.width * ratio * 0.85), int(image.height * ratio * 0.85))

        resized = image.resize(new_size, Image.Resampling.LANCZOS)

        # Convert to PhotoImage
        self.preview_photo = ImageTk.PhotoImage(resized)

        # Clear canvas and display
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(
            canvas_width // 2, canvas_height // 2,
            image=self.preview_photo, anchor=tk.CENTER
        )

    def _print_label(self):
        if self.current_label_image is None:
            messagebox.showwarning("Warning", "Please preview the label first")
            return

        quantity = int(self.quantity_var.get())

        # Try to print
        use_qrcode = self.barcode_type_var.get() == "qrcode"

        success, message = self.printer.print_label(
            self.current_barcode_data,
            self.current_product['name'],
            self.current_location['name'],
            self.current_packer['name'],
            use_qrcode,
            quantity
        )

        if success:
            # Save to history
            db.save_barcode_history(
                self.current_barcode_data,
                self.current_product['id'],
                self.current_location['id'],
                self.current_packer['id'],
                quantity
            )

            # If carton mode is enabled, add to carton
            if self.carton_enabled_var.get():
                if not self.current_carton:
                    # Auto-create carton if none exists
                    carton_id, barcode = db.create_carton(
                        self.current_location['id'],
                        self.current_packer['id'],
                        ""
                    )
                    self.current_carton = db.get_carton_by_id(carton_id)

                # Add product to carton
                db.add_product_to_carton(
                    self.current_carton['id'],
                    self.current_product['id'],
                    quantity,
                    self.current_barcode_data
                )
                self._update_carton_display()

                messagebox.showinfo("Success",
                    f"Printed {quantity} label(s) and added to carton\n\n"
                    f"Carton: {self.current_carton['barcode']}"
                )
            else:
                messagebox.showinfo("Success", f"Printed {quantity} label(s)")

            self._refresh_history()
        else:
            if messagebox.askyesno(
                "Print Failed",
                f"{message}\n\nWould you like to save as a .prn file instead?"
            ):
                self._save_tspl_file()

    def _save_label_image(self):
        """Save label as image file"""
        if self.current_label_image is None:
            messagebox.showwarning("Warning", "Please preview the label first")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("JPEG Image", "*.jpg"), ("All files", "*.*")]
        )

        if filename:
            self.current_label_image.save(filename)
            messagebox.showinfo("Success", f"Label saved to {filename}")

    def _save_tspl_file(self):
        """Save TSPL commands to file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".prn",
            filetypes=[("Printer File", "*.prn"), ("TSPL File", "*.tspl"), ("All files", "*.*")]
        )

        if filename:
            use_qrcode = self.barcode_type_var.get() == "qrcode"
            saved_path = self.printer.save_tspl_file(
                self.current_barcode_data,
                self.current_product['name'],
                self.current_location['name'],
                self.current_packer['name'],
                filename,
                use_qrcode
            )
            messagebox.showinfo("Success", f"File saved to:\n{saved_path}")

    def _validate_selection(self):
        """Validate that all required selections are made"""
        if not self.product_var.get():
            messagebox.showwarning("Warning", "Please select a product")
            return False
        if not self.location_var.get():
            messagebox.showwarning("Warning", "Please select a destination")
            return False
        if not self.packer_var.get():
            messagebox.showwarning("Warning", "Please select a packer")
            return False
        return True

    def _get_selected_product(self):
        """Get selected product details"""
        selection = self.product_var.get()
        if selection:
            code = selection.split(" - ")[0]
            for p in db.get_all_products():
                if p['code'] == code:
                    return dict(p)
        return None

    def _get_selected_location(self):
        """Get selected location details"""
        selection = self.location_var.get()
        if selection:
            code = selection.split(" - ")[0]
            for l in db.get_all_locations():
                if l['code'] == code:
                    return dict(l)
        return None

    def _get_selected_packer(self):
        """Get selected packer details"""
        selection = self.packer_var.get()
        if selection:
            code = selection.split(" - ")[0]
            for p in db.get_all_packers():
                if p['code'] == code:
                    return dict(p)
        return None

    # ==================== CARTON LOOKUP TAB ====================

    def _create_carton_lookup_tab(self):
        """Create carton lookup tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Carton Lookup  ")

        # Search section
        search_frame = ttk.LabelFrame(tab, text="Scan Carton Barcode", padding=20)
        search_frame.pack(fill=tk.X, padx=15, pady=15)

        input_frame = ttk.Frame(search_frame)
        input_frame.pack(fill=tk.X)

        ttk.Label(input_frame, text="Carton Barcode:", style="Header.TLabel").pack(side=tk.LEFT, padx=(0, 10))
        self.lookup_barcode_var = tk.StringVar()
        self.lookup_entry = ttk.Entry(input_frame, textvariable=self.lookup_barcode_var, width=40, font=("Consolas", 12))
        self.lookup_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.lookup_entry.bind('<Return>', lambda e: self._lookup_carton())

        ttk.Button(input_frame, text="Lookup", command=self._lookup_carton).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(input_frame, text="Clear", command=self._clear_lookup).pack(side=tk.LEFT)

        # Results container
        results_container = ttk.Frame(tab)
        results_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        # Carton info
        info_frame = ttk.LabelFrame(results_container, text="Carton Information", padding=15)
        info_frame.pack(fill=tk.X, pady=(0, 10))

        self.lookup_info_text = tk.Text(
            info_frame, height=5, wrap=tk.WORD,
            bg=ModernStyle.BG_PRIMARY, fg=ModernStyle.TEXT_PRIMARY,
            font=("Consolas", 11), relief=tk.FLAT, padx=10, pady=10
        )
        self.lookup_info_text.pack(fill=tk.X)
        self.lookup_info_text.config(state=tk.DISABLED)

        # Contents summary
        summary_frame = ttk.LabelFrame(results_container, text="Contents Summary", padding=15)
        summary_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("product_code", "product_name", "total_quantity")
        self.summary_tree = ttk.Treeview(summary_frame, columns=columns, show="headings")

        self.summary_tree.heading("product_code", text="Product Code")
        self.summary_tree.heading("product_name", text="Product Name")
        self.summary_tree.heading("total_quantity", text="Total Quantity")

        self.summary_tree.column("product_code", width=150)
        self.summary_tree.column("product_name", width=350)
        self.summary_tree.column("total_quantity", width=120)

        scrollbar = ttk.Scrollbar(summary_frame, orient=tk.VERTICAL, command=self.summary_tree.yview)
        self.summary_tree.configure(yscrollcommand=scrollbar.set)

        self.summary_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _lookup_carton(self):
        """Look up carton by barcode"""
        barcode = self.lookup_barcode_var.get().strip()
        if not barcode:
            messagebox.showwarning("Warning", "Please enter a carton barcode")
            return

        carton = db.lookup_carton_by_barcode(barcode)

        if not carton:
            messagebox.showwarning("Not Found", f"No carton found with barcode:\n{barcode}")
            self._clear_lookup()
            return

        # Update info display
        self.lookup_info_text.config(state=tk.NORMAL)
        self.lookup_info_text.delete(1.0, tk.END)

        status_color = "OPEN" if carton['status'] == 'open' else "CLOSED"
        info = (
            f"Barcode:     {carton['barcode']}\n"
            f"Status:      {status_color}\n"
            f"Destination: {carton['location_name']} ({carton['location_code']})\n"
            f"Packed by:   {carton['packer_name']} ({carton['packer_code']})\n"
            f"Created:     {carton['created_at']}"
        )
        if carton['closed_at']:
            info += f"\nClosed:      {carton['closed_at']}"

        self.lookup_info_text.insert(tk.END, info)
        self.lookup_info_text.config(state=tk.DISABLED)

        # Update summary
        self.summary_tree.delete(*self.summary_tree.get_children())
        for s in carton['summary']:
            self.summary_tree.insert("", tk.END, values=(
                s['product_code'],
                s['product_name'],
                int(s['total_quantity'])
            ))

    def _clear_lookup(self):
        """Clear lookup results"""
        self.lookup_barcode_var.set("")
        self.lookup_info_text.config(state=tk.NORMAL)
        self.lookup_info_text.delete(1.0, tk.END)
        self.lookup_info_text.config(state=tk.DISABLED)
        self.summary_tree.delete(*self.summary_tree.get_children())

    # ==================== PRODUCTS TAB ====================

    def _create_products_tab(self):
        """Create products management tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Products  ")

        # Add form
        form_frame = ttk.LabelFrame(tab, text="Add New Product", padding=15)
        form_frame.pack(fill=tk.X, padx=15, pady=15)

        form_inner = ttk.Frame(form_frame)
        form_inner.pack(fill=tk.X)

        ttk.Label(form_inner, text="Code:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        self.new_product_code = ttk.Entry(form_inner, width=15)
        self.new_product_code.grid(row=0, column=1, sticky=tk.W, pady=5, padx=(0, 20))

        ttk.Label(form_inner, text="Name:").grid(row=0, column=2, sticky=tk.W, pady=5, padx=(0, 10))
        self.new_product_name = ttk.Entry(form_inner, width=30)
        self.new_product_name.grid(row=0, column=3, sticky=tk.W, pady=5, padx=(0, 20))

        ttk.Label(form_inner, text="Description:").grid(row=0, column=4, sticky=tk.W, pady=5, padx=(0, 10))
        self.new_product_desc = ttk.Entry(form_inner, width=35)
        self.new_product_desc.grid(row=0, column=5, sticky=tk.W, pady=5, padx=(0, 20))

        ttk.Button(form_inner, text="Add Product", command=self._add_product).grid(row=0, column=6, padx=10)

        # Products list
        list_frame = ttk.Frame(tab)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        columns = ("code", "name", "description", "created")
        self.products_tree = ttk.Treeview(list_frame, columns=columns, show="headings")

        self.products_tree.heading("code", text="Code")
        self.products_tree.heading("name", text="Name")
        self.products_tree.heading("description", text="Description")
        self.products_tree.heading("created", text="Created")

        self.products_tree.column("code", width=100)
        self.products_tree.column("name", width=200)
        self.products_tree.column("description", width=300)
        self.products_tree.column("created", width=150)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.products_tree.yview)
        self.products_tree.configure(yscrollcommand=scrollbar.set)

        self.products_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Delete button
        ttk.Button(tab, text="Delete Selected", command=self._delete_product).pack(pady=(0, 15))

    def _add_product(self):
        """Add a new product"""
        code = self.new_product_code.get().strip()
        name = self.new_product_name.get().strip()
        desc = self.new_product_desc.get().strip()

        if not code or not name:
            messagebox.showwarning("Warning", "Code and Name are required")
            return

        try:
            db.add_product(code, name, desc)
            self._refresh_products()
            self.new_product_code.delete(0, tk.END)
            self.new_product_name.delete(0, tk.END)
            self.new_product_desc.delete(0, tk.END)
            messagebox.showinfo("Success", "Product added successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Could not add product: {e}")

    def _delete_product(self):
        """Delete selected product"""
        selection = self.products_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a product to delete")
            return

        if messagebox.askyesno("Confirm", "Are you sure you want to delete this product?"):
            item = self.products_tree.item(selection[0])
            code = item['values'][0]
            for p in db.get_all_products():
                if p['code'] == code:
                    db.delete_product(p['id'])
                    break
            self._refresh_products()

    def _refresh_products(self):
        """Refresh products list"""
        self.products_tree.delete(*self.products_tree.get_children())
        for p in db.get_all_products():
            self.products_tree.insert("", tk.END, values=(
                p['code'], p['name'], p['description'] or "", p['created_at']
            ))
        self._refresh_combos()

    # ==================== LOCATIONS TAB ====================

    def _create_locations_tab(self):
        """Create locations management tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Locations  ")

        # Add form
        form_frame = ttk.LabelFrame(tab, text="Add New Location", padding=15)
        form_frame.pack(fill=tk.X, padx=15, pady=15)

        form_inner = ttk.Frame(form_frame)
        form_inner.pack(fill=tk.X)

        ttk.Label(form_inner, text="Code:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        self.new_location_code = ttk.Entry(form_inner, width=15)
        self.new_location_code.grid(row=0, column=1, sticky=tk.W, pady=5, padx=(0, 20))

        ttk.Label(form_inner, text="Name:").grid(row=0, column=2, sticky=tk.W, pady=5, padx=(0, 10))
        self.new_location_name = ttk.Entry(form_inner, width=30)
        self.new_location_name.grid(row=0, column=3, sticky=tk.W, pady=5, padx=(0, 20))

        ttk.Label(form_inner, text="Address:").grid(row=0, column=4, sticky=tk.W, pady=5, padx=(0, 10))
        self.new_location_addr = ttk.Entry(form_inner, width=35)
        self.new_location_addr.grid(row=0, column=5, sticky=tk.W, pady=5, padx=(0, 20))

        ttk.Button(form_inner, text="Add Location", command=self._add_location).grid(row=0, column=6, padx=10)

        # Locations list
        list_frame = ttk.Frame(tab)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        columns = ("code", "name", "address", "created")
        self.locations_tree = ttk.Treeview(list_frame, columns=columns, show="headings")

        self.locations_tree.heading("code", text="Code")
        self.locations_tree.heading("name", text="Name")
        self.locations_tree.heading("address", text="Address")
        self.locations_tree.heading("created", text="Created")

        self.locations_tree.column("code", width=100)
        self.locations_tree.column("name", width=200)
        self.locations_tree.column("address", width=300)
        self.locations_tree.column("created", width=150)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.locations_tree.yview)
        self.locations_tree.configure(yscrollcommand=scrollbar.set)

        self.locations_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Button(tab, text="Delete Selected", command=self._delete_location).pack(pady=(0, 15))

    def _add_location(self):
        """Add a new location"""
        code = self.new_location_code.get().strip()
        name = self.new_location_name.get().strip()
        addr = self.new_location_addr.get().strip()

        if not code or not name:
            messagebox.showwarning("Warning", "Code and Name are required")
            return

        try:
            db.add_location(code, name, addr)
            self._refresh_locations()
            self.new_location_code.delete(0, tk.END)
            self.new_location_name.delete(0, tk.END)
            self.new_location_addr.delete(0, tk.END)
            messagebox.showinfo("Success", "Location added successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Could not add location: {e}")

    def _delete_location(self):
        """Delete selected location"""
        selection = self.locations_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a location to delete")
            return

        if messagebox.askyesno("Confirm", "Are you sure you want to delete this location?"):
            item = self.locations_tree.item(selection[0])
            code = item['values'][0]
            for l in db.get_all_locations():
                if l['code'] == code:
                    db.delete_location(l['id'])
                    break
            self._refresh_locations()

    def _refresh_locations(self):
        """Refresh locations list"""
        self.locations_tree.delete(*self.locations_tree.get_children())
        for l in db.get_all_locations():
            self.locations_tree.insert("", tk.END, values=(
                l['code'], l['name'], l['address'] or "", l['created_at']
            ))
        self._refresh_combos()

    # ==================== PACKERS TAB ====================

    def _create_packers_tab(self):
        """Create packers management tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  Packers  ")

        # Add form
        form_frame = ttk.LabelFrame(tab, text="Add New Packer", padding=15)
        form_frame.pack(fill=tk.X, padx=15, pady=15)

        form_inner = ttk.Frame(form_frame)
        form_inner.pack(fill=tk.X)

        ttk.Label(form_inner, text="Code:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        self.new_packer_code = ttk.Entry(form_inner, width=15)
        self.new_packer_code.grid(row=0, column=1, sticky=tk.W, pady=5, padx=(0, 20))

        ttk.Label(form_inner, text="Name:").grid(row=0, column=2, sticky=tk.W, pady=5, padx=(0, 10))
        self.new_packer_name = ttk.Entry(form_inner, width=30)
        self.new_packer_name.grid(row=0, column=3, sticky=tk.W, pady=5, padx=(0, 20))

        ttk.Button(form_inner, text="Add Packer", command=self._add_packer).grid(row=0, column=4, padx=10)

        # Packers list
        list_frame = ttk.Frame(tab)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        columns = ("code", "name", "active", "created")
        self.packers_tree = ttk.Treeview(list_frame, columns=columns, show="headings")

        self.packers_tree.heading("code", text="Code")
        self.packers_tree.heading("name", text="Name")
        self.packers_tree.heading("active", text="Active")
        self.packers_tree.heading("created", text="Created")

        self.packers_tree.column("code", width=100)
        self.packers_tree.column("name", width=200)
        self.packers_tree.column("active", width=100)
        self.packers_tree.column("created", width=150)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.packers_tree.yview)
        self.packers_tree.configure(yscrollcommand=scrollbar.set)

        self.packers_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = ttk.Frame(tab)
        btn_frame.pack(pady=(0, 15))
        ttk.Button(btn_frame, text="Toggle Active", command=self._toggle_packer).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Delete Selected", command=self._delete_packer).pack(side=tk.LEFT, padx=5)

    def _add_packer(self):
        """Add a new packer"""
        code = self.new_packer_code.get().strip()
        name = self.new_packer_name.get().strip()

        if not code or not name:
            messagebox.showwarning("Warning", "Code and Name are required")
            return

        try:
            db.add_packer(code, name)
            self._refresh_packers()
            self.new_packer_code.delete(0, tk.END)
            self.new_packer_name.delete(0, tk.END)
            messagebox.showinfo("Success", "Packer added successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Could not add packer: {e}")

    def _toggle_packer(self):
        """Toggle packer active status"""
        selection = self.packers_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a packer")
            return

        item = self.packers_tree.item(selection[0])
        code = item['values'][0]
        for p in db.get_all_packers(active_only=False):
            if p['code'] == code:
                db.toggle_packer_active(p['id'])
                break
        self._refresh_packers()

    def _delete_packer(self):
        """Delete selected packer"""
        selection = self.packers_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a packer to delete")
            return

        if messagebox.askyesno("Confirm", "Are you sure you want to delete this packer?"):
            item = self.packers_tree.item(selection[0])
            code = item['values'][0]
            for p in db.get_all_packers(active_only=False):
                if p['code'] == code:
                    db.delete_packer(p['id'])
                    break
            self._refresh_packers()

    def _refresh_packers(self):
        """Refresh packers list"""
        self.packers_tree.delete(*self.packers_tree.get_children())
        for p in db.get_all_packers(active_only=False):
            self.packers_tree.insert("", tk.END, values=(
                p['code'], p['name'], "Yes" if p['active'] else "No", p['created_at']
            ))
        self._refresh_combos()

    # ==================== HISTORY TAB ====================

    def _create_history_tab(self):
        """Create history and statistics tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="  History  ")

        # Statistics frame
        stats_frame = ttk.LabelFrame(tab, text="Today's Statistics", padding=15)
        stats_frame.pack(fill=tk.X, padx=15, pady=15)

        self.stats_label = ttk.Label(stats_frame, text="Loading...", style="Header.TLabel")
        self.stats_label.pack(anchor=tk.W)

        # History list
        list_frame = ttk.Frame(tab)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        columns = ("barcode", "product", "location", "packer", "qty", "created")
        self.history_tree = ttk.Treeview(list_frame, columns=columns, show="headings")

        self.history_tree.heading("barcode", text="Barcode Data")
        self.history_tree.heading("product", text="Product")
        self.history_tree.heading("location", text="Location")
        self.history_tree.heading("packer", text="Packer")
        self.history_tree.heading("qty", text="Qty")
        self.history_tree.heading("created", text="Created")

        self.history_tree.column("barcode", width=220)
        self.history_tree.column("product", width=150)
        self.history_tree.column("location", width=150)
        self.history_tree.column("packer", width=100)
        self.history_tree.column("qty", width=50)
        self.history_tree.column("created", width=150)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)

        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Button(tab, text="Refresh", command=self._refresh_history).pack(pady=(0, 15))

    def _refresh_history(self):
        """Refresh history and statistics"""
        # Update statistics
        stats = db.get_daily_stats()
        if stats:
            stats_text = "Today: " + " | ".join(
                [f"{s['packer_name']}: {int(s['total_items'])} items" for s in stats]
            )
        else:
            stats_text = "No labels printed today"
        self.stats_label.config(text=stats_text)

        # Update history list
        self.history_tree.delete(*self.history_tree.get_children())
        for h in db.get_barcode_history():
            self.history_tree.insert("", tk.END, values=(
                h['barcode_data'],
                h['product_name'] or "Unknown",
                h['location_name'] or "Unknown",
                h['packer_name'] or "Unknown",
                h['quantity'],
                h['created_at']
            ))

    # ==================== UTILITY METHODS ====================

    def _refresh_combos(self):
        """Refresh all combo boxes"""
        # Products
        products = db.get_all_products()
        product_values = [f"{p['code']} - {p['name']}" for p in products]
        self.product_combo['values'] = product_values

        # Locations
        locations = db.get_all_locations()
        location_values = [f"{l['code']} - {l['name']}" for l in locations]
        self.location_combo['values'] = location_values

        # Packers (active only)
        packers = db.get_all_packers(active_only=True)
        packer_values = [f"{p['code']} - {p['name']}" for p in packers]
        self.packer_combo['values'] = packer_values

    def _refresh_all_data(self):
        """Refresh all data in the application"""
        self._refresh_products()
        self._refresh_locations()
        self._refresh_packers()
        self._refresh_history()

    def _export_history(self):
        """Export history to CSV"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV File", "*.csv"), ("All files", "*.*")]
        )

        if filename:
            history = db.get_barcode_history(limit=10000)
            with open(filename, 'w') as f:
                f.write("Barcode,Product,Location,Packer,Quantity,Created\n")
                for h in history:
                    f.write(f"{h['barcode_data']},{h['product_name']},{h['location_name']},"
                            f"{h['packer_name']},{h['quantity']},{h['created_at']}\n")
            messagebox.showinfo("Success", f"History exported to {filename}")

    def _show_printer_setup(self):
        """Show printer setup dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Printer Setup")
        dialog.geometry("550x450")
        dialog.transient(self.root)
        dialog.configure(bg=ModernStyle.BG_SECONDARY)

        # Content frame
        content = ttk.Frame(dialog, padding=20)
        content.pack(fill=tk.BOTH, expand=True)

        ttk.Label(content, text="Printer Configuration", style="Title.TLabel").pack(anchor=tk.W, pady=(0, 20))

        # Available printers
        ttk.Label(content, text="Available Printers:", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 10))

        printers = TSCPrinter.list_printers()
        if printers:
            for p in printers:
                if 'TSC' in p.upper():
                    ttk.Label(content, text=f"  * {p}", style="Success.TLabel").pack(anchor=tk.W)
                else:
                    ttk.Label(content, text=f"  - {p}", style="Subtitle.TLabel").pack(anchor=tk.W)
        else:
            ttk.Label(content, text="  No printers found", style="Accent.TLabel").pack(anchor=tk.W)

        # Detected TSC printer
        detected = self.printer.find_tsc_printer()
        ttk.Label(content, text=f"\nDetected TSC Printer:", style="Header.TLabel").pack(anchor=tk.W, pady=(15, 5))
        ttk.Label(content, text=f"  {detected or 'None'}", style="Success.TLabel" if detected else "Subtitle.TLabel").pack(anchor=tk.W)

        # Current settings
        ttk.Label(content, text="\nCurrent Settings:", style="Header.TLabel").pack(anchor=tk.W, pady=(15, 5))
        ttk.Label(content, text=f"  Configured Name: {self.printer.printer_name}").pack(anchor=tk.W)
        ttk.Label(content, text=f"  Port: {self.printer.port}").pack(anchor=tk.W)
        ttk.Label(content, text=f"  Label Size: {self.printer.width/8}mm x {self.printer.height/8}mm").pack(anchor=tk.W)

        # Test buttons
        btn_frame = ttk.Frame(content)
        btn_frame.pack(pady=25)

        def test_connection():
            success, msg = self.printer.test_connection()
            if success:
                messagebox.showinfo("Connection Test", msg)
            else:
                messagebox.showerror("Connection Test", msg)

        def test_print():
            success, msg = self.printer.print_label(
                "TEST-001", "Test Product", "Test Location", "Test Packer"
            )
            if success:
                messagebox.showinfo("Test Print", f"Test label sent!\n\n{msg}")
            else:
                messagebox.showerror("Test Print Failed", msg)

        ttk.Button(btn_frame, text="Test Connection", command=test_connection).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Print Test Label", command=test_print).pack(side=tk.LEFT, padx=5)

        ttk.Label(content, text="Edit config.py to change printer settings", style="Subtitle.TLabel").pack(pady=(10, 0))

        ttk.Button(content, text="Close", command=dialog.destroy).pack(pady=15)

    def _show_about(self):
        """Show about dialog"""
        messagebox.showinfo(
            "About",
            "Barcode Generator Pro\n\n"
            "Version 2.0\n\n"
            "Features:\n"
            "- Generate Code128 and QR barcodes\n"
            "- Automatic carton packing & tracking\n"
            "- Scan carton to view contents\n"
            "- Print directly to TSC TE200\n"
            "- Track printing history"
        )


def main():
    """Main entry point"""
    root = tk.Tk()
    app = BarcodeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
