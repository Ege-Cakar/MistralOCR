import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import os
import tempfile
import webbrowser
from pathlib import Path
import threading
import pyperclip
from mistralai import Mistral
from mistralai import DocumentURLChunk
import markdown
import tkhtmlview
import sys

# Determine the appropriate config file path based on whether we're running as a bundled app
def get_config_file_path():
    # For macOS app bundles
    if getattr(sys, 'frozen', False):
        # Running as compiled app
        if sys.platform == 'darwin':
            # macOS app bundle
            bundle_dir = os.path.dirname(sys.executable)
            if 'Contents/MacOS' in bundle_dir:
                # Running as a macOS app bundle
                resources_dir = os.path.abspath(os.path.join(bundle_dir, os.pardir, 'Resources'))
                return os.path.join(resources_dir, "mistral_ocr_config.json")
            # Fallback - use the executable directory
            return os.path.join(bundle_dir, "mistral_ocr_config.json")
        else:
            # Windows/Linux bundled
            bundle_dir = os.path.dirname(sys.executable)
            return os.path.join(bundle_dir, "mistral_ocr_config.json")
    else:
        # Running as a script
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "mistral_ocr_config.json")

CONFIG_FILE = get_config_file_path()

class MistralOCRApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mistral OCR - PDF to Markdown Converter")
        self.root.geometry("1000x800")
        self.root.minsize(800, 600)
        
        self.api_key = tk.StringVar()
        self.pdf_path = tk.StringVar()
        self.status = tk.StringVar()
        self.status.set("Ready")
        self.markdown_content = ""
        self.html_content = ""
        
        self.create_widgets()
        self.load_config()
    
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # API Key section
        api_frame = ttk.LabelFrame(main_frame, text="API Settings", padding="10")
        api_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(api_frame, text="Mistral API Key:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        api_entry = ttk.Entry(api_frame, textvariable=self.api_key, width=50, show="*")
        api_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        show_hide_btn = ttk.Button(api_frame, text="Show/Hide", command=self.toggle_api_key_visibility)
        show_hide_btn.grid(row=0, column=2, padx=5, pady=5)
        
        save_api_btn = ttk.Button(api_frame, text="Save API Key", command=self.save_api_key)
        save_api_btn.grid(row=0, column=3, padx=5, pady=5)
        
        # File selection section
        file_frame = ttk.LabelFrame(main_frame, text="PDF File Selection", padding="10")
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(file_frame, text="PDF File:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(file_frame, textvariable=self.pdf_path, width=60, state="readonly").grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        browse_btn = ttk.Button(file_frame, text="Browse", command=self.browse_pdf)
        browse_btn.grid(row=0, column=2, padx=5, pady=5)
        
        convert_btn = ttk.Button(file_frame, text="Convert to Markdown", command=self.start_conversion)
        convert_btn.grid(row=0, column=3, padx=5, pady=5)
        
        # Result section
        result_frame = ttk.LabelFrame(main_frame, text="Conversion Result", padding="10")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(result_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Markdown source
        self.markdown_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.markdown_tab, text="Markdown Source")
        
        # Markdown text area
        self.markdown_text = scrolledtext.ScrolledText(self.markdown_tab, wrap=tk.WORD, height=20)
        self.markdown_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tab 2: Preview
        self.preview_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.preview_tab, text="Preview")
        
        # Preview area
        self.preview_widget = tkhtmlview.HTMLScrolledText(
            self.preview_tab, 
            html="<html><body><p>Markdown preview will appear here</p></body></html>"
        )
        self.preview_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Action buttons
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=5)
        
        copy_btn = ttk.Button(action_frame, text="Copy to Clipboard", command=self.copy_to_clipboard)
        copy_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        save_btn = ttk.Button(action_frame, text="Save to File", command=self.save_to_file)
        save_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        browser_btn = ttk.Button(action_frame, text="Open in Browser", command=self.open_in_browser)
        browser_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Status bar
        status_bar = ttk.Label(main_frame, textvariable=self.status, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, padx=5, pady=5)
    
    def toggle_api_key_visibility(self):
        api_entry = self.root.nametowidget(self.root.focus_get().master.winfo_parent()).winfo_children()[1]
        if api_entry.cget('show') == '*':
            api_entry.config(show='')
        else:
            api_entry.config(show='*')
    
    def save_api_key(self):
        config = {"api_key": self.api_key.get()}
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f)
            
            self.status.set(f"API key saved to {CONFIG_FILE}")
            messagebox.showinfo("Success", f"API key saved successfully to:\n{CONFIG_FILE}")
        except Exception as e:
            error_msg = f"Failed to save API key: {str(e)}"
            self.status.set(error_msg)
            messagebox.showerror("Error", f"{error_msg}\nPath: {CONFIG_FILE}")
    
    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.api_key.set(config.get("api_key", ""))
                self.status.set("Config loaded from: " + CONFIG_FILE)
            else:
                # Config file doesn't exist yet
                self.status.set("No config file found. Will create at: " + CONFIG_FILE)
                # Create parent directories if they don't exist
                os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        except Exception as e:
            self.status.set("Error loading config: " + str(e))
            messagebox.showwarning("Config Loading Error", 
                                   f"Could not load configuration from {CONFIG_FILE}\nError: {str(e)}")
    
    def browse_pdf(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")]
        )
        if file_path:
            self.pdf_path.set(file_path)
    
    def start_conversion(self):
        if not self.api_key.get():
            messagebox.showerror("Error", "Please enter your Mistral API key")
            return
        
        if not self.pdf_path.get():
            messagebox.showerror("Error", "Please select a PDF file")
            return
        
        self.status.set("Converting PDF to Markdown...")
        self.markdown_text.delete(1.0, tk.END)
        
        # Start conversion in a separate thread to avoid freezing UI
        thread = threading.Thread(target=self.convert_pdf)
        thread.daemon = True
        thread.start()
    
    def convert_pdf(self):
        try:
            # Get the PDF path and API key
            pdf_file = Path(self.pdf_path.get())
            api_key = self.api_key.get()
            
            if not pdf_file.is_file():
                self.update_status("Error: Invalid PDF file path")
                return
            
            # Initialize Mistral client
            client = Mistral(api_key=api_key)
            
            # Upload the file
            self.update_status("Uploading PDF file...")
            uploaded_file = client.files.upload(
                file={
                    "file_name": pdf_file.stem,
                    "content": pdf_file.read_bytes(),
                },
                purpose="ocr",
            )
            
            # Get the signed URL
            self.update_status("Processing with OCR...")
            signed_url = client.files.get_signed_url(file_id=uploaded_file.id, expiry=1)
            
            # Process the PDF with OCR
            pdf_response = client.ocr.process(
                document=DocumentURLChunk(document_url=signed_url.url),
                model="mistral-ocr-latest",
                include_image_base64=True
            )
            
            # Extract and format markdown
            self.update_status("Preparing markdown...")
            markdown_content = self.get_combined_markdown(pdf_response)
            self.markdown_content = markdown_content
            
            # Update the UI with the result
            self.root.after(0, self.update_result, markdown_content)
            
            self.update_status("Conversion completed")
            
        except Exception as e:
            error_message = str(e)
            self.update_status("Error: " + error_message)
            self.root.after(0, lambda: messagebox.showerror("Error", error_message))
    
    def update_status(self, message):
        self.root.after(0, lambda: self.status.set(message))
    
    def update_result(self, markdown_content):
        # Update markdown text
        self.markdown_text.delete(1.0, tk.END)
        self.markdown_text.insert(tk.END, markdown_content)
        
        # Update preview with MathJax support
        html_content = markdown.markdown(
            markdown_content,
            extensions=['tables', 'fenced_code', 'codehilite']
        )
        
        # Store for browser view
        self.html_content = (
            "<!DOCTYPE html>"
            "<html>"
            "<head>"
            "    <script type=\"text/javascript\" id=\"MathJax-script\" async "
            "        src=\"https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js\">"
            "    </script>"
            "    <script>"
            "    window.MathJax = {"
            "        tex: {"
            "            inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],"
            "            displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],"
            "            processEscapes: true"
            "        },"
            "        svg: {"
            "            fontCache: 'global'"
            "        }"
            "    };"
            "    </script>"
            "    <style>"
            "        body { font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; }"
            "        pre { background-color: #f5f5f5; padding: 10px; border-radius: 5px; }"
            "        code { font-family: monospace; }"
            "        img { max-width: 100%; }"
            "        table { border-collapse: collapse; width: 100%; }"
            "        th, td { border: 1px solid #ddd; padding: 8px; }"
            "        th { background-color: #f2f2f2; }"
            "    </style>"
            "</head>"
            "<body>"
            + html_content +
            "</body>"
            "</html>"
        )
        
        # Simplified version for in-app preview
        simple_html = (
            "<html><head>"
            "<style>"
            "body { font-family: Arial, sans-serif; line-height: 1.6; }"
            "pre { background-color: #f5f5f5; padding: 10px; border-radius: 5px; }"
            "code { font-family: monospace; }"
            "img { max-width: 100%; }"
            "table { border-collapse: collapse; width: 100%; }"
            "th, td { border: 1px solid #ddd; padding: 8px; }"
            "</style></head><body>"
            + html_content +
            "</body></html>"
        )
        
        self.preview_widget.set_html(simple_html)
    
    def replace_images_in_markdown(self, markdown_str, images_dict):
        result = markdown_str
        for img_name, base64_str in images_dict.items():
            placeholder = "![" + img_name + "]()"
            replacement = "![" + img_name + "](data:image/png;base64," + base64_str + ")"
            result = result.replace(placeholder, replacement)
        return result
    
    def get_combined_markdown(self, pdf_response):
        markdowns = []
        for page in pdf_response.pages:
            img_data = {}
            for img in page.images:
                img_data[img.id] = img.image_base64
            page_md = self.replace_images_in_markdown(page.markdown, img_data)
            markdowns.append(page_md)
        return "\n\n".join(markdowns)
    
    def copy_to_clipboard(self):
        if not self.markdown_content:
            messagebox.showinfo("Info", "No markdown content to copy")
            return
        
        pyperclip.copy(self.markdown_content)
        self.status.set("Markdown copied to clipboard")
    
    def save_to_file(self):
        if not self.markdown_content:
            messagebox.showinfo("Info", "No markdown content to save")
            return
        
        pdf_path = Path(self.pdf_path.get())
        default_filename = pdf_path.stem + ".md"
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown Files", "*.md"), ("Text Files", "*.txt"), ("All Files", "*.*")],
            initialfile=default_filename
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.markdown_content)
                self.status.set("Markdown saved to " + file_path)
            except Exception as e:
                messagebox.showerror("Error", "Failed to save file: " + str(e))
    
    def open_in_browser(self):
        """Open the HTML preview with MathJax in the default web browser."""
        if not hasattr(self, 'html_content') or not self.html_content:
            messagebox.showinfo("Info", "No content to preview")
            return
        
        # Create a temporary HTML file
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False, mode='w', encoding='utf-8') as f:
            f.write(self.html_content)
            temp_path = f.name
        
        # Open the file in the default browser
        webbrowser.open('file://' + temp_path)
        
        # Update status
        self.status.set("Opened preview in browser")
        
        # Schedule file cleanup (optional)
        self.root.after(30000, lambda: self._cleanup_temp_file(temp_path))
    
    def _cleanup_temp_file(self, filepath):
        """Delete temporary files after a delay."""
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass

if __name__ == "__main__":
    root = tk.Tk()
    app = MistralOCRApp(root)
    root.mainloop()