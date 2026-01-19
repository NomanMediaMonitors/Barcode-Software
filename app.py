import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from PIL import Image, ImageTk
import os

import database as db
from barcode_generator import BarcodeGenerator
from printer import TSCPrinter, print_barcode_label
from config import SHORT_DATE_FORMAT


class BarcodeApp:
    """Main application window"""

    def __init__(self, root):
        self.root = root
        self.root.title("Barcode Generator - TSC TE200")
        self.root.geometry("1000x700")
        self.root.minsize(900, 600)

        # Initialize components
        self.barcode_gen = BarcodeGenerator()
        self.printer = TSCPrinter()
        self.current_label_image = None

        # Create main UI
        self._create_menu()
        self._create_notebook()
        self._setup_styles()

        # Load initial data
        self._refresh_all_data()

    def _setup_styles(self):
        style = ttk.Style()
        style.configure("Title.TLabel", font=("Helvetica", 14, "bold"))
        style.configure("Header.TLabel", font=("Helvetica", 11, "bold"))

    def _create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export History", command=self._export_history)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Printer Setup", command=self._show_printer_setup)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)

    def _create_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create tabs
        self._create_generate_tab()
        self._create_carton_packing_tab()
        self._create_carton_lookup_tab()
        self._create_products_tab()
        self._create_locations_tab()
        self._create_packers_tab()
        self._create_history_tab()

        # Current carton being packed
        self.current_carton = None

    # ==================== GENERATE TAB ====================

    def _create_generate_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Generate Barcode")

        # Left panel - Form
        left_frame = ttk.LabelFrame(tab, text="Label Information", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Product selection
        ttk.Label(left_frame, text="Product:", style="Header.TLabel").grid(
            row=0, column=0, sticky=tk.W, pady=5
        )
        self.product_var = tk.StringVar()
        self.product_combo = ttk.Combobox(
            left_frame, textvariable=self.product_var, state="readonly", width=30
        )
        self.product_combo.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)

        # Location selection
        ttk.Label(left_frame, text="Destination:", style="Header.TLabel").grid(
            row=1, column=0, sticky=tk.W, pady=5
        )
        self.location_var = tk.StringVar()
        self.location_combo = ttk.Combobox(
            left_frame, textvariable=self.location_var, state="readonly", width=30
        )
        self.location_combo.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)

        # Packer selection
        ttk.Label(left_frame, text="Packer:", style="Header.TLabel").grid(
            row=2, column=0, sticky=tk.W, pady=5
        )
        self.packer_var = tk.StringVar()
        self.packer_combo = ttk.Combobox(
            left_frame, textvariable=self.packer_var, state="readonly", width=30
        )
        self.packer_combo.grid(row=2, column=1, sticky=tk.W, pady=5, padx=5)

        # Barcode type
        ttk.Label(left_frame, text="Barcode Type:", style="Header.TLabel").grid(
            row=3, column=0, sticky=tk.W, pady=5
        )
        self.barcode_type_var = tk.StringVar(value="code128")
        barcode_frame = ttk.Frame(left_frame)
        barcode_frame.grid(row=3, column=1, sticky=tk.W, pady=5, padx=5)
        ttk.Radiobutton(
            barcode_frame, text="Code 128", variable=self.barcode_type_var, value="code128"
        ).pack(side=tk.LEFT)
        ttk.Radiobutton(
            barcode_frame, text="QR Code", variable=self.barcode_type_var, value="qrcode"
        ).pack(side=tk.LEFT, padx=10)

        # Quantity
        ttk.Label(left_frame, text="Quantity:", style="Header.TLabel").grid(
            row=4, column=0, sticky=tk.W, pady=5
        )
        self.quantity_var = tk.StringVar(value="1")
        quantity_spin = ttk.Spinbox(
            left_frame, from_=1, to=100, textvariable=self.quantity_var, width=10
        )
        quantity_spin.grid(row=4, column=1, sticky=tk.W, pady=5, padx=5)

        # Buttons
        btn_frame = ttk.Frame(left_frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=20)

        ttk.Button(
            btn_frame, text="Preview Label", command=self._preview_label
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame, text="Print Label", command=self._print_label
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame, text="Save as Image", command=self._save_label_image
        ).pack(side=tk.LEFT, padx=5)

        # Right panel - Preview
        right_frame = ttk.LabelFrame(tab, text="Label Preview", padding=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.preview_canvas = tk.Canvas(right_frame, bg="white", width=400, height=300)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)

        # Barcode data display
        self.barcode_data_var = tk.StringVar(value="Select options and click Preview")
        ttk.Label(
            right_frame, textvariable=self.barcode_data_var, font=("Courier", 10)
        ).pack(pady=10)

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
        self.barcode_data_var.set(f"Barcode: {barcode_data}")

    def _display_preview(self, image: Image.Image):
        # Resize to fit canvas
        canvas_width = self.preview_canvas.winfo_width() or 400
        canvas_height = self.preview_canvas.winfo_height() or 300

        ratio = min(canvas_width / image.width, canvas_height / image.height)
        new_size = (int(image.width * ratio * 0.9), int(image.height * ratio * 0.9))

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
            messagebox.showinfo("Success", f"Printed {quantity} label(s)\n\n{message}")
            self._refresh_history()
        else:
            # Show error and offer to save TSPL file instead
            if messagebox.askyesno(
                "Print Failed",
                f"{message}\n\nWould you like to save as a .prn file instead?\n"
                "(You can print it manually by copying to your printer)"
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
            messagebox.showinfo(
                "Success",
                f"File saved to:\n{saved_path}\n\n"
                "To print manually, open Command Prompt and run:\n"
                f'copy /b "{saved_path}" "\\\\%COMPUTERNAME%\\YourPrinterName"'
            )

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

    # ==================== CARTON PACKING TAB ====================

    def _create_carton_packing_tab(self):
        """Create carton packing tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Carton Packing")

        # Main container with two panels
        main_paned = ttk.PanedWindow(tab, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel - Carton Control
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=1)

        # Create new carton section
        create_frame = ttk.LabelFrame(left_frame, text="Create New Carton", padding=10)
        create_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(create_frame, text="Destination:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.carton_location_var = tk.StringVar()
        self.carton_location_combo = ttk.Combobox(
            create_frame, textvariable=self.carton_location_var, state="readonly", width=30
        )
        self.carton_location_combo.grid(row=0, column=1, sticky=tk.W, pady=2, padx=5)

        ttk.Label(create_frame, text="Packer:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.carton_packer_var = tk.StringVar()
        self.carton_packer_combo = ttk.Combobox(
            create_frame, textvariable=self.carton_packer_var, state="readonly", width=30
        )
        self.carton_packer_combo.grid(row=1, column=1, sticky=tk.W, pady=2, padx=5)

        ttk.Label(create_frame, text="Notes:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.carton_notes_entry = ttk.Entry(create_frame, width=33)
        self.carton_notes_entry.grid(row=2, column=1, sticky=tk.W, pady=2, padx=5)

        ttk.Button(create_frame, text="Create Carton", command=self._create_carton).grid(
            row=3, column=0, columnspan=2, pady=10
        )

        # Current carton info
        current_frame = ttk.LabelFrame(left_frame, text="Current Carton", padding=10)
        current_frame.pack(fill=tk.X, padx=5, pady=5)

        self.current_carton_label = ttk.Label(
            current_frame, text="No carton active", font=("Helvetica", 11, "bold")
        )
        self.current_carton_label.pack(pady=5)

        self.current_carton_info = ttk.Label(current_frame, text="")
        self.current_carton_info.pack(pady=2)

        self.current_carton_count = ttk.Label(current_frame, text="Items: 0")
        self.current_carton_count.pack(pady=2)

        carton_btn_frame = ttk.Frame(current_frame)
        carton_btn_frame.pack(pady=10)

        ttk.Button(carton_btn_frame, text="Print Carton Label", command=self._print_carton_label).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(carton_btn_frame, text="Close Carton", command=self._close_carton).pack(
            side=tk.LEFT, padx=5
        )

        # Add product section
        add_frame = ttk.LabelFrame(left_frame, text="Add Product to Carton", padding=10)
        add_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(add_frame, text="Product:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.carton_product_var = tk.StringVar()
        self.carton_product_combo = ttk.Combobox(
            add_frame, textvariable=self.carton_product_var, state="readonly", width=30
        )
        self.carton_product_combo.grid(row=0, column=1, sticky=tk.W, pady=2, padx=5)

        ttk.Label(add_frame, text="Quantity:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.carton_qty_var = tk.StringVar(value="1")
        ttk.Spinbox(add_frame, from_=1, to=100, textvariable=self.carton_qty_var, width=10).grid(
            row=1, column=1, sticky=tk.W, pady=2, padx=5
        )

        ttk.Label(add_frame, text="Product Barcode:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.product_barcode_entry = ttk.Entry(add_frame, width=33)
        self.product_barcode_entry.grid(row=2, column=1, sticky=tk.W, pady=2, padx=5)
        self.product_barcode_entry.bind('<Return>', lambda e: self._add_product_to_carton())

        ttk.Button(add_frame, text="Add to Carton", command=self._add_product_to_carton).grid(
            row=3, column=0, columnspan=2, pady=10
        )

        # Right panel - Carton Contents
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=2)

        contents_frame = ttk.LabelFrame(right_frame, text="Carton Contents", padding=10)
        contents_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ("product_code", "product_name", "quantity", "barcode", "added")
        self.contents_tree = ttk.Treeview(contents_frame, columns=columns, show="headings")

        self.contents_tree.heading("product_code", text="Code")
        self.contents_tree.heading("product_name", text="Product")
        self.contents_tree.heading("quantity", text="Qty")
        self.contents_tree.heading("barcode", text="Product Barcode")
        self.contents_tree.heading("added", text="Added")

        self.contents_tree.column("product_code", width=80)
        self.contents_tree.column("product_name", width=150)
        self.contents_tree.column("quantity", width=50)
        self.contents_tree.column("barcode", width=150)
        self.contents_tree.column("added", width=130)

        scrollbar = ttk.Scrollbar(contents_frame, orient=tk.VERTICAL, command=self.contents_tree.yview)
        self.contents_tree.configure(yscrollcommand=scrollbar.set)

        self.contents_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Button(right_frame, text="Remove Selected", command=self._remove_from_carton).pack(pady=5)

        # Open cartons list
        open_frame = ttk.LabelFrame(right_frame, text="Open Cartons", padding=10)
        open_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ("barcode", "location", "packer", "items", "created")
        self.open_cartons_tree = ttk.Treeview(open_frame, columns=columns, show="headings", height=5)

        self.open_cartons_tree.heading("barcode", text="Carton Barcode")
        self.open_cartons_tree.heading("location", text="Destination")
        self.open_cartons_tree.heading("packer", text="Packer")
        self.open_cartons_tree.heading("items", text="Items")
        self.open_cartons_tree.heading("created", text="Created")

        self.open_cartons_tree.column("barcode", width=180)
        self.open_cartons_tree.column("location", width=120)
        self.open_cartons_tree.column("packer", width=100)
        self.open_cartons_tree.column("items", width=50)
        self.open_cartons_tree.column("created", width=130)

        self.open_cartons_tree.pack(fill=tk.BOTH, expand=True)
        self.open_cartons_tree.bind('<Double-1>', self._select_open_carton)

        ttk.Button(open_frame, text="Select Carton", command=self._select_open_carton).pack(pady=5)

    def _create_carton(self):
        """Create a new carton"""
        if not self.carton_location_var.get():
            messagebox.showwarning("Warning", "Please select a destination")
            return
        if not self.carton_packer_var.get():
            messagebox.showwarning("Warning", "Please select a packer")
            return

        # Get location and packer IDs
        location = self._get_selected_carton_location()
        packer = self._get_selected_carton_packer()

        if not location or not packer:
            messagebox.showerror("Error", "Could not get location or packer details")
            return

        notes = self.carton_notes_entry.get().strip()

        try:
            carton_id, barcode = db.create_carton(location['id'], packer['id'], notes)
            self.current_carton = db.get_carton_by_id(carton_id)
            self._update_current_carton_display()
            self._refresh_open_cartons()
            self.carton_notes_entry.delete(0, tk.END)
            messagebox.showinfo("Success", f"Carton created!\n\nBarcode: {barcode}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not create carton: {e}")

    def _update_current_carton_display(self):
        """Update the current carton display"""
        if self.current_carton:
            self.current_carton_label.config(
                text=f"Barcode: {self.current_carton['barcode']}"
            )
            self.current_carton_info.config(
                text=f"Destination: {self.current_carton['location_name']} | "
                     f"Packer: {self.current_carton['packer_name']}"
            )
            # Get item count
            contents = db.get_carton_contents(self.current_carton['id'])
            total_qty = sum(c['quantity'] for c in contents)
            self.current_carton_count.config(text=f"Items: {len(contents)} entries, {total_qty} total quantity")
            self._refresh_carton_contents()
        else:
            self.current_carton_label.config(text="No carton active")
            self.current_carton_info.config(text="")
            self.current_carton_count.config(text="Items: 0")
            self.contents_tree.delete(*self.contents_tree.get_children())

    def _add_product_to_carton(self):
        """Add a product to the current carton"""
        if not self.current_carton:
            messagebox.showwarning("Warning", "Please create or select a carton first")
            return

        if self.current_carton['status'] == 'closed':
            messagebox.showwarning("Warning", "This carton is closed. Cannot add products.")
            return

        if not self.carton_product_var.get():
            messagebox.showwarning("Warning", "Please select a product")
            return

        product = self._get_selected_carton_product()
        if not product:
            messagebox.showerror("Error", "Could not get product details")
            return

        quantity = int(self.carton_qty_var.get())
        product_barcode = self.product_barcode_entry.get().strip() or None

        try:
            db.add_product_to_carton(
                self.current_carton['id'],
                product['id'],
                quantity,
                product_barcode
            )
            self._update_current_carton_display()
            self.product_barcode_entry.delete(0, tk.END)
            self._refresh_open_cartons()
        except Exception as e:
            messagebox.showerror("Error", f"Could not add product: {e}")

    def _remove_from_carton(self):
        """Remove selected item from carton"""
        if not self.current_carton:
            return

        selection = self.contents_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an item to remove")
            return

        if messagebox.askyesno("Confirm", "Remove this item from the carton?"):
            item = self.contents_tree.item(selection[0])
            content_id = item['tags'][0] if item['tags'] else None
            if content_id:
                db.remove_product_from_carton(int(content_id))
                self._update_current_carton_display()
                self._refresh_open_cartons()

    def _refresh_carton_contents(self):
        """Refresh carton contents display"""
        self.contents_tree.delete(*self.contents_tree.get_children())
        if self.current_carton:
            contents = db.get_carton_contents(self.current_carton['id'])
            for c in contents:
                self.contents_tree.insert("", tk.END, values=(
                    c['product_code'],
                    c['product_name'],
                    c['quantity'],
                    c['product_barcode'] or "",
                    c['added_at']
                ), tags=(str(c['id']),))

    def _print_carton_label(self):
        """Print label for current carton"""
        if not self.current_carton:
            messagebox.showwarning("Warning", "No carton selected")
            return

        # Get carton summary
        summary = db.get_carton_summary(self.current_carton['id'])
        summary_text = ", ".join([f"{s['product_code']}x{s['total_quantity']}" for s in summary])

        # Generate carton label
        label_img = self.barcode_gen.create_label(
            self.current_carton['barcode'],
            f"CARTON: {summary_text[:30]}",
            self.current_carton['location_name'],
            self.current_carton['packer_name'],
            "qrcode"  # Use QR for cartons for more data
        )

        # Try to print
        success, message = self.printer.print_label(
            self.current_carton['barcode'],
            f"CARTON",
            self.current_carton['location_name'],
            self.current_carton['packer_name'],
            True,  # Use QR code
            1
        )

        if success:
            messagebox.showinfo("Success", f"Carton label printed!\n\n{message}")
        else:
            messagebox.showerror("Print Failed", message)

    def _close_carton(self):
        """Close the current carton"""
        if not self.current_carton:
            messagebox.showwarning("Warning", "No carton selected")
            return

        contents = db.get_carton_contents(self.current_carton['id'])
        if not contents:
            if not messagebox.askyesno("Warning", "This carton is empty. Close anyway?"):
                return

        if messagebox.askyesno("Confirm", f"Close carton {self.current_carton['barcode']}?\n\n"
                                          "This will seal the carton."):
            db.close_carton(self.current_carton['id'])
            messagebox.showinfo("Success", "Carton closed!")
            self.current_carton = None
            self._update_current_carton_display()
            self._refresh_open_cartons()

    def _refresh_open_cartons(self):
        """Refresh list of open cartons"""
        self.open_cartons_tree.delete(*self.open_cartons_tree.get_children())
        cartons = db.get_open_cartons()
        for c in cartons:
            self.open_cartons_tree.insert("", tk.END, values=(
                c['barcode'],
                c['location_name'] or "",
                c['packer_name'] or "",
                c['total_quantity'] or 0,
                c['created_at']
            ), tags=(str(c['id']),))

    def _select_open_carton(self, event=None):
        """Select an open carton to work with"""
        selection = self.open_cartons_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a carton")
            return

        item = self.open_cartons_tree.item(selection[0])
        carton_id = item['tags'][0] if item['tags'] else None
        if carton_id:
            self.current_carton = db.get_carton_by_id(int(carton_id))
            self._update_current_carton_display()

    def _get_selected_carton_location(self):
        """Get selected location for carton"""
        selection = self.carton_location_var.get()
        if selection:
            code = selection.split(" - ")[0]
            for l in db.get_all_locations():
                if l['code'] == code:
                    return dict(l)
        return None

    def _get_selected_carton_packer(self):
        """Get selected packer for carton"""
        selection = self.carton_packer_var.get()
        if selection:
            code = selection.split(" - ")[0]
            for p in db.get_all_packers():
                if p['code'] == code:
                    return dict(p)
        return None

    def _get_selected_carton_product(self):
        """Get selected product for carton"""
        selection = self.carton_product_var.get()
        if selection:
            code = selection.split(" - ")[0]
            for p in db.get_all_products():
                if p['code'] == code:
                    return dict(p)
        return None

    # ==================== CARTON LOOKUP TAB ====================

    def _create_carton_lookup_tab(self):
        """Create carton lookup tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Carton Lookup")

        # Search section
        search_frame = ttk.LabelFrame(tab, text="Scan/Enter Carton Barcode", padding=10)
        search_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(search_frame, text="Carton Barcode:", style="Header.TLabel").pack(side=tk.LEFT, padx=5)
        self.lookup_barcode_var = tk.StringVar()
        self.lookup_entry = ttk.Entry(search_frame, textvariable=self.lookup_barcode_var, width=40)
        self.lookup_entry.pack(side=tk.LEFT, padx=5)
        self.lookup_entry.bind('<Return>', lambda e: self._lookup_carton())

        ttk.Button(search_frame, text="Lookup", command=self._lookup_carton).pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="Clear", command=self._clear_lookup).pack(side=tk.LEFT, padx=5)

        # Results section
        results_frame = ttk.Frame(tab)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Carton info
        info_frame = ttk.LabelFrame(results_frame, text="Carton Information", padding=10)
        info_frame.pack(fill=tk.X, pady=5)

        self.lookup_info_text = tk.Text(info_frame, height=6, state=tk.DISABLED, wrap=tk.WORD)
        self.lookup_info_text.pack(fill=tk.X)

        # Contents summary
        summary_frame = ttk.LabelFrame(results_frame, text="Contents Summary", padding=10)
        summary_frame.pack(fill=tk.X, pady=5)

        columns = ("product_code", "product_name", "total_quantity")
        self.summary_tree = ttk.Treeview(summary_frame, columns=columns, show="headings", height=5)

        self.summary_tree.heading("product_code", text="Product Code")
        self.summary_tree.heading("product_name", text="Product Name")
        self.summary_tree.heading("total_quantity", text="Total Quantity")

        self.summary_tree.column("product_code", width=150)
        self.summary_tree.column("product_name", width=300)
        self.summary_tree.column("total_quantity", width=100)

        self.summary_tree.pack(fill=tk.X)

        # Detailed contents
        detail_frame = ttk.LabelFrame(results_frame, text="Detailed Contents", padding=10)
        detail_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        columns = ("product_code", "product_name", "quantity", "barcode", "added")
        self.detail_tree = ttk.Treeview(detail_frame, columns=columns, show="headings")

        self.detail_tree.heading("product_code", text="Code")
        self.detail_tree.heading("product_name", text="Product")
        self.detail_tree.heading("quantity", text="Qty")
        self.detail_tree.heading("barcode", text="Product Barcode")
        self.detail_tree.heading("added", text="Added")

        self.detail_tree.column("product_code", width=100)
        self.detail_tree.column("product_name", width=200)
        self.detail_tree.column("quantity", width=50)
        self.detail_tree.column("barcode", width=180)
        self.detail_tree.column("added", width=150)

        scrollbar = ttk.Scrollbar(detail_frame, orient=tk.VERTICAL, command=self.detail_tree.yview)
        self.detail_tree.configure(yscrollcommand=scrollbar.set)

        self.detail_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _lookup_carton(self):
        """Look up carton by barcode"""
        barcode = self.lookup_barcode_var.get().strip()
        if not barcode:
            messagebox.showwarning("Warning", "Please enter a carton barcode")
            return

        carton = db.lookup_carton_by_barcode(barcode)

        if not carton:
            messagebox.showwarning("Not Found", f"No carton found with barcode: {barcode}")
            self._clear_lookup()
            return

        # Update info display
        self.lookup_info_text.config(state=tk.NORMAL)
        self.lookup_info_text.delete(1.0, tk.END)

        info = (
            f"Barcode: {carton['barcode']}\n"
            f"Status: {carton['status'].upper()}\n"
            f"Destination: {carton['location_name']} ({carton['location_code']})\n"
            f"Packed by: {carton['packer_name']} ({carton['packer_code']})\n"
            f"Created: {carton['created_at']}\n"
        )
        if carton['closed_at']:
            info += f"Closed: {carton['closed_at']}\n"
        if carton['notes']:
            info += f"Notes: {carton['notes']}\n"

        self.lookup_info_text.insert(tk.END, info)
        self.lookup_info_text.config(state=tk.DISABLED)

        # Update summary
        self.summary_tree.delete(*self.summary_tree.get_children())
        for s in carton['summary']:
            self.summary_tree.insert("", tk.END, values=(
                s['product_code'],
                s['product_name'],
                s['total_quantity']
            ))

        # Update detailed contents
        self.detail_tree.delete(*self.detail_tree.get_children())
        for c in carton['contents']:
            self.detail_tree.insert("", tk.END, values=(
                c['product_code'],
                c['product_name'],
                c['quantity'],
                c['product_barcode'] or "",
                c['added_at']
            ))

    def _clear_lookup(self):
        """Clear lookup results"""
        self.lookup_barcode_var.set("")
        self.lookup_info_text.config(state=tk.NORMAL)
        self.lookup_info_text.delete(1.0, tk.END)
        self.lookup_info_text.config(state=tk.DISABLED)
        self.summary_tree.delete(*self.summary_tree.get_children())
        self.detail_tree.delete(*self.detail_tree.get_children())

    # ==================== PRODUCTS TAB ====================

    def _create_products_tab(self):
        """Create products management tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Products")

        # Add form
        form_frame = ttk.LabelFrame(tab, text="Add New Product", padding=10)
        form_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(form_frame, text="Code:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.new_product_code = ttk.Entry(form_frame, width=15)
        self.new_product_code.grid(row=0, column=1, sticky=tk.W, pady=2, padx=5)

        ttk.Label(form_frame, text="Name:").grid(row=0, column=2, sticky=tk.W, pady=2, padx=10)
        self.new_product_name = ttk.Entry(form_frame, width=30)
        self.new_product_name.grid(row=0, column=3, sticky=tk.W, pady=2, padx=5)

        ttk.Label(form_frame, text="Description:").grid(row=0, column=4, sticky=tk.W, pady=2, padx=10)
        self.new_product_desc = ttk.Entry(form_frame, width=40)
        self.new_product_desc.grid(row=0, column=5, sticky=tk.W, pady=2, padx=5)

        ttk.Button(form_frame, text="Add Product", command=self._add_product).grid(
            row=0, column=6, padx=10
        )

        # Products list
        list_frame = ttk.Frame(tab)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

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
        ttk.Button(tab, text="Delete Selected", command=self._delete_product).pack(pady=5)

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
            # Clear form
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
        self.notebook.add(tab, text="Locations")

        # Add form
        form_frame = ttk.LabelFrame(tab, text="Add New Location", padding=10)
        form_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(form_frame, text="Code:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.new_location_code = ttk.Entry(form_frame, width=15)
        self.new_location_code.grid(row=0, column=1, sticky=tk.W, pady=2, padx=5)

        ttk.Label(form_frame, text="Name:").grid(row=0, column=2, sticky=tk.W, pady=2, padx=10)
        self.new_location_name = ttk.Entry(form_frame, width=30)
        self.new_location_name.grid(row=0, column=3, sticky=tk.W, pady=2, padx=5)

        ttk.Label(form_frame, text="Address:").grid(row=0, column=4, sticky=tk.W, pady=2, padx=10)
        self.new_location_addr = ttk.Entry(form_frame, width=40)
        self.new_location_addr.grid(row=0, column=5, sticky=tk.W, pady=2, padx=5)

        ttk.Button(form_frame, text="Add Location", command=self._add_location).grid(
            row=0, column=6, padx=10
        )

        # Locations list
        list_frame = ttk.Frame(tab)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

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

        ttk.Button(tab, text="Delete Selected", command=self._delete_location).pack(pady=5)

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
        self.notebook.add(tab, text="Packers")

        # Add form
        form_frame = ttk.LabelFrame(tab, text="Add New Packer", padding=10)
        form_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(form_frame, text="Code:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.new_packer_code = ttk.Entry(form_frame, width=15)
        self.new_packer_code.grid(row=0, column=1, sticky=tk.W, pady=2, padx=5)

        ttk.Label(form_frame, text="Name:").grid(row=0, column=2, sticky=tk.W, pady=2, padx=10)
        self.new_packer_name = ttk.Entry(form_frame, width=30)
        self.new_packer_name.grid(row=0, column=3, sticky=tk.W, pady=2, padx=5)

        ttk.Button(form_frame, text="Add Packer", command=self._add_packer).grid(
            row=0, column=4, padx=10
        )

        # Packers list
        list_frame = ttk.Frame(tab)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

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
        btn_frame.pack(pady=5)
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
        self.notebook.add(tab, text="History")

        # Statistics frame
        stats_frame = ttk.LabelFrame(tab, text="Today's Statistics", padding=10)
        stats_frame.pack(fill=tk.X, padx=10, pady=5)

        self.stats_label = ttk.Label(stats_frame, text="Loading...")
        self.stats_label.pack()

        # History list
        list_frame = ttk.Frame(tab)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("barcode", "product", "location", "packer", "qty", "created")
        self.history_tree = ttk.Treeview(list_frame, columns=columns, show="headings")

        self.history_tree.heading("barcode", text="Barcode Data")
        self.history_tree.heading("product", text="Product")
        self.history_tree.heading("location", text="Location")
        self.history_tree.heading("packer", text="Packer")
        self.history_tree.heading("qty", text="Qty")
        self.history_tree.heading("created", text="Created")

        self.history_tree.column("barcode", width=200)
        self.history_tree.column("product", width=150)
        self.history_tree.column("location", width=150)
        self.history_tree.column("packer", width=100)
        self.history_tree.column("qty", width=50)
        self.history_tree.column("created", width=150)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)

        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Button(tab, text="Refresh", command=self._refresh_history).pack(pady=5)

    def _refresh_history(self):
        """Refresh history and statistics"""
        # Update statistics
        stats = db.get_daily_stats()
        if stats:
            stats_text = "Today: " + " | ".join(
                [f"{s['packer_name']}: {s['total_items']} items" for s in stats]
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
        self.carton_product_combo['values'] = product_values

        # Locations
        locations = db.get_all_locations()
        location_values = [f"{l['code']} - {l['name']}" for l in locations]
        self.location_combo['values'] = location_values
        self.carton_location_combo['values'] = location_values

        # Packers (active only)
        packers = db.get_all_packers(active_only=True)
        packer_values = [f"{p['code']} - {p['name']}" for p in packers]
        self.packer_combo['values'] = packer_values
        self.carton_packer_combo['values'] = packer_values

    def _refresh_all_data(self):
        """Refresh all data in the application"""
        self._refresh_products()
        self._refresh_locations()
        self._refresh_packers()
        self._refresh_history()
        self._refresh_open_cartons()

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
        dialog.geometry("500x400")
        dialog.transient(self.root)

        # Available printers
        ttk.Label(dialog, text="Available Printers:", style="Header.TLabel").pack(pady=10)

        printers = TSCPrinter.list_printers()
        if printers:
            for p in printers:
                # Highlight TSC printers
                if 'TSC' in p.upper():
                    ttk.Label(dialog, text=f"  * {p} (TSC Detected)", foreground="green").pack()
                else:
                    ttk.Label(dialog, text=f"  - {p}").pack()
        else:
            ttk.Label(dialog, text="  No printers found", foreground="red").pack()

        # Detected TSC printer
        detected = self.printer.find_tsc_printer()
        ttk.Label(dialog, text=f"\nDetected TSC Printer: {detected}", style="Header.TLabel").pack(pady=5)

        # Current settings
        ttk.Label(dialog, text="\nCurrent Settings:", style="Header.TLabel").pack(pady=5)
        ttk.Label(dialog, text=f"  Configured Name: {self.printer.printer_name}").pack()
        ttk.Label(dialog, text=f"  Port: {self.printer.port}").pack()
        ttk.Label(dialog, text=f"  Label Size: {self.printer.width/8}mm x {self.printer.height/8}mm").pack()

        # Test connection
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

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=15)
        ttk.Button(btn_frame, text="Test Connection", command=test_connection).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Print Test Label", command=test_print).pack(side=tk.LEFT, padx=5)

        ttk.Label(
            dialog, text="\nEdit config.py to change printer settings",
            font=("Helvetica", 9, "italic")
        ).pack(pady=10)

        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)

    def _show_about(self):
        """Show about dialog"""
        messagebox.showinfo(
            "About",
            "Barcode Generator for TSC TE200\n\n"
            "Version 1.1\n\n"
            "Features:\n"
            "- Generate Code128 and QR barcodes\n"
            "- Embed destination, product, and packer info\n"
            "- Print directly to TSC TE200\n"
            "- Track printing history\n"
            "- Carton packing and tracking\n"
            "- Scan carton to view contents"
        )


def main():
    """Main entry point"""
    root = tk.Tk()
    app = BarcodeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
