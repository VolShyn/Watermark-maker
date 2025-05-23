import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import pandas as pd
import threading

# import functions from url.py
try:
    # when running from the same directory
    from fetch import download_image, add_border_and_watermark, ensure_dir, load_code_image_urls
except ImportError:
    # when running as a package
    from .fetch import download_image, add_border_and_watermark, ensure_dir, load_code_image_urls


EXCEL_PATH = 'export-products-17-05-25_21-55-25.xlsx'
SHEET_NAME = 'Export Products Sheet'
DOWNLOAD_DIR = 'downloaded_images'
OUTPUT_DIR = 'watermarked_images'

class ImageProcessorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Prikolchik")
        self.root.geometry("600x400")
        self.root.resizable(True, True)

        self.excel_path = tk.StringVar()
        self.sheet_name = tk.StringVar()
        self.image_column = tk.StringVar(value="Ссылка_изображения")  # default
        self.code_column = tk.StringVar(value="Код_товара")  # default

        self.available_sheets = []
        self.available_columns = []

        self.create_widgets()

        ensure_dir(DOWNLOAD_DIR)
        ensure_dir(OUTPUT_DIR)

    def create_widgets(self):
        # excel file selection
        frame1 = ttk.LabelFrame(self.root, text="Excel File Selection")
        frame1.pack(fill="x", padx=10, pady=10, ipady=5)

        ttk.Label(frame1, text="Excel File:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(frame1, textvariable=self.excel_path, width=50).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(frame1, text="Browse...", command=self.browse_excel).grid(row=0, column=2, padx=5, pady=5)

        # sheet selection
        frame2 = ttk.LabelFrame(self.root, text="Sheet and Column Selection")
        frame2.pack(fill="x", padx=10, pady=10, ipady=5)

        ttk.Label(frame2, text="Sheet:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.sheet_combobox = ttk.Combobox(frame2, textvariable=self.sheet_name, state="readonly")
        self.sheet_combobox.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        self.sheet_combobox.bind("<<ComboboxSelected>>", self.update_columns)

        ttk.Label(frame2, text="Image URL Column:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.column_combobox = ttk.Combobox(frame2, textvariable=self.image_column, state="readonly")
        self.column_combobox.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        ttk.Label(frame2, text="Code Column:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.code_combobox = ttk.Combobox(frame2, textvariable=self.code_column, state="readonly")
        self.code_combobox.grid(row=2, column=1, sticky="ew", padx=5, pady=5)

        # action buttons
        frame3 = ttk.Frame(self.root)
        frame3.pack(fill="x", padx=10, pady=20)

        ttk.Button(
            frame3,
            text="Download Images",
            command=self.download_images
        ).pack(side="left", padx=10)

        ttk.Button(
            frame3,
            text="Add Watermarks",
            command=self.add_watermarks
        ).pack(side="right", padx=10)

        # status area
        frame4 = ttk.LabelFrame(self.root, text="Status")
        frame4.pack(fill="both", expand=True, padx=10, pady=10)

        self.status_text = tk.Text(frame4, height=10, wrap="word")
        self.status_text.pack(fill="both", expand=True, padx=5, pady=5)

        # adding a scrollbar to the status text
        scrollbar = ttk.Scrollbar(self.status_text, command=self.status_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.status_text.config(yscrollcommand=scrollbar.set)

        # status text read-only
        self.status_text.config(state="disabled")

    def browse_excel(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        if filepath:
            self.excel_path.set(filepath)
            self.load_sheets()

    def load_sheets(self):
        try:
            self.status_update(f"Loading sheets from {self.excel_path.get()}...")
            excel_file = pd.ExcelFile(self.excel_path.get())
            self.available_sheets = excel_file.sheet_names
            self.sheet_combobox["values"] = self.available_sheets

            if self.available_sheets:
                self.sheet_name.set(self.available_sheets[0])
                self.update_columns()

            self.status_update(f"Loaded {len(self.available_sheets)} sheets.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load Excel file: {e}")
            self.status_update(f"Error: {e}")

    def update_columns(self, event=None):
        try:
            if not self.excel_path.get() or not self.sheet_name.get():
                return

            self.status_update(f"Loading columns from sheet '{self.sheet_name.get()}'...")
            df = pd.read_excel(self.excel_path.get(), sheet_name=self.sheet_name.get())
            self.available_columns = df.columns.tolist()
            self.column_combobox["values"] = self.available_columns
            self.code_combobox["values"] = self.available_columns

            # trying to select the default image/code column or the first column
            if "Ссылка_изображения" in self.available_columns:
                self.image_column.set("Ссылка_изображения")
            elif self.available_columns:
                self.image_column.set(self.available_columns[0])

            if "Код_товара" in self.available_columns:
                self.code_column.set("Код_товара")
            elif self.available_columns:
                self.code_column.set(self.available_columns[0])

            self.status_update(f"Loaded {len(self.available_columns)} columns")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load columns: {e}")
            self.status_update(f"Error: {e}")

    def download_images(self):
        if not self._validate_inputs():
            return

        # start downloading in a separate thread
        threading.Thread(target=self._download_images_thread, daemon=True).start()

    def _download_images_thread(self):
        self.status_update("Starting download process...")
        try:
            # load (code, image_urls) tuples
            code_image_tuples = load_code_image_urls(
                self.excel_path.get(),
                self.sheet_name.get(),
                self.code_column.get(),
                self.image_column.get()
            )

            self.status_update(f"Found {len(code_image_tuples)} rows to process.")

            total_images = 0
            for i, (code, image_urls) in enumerate(code_image_tuples):
                # Split image_urls by comma if multiple URLs in one cell
                url_list = [u.strip() for u in str(image_urls).split(",") if u.strip()]
                code_dir = os.path.join(DOWNLOAD_DIR, str(code))
                ensure_dir(code_dir)
                for url in url_list:
                    self.status_update(f"Downloading for code {code}: {url}")
                    fname = download_image(url, code_dir)
                    if not fname:
                        self.status_update(f"✗ Failed to download {url}")
                    else:
                        self.status_update(f"✓ Downloaded {fname} to {code_dir}")
                    total_images += 1

            self.status_update(f"Download process completed. Total images attempted: {total_images}")
            messagebox.showinfo("Success", "All images are downloaded")
        except Exception as e:
            self.status_update(f"Error during download: {e}")
            messagebox.showerror("Error", f"Failed to download images: {e}")

    def add_watermarks(self):
        # starting watermarking in a separate thread
        threading.Thread(target=self._add_watermarks_thread, daemon=True).start()

    def _add_watermarks_thread(self):
        self.status_update("Starting watermarking process...")
        try:
            # traverse all code-named folders in downloaded_images
            total_images = 0
            processed_images = 0
            if not os.path.exists(DOWNLOAD_DIR):
                self.status_update("No download directory found")
                messagebox.showinfo("No Images", "No images found to watermark")
                return

            code_folders = [d for d in os.listdir(DOWNLOAD_DIR) if os.path.isdir(os.path.join(DOWNLOAD_DIR, d))]
            if not code_folders:
                self.status_update("no code column folders found in download directory")
                messagebox.showinfo("No Images", "No images found to watermark")
                return

            for code in code_folders:
                code_dir = os.path.join(DOWNLOAD_DIR, code)
                output_code_dir = os.path.join(OUTPUT_DIR, code)
                ensure_dir(output_code_dir)
                images = [f for f in os.listdir(code_dir) if os.path.isfile(os.path.join(code_dir, f))]
                total_images += len(images)
                for i, fname in enumerate(images):
                    src = os.path.join(code_dir, fname)
                    dst = os.path.join(output_code_dir, fname)
                    self.status_update(f"Watermarking [{code}] {fname} ({processed_images+1}/{total_images})")
                    try:
                        add_border_and_watermark(src, dst)
                        self.status_update(f"✓ {fname} saved to {output_code_dir}")
                    except Exception as e:
                        self.status_update(f"✗ {fname}: {e}")
                    processed_images += 1

            self.status_update("Watermarking process is done")
            messagebox.showinfo("Success", "All images watermarked")
        except Exception as e:
            self.status_update(f"Error during watermarking: {e}")
            messagebox.showerror("Error", f"Failed to watermark images: {e}")

    def _validate_inputs(self):
        if not self.excel_path.get():
            messagebox.showerror("Error", "Please select an excel file")
            return False

        if not self.sheet_name.get():
            messagebox.showerror("Error", "Please select a sheet")
            return False

        if not self.image_column.get():
            messagebox.showerror("Error", "Please select an image url column")
            return False

        return True

    def status_update(self, message):
        self.status_text.config(state="normal")
        self.status_text.insert("end", message + "\n")
        self.status_text.see("end")
        self.status_text.config(state="disabled")
        self.root.update_idletasks()


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageProcessorApp(root)
    root.mainloop()
