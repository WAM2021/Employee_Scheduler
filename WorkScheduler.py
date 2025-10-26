# work_scheduler.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import json
import os
import calendar
import time
from datetime import datetime, timedelta, date
from tkcalendar import DateEntry
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import requests
import threading
import zipfile
import tempfile
import shutil
import subprocess
import sys

# Version information
APP_VERSION = "1.0.0"  # Current version of the application
GITHUB_REPO = "WAM2021/Employee_Scheduler"  # Your actual GitHub repo
UPDATE_CHECK_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

DATA_FILE = "employees.json"
DATE_FMT = "%Y-%m-%d"
TIME_FMT = "%I:%M %p"

def ensure_data_file():
    if not os.path.exists(DATA_FILE):
        template = {
            "employees": [],
            "schedule": {},  # monthly keyed schedule: "YYYY-MM": { "YYYY-MM-DD": [ {employee,start,end}, ... ] }
            "store_hours": {
                "monday": ("8:30 AM", "7:00 PM"),
                "tuesday": ("8:30 AM", "7:00 PM"),
                "wednesday": ("8:30 AM", "7:00 PM"),
                "thursday": ("8:30 AM", "7:00 PM"),
                "friday": ("8:30 AM", "7:00 PM"),
                "saturday": ("9:00 AM", "3:00 PM"),
                "sunday": None  # closed
            }
        }
        with open(DATA_FILE, "w") as f:
            json.dump(template, f, indent=4)

def load_data():
    ensure_data_file()
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
    
    # Ensure store_hours exists (for backwards compatibility)
    if "store_hours" not in data:
        data["store_hours"] = {
            "monday": ("8:30 AM", "7:00 PM"),
            "tuesday": ("8:30 AM", "7:00 PM"),
            "wednesday": ("8:30 AM", "7:00 PM"),
            "thursday": ("8:30 AM", "7:00 PM"),
            "friday": ("8:30 AM", "7:00 PM"),
            "saturday": ("9:00 AM", "3:00 PM"),
            "sunday": None
        }
        save_data(data)
    
    return data

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def generate_times(start_str, end_str, interval_minutes=30):
    """Return list of times between start and end inclusive formatted with TIME_FMT."""
    start_dt = datetime.strptime(start_str, TIME_FMT)
    end_dt = datetime.strptime(end_str, TIME_FMT)
    times = []
    current = start_dt
    while current <= end_dt:
        times.append(current.strftime(TIME_FMT))
        current += timedelta(minutes=interval_minutes)
    return times

# Auto-Update System Functions
def version_compare(version1, version2):
    """Compare two version strings. Returns 1 if version1 > version2, -1 if version1 < version2, 0 if equal."""
    def version_tuple(v):
        return tuple(map(int, (v.split("."))))
    
    v1_tuple = version_tuple(version1)
    v2_tuple = version_tuple(version2)
    
    if v1_tuple > v2_tuple:
        return 1
    elif v1_tuple < v2_tuple:
        return -1
    else:
        return 0

def check_for_updates(callback=None):
    """Check GitHub for latest release version. Runs in background thread."""
    def _check():
        try:
            response = requests.get(UPDATE_CHECK_URL, timeout=10)
            if response.status_code == 200:
                release_data = response.json()
                latest_version = release_data.get('tag_name', '').lstrip('v')
                download_url = None
                
                # Look for .exe file in assets
                for asset in release_data.get('assets', []):
                    if asset['name'].endswith('.exe'):
                        download_url = asset['browser_download_url']
                        break
                
                if callback:
                    callback(latest_version, download_url, release_data.get('body', ''))
            else:
                if callback:
                    callback(None, None, f"Failed to check for updates: HTTP {response.status_code}")
        except Exception as e:
            if callback:
                callback(None, None, f"Error checking for updates: {str(e)}")
    
    thread = threading.Thread(target=_check, daemon=True)
    thread.start()

def download_update(download_url, progress_callback=None, completion_callback=None):
    """Download update file. Runs in background thread."""
    def _download():
        try:
            response = requests.get(download_url, stream=True, timeout=30)
            if response.status_code == 200:
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                # Create temporary file
                temp_dir = tempfile.mkdtemp()
                temp_file = os.path.join(temp_dir, "update.exe")
                
                with open(temp_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback and total_size > 0:
                                progress = (downloaded / total_size) * 100
                                progress_callback(progress)
                
                if completion_callback:
                    completion_callback(temp_file, None)
            else:
                if completion_callback:
                    completion_callback(None, f"Download failed: HTTP {response.status_code}")
        except Exception as e:
            if completion_callback:
                completion_callback(None, f"Download error: {str(e)}")
    
    thread = threading.Thread(target=_download, daemon=True)
    thread.start()

def apply_update(update_file_path):
    """Apply the downloaded update by replacing the current executable."""
    try:
        current_exe = sys.executable
        if hasattr(sys, 'frozen'):
            # Running as compiled executable
            current_exe = sys.executable
        else:
            # Running as script, can't auto-update
            messagebox.showinfo("Update", "Please manually replace the executable file.")
            return False
        
        # Create batch file to handle the update process
        batch_content = f"""@echo off
timeout /t 2 /nobreak > nul
move "{update_file_path}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
"""
        
        batch_file = os.path.join(os.path.dirname(current_exe), "update.bat")
        with open(batch_file, 'w') as f:
            f.write(batch_content)
        
        # Start the batch file and exit current application
        subprocess.Popen([batch_file], shell=True)
        return True
        
    except Exception as e:
        messagebox.showerror("Update Error", f"Failed to apply update: {str(e)}")
        return False

def friendly_weekday_name(dt):
    return dt.strftime("%A")  # 'Monday' etc.

def format_time_simple(time_str):
    """Convert '7:00 PM' format to '7' or '7:30' format."""
    try:
        dt = datetime.strptime(time_str, TIME_FMT)
        hour = dt.hour
        if hour > 12:
            hour -= 12
        elif hour == 0:
            hour = 12
        if dt.minute == 0:
            return str(hour)
        return f"{hour}:{dt.minute:02d}"
    except ValueError:
        return time_str  # Return original if parsing fails

class WorkSchedulerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Work Scheduler")  # No version for testing
        
        # Set initial window size
        self.root.geometry("1024x768")
        
        # Set darker background for main window
        self.root.configure(bg='#B4B4B4')
        
        # Configure Combobox styles
        self.style = ttk.Style()
        
        # Configure Notebook (tabs) style with cyan blue color scheme
        self.style.configure('TNotebook', background='#49D3E6', borderwidth=0)
        self.style.configure('TNotebook.Tab', 
                           background='#3AB8CC',  # Slightly darker cyan for inactive tabs
                           foreground='white')
        self.style.map('TNotebook.Tab',
                      background=[('selected', '#49D3E6')],  # Brighter cyan for active tab
                      foreground=[('selected', 'white')])
        
        # Normal state - white background
        self.style.map('TCombobox',
            fieldbackground=[('disabled', 'SystemButtonFace'),
                           ('readonly', 'white')],
            selectbackground=[('disabled', 'SystemButtonFace'),
                            ('readonly', 'SystemHighlight')],
            selectforeground=[('disabled', 'SystemGrayText'),
                            ('readonly', 'SystemHighlightText')])
        
        # Initialize size parameters
        self.min_font_size = 8
        self.max_font_size = 24
        self._resize_timer = None
        self._last_width = 0
        self._last_height = 0
        self._cached_font_sizes = {}
        
        # List to track schedule labels that need to be updated during resize
        self.schedule_labels = []

        # Auto-save controls for Employee Manager
        self._auto_save_timer = None
        self._suspend_auto_save = False
        
        # Initialize font-trackable widget lists
        self.employee_tab_widgets = {
            'headers': [],
            'labels': [],
            'buttons': [],
            'listbox': None
        }
        
        self.admin_tab_widgets = {
            'headers': [],
            'labels': []
        }
        
        # Ctrl+drag state for copying shifts
        self.ctrl_drag_data = {"active": False, "source_day": None, "source_shifts": None, "source_widget": None}

        # Data
        self.data = load_data()
        if "schedule" not in self.data:
            self.data["schedule"] = {}
            
        # Current month shown
        today = date.today()
        self.current_year = today.year
        self.current_month = today.month

        # Configure root window to be responsive
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.grid(row=0, column=0, sticky="nsew")
        
        # Create menu bar
        self.create_menu_bar()

        # Create tabs
        self.employee_tab = tk.Frame(self.notebook)
        self.schedule_tab = tk.Frame(self.notebook)
        self.admin_tab = tk.Frame(self.notebook)
        
        # Make tabs responsive
        self.employee_tab.grid_rowconfigure(0, weight=1)
        self.employee_tab.grid_columnconfigure(1, weight=3)  # Make center column expand more
        self.schedule_tab.grid_rowconfigure(1, weight=1)
        self.schedule_tab.grid_columnconfigure(0, weight=1)
        self.admin_tab.grid_rowconfigure(0, weight=1)
        self.admin_tab.grid_columnconfigure(0, weight=1)

        # Add tabs to notebook
        self.notebook.add(self.employee_tab, text="Employee Manager")
        self.notebook.add(self.schedule_tab, text="Schedule (Month View)")
        self.notebook.add(self.admin_tab, text="Admin")

        # Build UI
        self.setup_employee_tab()
        self.setup_schedule_tab()
        self.setup_admin_tab()
        
        # Check for updates on startup (in background)
        self.check_for_updates_on_startup()
        
        # Bind resize event
        self.root.bind("<Configure>", self.on_window_resize)
            
    def center_dialog(self, dialog, width=None, height=None):
        """Center a dialog window relative to the main window"""
        # Set size first
        if width and height:
            dialog.geometry(f"{width}x{height}")
            
        # Make sure dialog is fully created
        dialog.update_idletasks()
        
        # Get dialog size if not specified
        if width is None:
            width = dialog.winfo_width()
        if height is None:
            height = dialog.winfo_height()
            
        # Get main window position and size
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_width = self.root.winfo_width()
        main_height = self.root.winfo_height()
        
        # Calculate position
        x = main_x + (main_width - width) // 2
        y = main_y + (main_height - height) // 2
        
        # Position dialog and set minimum size
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        dialog.minsize(width, height)
            
        # Initialize size parameters
        self.min_font_size = 8
        self.max_font_size = 24
        self._resize_timer = None
        self._last_width = 0
        self._last_height = 0
        self._cached_font_sizes = {}
        
        # List to track schedule labels that need to be updated during resize
        self.schedule_labels = []
        
        # Resize event will be bound only once in __init__
        
    def create_menu_bar(self):
        """Create the application menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Check for Updates", command=self.manual_check_for_updates)
        help_menu.add_separator()
        help_menu.add_command(label=f"About Work Scheduler v{APP_VERSION}", command=self.show_about_dialog)
    
    def show_about_dialog(self):
        """Show the about dialog."""
        dialog = tk.Toplevel(self.root)
        dialog.title("About Work Scheduler")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        self.center_dialog(dialog, 350, 250)
        
        # Header
        header_frame = tk.Frame(dialog, bg="#49D3E6", height=60)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, text="Work Scheduler", 
                font=("Arial", 18, "bold"), 
                bg="#49D3E6", fg="white").pack(expand=True)
        
        # Content
        content_frame = tk.Frame(dialog, padx=20, pady=20)
        content_frame.pack(fill="both", expand=True)
        
        info_text = f"""Version: {APP_VERSION}

A comprehensive employee scheduling application
with auto-update capabilities.

Brought to you by WILLSTER"""
        
        tk.Label(content_frame, text=info_text, font=("Arial", 10), justify="center").pack(expand=True)
        
        # Close button
        tk.Button(content_frame, text="Close", command=dialog.destroy).pack(pady=(20, 0))
        
    def calculate_font_size(self, base_size=10):
        """Calculate font size based on window dimensions with improved caching"""
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        
        # Return cached value if dimensions haven't changed significantly
        cache_key = (width // 25, height // 25)  # Finer grouping for better responsiveness
        if cache_key in self._cached_font_sizes:
            return self._cached_font_sizes[cache_key]
            
        if width <= 100 or height <= 100:  # Window not yet properly realized
            return base_size
            
        # Calculate new size based on smaller dimension for better scaling
        size = min(width, height)
        # More responsive scaling formula
        if size < 400:
            scale_factor = 0.012  # Smaller scaling for small windows
        elif size < 800:
            scale_factor = 0.014
        else:
            scale_factor = 0.016  # Larger scaling for big windows
            
        new_size = max(int(size * scale_factor), self.min_font_size)
        new_size = min(new_size, self.max_font_size)
        
        # Cache the result and limit cache size
        if len(self._cached_font_sizes) > 50:  # Prevent memory bloat
            self._cached_font_sizes.clear()
        self._cached_font_sizes[cache_key] = new_size
        return new_size
        
    def on_window_resize(self, event=None):
        """Handle window resize events with improved debouncing and dialog detection"""
        # Only respond to root window resizes
        if event and event.widget != self.root:
            return
            
        # Get current dimensions
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        
        # Skip if dimensions are too small (likely minimized or dialog opened)
        if width < 200 or height < 150:
            return
            
        # Skip if change is too small (reduces unnecessary updates)
        if (abs(width - self._last_width) < 30 and 
            abs(height - self._last_height) < 30):
            return
            
        self._last_width = width
        self._last_height = height
            
        # Cancel previous timer if it exists
        if self._resize_timer is not None:
            self.root.after_cancel(self._resize_timer)
            
        # Set timer with appropriate delay - shorter for better responsiveness
        self._resize_timer = self.root.after(150, self.update_ui_sizes_optimized)
    # Note: Do not rebuild tabs or UI here; it causes tab selection to reset
    # and can lead to duplicated widgets. Resizing should only adjust sizes.

    # -------------------------
    # Employee Tab
    # -------------------------
    def setup_employee_tab(self):
        left = tk.Frame(self.employee_tab, padx=10, pady=10)
        center = tk.Frame(self.employee_tab, padx=10, pady=10)
        right = tk.Frame(self.employee_tab, padx=10, pady=10)
        bottom = tk.Frame(self.employee_tab, pady=10)

        left.grid(row=0, column=0, sticky="nsew", padx=5)
        center.grid(row=0, column=1, sticky="nsew", padx=5)
        right.grid(row=0, column=2, sticky="nsew", padx=5)
        bottom.grid(row=1, column=0, columnspan=3, sticky="ew", pady=5)

        # Configure column weights for proper resizing
        self.employee_tab.grid_columnconfigure(1, weight=3)  # Center gets more space
        self.employee_tab.grid_columnconfigure(0, weight=1)  # Left gets less space
        self.employee_tab.grid_columnconfigure(2, weight=1)  # Right gets less space
        
        # Configure row weight for vertical expansion
        self.employee_tab.grid_rowconfigure(0, weight=1)

        # Left: employee list
        base_font_size = self.calculate_font_size()
        header_font_size = min(base_font_size + 2, self.max_font_size)
        
        emp_header = tk.Label(left, text="Employees", font=("Arial", header_font_size, "bold"))
        emp_header.pack()
        self.employee_tab_widgets['headers'].append(emp_header)
        
        # Keep selection even when focus moves to other widgets (e.g., comboboxes)
        self.emp_listbox = tk.Listbox(left, width=30, height=18, exportselection=False, 
                                    font=("Arial", base_font_size))
        self.emp_listbox.pack(pady=5, fill="both", expand=True)
        self.emp_listbox.bind("<<ListboxSelect>>", self.on_employee_select)
        self.employee_tab_widgets['listbox'] = self.emp_listbox

        add_btn = tk.Button(left, text="Add Employee", command=self.add_employee, font=("Arial", base_font_size))
        add_btn.pack(fill="x", pady=2)
        self.employee_tab_widgets['buttons'].append(add_btn)
        
        edit_btn = tk.Button(left, text="Edit Name", command=self.edit_employee_name, font=("Arial", base_font_size))
        edit_btn.pack(fill="x", pady=2)
        self.employee_tab_widgets['buttons'].append(edit_btn)
        
        remove_btn = tk.Button(left, text="Remove Employee", command=self.remove_employee, font=("Arial", base_font_size))
        remove_btn.pack(fill="x", pady=2)
        self.employee_tab_widgets['buttons'].append(remove_btn)

        # Populate listbox
        self.refresh_employee_list()

        # Center: availability editor
        base_font_size = self.calculate_font_size()
        header_font_size = min(base_font_size + 2, self.max_font_size)
        
        avail_header = tk.Label(center, text="Availability (check if available; choose start/end)", 
                               font=("Arial", header_font_size, "bold"))
        avail_header.grid(row=0, column=0, columnspan=4)
        self.employee_tab_widgets['headers'].append(avail_header)
        
        self.days = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
        # For each day we'll store widgets: { day: { 'var': IntVar, 'start_var': StringVar, 'end_var': StringVar, 'start_cb': Combobox, 'end_cb': Combobox } }
        self.avail_widgets = {}
        for i, day in enumerate(self.days):
            day_label = tk.Label(center, text=day.capitalize(), font=("Arial", base_font_size))
            day_label.grid(row=i+1, column=0, sticky="e", padx=5, pady=2)
            self.employee_tab_widgets['labels'].append(day_label)
            # availability checkbox
            var = tk.IntVar(value=0)
            cb = tk.Checkbutton(center, variable=var)
            cb.grid(row=i+1, column=1, padx=4)

            # time options based on store hours for that day
            store_range = self.data.get("store_hours", {}).get(day)
            if store_range:
                times = generate_times(store_range[0], store_range[1])
            else:
                times = []

            start_var = tk.StringVar()
            start_cb = ttk.Combobox(center, textvariable=start_var, values=times, state="readonly", width=12)
            start_cb.grid(row=i+1, column=2, padx=4)

            end_var = tk.StringVar()
            end_cb = ttk.Combobox(center, textvariable=end_var, values=times, state="readonly", width=12)
            end_cb.grid(row=i+1, column=3, padx=4)

            # Initial state setup
            if not store_range:
                # Store is closed this day
                cb.config(state="disabled")
                start_cb.configure(state="disabled")
                end_cb.configure(state="disabled")
            else:
                # Store is open but availability not checked
                start_cb.configure(state="disabled")
                end_cb.configure(state="disabled")

            # when checkbox toggled, enable/disable comboboxes
            def make_toggle(s_cb=start_cb, e_cb=end_cb, v=var):
                def toggle(*args):
                    if v.get():
                        # Enable comboboxes if they have values and set sensible defaults
                        vals_s = s_cb['values'] if 'values' in s_cb.keys() else s_cb.cget('values')
                        vals_e = e_cb['values'] if 'values' in e_cb.keys() else e_cb.cget('values')
                        
                        # Start time handling
                        if vals_s:
                            try:
                                # Set to first available time by default
                                first = vals_s[0]
                                s_cb.set(first)
                                s_cb.configure(state='readonly')  # White background
                            except Exception:
                                s_cb.configure(state='disabled')  # Gray background
                        else:
                            s_cb.configure(state='disabled')  # Gray background

                        # End time handling
                        if vals_e:
                            try:
                                # Set to last available time by default
                                last = vals_e[-1]
                                e_cb.set(last)
                                e_cb.configure(state='readonly')  # White background
                            except Exception:
                                e_cb.configure(state='disabled')  # Gray background
                        else:
                            e_cb.configure(state='disabled')  # Gray background
                    else:
                        # Clear and disable both comboboxes
                        s_cb.set("")
                        e_cb.set("")
                        s_cb.configure(state='disabled')  # Gray background
                        e_cb.configure(state='disabled')  # Gray background
                return toggle

            # Validation function to check start time is not after end time
            def validate_availability_times(s_cb=start_cb, e_cb=end_cb, s_var=start_var, e_var=end_var, day_name=day):
                def validate(*args):
                    start_time = s_var.get()
                    end_time = e_var.get()
                    
                    # Only validate if both times are selected
                    if start_time and end_time:
                        try:
                            start_dt = datetime.strptime(start_time, TIME_FMT)
                            end_dt = datetime.strptime(end_time, TIME_FMT)
                            
                            if start_dt >= end_dt:
                                # Invalid: start is after or equal to end
                                messagebox.showerror(
                                    "Invalid Time Range",
                                    f"Start time must be before end time for {day_name.capitalize()}.\n\n"
                                    f"Start: {start_time}\n"
                                    f"End: {end_time}"
                                )
                                # Reset to default values
                                vals_s = s_cb['values'] if 'values' in s_cb.keys() else s_cb.cget('values')
                                vals_e = e_cb['values'] if 'values' in e_cb.keys() else e_cb.cget('values')
                                if vals_s:
                                    s_cb.set(vals_s[0])
                                if vals_e:
                                    e_cb.set(vals_e[-1])
                                return
                        except Exception:
                            pass
                return validate

            var.trace_add('write', make_toggle())
            # also mark dirty when availability checkbox changes
            var.trace_add('write', lambda *a, d=day: self.mark_employee_dirty())
            # mark dirty when start/end selection changes
            start_var.trace_add('write', lambda *a, d=day: self.mark_employee_dirty())
            end_var.trace_add('write', lambda *a, d=day: self.mark_employee_dirty())
            # Add validation for time selections
            start_var.trace_add('write', validate_availability_times())
            end_var.trace_add('write', validate_availability_times())

            self.avail_widgets[day] = {
                'var': var,
                'checkbutton': cb,
                'start_var': start_var,
                'end_var': end_var,
                'start_cb': start_cb,
                'end_cb': end_cb,
            }

        # Right: requested days off
        days_off_header = tk.Label(right, text="Requested Days Off (YYYY-MM-DD)", font=("Arial", header_font_size, "bold"))
        days_off_header.pack()
        self.employee_tab_widgets['headers'].append(days_off_header)
        
        self.days_off_list = tk.Listbox(right, width=30, height=12, font=("Arial", base_font_size))
        self.days_off_list.pack(pady=5)
        
        add_day_btn = tk.Button(right, text="Add Day Off", command=self.add_requested_day, font=("Arial", base_font_size))
        add_day_btn.pack(fill="x", pady=2)
        self.employee_tab_widgets['buttons'].append(add_day_btn)
        
        remove_day_btn = tk.Button(right, text="Remove Selected Off", command=self.remove_requested_day, font=("Arial", base_font_size))
        remove_day_btn.pack(fill="x", pady=2)
        self.employee_tab_widgets['buttons'].append(remove_day_btn)

        # Bottom: auto-save status indicator
        save_row = tk.Frame(bottom)
        save_row.pack(pady=8)
        self.save_emp_lbl = tk.Label(save_row, text="Changes save automatically", font=("Arial", base_font_size, "bold"))
        self.save_emp_lbl.pack(side="left")
        self.employee_tab_widgets['labels'].append(self.save_emp_lbl)
        
        self.save_indicator = tk.Label(save_row, text="", fg="red", font=("Arial", base_font_size, "bold"))
        self.save_indicator.pack(side="left", padx=(8,0))
        self.employee_tab_widgets['labels'].append(self.save_indicator)
        # internal flag
        self._employee_dirty = False

    def refresh_employee_list(self):
        self.emp_listbox.delete(0, tk.END)
        # Sort employees alphabetically by name
        employees = self.data.get("employees", [])
        sorted_employees = sorted(employees, key=lambda emp: emp.get("name", "").lower())
        for emp in sorted_employees:
            self.emp_listbox.insert(tk.END, emp["name"])

    def mark_employee_dirty(self):
        # Skip auto-save triggers while we're programmatically populating UI
        if getattr(self, '_suspend_auto_save', False):
            return
        # Mark dirty and debounce an auto-save
        self._employee_dirty = True
        try:
            self.save_indicator.config(text='● Saving…')
        except Exception:
            pass
        # Debounce: cancel any pending auto-save and schedule a new one
        try:
            if self._auto_save_timer is not None:
                self.root.after_cancel(self._auto_save_timer)
        except Exception:
            pass
        # Save soon after user stops typing/changing
        self._auto_save_timer = self.root.after(600, lambda: self.save_employee_changes(silent=True))

    def clear_employee_dirty(self):
        if getattr(self, '_employee_dirty', False):
            self._employee_dirty = False
        # Clear any pending auto-save timer
        try:
            if self._auto_save_timer is not None:
                self.root.after_cancel(self._auto_save_timer)
                self._auto_save_timer = None
        except Exception:
            pass
        try:
            self.save_indicator.config(text='')
        except Exception:
            pass

    def find_employee_by_display(self, display_name):
        """Return the employee dict matching a display name."""
        for e in self.data.get("employees", []):
            if e.get("name") == display_name:
                return e
        return None

    def add_employee(self):
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("New Employee")
        dialog.transient(self.root)
        dialog.grab_set()  # Make dialog modal
        
        # Set size and center the dialog
        self.center_dialog(dialog, width=300, height=150)

        # Main frame with padding
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.pack(fill="both", expand=True)

        # First Name
        ttk.Label(main_frame, text="First Name:").pack(anchor="w", pady=(0, 2))
        first_name_var = tk.StringVar()
        first_name_entry = ttk.Entry(main_frame, textvariable=first_name_var)
        first_name_entry.pack(fill="x", pady=(0, 8))

        # Last Name
        ttk.Label(main_frame, text="Last Name:").pack(anchor="w", pady=(0, 2))
        last_name_var = tk.StringVar()
        last_name_entry = ttk.Entry(main_frame, textvariable=last_name_var)
        last_name_entry.pack(fill="x", pady=(0, 8))

        def save_employee():
            first = first_name_var.get().strip()
            last = last_name_var.get().strip()
            
            if not first and not last:
                messagebox.showerror("Invalid Input", "At least one name field must be filled.")
                return

            # Create the employee
            full_name = (first + " " + last).strip()
            new_emp = {
                "id": max([e.get("id",0) for e in self.data.get("employees", [])] + [0]) + 1,
                "name": full_name,
                "firstName": first,
                "lastName": last,
                "position": "",
                "availability": {d: ["off"] for d in self.days},
                "requested_days_off": []
            }
            self.data["employees"].append(new_emp)
            save_data(self.data)
            self.refresh_employee_list()
            dialog.destroy()

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=(8, 0))
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Save", command=save_employee).pack(side="right", padx=5)

        # Set focus to first name entry
        first_name_entry.focus()

    def remove_employee(self):
        sel = self.emp_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        # Get the employee name from the listbox
        emp_name = self.emp_listbox.get(idx)
        # Find the employee in the data by name
        emp = None
        emp_index = None
        for i, e in enumerate(self.data["employees"]):
            if e.get("name") == emp_name:
                emp = e
                emp_index = i
                break
        
        if not emp:
            return
        
        # Count shifts to show in confirmation
        shift_count = 0
        schedule = self.data.get("schedule", {})
        for month_data in schedule.values():
            if isinstance(month_data, dict):
                for shifts in month_data.values():
                    if isinstance(shifts, list):
                        shift_count += sum(1 for s in shifts if s.get("employee") == emp["name"])
        
        # Show confirmation dialog with shift count
        if not messagebox.askyesno("Confirm Remove", 
            f"Are you sure you want to remove {emp['name']}?\n\n"
            f"This will also remove their {shift_count} scheduled shift(s)."):
            return
            
        # Remove if confirmed
        self.data["employees"].pop(emp_index)
        
        # Remove any scheduled shifts for this employee across all months
        shifts_removed = False
        for month_key in list(schedule.keys()):
            month_data = schedule[month_key]
            # Handle both dictionary and list structures
            if isinstance(month_data, dict):
                for day_key in list(month_data.keys()):
                    shifts = month_data[day_key]
                    if isinstance(shifts, list):
                        filtered_shifts = [s for s in shifts if s.get("employee") != emp["name"]]
                        if len(filtered_shifts) != len(shifts):
                            shifts_removed = True
                        month_data[day_key] = filtered_shifts
                        # Clean up empty days
                        if not filtered_shifts:
                            del month_data[day_key]
                # Clean up empty months
                if not month_data:
                    del schedule[month_key]
            elif isinstance(month_data, list):
                filtered_shifts = [s for s in month_data if s.get("employee") != emp["name"]]
                if len(filtered_shifts) != len(month_data):
                    shifts_removed = True
                schedule[month_key] = filtered_shifts
                if not filtered_shifts:
                    del schedule[month_key]
        
        save_data(self.data)
        self.refresh_employee_list()
        self.clear_employee_editor()
        
        # Update schedule view if we removed any shifts
        if shifts_removed:
            self.draw_calendar()

    def on_employee_select(self, event):
        # Prevent auto-save from firing while we populate fields
        self._suspend_auto_save = True
        try:
            sel = self.emp_listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            # Get the employee name from the listbox
            emp_name = self.emp_listbox.get(idx)
            # Find the employee in the data by name
            emp = None
            for e in self.data["employees"]:
                if e.get("name") == emp_name:
                    emp = e
                    break
            
            if not emp:
                return
            
            # Fill availability into widgets
            for day, w in self.avail_widgets.items():
                avail = emp.get("availability", {}).get(day, ["off"])
                var = w['var']
                if avail == ["off"]:
                    var.set(0)
                    # ensure comboboxes disabled
                    w['start_cb'].set("")
                    w['end_cb'].set("")
                    w['start_cb'].config(state='disabled')
                    w['end_cb'].config(state='disabled')
                else:
                    var.set(1)
                    # set values if valid
                    w['start_var'].set(avail[0])
                    w['end_var'].set(avail[1])
                    # enable comboboxes if they have values
                    if w['start_cb']['values']:
                        w['start_cb'].config(state='readonly')
                    if w['end_cb']['values']:
                        w['end_cb'].config(state='readonly')
            
            # Fill days off
            self.days_off_list.delete(0, tk.END)
            for time_off in emp.get("requested_days_off", []):
                if isinstance(time_off, dict):  # New format
                    if time_off["type"] == "partial":
                        display_text = f"{time_off['date']} ({time_off['times']})"
                    else:  # full day
                        display_text = time_off["date"]
                else:  # Old format - just a date string
                    display_text = time_off
                self.days_off_list.insert(tk.END, display_text)
        finally:
            # Clear dirty indicator and re-enable auto-save
            self._suspend_auto_save = False
            try:
                self.save_indicator.config(text='')
            except Exception:
                pass

    def edit_employee_name(self):
        sel = self.emp_listbox.curselection()
        if not sel:
            messagebox.showwarning("Select Employee", "Please select an employee first.")
            return
            
        idx = sel[0]
        # Get the employee name from the listbox
        emp_name = self.emp_listbox.get(idx)
        # Find the employee in the data by name
        emp = None
        for e in self.data["employees"]:
            if e.get("name") == emp_name:
                emp = e
                break
        
        if not emp:
            return
        
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Employee Name")
        dialog.transient(self.root)
        dialog.grab_set()  # Make dialog modal
        
        # Set size and center the dialog
        self.center_dialog(dialog, width=300, height=150)

        # Main frame with padding
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.pack(fill="both", expand=True)

        # First Name
        ttk.Label(main_frame, text="First Name:").pack(anchor="w", pady=(0, 2))
        first_name_var = tk.StringVar(value=emp.get("firstName", ""))
        first_name_entry = ttk.Entry(main_frame, textvariable=first_name_var)
        first_name_entry.pack(fill="x", pady=(0, 8))

        # Last Name
        ttk.Label(main_frame, text="Last Name:").pack(anchor="w", pady=(0, 2))
        last_name_var = tk.StringVar(value=emp.get("lastName", ""))
        last_name_entry = ttk.Entry(main_frame, textvariable=last_name_var)
        last_name_entry.pack(fill="x", pady=(0, 8))

        def save_changes():
            first = first_name_var.get().strip()
            last = last_name_var.get().strip()
            
            if not first and not last:
                messagebox.showerror("Invalid Input", "At least one name field must be filled.")
                return

            # Update employee data
            emp["firstName"] = first
            emp["lastName"] = last
            emp["name"] = (first + " " + last).strip()  # Update legacy name field
            
            # Save changes
            save_data(self.data)
            self.refresh_employee_list()
            
            # Select the edited employee in the list
            for i in range(self.emp_listbox.size()):
                if self.emp_listbox.get(i) == emp["name"]:
                    self.emp_listbox.selection_clear(0, tk.END)
                    self.emp_listbox.selection_set(i)
                    break
                    
            dialog.destroy()

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=(8, 0))
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Save", command=save_changes).pack(side="right", padx=5)

    def clear_employee_editor(self):
        for day, w in self.avail_widgets.items():
            w['var'].set(0)
            w['start_cb'].set("")
            w['end_cb'].set("")
            w['start_cb'].config(state='disabled')
            w['end_cb'].config(state='disabled')
        self.days_off_list.delete(0, tk.END)

    def add_requested_day(self):
        sel = self.emp_listbox.curselection()
        if not sel:
            messagebox.showwarning("Select Employee", "Please select an employee first.")
            return

        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("Request Time Off")
        dialog.transient(self.root)
        dialog.grab_set()  # Make dialog modal
        
        # Set size and center the dialog
        self.center_dialog(dialog, width=400, height=400)

        # Main frame with padding
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.pack(fill="both", expand=True)

        # Request type selection
        ttk.Label(main_frame, text="Type of Request:", font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))
        request_type = tk.StringVar(value="full_day")
        type_frame = ttk.Frame(main_frame)
        type_frame.pack(fill="x", pady=(0, 10))
        type_cb = ttk.Combobox(type_frame, textvariable=request_type, state="readonly", width=30)
        type_cb['values'] = ["Single Full Day", "Partial Day", "Multiple Days"]
        type_cb.current(0)
        type_cb.pack(side="left")

        # Frames for different request types
        full_day_frame = ttk.LabelFrame(main_frame, text="Single Full Day", padding="5")
        partial_day_frame = ttk.LabelFrame(main_frame, text="Partial Day", padding="5")
        multi_day_frame = ttk.LabelFrame(main_frame, text="Multiple Days", padding="5")

        # Calendar style configuration
        style = ttk.Style()
        style.configure('Calendar.TFrame', background='white')
        
        # Full day widgets
        ttk.Label(full_day_frame, text="Date:").pack(anchor="w")
        full_day_cal = DateEntry(full_day_frame, width=15, background='white',
                               foreground='black', borderwidth=2, date_pattern='yyyy-mm-dd',
                               firstweekday='monday', showweeknumbers=False)
        full_day_cal.pack(anchor="w", pady=(0, 5))

        # Partial day widgets
        ttk.Label(partial_day_frame, text="Date:").pack(anchor="w")
        partial_day_cal = DateEntry(partial_day_frame, width=15, background='white',
                                  foreground='black', borderwidth=2, date_pattern='yyyy-mm-dd',
                                  firstweekday='monday', showweeknumbers=False)
        partial_day_cal.pack(anchor="w", pady=(0, 5))
        
        time_frame = ttk.Frame(partial_day_frame)
        time_frame.pack(fill="x", pady=5)
        
        # Generate time options
        times = generate_times("8:30 AM", "7:00 PM")
        
        start_frame = ttk.Frame(time_frame)
        start_frame.pack(anchor="w", pady=2)
        ttk.Label(start_frame, text="Start Time:").pack(side="left")
        start_var = tk.StringVar()
        start_cb = ttk.Combobox(start_frame, textvariable=start_var, values=times, state="readonly", width=10)
        start_cb.pack(side="left", padx=(5, 0))
        
        end_frame = ttk.Frame(time_frame)
        end_frame.pack(anchor="w", pady=2)
        ttk.Label(end_frame, text="End Time:  ").pack(side="left")
        end_var = tk.StringVar()
        end_cb = ttk.Combobox(end_frame, textvariable=end_var, values=times, state="readonly", width=10)
        end_cb.pack(side="left", padx=(5, 0))

        # Multiple days widgets
        date_range_frame = ttk.Frame(multi_day_frame)
        date_range_frame.pack(fill="x", pady=5)
        
        # Start date
        start_date_frame = ttk.Frame(date_range_frame)
        start_date_frame.pack(anchor="w", pady=2)
        ttk.Label(start_date_frame, text="Start Date:").pack(side="left")
        start_date_cal = DateEntry(start_date_frame, width=15, background='white',
                                 foreground='black', borderwidth=2, date_pattern='yyyy-mm-dd',
                                 firstweekday='monday', showweeknumbers=False)
        start_date_cal.pack(side="left", padx=(5, 0))
        
        # End date
        end_date_frame = ttk.Frame(date_range_frame)
        end_date_frame.pack(anchor="w", pady=2)
        ttk.Label(end_date_frame, text="End Date:  ").pack(side="left")
        end_date_cal = DateEntry(end_date_frame, width=15, background='white',
                               foreground='black', borderwidth=2, date_pattern='yyyy-mm-dd',
                               firstweekday='monday', showweeknumbers=False)
        end_date_cal.pack(side="left", padx=(5, 0))

        def show_frame():
            # Hide all frames first
            full_day_frame.pack_forget()
            partial_day_frame.pack_forget()
            multi_day_frame.pack_forget()
            
            # Show the selected frame
            selection = request_type.get()
            if selection == "Single Full Day":
                full_day_frame.pack(fill="x", pady=10)
            elif selection == "Partial Day":
                partial_day_frame.pack(fill="x", pady=10)
            elif selection == "Multiple Days":
                multi_day_frame.pack(fill="x", pady=10)

        type_cb.bind('<<ComboboxSelected>>', lambda e: show_frame())
        
        # Show initial frame
        show_frame()

        def validate_and_save():
            try:
                selection = request_type.get()
                if selection == "Single Full Day":
                    date_str = full_day_cal.get()
                    if not date_str:
                        raise ValueError("Please select a date")
                    date = datetime.strptime(date_str, DATE_FMT)
                    self.days_off_list.insert(tk.END, date_str)
                    
                elif selection == "Partial Day":
                    date_str = partial_day_cal.get()
                    start_time = start_var.get()
                    end_time = end_var.get()
                    
                    if not all([date_str, start_time, end_time]):
                        raise ValueError("Please fill in all fields")
                        
                    # Validate date and times
                    date = datetime.strptime(date_str, DATE_FMT)
                    start_dt = datetime.strptime(start_time, TIME_FMT)
                    end_dt = datetime.strptime(end_time, TIME_FMT)
                    
                    if end_dt <= start_dt:
                        raise ValueError("End time must be after start time")
                        
                    # Format: YYYY-MM-DD (HH:MM AM - HH:MM PM)
                    formatted = f"{date_str} ({start_time} - {end_time})"
                    self.days_off_list.insert(tk.END, formatted)
                    
                elif selection == "Multiple Days":
                    start_str = start_date_cal.get()
                    end_str = end_date_cal.get()
                    
                    if not all([start_str, end_str]):
                        raise ValueError("Please select both start and end dates")
                        
                    start_date = datetime.strptime(start_str, DATE_FMT)
                    end_date = datetime.strptime(end_str, DATE_FMT)
                    
                    if end_date < start_date:
                        raise ValueError("End date must be after start date")
                        
                    # Generate all dates in range
                    current = start_date
                    while current <= end_date:
                        self.days_off_list.insert(tk.END, current.strftime(DATE_FMT))
                        current += timedelta(days=1)
                
                # Mark that there are unsaved changes for this employee
                self.mark_employee_dirty()
                dialog.destroy()
                
            except ValueError as e:
                messagebox.showerror("Invalid Input", str(e))
            except Exception as e:
                messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD.")

        # Buttons frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=15)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Save", command=validate_and_save).pack(side="right", padx=5)

    def remove_requested_day(self):
        sel = self.days_off_list.curselection()
        if not sel:
            return
        self.days_off_list.delete(sel[0])
        # Mark dirty after removing a requested day
        self.mark_employee_dirty()

    def save_employee_changes(self, silent=False):
        sel = self.emp_listbox.curselection()
        if not sel:
            if not silent:
                messagebox.showwarning("Select Employee", "Please select an employee first.")
            return False
        idx = sel[0]
        # Get the employee name from the listbox
        emp_name = self.emp_listbox.get(idx)
        # Find the employee in the data by name
        emp = None
        for e in self.data["employees"]:
            if e.get("name") == emp_name:
                emp = e
                break
        
        if not emp:
            if not silent:
                messagebox.showerror("Error", "Employee not found.")
            return False
        
        # Availability parsing
        for day, w in self.avail_widgets.items():
            if w['var'].get():
                start = w['start_var'].get().strip()
                end = w['end_var'].get().strip()
                if not start or not end:
                    if not silent:
                        messagebox.showerror("Invalid", f"Please select start and end times for {day.capitalize()} or uncheck availability.")
                    return False
                # validate times and order
                try:
                    s_dt = datetime.strptime(start, TIME_FMT)
                    e_dt = datetime.strptime(end, TIME_FMT)
                    if e_dt <= s_dt:
                        if not silent:
                            messagebox.showerror("Invalid", f"End time must be after start time for {day.capitalize()}.")
                        return False
                    emp["availability"][day] = [s_dt.strftime(TIME_FMT), e_dt.strftime(TIME_FMT)]
                except Exception:
                    if not silent:
                        messagebox.showerror("Invalid", f"Invalid time selection for {day.capitalize()}.")
                    return False
            else:
                emp["availability"][day] = ["off"]
        # requested days off - handle both full days and partial days
        requested_off = []
        for i in range(self.days_off_list.size()):
            time_off = self.days_off_list.get(i)
            # Check if it's a partial day entry
            if "(" in time_off:  # Format: YYYY-MM-DD (HH:MM AM - HH:MM PM)
                date_part = time_off.split(" (")[0]
                time_part = time_off.split(" (")[1].rstrip(")")
                requested_off.append({
                    "date": date_part,
                    "type": "partial",
                    "times": time_part
                })
            else:  # Full day entry
                requested_off.append({
                    "date": time_off,
                    "type": "full"
                })
        
        emp["requested_days_off"] = requested_off
        save_data(self.data)
        # Update status indicator
        if silent:
            # Mark clean and briefly show Saved status
            self._employee_dirty = False
            try:
                self.save_indicator.config(text='✓ Saved')
                # Clear message after a short delay
                self.root.after(1200, lambda: self.save_indicator.config(text=''))
            except Exception:
                pass
        else:
            messagebox.showinfo("Saved", f"Saved changes for {emp['name']}")
            # Clear dirty flag after successful save
            self.clear_employee_dirty()
        # Clear any pending timer
        self._auto_save_timer = None
        return True

    # -------------------------
    # Schedule Tab
    # -------------------------
    def setup_schedule_tab(self):
        # Top navigation and controls
        top = tk.Frame(self.schedule_tab, pady=8)
        top.grid(row=0, column=0, sticky="ew")
        self.schedule_tab.grid_columnconfigure(0, weight=1)

        # Navigation frame with month controls
        nav = tk.Frame(top)
        nav.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(0, weight=1)

        # Navigation buttons and label in a grid
        self.prev_btn = tk.Button(nav, text="◀ Previous", command=self.prev_month)
        self.prev_btn.grid(row=0, column=0, padx=8)
        self.month_label = tk.Label(nav, text="", font=("Arial", 14, "bold"))
        self.month_label.grid(row=0, column=1, padx=8)
        self.next_btn = tk.Button(nav, text="Next ▶", command=self.next_month)
        self.next_btn.grid(row=0, column=2, padx=8)
        
        # Configure navigation frame columns
        nav.grid_columnconfigure(1, weight=1)

        # PDF button on the right
        pdf_btn = tk.Button(top, text="Generate PDF for Month", command=self.generate_month_pdf)
        pdf_btn.grid(row=0, column=1, padx=10)

        # Calendar frame
        self.calendar_frame = tk.Frame(self.schedule_tab, padx=10, pady=10)
        self.calendar_frame.grid(row=1, column=0, sticky="nsew")
        
        # Make calendar frame expand to fill space
        self.schedule_tab.grid_rowconfigure(1, weight=1)

        # draw initial calendar
        self.draw_calendar()

    def prev_month(self):
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self.draw_calendar()

    def next_month(self):
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self.draw_calendar()
        
    def update_ui_sizes_optimized(self):
        """Optimized UI size updates that don't recreate widgets"""
        try:
            # Clear font cache first to ensure fresh calculation
            self._cached_font_sizes.clear()
            
            base_font_size = self.calculate_font_size()
            header_font_size = min(base_font_size + 2, self.max_font_size)
            shift_font_size = max(int(base_font_size * 0.8), self.min_font_size)
            icon_font_size = int(min(base_font_size * 1.2, 18))
            
            # Cache font configurations
            normal_font = ("Arial", base_font_size)
            bold_font = ("Arial", base_font_size, "bold")
            header_font = ("Arial", header_font_size, "bold")
            shift_font = ("Arial", shift_font_size)
            icon_font = ("Arial", icon_font_size)
            
            # Update calendar elements without full redraw
            self.update_calendar_fonts(header_font, normal_font, shift_font, icon_font)
            
            # Update other UI elements
            self.update_other_ui_fonts(normal_font, header_font)
            
        except Exception as e:
            print(f"Error updating UI sizes: {e}")  # For debugging
    
    def update_calendar_fonts(self, header_font, normal_font, shift_font, icon_font):
        """Update calendar fonts without recreating the calendar"""
        if not hasattr(self, 'calendar_frame') or not self.calendar_frame.winfo_exists():
            return
            
        try:
            # Update month label
            if hasattr(self, 'month_label'):
                self.month_label.configure(font=header_font)
            
            # Update navigation buttons
            for btn in [getattr(self, 'prev_btn', None), getattr(self, 'next_btn', None)]:
                if btn and hasattr(btn, 'configure'):
                    btn.configure(font=normal_font)
            
            # Update day number labels directly
            self.update_day_number_fonts(normal_font)
            
            # Update calendar cells efficiently
            for cell in self.calendar_frame.winfo_children():
                self.update_cell_fonts_recursive(cell, header_font, normal_font, shift_font, icon_font)
                # Also update any hover managers in the cell
                self.update_hover_manager_fonts(cell)
                
        except Exception as e:
            print(f"Error updating calendar fonts: {e}")
            
    def update_day_number_fonts(self, normal_font):
        """Update day number fonts directly"""
        try:
            if hasattr(self, 'day_labels'):
                base_size = normal_font[1] if isinstance(normal_font, tuple) else 12
                day_font = ("Arial", base_size, "bold")
                
                for day_label in self.day_labels:
                    if day_label and hasattr(day_label, 'configure') and day_label.winfo_exists():
                        day_label.configure(font=day_font)
        except Exception as e:
            pass  # Skip any errors
            
    def update_hover_manager_fonts(self, cell):
        """Update fonts for hover manager icons in a calendar cell"""
        try:
            # Look for stored hover manager reference
            if hasattr(cell, '_hover_mgr'):
                hover_mgr = cell._hover_mgr
                if hover_mgr and hasattr(hover_mgr, 'update_icon_sizes'):
                    hover_mgr.update_icon_sizes(self)
        except:
            pass  # Skip any errors
            
    def update_cell_fonts_recursive(self, widget, header_font, normal_font, shift_font, icon_font):
        """Recursively update fonts in calendar cells"""
        try:
            if isinstance(widget, tk.Label):
                text = widget.cget("text")
                current_font = widget.cget("font")
                
                # Determine appropriate font based on label content and current font
                if text and text.strip().isdigit():  # Day numbers (pure digits)
                    # Day numbers should be bold
                    base_size = normal_font[1] if isinstance(normal_font, tuple) else normal_font
                    day_font = ("Arial", base_size, "bold")
                    widget.configure(font=day_font)
                elif text in ["✏️", "📋", "🗑️"]:  # Action icons
                    widget.configure(font=icon_font)
                elif text and "(" in text and "-" in text:  # Shift labels (contain time)
                    widget.configure(font=shift_font)
                elif text and len(text.strip()) <= 2 and text.strip():  # Very short labels (might be day numbers)
                    # Check if it's in a header-like position (likely a day number)
                    parent = widget.master
                    if parent and hasattr(parent, 'grid_info'):
                        grid_info = widget.grid_info() or widget.pack_info()
                        # If it's packed to the left or has grid row 0, it's likely a day number
                        if (grid_info and 
                            ((hasattr(widget, 'pack_info') and widget.pack_info().get('side') == 'left') or
                             (hasattr(widget, 'grid_info') and widget.grid_info().get('row') == 0))):
                            base_size = normal_font[1] if isinstance(normal_font, tuple) else normal_font
                            day_font = ("Arial", base_size, "bold")
                            widget.configure(font=day_font)
                        else:
                            widget.configure(font=normal_font)
                    else:
                        # Check if current font is bold (likely a day number)
                        if isinstance(current_font, tuple) and len(current_font) > 2 and "bold" in str(current_font):
                            base_size = normal_font[1] if isinstance(normal_font, tuple) else normal_font
                            day_font = ("Arial", base_size, "bold")
                            widget.configure(font=day_font)
                        else:
                            widget.configure(font=normal_font)
                else:  # Other labels
                    widget.configure(font=normal_font)
            
            # Recursively update children
            if hasattr(widget, 'winfo_children'):
                for child in widget.winfo_children():
                    self.update_cell_fonts_recursive(child, header_font, normal_font, shift_font, icon_font)
                    
        except Exception as e:
            pass  # Skip any problematic widgets
    
    def update_other_ui_fonts(self, normal_font, header_font):
        """Update fonts for non-calendar UI elements"""
        try:
            # Update employee tab elements
            self.update_employee_tab_fonts(normal_font, header_font)
            
            # Update admin tab elements
            self.update_admin_tab_fonts(normal_font, header_font)
                
            # Update other buttons throughout the app
            for attr_name in dir(self):
                attr = getattr(self, attr_name)
                if (isinstance(attr, tk.Button) and 
                    hasattr(attr, 'winfo_exists') and 
                    attr.winfo_exists()):
                    try:
                        attr.configure(font=normal_font)
                    except:
                        pass
                    
        except Exception as e:
            pass
            
    def update_employee_tab_fonts(self, normal_font, header_font):
        """Update all fonts in the employee tab"""
        try:
            if not hasattr(self, 'employee_tab_widgets'):
                return
                
            # Update headers
            for widget in self.employee_tab_widgets['headers']:
                if widget and hasattr(widget, 'configure') and widget.winfo_exists():
                    widget.configure(font=header_font)
            
            # Update labels
            for widget in self.employee_tab_widgets['labels']:
                if widget and hasattr(widget, 'configure') and widget.winfo_exists():
                    widget.configure(font=normal_font)
            
            # Update buttons
            for widget in self.employee_tab_widgets['buttons']:
                if widget and hasattr(widget, 'configure') and widget.winfo_exists():
                    widget.configure(font=normal_font)
            
            # Update listboxes
            if (self.employee_tab_widgets['listbox'] and 
                hasattr(self.employee_tab_widgets['listbox'], 'configure') and 
                self.employee_tab_widgets['listbox'].winfo_exists()):
                self.employee_tab_widgets['listbox'].configure(font=normal_font)
                
            # Update the days off listbox
            if hasattr(self, 'days_off_list') and self.days_off_list.winfo_exists():
                self.days_off_list.configure(font=normal_font)
                
        except Exception as e:
            pass
            
    def update_admin_tab_fonts(self, normal_font, header_font):
        """Update all fonts in the admin tab"""
        try:
            if not hasattr(self, 'admin_tab_widgets'):
                return
                
            # Update headers
            for widget in self.admin_tab_widgets['headers']:
                if widget and hasattr(widget, 'configure') and widget.winfo_exists():
                    widget.configure(font=header_font)
            
            # Update labels
            for widget in self.admin_tab_widgets['labels']:
                if widget and hasattr(widget, 'configure') and widget.winfo_exists():
                    widget.configure(font=normal_font)
                    
        except Exception as e:
            pass
            
    def update_ui_sizes(self):
        """Legacy method - redirects to optimized version"""
        self.update_ui_sizes_optimized()
        if len(self._cached_font_sizes) > 100:
            self._cached_font_sizes.clear()

    def setup_admin_tab(self):
        """Setup the Admin tab for managing store hours"""
        # Calculate font sizes for admin tab
        base_font_size = self.calculate_font_size()
        header_font_size = min(base_font_size + 4, self.max_font_size)  # Larger header
        
        # Main container with padding
        main_frame = tk.Frame(self.admin_tab, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title = tk.Label(main_frame, text="Store Hours Configuration", 
                        font=("Arial", header_font_size, "bold"))
        title.pack(pady=(0, 20))
        self.admin_tab_widgets['headers'].append(title)
        
        # Instructions
        instructions = tk.Label(main_frame, 
                               text="Configure the days and hours your store is open. "
                               "Unchecked days are considered closed.",
                               font=("Arial", base_font_size), fg="gray")
        instructions.pack(pady=(0, 20))
        self.admin_tab_widgets['labels'].append(instructions)
        
        # Create frame for store hours editor
        hours_frame = tk.Frame(main_frame)
        hours_frame.pack(fill="both", expand=True)
        
        # Headers - use calculated font sizes
        header_font = ("Arial", base_font_size, "bold")
        day_header = tk.Label(hours_frame, text="Day", font=header_font)
        day_header.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.admin_tab_widgets['headers'].append(day_header)
        
        open_header = tk.Label(hours_frame, text="Open", font=header_font)
        open_header.grid(row=0, column=1, padx=10, pady=5)
        self.admin_tab_widgets['headers'].append(open_header)
        
        start_header = tk.Label(hours_frame, text="Start Time", font=header_font)
        start_header.grid(row=0, column=2, padx=10, pady=5)
        self.admin_tab_widgets['headers'].append(start_header)
        
        end_header = tk.Label(hours_frame, text="End Time", font=header_font)
        end_header.grid(row=0, column=3, padx=10, pady=5)
        self.admin_tab_widgets['headers'].append(end_header)
        
        # Store widgets for each day
        self.store_hours_widgets = {}
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        
        # Generate time options (all possible times)
        all_times = generate_times("12:00 AM", "11:30 PM", 30)
        
        for i, day in enumerate(days):
            row = i + 1
            
            # Day label - use calculated font
            day_label = tk.Label(hours_frame, text=day.capitalize(), font=("Arial", base_font_size))
            day_label.grid(row=row, column=0, padx=10, pady=5, sticky="w")
            self.admin_tab_widgets['labels'].append(day_label)
            
            # Open checkbox
            is_open_var = tk.IntVar()
            store_hours = self.data.get("store_hours", {})
            day_hours = store_hours.get(day)
            
            if day_hours is not None:
                is_open_var.set(1)
            
            open_cb = tk.Checkbutton(hours_frame, variable=is_open_var)
            open_cb.grid(row=row, column=1, padx=10, pady=5)
            
            # Start time combobox
            start_var = tk.StringVar()
            start_cb = ttk.Combobox(hours_frame, textvariable=start_var, values=all_times, 
                                   state="readonly", width=12)
            start_cb.grid(row=row, column=2, padx=10, pady=5)
            
            # End time combobox
            end_var = tk.StringVar()
            end_cb = ttk.Combobox(hours_frame, textvariable=end_var, values=all_times, 
                                 state="readonly", width=12)
            end_cb.grid(row=row, column=3, padx=10, pady=5)
            
            # Set initial values
            if day_hours is not None:
                start_cb.set(day_hours[0])
                end_cb.set(day_hours[1])
                start_cb.configure(state="readonly")
                end_cb.configure(state="readonly")
            else:
                start_cb.set("")
                end_cb.set("")
                start_cb.configure(state="disabled")
                end_cb.configure(state="disabled")
            
            # Toggle function for enabling/disabling time selectors
            def make_toggle(s_cb=start_cb, e_cb=end_cb, v=is_open_var, d=day):
                def toggle(*args):
                    if v.get():
                        # Enable and set default times
                        s_cb.set("8:30 AM")
                        e_cb.set("7:00 PM")
                        s_cb.configure(state="readonly")
                        e_cb.configure(state="readonly")
                    else:
                        # Disable and clear
                        s_cb.set("")
                        e_cb.set("")
                        s_cb.configure(state="disabled")
                        e_cb.configure(state="disabled")
                    # Trigger auto-save
                    self.mark_store_hours_dirty()
                return toggle
            
            is_open_var.trace_add('write', make_toggle())
            
            # Add auto-save triggers for time changes
            start_var.trace_add('write', lambda *args: self.mark_store_hours_dirty())
            end_var.trace_add('write', lambda *args: self.mark_store_hours_dirty())
            
            # Store widgets
            self.store_hours_widgets[day] = {
                'is_open_var': is_open_var,
                'start_var': start_var,
                'end_var': end_var,
                'start_cb': start_cb,
                'end_cb': end_cb
            }
        
        # Auto-save indicator
        save_frame = tk.Frame(main_frame)
        save_frame.pack(pady=20)
        
        tk.Label(save_frame, text="Changes save automatically", 
                font=("Arial", 11, "bold")).pack(side="left")
        self.store_hours_indicator = tk.Label(save_frame, text="", fg="red", 
                                              font=("Arial", 10, "bold"))
        self.store_hours_indicator.pack(side="left", padx=(8, 0))
        
        # Initialize auto-save timer
        self._store_hours_timer = None
    
    def mark_store_hours_dirty(self):
        """Mark store hours as dirty and schedule auto-save"""
        try:
            self.store_hours_indicator.config(text='● Saving…')
        except Exception:
            pass
        
        # Debounce: cancel any pending auto-save and schedule a new one
        try:
            if self._store_hours_timer is not None:
                self.root.after_cancel(self._store_hours_timer)
        except Exception:
            pass
        
        # Save soon after user stops changing
        self._store_hours_timer = self.root.after(600, self.auto_save_store_hours)
    
    def auto_save_store_hours(self):
        """Auto-save store hours with validation"""
        # Validate and save store hours
        new_store_hours = {}
        errors = []
        
        for day, widgets in self.store_hours_widgets.items():
            if widgets['is_open_var'].get():
                start = widgets['start_var'].get()
                end = widgets['end_var'].get()
                
                if not start or not end:
                    errors.append(f"{day.capitalize()}: Please select both start and end times")
                    continue
                
                # Validate start is before end
                try:
                    start_dt = datetime.strptime(start, TIME_FMT)
                    end_dt = datetime.strptime(end, TIME_FMT)
                    
                    if start_dt >= end_dt:
                        errors.append(f"{day.capitalize()}: Start time must be before end time")
                        continue
                except Exception:
                    errors.append(f"{day.capitalize()}: Invalid time format")
                    continue
                
                new_store_hours[day] = (start, end)
            else:
                new_store_hours[day] = None
        
        if errors:
            # Show errors but don't save
            try:
                self.store_hours_indicator.config(text='✗ Error')
            except Exception:
                pass
            messagebox.showerror("Validation Error", "\n".join(errors))
            return
        
        # Save to data
        self.data["store_hours"] = new_store_hours
        save_data(self.data)
        
        # Refresh Employee Manager availability section
        self.refresh_employee_availability_times()
        
        # Redraw the calendar to update closed day colors
        self.draw_calendar()
        
        # Update indicator
        try:
            self.store_hours_indicator.config(text='✓ Saved')
            # Clear the saved indicator after 2 seconds
            self.root.after(2000, lambda: self.store_hours_indicator.config(text=''))
        except Exception:
            pass
    
    def refresh_employee_availability_times(self):
        """Refresh the time options in employee availability section based on new store hours"""
        if not hasattr(self, 'avail_widgets'):
            return
            
        for day, widgets in self.avail_widgets.items():
            store_hours = self.data.get("store_hours", {})
            store_range = store_hours.get(day)
            
            if store_range:
                times = generate_times(store_range[0], store_range[1])
            else:
                times = []
            
            # Update combobox values
            widgets['start_cb']['values'] = times
            widgets['end_cb']['values'] = times
            
            # Update state based on store hours
            if not store_range:
                # Store is now closed this day
                widgets['var'].set(0)
                widgets['checkbutton'].config(state="disabled")
                widgets['start_cb'].configure(state="disabled")
                widgets['end_cb'].configure(state="disabled")
            else:
                # Store is open, enable checkbox
                widgets['checkbutton'].config(state="normal")

    def draw_calendar(self):

        # Clear old labels list
        self.schedule_labels = []
        self.day_labels = []  # Track day number labels for font updates
        
        # Clear calendar
        for w in self.calendar_frame.winfo_children():
            w.destroy()

        # Calculate font sizes once for the entire calendar
        base_font_size = self.calculate_font_size()
        header_font = ("Arial", base_font_size, "bold")
        day_font = ("Arial", base_font_size, "bold")
        shift_font_size = max(int(base_font_size * 0.8), self.min_font_size)
        shift_font = ("Arial", shift_font_size)

        # Header label
        month_name = datetime(self.current_year, self.current_month, 1).strftime("%B %Y")
        self.month_label.config(text=month_name)

        # Configure calendar frame to expand cells evenly
        for i in range(7):  # 7 columns for days
            self.calendar_frame.grid_columnconfigure(i, weight=1)
        for i in range(7):  # 6 rows for weeks + 1 for headers
            self.calendar_frame.grid_rowconfigure(i, weight=1)

        # Weekday headers - use calculated font size
        days_header = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]
        for c, dh in enumerate(days_header):
            lbl = tk.Label(self.calendar_frame, text=dh, font=header_font, borderwidth=1, relief="groove")
            lbl.grid(row=0, column=c, padx=1, pady=1, sticky="nsew")

        # Set calendar to start on Sunday (6 = Sunday in Python's calendar module)
        cal = calendar.Calendar(firstweekday=6)
        month_days = cal.monthdayscalendar(self.current_year, self.current_month)
        # Rows for weeks start at row 1
        for r, week in enumerate(month_days, start=1):
            for c, day in enumerate(week):
                # Create cell frame that will expand with window
                cell_frame = tk.Frame(self.calendar_frame, borderwidth=1, relief="solid")
                cell_frame.grid(row=r, column=c, padx=2, pady=2, sticky="nsew")
                
                # Make the cell contents expand with the cell
                cell_frame.grid_columnconfigure(0, weight=1)
                cell_frame.grid_rowconfigure(0, weight=1)
                cell_frame.grid_rowconfigure(1, weight=4)  # Give more space to schedule area

                # Create hover effect manager for this cell
                class CellHoverManager:
                    def __init__(self, master):
                        self.master = master
                        self.hover_active = False
                        self.mouse_inside = False
                        
                        # Calculate icon size (will be set properly when parent_app is available)
                        icon_size = 14  # Default size, will be updated when actions are set
                        
                        # Create three action icons with better clickability
                        # 1. Edit icon (pen) - with padding for easier clicking
                        self.edit_label = tk.Label(master, text="✏️", font=("Arial", icon_size), 
                                                 fg="#4A4A4A", bg="SystemButtonFace", cursor="hand2",
                                                 padx=4, pady=2, relief="flat")
                        self.edit_label.place_forget()
                        
                        # 2. Copy icon (clipboard) - with padding for easier clicking
                        self.copy_label = tk.Label(master, text="📋", font=("Arial", icon_size), 
                                                 fg="#2E8B57", bg="SystemButtonFace", cursor="hand2",
                                                 padx=4, pady=2, relief="flat")
                        self.copy_label.place_forget()
                        
                        # 3. Delete icon (trash) - with padding for easier clicking
                        self.delete_label = tk.Label(master, text="🗑️", font=("Arial", icon_size), 
                                                   fg="#B22222", bg="SystemButtonFace", cursor="hand2",
                                                   padx=4, pady=2, relief="flat")
                        self.delete_label.place_forget()
                        
                        # Add hover handling to all icons
                        for icon in [self.edit_label, self.copy_label, self.delete_label]:
                            icon.bind("<Enter>", self.on_icon_enter)
                            icon.bind("<Leave>", self.on_icon_leave)
                        
                        self.widgets_to_tint = []
                        
                        # Store day_str and shifts for actions
                        self.day_str = None
                        self.shifts = None
                        self.parent_app = None
                        
                    def update_icon_sizes(self, parent_app):
                        """Update icon sizes and positions based on parent app's font calculation"""
                        if parent_app:
                            base_font_size = parent_app.calculate_font_size()
                            icon_size = int(min(base_font_size * 1.2, 18))
                            
                            icon_font = ("Arial", icon_size)
                            for icon in [self.edit_label, self.copy_label, self.delete_label]:
                                try:
                                    icon.configure(font=icon_font)
                                except:
                                    pass
                            
                            # Re-position icons if they're currently visible
                            if self.hover_active:
                                # Small delay to ensure widgets are updated, then reposition
                                self.master.after(10, self.reposition_icons)
                    
                    def reposition_icons(self):
                        """Reposition icons after resize to maintain proper hit areas"""
                        if self.hover_active:
                            self.hide_icons()
                            # Small delay then show again with updated positions
                            self.master.after(5, self.show_icons)
                    
                    def set_actions(self, day_str, shifts, parent_app):
                        """Set up action bindings for all three icons"""
                        self.day_str = day_str
                        self.shifts = shifts
                        self.parent_app = parent_app
                        
                        # Update icon sizes using parent app's font system
                        self.update_icon_sizes(parent_app)
                        
                        # Edit icon - click to open day editor
                        self.edit_label.bind("<Button-1>", lambda e: parent_app.open_day_editor(day_str))
                        
                        # Copy icon - click and drag to copy shifts
                        self.copy_label.bind("<Button-1>", self.start_copy_drag)
                        self.copy_label.bind("<B1-Motion>", self.continue_copy_drag)
                        self.copy_label.bind("<ButtonRelease-1>", self.end_copy_drag)
                        
                        # Delete icon - click to delete shifts with confirmation
                        self.delete_label.bind("<Button-1>", self.delete_shifts)
                    
                    def add_widget(self, widget):
                        self.widgets_to_tint.append(widget)
                        widget.bind("<Enter>", self.on_enter)
                        widget.bind("<Leave>", self.on_leave)
                    
                    def show_icons(self):
                        """Show the action icons if hover is active with proper spacing"""
                        if self.hover_active:
                            # Determine which icons to show
                            has_shifts = self.shifts and len(self.shifts) > 0
                            
                            if has_shifts:
                                # Show all three icons with equal spacing
                                self.edit_label.place(relx=0.2, rely=0.5, anchor="center")
                                self.copy_label.place(relx=0.5, rely=0.5, anchor="center")
                                self.delete_label.place(relx=0.8, rely=0.5, anchor="center")
                            else:
                                # Only show edit icon, centered
                                self.edit_label.place(relx=0.5, rely=0.5, anchor="center")
                            
                            # Lift all icons to top layer
                            for icon in [self.edit_label, self.copy_label, self.delete_label]:
                                icon.lift()
                                
                            # Add visual feedback on hover
                            self.add_icon_hover_effects()
                    
                    def add_icon_hover_effects(self):
                        """Add hover effects to make icons more interactive"""
                        def on_icon_hover_enter(icon, original_bg):
                            def handler(event):
                                icon.configure(bg="#E6E6E6", relief="raised")
                            return handler
                        
                        def on_icon_hover_leave(icon, original_bg):
                            def handler(event):
                                icon.configure(bg=original_bg, relief="flat")
                            return handler
                        
                        # Add hover effects to each visible icon
                        for icon in [self.edit_label, self.copy_label, self.delete_label]:
                            if icon.winfo_viewable():
                                original_bg = icon.cget("bg")
                                # Remove old bindings to avoid duplicates
                                icon.unbind("<Enter>")
                                icon.unbind("<Leave>")
                                # Add new hover bindings
                                icon.bind("<Enter>", on_icon_hover_enter(icon, original_bg))
                                icon.bind("<Leave>", on_icon_hover_leave(icon, original_bg))
                                # Re-add the main hover bindings
                                icon.bind("<Enter>", self.on_icon_enter, add="+")
                                icon.bind("<Leave>", self.on_icon_leave, add="+")
                            
                    def hide_icons(self):
                        """Hide the action icons"""
                        self.hover_active = False
                        for icon in [self.edit_label, self.copy_label, self.delete_label]:
                            icon.place_forget()
                    
                    def on_icon_enter(self, event=None):
                        """Handle mouse entering any icon"""
                        self.mouse_inside = True
                        # Keep the icons visible
                        self.hover_active = True
                        self.show_icons()
                    
                    def on_icon_leave(self, event=None):
                        """Handle mouse leaving any icon"""
                        self.mouse_inside = False
                        # Small delay to check if we're still in the cell
                        self.master.after(50, self.check_hide_icons)
                    
                    def check_hide_icons(self):
                        """Check if we should hide the icons"""
                        if not self.mouse_inside and not self.hover_active:
                            self.hide_icons()
                    
                    def on_enter(self, event=None):
                        """Handle mouse entering the cell or its widgets"""
                        self.hover_active = True
                        self.show_icons()
                    
                    def on_leave(self, event=None):
                        """Handle mouse leaving the cell or its widgets"""
                        self.hover_active = False
                        # Small delay to check if we're still in the icons
                        self.master.after(50, self.check_hide_icons)
                    
                    def start_copy_drag(self, event):
                        """Start copying shifts via drag operation"""
                        if self.shifts and len(self.shifts) > 0:
                            self.parent_app.start_ctrl_drag(event, self.day_str, self.shifts, self.copy_label)
                    
                    def continue_copy_drag(self, event):
                        """Continue copy drag operation"""
                        if self.parent_app.ctrl_drag_data["active"]:
                            self.parent_app.continue_ctrl_drag(event)
                    
                    def end_copy_drag(self, event):
                        """End copy drag operation"""
                        if self.parent_app.ctrl_drag_data["active"]:
                            self.parent_app.end_ctrl_drag(event)
                    
                    def delete_shifts(self, event):
                        """Delete all shifts for this day with confirmation"""
                        if not self.shifts or len(self.shifts) == 0:
                            return
                        
                        # Show confirmation dialog
                        from tkinter import messagebox
                        day_date = datetime.strptime(self.day_str, "%Y-%m-%d").strftime("%A, %B %d, %Y")
                        
                        result = messagebox.askyesno(
                            "Confirm Delete", 
                            f"Are you sure you want to delete all shifts for {day_date}?\n\n"
                            f"This will remove {len(self.shifts)} shift(s) and cannot be undone.",
                            icon="warning"
                        )
                        
                        if result:
                            self.parent_app.delete_day_shifts(self.day_str)
                
                # Create and configure hover manager for this cell
                hover_mgr = CellHoverManager(cell_frame)
                hover_mgr.add_widget(cell_frame)
                
                # Store reference for font updates
                cell_frame._hover_mgr = hover_mgr

                if day == 0:
                    # empty cell - set minimum size and darken background
                    cell_frame.config(bg="#D3D3D3")  # Light gray for empty cells
                    spacer = tk.Frame(cell_frame, width=140, height=100, bg="#D3D3D3")
                    spacer.grid(row=0, column=0)
                    continue

                # Check if store is closed on this day
                day_dt = date(self.current_year, self.current_month, day)
                day_str = day_dt.strftime(DATE_FMT)
                day_name = day_dt.strftime("%A").lower()
                store_hours = self.data.get("store_hours", {})
                is_closed = store_hours.get(day_name) is None
                
                # Set background color based on store status
                if is_closed:
                    bg_color = "#F0F0F0"  # Light grey for closed days (lighter than empty cells)
                else:
                    bg_color = "white"  # White for open days
                
                cell_frame.config(bg=bg_color)
                
                # Header frame (day number)
                header_frame = tk.Frame(cell_frame, bg=bg_color)
                header_frame.grid(row=0, column=0, sticky="ew")
                # Use pre-calculated day font
                day_label = tk.Label(header_frame, text=str(day), anchor="nw", font=day_font, bg=bg_color)
                day_label.pack(side="left", padx=4, pady=2)
                
                # Track day labels for font updates
                self.day_labels.append(day_label)
                
                # Content frame (shifts)
                content_frame = tk.Frame(cell_frame, bg=bg_color)
                content_frame.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
                
                # Add frames to hover manager
                hover_mgr.add_widget(header_frame)
                hover_mgr.add_widget(content_frame)
                hover_mgr.add_widget(day_label)
                
                # Get shifts
                month_key = f"{self.current_year}-{self.current_month:02d}"
                shifts = self.data.get("schedule", {}).get(month_key, {}).get(day_str, [])
                
                # Add shifts with auto-height and responsive text
                for s in shifts:
                    shift_frame = tk.Frame(content_frame, bg=bg_color)
                    shift_frame.pack(fill="x", expand=True, pady=1)
                    
                    # Create label with pre-calculated shift font
                    lbl = tk.Label(shift_frame, 
                                 text=f"{s['employee']} ({format_time_simple(s['start'])}-{format_time_simple(s['end'])})", 
                                 font=shift_font,
                                 anchor="w", bg=bg_color)
                    lbl.pack(fill="x", expand=True, padx=2)
                    
                    # Add to list of widgets to update during resize
                    self.schedule_labels.append((lbl, 'shift'))  # Store label and its type
                    
                    # Add shift widgets to hover manager
                    hover_mgr.add_widget(shift_frame)
                    hover_mgr.add_widget(lbl)

                # No longer need cell-wide bindings - icons handle their own actions
                
                # Set up the three action icons (edit, copy, delete)
                hover_mgr.set_actions(day_str, shifts, self)

    # Note: setup_cell_bindings method removed - icons now handle their own specific actions

    def start_ctrl_drag(self, event, day_str, shifts, source_widget):
        """Start Ctrl+drag operation"""
        self.ctrl_drag_data["active"] = True
        self.ctrl_drag_data["source_day"] = day_str
        self.ctrl_drag_data["source_shifts"] = shifts.copy()
        self.ctrl_drag_data["source_widget"] = source_widget
        
        # Visual feedback - change cursor and add border
        source_widget.configure(cursor="plus")
        
        # Find the cell frame (walk up the widget hierarchy)
        current = source_widget
        while current and current.master != self.calendar_frame:
            current = current.master
        
        if current:
            current.configure(relief="raised", borderwidth=3)
            self.ctrl_drag_data["source_cell"] = current

    def continue_ctrl_drag(self, event):
        """Handle mouse motion during Ctrl+drag"""
        if not self.ctrl_drag_data["active"]:
            return
        
        # Find widget under cursor
        x, y = event.x_root, event.y_root
        target_widget = self.root.winfo_containing(x, y)
        
        if target_widget:
            # Find if we're over a calendar cell
            current = target_widget
            while current and current.master != self.calendar_frame:
                current = current.master
            
            # Reset previous highlights
            for child in self.calendar_frame.winfo_children():
                if child != self.ctrl_drag_data.get("source_cell"):
                    child.configure(relief="solid", borderwidth=1)
            
            # Highlight current target
            if current and hasattr(current, 'winfo_children') and current != self.ctrl_drag_data.get("source_cell"):
                current.configure(relief="sunken", borderwidth=2)

    def end_ctrl_drag(self, event):
        """End Ctrl+drag operation and copy shifts if valid target"""
        if not self.ctrl_drag_data["active"]:
            return
        
        try:
            # Reset visual feedback
            if self.ctrl_drag_data["source_widget"]:
                self.ctrl_drag_data["source_widget"].configure(cursor="")
            
            if "source_cell" in self.ctrl_drag_data and self.ctrl_drag_data["source_cell"]:
                self.ctrl_drag_data["source_cell"].configure(relief="solid", borderwidth=1)
            
            # Reset all cell highlights
            for child in self.calendar_frame.winfo_children():
                child.configure(relief="solid", borderwidth=1)
            
            # Find drop target
            x, y = event.x_root, event.y_root
            target_widget = self.root.winfo_containing(x, y)
            
            if target_widget:
                # Find target day by looking for day_str in widget hierarchy
                target_day = self.find_day_str_in_widget_tree(target_widget)
                
                if (target_day and 
                    target_day != self.ctrl_drag_data["source_day"] and 
                    self.ctrl_drag_data["source_shifts"]):
                    
                    self.copy_shifts_to_day(self.ctrl_drag_data["source_shifts"], target_day)
        
        finally:
            # Reset drag state
            self.ctrl_drag_data = {"active": False, "source_day": None, "source_shifts": None, "source_widget": None}

    def find_day_str_in_widget_tree(self, widget):
        """Walk up widget tree to find a calendar cell and extract its day_str"""
        # Look through all calendar cells to find which one contains this widget
        for child in self.calendar_frame.winfo_children():
            if self.widget_is_descendant_of(widget, child):
                # Found the cell, now extract the day_str
                # Look for a label with day number text
                return self.extract_day_str_from_cell(child)
        return None

    def widget_is_descendant_of(self, widget, ancestor):
        """Check if widget is a descendant of ancestor"""
        current = widget
        while current and current != self.root:
            if current == ancestor:
                return True
            current = current.master
        return False

    def extract_day_str_from_cell(self, cell_widget):
        """Extract day string from a calendar cell widget"""
        try:
            # Look for the day label in the cell's children
            for child in cell_widget.winfo_children():
                if isinstance(child, tk.Frame):  # header_frame
                    for grandchild in child.winfo_children():
                        if isinstance(grandchild, tk.Label):
                            day_text = grandchild.cget("text")
                            if day_text.isdigit():
                                day_num = int(day_text)
                                # Convert to day_str format
                                day_dt = date(self.current_year, self.current_month, day_num)
                                return day_dt.strftime(DATE_FMT)
        except:
            pass
        return None

    def copy_shifts_to_day(self, shifts, target_day_str):
        """Copy shifts from source to target day"""
        try:
            # Parse target date to get month info
            target_dt = datetime.strptime(target_day_str, DATE_FMT).date()
            target_day_name = target_dt.strftime("%A").lower()
            
            # Check if target day is open
            store_hours = self.data.get("store_hours", {})
            if store_hours.get(target_day_name) is None:
                messagebox.showwarning("Cannot Copy", 
                                     f"Cannot copy shifts to {target_dt.strftime('%A')} - store is closed that day.")
                return
            
            month_key = f"{target_dt.year}-{target_dt.month:02d}"
            
            # Initialize schedule structure if needed
            if "schedule" not in self.data:
                self.data["schedule"] = {}
            if month_key not in self.data["schedule"]:
                self.data["schedule"][month_key] = {}
            if target_day_str not in self.data["schedule"][month_key]:
                self.data["schedule"][month_key][target_day_str] = []
            
            # Copy shifts to target day
            target_shifts = self.data["schedule"][month_key][target_day_str]
            
            # Check for duplicates before adding
            shifts_added = 0
            for shift in shifts:
                # Check if this exact shift already exists
                duplicate = False
                for existing in target_shifts:
                    if (existing["employee"] == shift["employee"] and 
                        existing["start"] == shift["start"] and 
                        existing["end"] == shift["end"]):
                        duplicate = True
                        break
                
                if not duplicate:
                    target_shifts.append(shift.copy())
                    shifts_added += 1
            
            if shifts_added > 0:
                # Save data and refresh calendar
                save_data(self.data)
                self.draw_calendar()
                
                messagebox.showinfo("Shifts Copied", 
                                  f"Successfully copied {shifts_added} shift(s) to {target_day_str}.")
            else:
                messagebox.showinfo("No Changes", 
                                  "All shifts already exist on the target day.")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy shifts: {str(e)}")

    def delete_day_shifts(self, day_str):
        """Delete all shifts for a specific day"""
        try:
            # Parse date to get month info
            day_dt = datetime.strptime(day_str, DATE_FMT).date()
            month_key = f"{day_dt.year}-{day_dt.month:02d}"
            
            # Remove shifts from data
            if "schedule" in self.data and month_key in self.data["schedule"]:
                if day_str in self.data["schedule"][month_key]:
                    deleted_count = len(self.data["schedule"][month_key][day_str])
                    del self.data["schedule"][month_key][day_str]
                    
                    # Save data and refresh calendar
                    save_data(self.data)
                    self.draw_calendar()
                    
                    messagebox.showinfo("Shifts Deleted", 
                                      f"Successfully deleted {deleted_count} shift(s) from {day_str}.")
                else:
                    messagebox.showinfo("No Shifts", "No shifts found to delete for this day.")
            else:
                messagebox.showinfo("No Shifts", "No shifts found to delete for this day.")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete shifts: {str(e)}")

    def open_day_editor(self, day_str):
        day_dt = datetime.strptime(day_str, DATE_FMT).date()
        day_name = day_dt.strftime("%A").lower()
        store_hours = self.data.get("store_hours", {})
        if store_hours.get(day_name) is None:
            messagebox.showinfo("Closed", f"Store is closed on {day_dt.strftime('%A')}. Cannot schedule.")
            return

        # Store current tab index before opening dialog
        current_tab = self.notebook.select()
        # Mark that a modal dialog is open to help guard resize flows if needed
        self._dialog_open = True

        win = tk.Toplevel(self.root)
        win.title(f"Edit Shifts for {day_str}")
        win.transient(self.root)
        win.grab_set()  # Make dialog modal - must be closed properly
        
        # Set size and center the dialog
        self.center_dialog(win, width=420, height=400)
        
        # Bind window close event to restore tab selection
        def _restore_tab_later():
            try:
                if current_tab:
                    self.notebook.select(current_tab)
                    self.root.focus_force()
            except Exception:
                pass

        def on_close():
            # Close the dialog and restore tab after a short delay so any pending
            # resize/redraw cycles complete first
            try:
                win.grab_release()
            except Exception:
                pass
            try:
                win.destroy()
            except Exception:
                pass
            self._dialog_open = False
            self.root.after(120, _restore_tab_later)
            
        win.protocol("WM_DELETE_WINDOW", on_close)

        # Existing shifts listbox
        tk.Label(win, text=f"Shifts on {day_str}", font=("Arial", 12, "bold")).pack(pady=6)
        shifts_frame = tk.Frame(win)
        shifts_frame.pack(fill="both", padx=8)
        shifts_listbox = tk.Listbox(shifts_frame, width=60, height=8)
        shifts_listbox.pack(side="left", fill="both", expand=True)
        scrollbar = tk.Scrollbar(shifts_frame, orient="vertical", command=shifts_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        shifts_listbox.config(yscrollcommand=scrollbar.set)

        month_key = f"{day_dt.year}-{day_dt.month:02d}"
        month_schedule = self.data.get("schedule", {}).get(month_key, {})
        day_shifts = month_schedule.get(day_str, [])

        for s in day_shifts:
            shifts_listbox.insert(tk.END, f"{s['employee']} | {s['start']} - {s['end']}")

        # Add/Edit area with status indicators
        form = tk.Frame(win, pady=8)
        form.pack(fill="x", padx=8)

        # Status indicator style
        def create_status_label():
            return tk.Label(form, text="", fg="red", width=30, anchor="w")

        # Employee row with status
        tk.Label(form, text="Employee:").grid(row=0, column=0, sticky="e", padx=4, pady=4)
        employees = []
        for e in self.data.get("employees", []):
            disp = ((e.get("firstName", "") + " " + e.get("lastName", "")).strip())
            if disp:
                employees.append(disp)
            else:
                employees.append(e.get("name", ""))
        # Sort employees alphabetically (case-insensitive)
        employees.sort(key=str.lower)
        emp_var = tk.StringVar()
        emp_cb = ttk.Combobox(form, textvariable=emp_var, values=employees, state="readonly")
        emp_cb.grid(row=0, column=1, padx=4, pady=4)
        emp_status = create_status_label()
        emp_status.grid(row=0, column=2, padx=4, pady=4)

        # Generate time options based on store hours for that day
        store_hours = self.data.get("store_hours", {})
        store_range = store_hours[day_name]  # tuple or None handled above
        times = generate_times(store_range[0], store_range[1])

        # Start time row with status
        tk.Label(form, text="Start:").grid(row=1, column=0, sticky="e", padx=4, pady=4)
        start_var = tk.StringVar()
        start_cb = ttk.Combobox(form, textvariable=start_var, values=times, state="readonly")
        start_cb.grid(row=1, column=1, padx=4, pady=4)
        start_status = create_status_label()
        start_status.grid(row=1, column=2, padx=4, pady=4)

        # End time row with status
        tk.Label(form, text="End:").grid(row=2, column=0, sticky="e", padx=4, pady=4)
        end_var = tk.StringVar()
        end_cb = ttk.Combobox(form, textvariable=end_var, values=times, state="readonly")
        end_cb.grid(row=2, column=1, padx=4, pady=4)
        end_status = create_status_label()
        end_status.grid(row=2, column=2, padx=4, pady=4)

        def check_conflicts(*args):
            emp_name = emp_var.get()
            start = start_var.get()
            end = end_var.get()
            
            # Create custom styles for valid/invalid states
            style = ttk.Style()
            style.configure("Valid.TCombobox", fieldbackground="white")
            style.configure("Invalid.TCombobox", fieldbackground="#ffe6e6")
            
            # Reset all to valid state
            emp_cb.configure(style="Valid.TCombobox")
            start_cb.configure(style="Valid.TCombobox")
            end_cb.configure(style="Valid.TCombobox")
            emp_status.config(text="")
            start_status.config(text="")
            end_status.config(text="")
            
            if not emp_name:
                return
                
            # Get employee data
            emp_data = self.find_employee_by_display(emp_name)
            if not emp_data:
                return
                
            has_conflicts = False
            
            # Check if employee already has ANY shift on this day
            month_key = f"{day_dt.year}-{day_dt.month:02d}"
            day_shifts_list = self.data.get("schedule", {}).get(month_key, {}).get(day_str, [])
            employee_already_scheduled = any(shift["employee"] == emp_name for shift in day_shifts_list)
            
            if employee_already_scheduled:
                emp_status.config(text="⚠ Already assigned to this day")
                emp_cb.configure(style="Invalid.TCombobox")
                has_conflicts = True

            # Check requested days off (supports new dict-format and legacy strings)
            def _time_overlap(a_start, a_end, b_start, b_end):
                return not (a_end <= b_start or a_start >= b_end)

            rd_list = emp_data.get("requested_days_off", [])
            for req in rd_list:
                # New structured format
                if isinstance(req, dict):
                    rtype = req.get("type")
                    rdate = req.get("date")
                    if rtype == "full" and rdate == day_str:
                        emp_status.config(text="⚠ Requested this day off")
                        emp_cb.configure(style="Invalid.TCombobox")
                        has_conflicts = True
                        break
                    if rtype == "partial" and rdate == day_str:
                        # times stored like "HH:MM AM - HH:MM PM"
                        times = req.get("times", "")
                        parts = [p.strip() for p in times.split("-")]
                        if len(parts) == 2:
                            try:
                                r_start = datetime.strptime(parts[0], TIME_FMT)
                                r_end = datetime.strptime(parts[1], TIME_FMT)
                                # if no start/end selected yet, indicate partial-day request
                                if not start and not end:
                                    emp_status.config(text="⚠ Requested partial day off")
                                    emp_cb.configure(style="Invalid.TCombobox")
                                    has_conflicts = True
                                    break
                                # if both selected, check overlap
                                if start and end:
                                    s_dt = datetime.strptime(start, TIME_FMT)
                                    e_dt = datetime.strptime(end, TIME_FMT)
                                    if _time_overlap(s_dt, e_dt, r_start, r_end):
                                        emp_status.config(text="⚠ Requested partial day off (overlaps)")
                                        start_cb.configure(style="Invalid.TCombobox")
                                        end_cb.configure(style="Invalid.TCombobox")
                                        has_conflicts = True
                                        break
                            except Exception:
                                pass
                else:
                    # legacy string format
                    if req == day_str:
                        emp_status.config(text="⚠ Requested this day off")
                        emp_cb.configure(style="Invalid.TCombobox")
                        has_conflicts = True
                        break
                
            # Check availability
            availability = emp_data.get("availability", {}).get(day_name, ["off"])
            if availability == ["off"]:
                emp_status.config(text="⚠ Not available this day")
                emp_cb.configure(style="Invalid.TCombobox")
                has_conflicts = True
            elif start or end:  # Only check times if they're selected
                try:
                    avail_start = datetime.strptime(availability[0], TIME_FMT)
                    avail_end = datetime.strptime(availability[1], TIME_FMT)
                    
                    if start:
                        s_dt = datetime.strptime(start, TIME_FMT)
                        if s_dt < avail_start:
                            start_status.config(text="⚠ Before availability start")
                            start_cb.configure(style="Invalid.TCombobox")
                            has_conflicts = True
                            
                    if end:
                        e_dt = datetime.strptime(end, TIME_FMT)
                        if e_dt > avail_end:
                            end_status.config(text="⚠ After availability end")
                            end_cb.configure(style="Invalid.TCombobox")
                            has_conflicts = True
                        
                        # Check if start and end are both selected and if end is before or equal to start
                        if start and e_dt <= datetime.strptime(start, TIME_FMT):
                            end_status.config(text="⚠ Must be after start time")
                            end_cb.configure(style="Invalid.TCombobox")
                            has_conflicts = True
                            
                except Exception:
                    pass
                    
            # Check for overlapping shifts if we have both start and end times
            if start and end and emp_name:
                try:
                    s_dt = datetime.strptime(start, TIME_FMT)
                    e_dt = datetime.strptime(end, TIME_FMT)
                    month_key = f"{day_dt.year}-{day_dt.month:02d}"
                    shifts = self.data.get("schedule", {}).get(month_key, {}).get(day_str, [])
                    
                    for shift in shifts:
                        if shift["employee"] == emp_name:
                            shift_start = datetime.strptime(shift["start"], TIME_FMT)
                            shift_end = datetime.strptime(shift["end"], TIME_FMT)
                            if not (e_dt <= shift_start or s_dt >= shift_end):
                                emp_status.config(text="⚠ Overlaps with existing shift")
                                start_cb.configure(style="Invalid.TCombobox")
                                end_cb.configure(style="Invalid.TCombobox")
                                has_conflicts = True
                except Exception:
                    pass

        # Bind change events
        emp_var.trace_add("write", check_conflicts)
        start_var.trace_add("write", check_conflicts)
        end_var.trace_add("write", check_conflicts)

        def add_shift():
            emp_name = emp_var.get()
            start = start_var.get()
            end = end_var.get()
            month_key = f"{day_dt.year}-{day_dt.month:02d}"  # Define month_key at the start
            
            if not emp_name or not start or not end:
                messagebox.showwarning("Missing", "Select employee, start, and end times.")
                return
            # Ensure end is after start
            try:
                s_dt = datetime.strptime(start, TIME_FMT)
                e_dt = datetime.strptime(end, TIME_FMT)
                if e_dt <= s_dt:
                    messagebox.showerror("Invalid", "End time must be after start time.")
                    return
            except Exception:
                messagebox.showerror("Invalid", "Time parse error.")
                return

            # validation: employee availability + requested days off
            emp_data = self.find_employee_by_display(emp_name)
            if not emp_data:
                messagebox.showerror("Missing", "Selected employee not found.")
                return
            
            # Collect all conflicts
            conflicts = []
            
            # Check requested days off (support both structured and legacy formats)
            rd_list = emp_data.get("requested_days_off", [])
            for req in rd_list:
                if isinstance(req, dict):
                    rtype = req.get("type")
                    rdate = req.get("date")
                    if rdate != day_str:
                        continue
                    if rtype == "full":
                        conflicts.append(f"{emp_name} requested this day off")
                    elif rtype == "partial":
                        times = req.get("times", "")
                        parts = [p.strip() for p in times.split("-")]
                        if len(parts) == 2:
                            try:
                                r_start = datetime.strptime(parts[0], TIME_FMT)
                                r_end = datetime.strptime(parts[1], TIME_FMT)
                                if not (e_dt <= r_start or s_dt >= r_end):
                                    conflicts.append(f"Requested partial day off ({parts[0]} - {parts[1]})")
                            except Exception:
                                # if malformed, just report requested day
                                conflicts.append(f"{emp_name} requested this day off")
                else:
                    # legacy string
                    if req == day_str:
                        conflicts.append(f"{emp_name} requested this day off")
                
            # Check day availability
            availability = emp_data.get("availability", {}).get(day_name, ["off"])
            if availability == ["off"]:
                conflicts.append(f"{emp_name} is not available on {day_name.capitalize()}s")
            else:
                # availability should be [start, end]
                try:
                    avail_start = datetime.strptime(availability[0], TIME_FMT)
                    avail_end = datetime.strptime(availability[1], TIME_FMT)
                    if s_dt < avail_start:
                        conflicts.append(f"Shift starts at {start} but {emp_name} is only available from {availability[0]}")
                    if e_dt > avail_end:
                        conflicts.append(f"Shift ends at {end} but {emp_name} is only available until {availability[1]}")
                except Exception:
                    messagebox.showerror("Invalid", f"{emp_name}'s availability data is malformed for {day_name}.")
                    return
                    
            # Check for overlap with existing shifts
            shifts = self.data.get("schedule", {}).get(month_key, {}).get(day_str, [])
            for shift in shifts:
                if shift["employee"] == emp_name:
                    shift_start = datetime.strptime(shift["start"], TIME_FMT)
                    shift_end = datetime.strptime(shift["end"], TIME_FMT)
                    if not (e_dt <= shift_start or s_dt >= shift_end):
                        conflicts.append(f"Overlaps with existing shift ({shift['start']} - {shift['end']})")
                        
            if conflicts:
                message = "The following conflicts were found:\n\n"
                message += "\n".join(f"• {conflict}" for conflict in conflicts)
                message += "\n\nDo you want to schedule this shift anyway?"
                if not messagebox.askyesno("Scheduling Conflicts", message):
                    return

            # All checks passed -> add shift
            month_key = f"{day_dt.year}-{day_dt.month:02d}"
            if "schedule" not in self.data:
                self.data["schedule"] = {}
            if month_key not in self.data["schedule"]:
                self.data["schedule"][month_key] = {}
            self.data["schedule"][month_key].setdefault(day_str, []).append({
                "employee": emp_name,
                "start": start,
                "end": end
            })
            save_data(self.data)
            # refresh UI
            shifts_listbox.insert(tk.END, f"{emp_name} | {start} - {end}")
            self.draw_calendar()
            messagebox.showinfo("Added", "Shift added.")
            # optionally clear selections
            emp_cb.set("")
            start_cb.set("")
            end_cb.set("")

        def remove_selected_shift():
            sel = shifts_listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            # remove from data
            month_key = f"{day_dt.year}-{day_dt.month:02d}"
            if month_key in self.data.get("schedule", {}) and day_str in self.data["schedule"][month_key]:
                try:
                    removed = self.data["schedule"][month_key][day_str].pop(idx)
                except IndexError:
                    return
                if not self.data["schedule"][month_key][day_str]:
                    # remove empty day entry
                    del self.data["schedule"][month_key][day_str]
                save_data(self.data)
                shifts_listbox.delete(idx)
                self.draw_calendar()
                messagebox.showinfo("Removed", f"Removed shift for {removed['employee']}")

        # Buttons
        btn_frame = tk.Frame(win, pady=8)
        btn_frame.pack()
        tk.Button(btn_frame, text="Add Shift", command=add_shift).grid(row=0, column=0, padx=6)
        tk.Button(btn_frame, text="Remove Selected Shift", command=remove_selected_shift).grid(row=0, column=1, padx=6)
        tk.Button(btn_frame, text="Close", command=on_close).grid(row=0, column=2, padx=6)

    def generate_month_pdf(self):
        month_key = f"{self.current_year}-{self.current_month:02d}"
        month_schedule = self.data.get("schedule", {}).get(month_key, {})
        default_name = f"Schedule_{month_key}.pdf"
        
        # Ask user where to save the file
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile=default_name,
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            title="Save Schedule PDF As"
        )
        
        if not file_path:  # User cancelled
            return
            
        c = canvas.Canvas(file_path, pagesize=letter)
        width, height = letter

        # Page header
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(width/2, height - 36, f"Work Schedule - {datetime(self.current_year, self.current_month, 1).strftime('%B %Y')}")

        # Calendar grid layout
        margin_x = 36
        margin_y = 60
        grid_width = width - 2 * margin_x
        grid_height = height - margin_y - 100
        cols = 7
        rows = 6  # max weeks in month
        cell_w = grid_width / cols
        cell_h = grid_height / rows

        # Weekday header labels
        c.setFont("Helvetica-Bold", 10)
        weekdays = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]
        for i, wd in enumerate(weekdays):
            x = margin_x + i * cell_w + 4
            y = height - 72
            c.drawString(x, y, wd)

        # Draw cells and fill days - Set calendar to start on Sunday
        cal_obj = calendar.Calendar(firstweekday=6)
        first_week = cal_obj.monthdayscalendar(self.current_year, self.current_month)
        # ensure 6 rows
        while len(first_week) < rows:
            first_week.append([0]*7)

        c.setFont("Helvetica", 9)
        for r, week in enumerate(first_week):
            for cidx, day in enumerate(week):
                x0 = margin_x + cidx * cell_w
                y0 = height - 90 - r * cell_h
                
                # Determine cell fill color based on day status
                if day == 0:
                    # Empty cell (no date) - dark grey
                    c.setFillColorRGB(0.827, 0.827, 0.827)  # #D3D3D3
                    c.rect(x0, y0 - cell_h, cell_w, cell_h, stroke=1, fill=1)
                    c.setFillColorRGB(0, 0, 0)  # Reset to black for text
                    continue
                
                # Check if store is closed on this day
                day_dt = date(self.current_year, self.current_month, day)
                day_str = day_dt.strftime(DATE_FMT)
                day_name = day_dt.strftime("%A").lower()
                store_hours = self.data.get("store_hours", {})
                is_closed = store_hours.get(day_name) is None
                
                if is_closed:
                    # Closed day - light grey
                    c.setFillColorRGB(0.941, 0.941, 0.941)  # #F0F0F0
                    c.rect(x0, y0 - cell_h, cell_w, cell_h, stroke=1, fill=1)
                    c.setFillColorRGB(0, 0, 0)  # Reset to black for text
                else:
                    # Open day - white (no fill, just border)
                    c.rect(x0, y0 - cell_h, cell_w, cell_h, stroke=1, fill=0)
                
                # day number
                c.setFont("Helvetica-Bold", 10)
                c.drawString(x0 + 4, y0 - 14, str(day))
                # shifts
                shifts = month_schedule.get(day_str, [])
                if shifts:
                    # list shifts with wrapping and auto-adjust font size per cell
                    # padding inside cell
                    padding_x = 6
                    max_text_w = cell_w - (padding_x + 4)
                    font_name = "Helvetica"

                    # Starting and minimum font sizes
                    max_font = 8.0
                    min_font = 6.0

                    # initial y position below the day number
                    y_start = y0 - 28
                    bottom_limit = y0 - cell_h + 6

                    # Helper: wrap text into lines for a given font size
                    def wrap_text_to_width(text, font, size, max_width):
                        words = text.split()
                        lines = []
                        current = ""
                        for w in words:
                            test = (current + " " + w).strip() if current else w
                            width = c.stringWidth(test, font, size)
                            if width <= max_width:
                                current = test
                            else:
                                if current:
                                    lines.append(current)
                                # if single word is too long, break it into chunks
                                if c.stringWidth(w, font, size) > max_width:
                                    chunk = ""
                                    for ch in w:
                                        if c.stringWidth(chunk + ch, font, size) <= max_width:
                                            chunk += ch
                                        else:
                                            if chunk:
                                                lines.append(chunk)
                                            chunk = ch
                                    if chunk:
                                        current = chunk
                                    else:
                                        current = ""
                                else:
                                    current = w
                        if current:
                            lines.append(current)
                        return lines

                    # Build shift entries as (name, times) so we can render name then indented times
                    shift_entries = []
                    for s in shifts:
                        emp_display = s.get('employee', '')
                        # try to find matching employee record
                        matched = self.find_employee_by_display(emp_display)
                        if matched:
                            name_text = matched.get('firstName') or matched.get('name') or emp_display
                        else:
                            # fallback: use the first token (first name) of stored employee string
                            name_text = emp_display.split()[0] if emp_display else ""
                        start_time = format_time_simple(s.get('start', ''))
                        end_time = format_time_simple(s.get('end', ''))
                        times_text = f"{start_time}-{end_time}"
                        shift_entries.append((name_text, times_text))

                    # Try font sizes to fit all lines (combine name and times on one line)
                    chosen_font = None
                    chosen_lines_per_entry = None
                    chosen_line_height = None

                    for candidate in [max_font, max_font - 0.5, min_font]:
                        line_height = candidate * 1.2
                        all_lines_count = 0
                        lines_per_entry = []
                        for name_text, times_text in shift_entries:
                            # Combine name and times on one line
                            full_text = f"{name_text} {times_text}"
                            # Wrap the combined text
                            wrapped_lines = wrap_text_to_width(full_text, font_name, candidate, max_text_w)
                            lines_per_entry.append(wrapped_lines)
                            all_lines_count += len(wrapped_lines)
                        total_height = all_lines_count * line_height
                        available_height = y_start - bottom_limit
                        if total_height <= available_height:
                            chosen_font = candidate
                            chosen_lines_per_entry = lines_per_entry
                            chosen_line_height = line_height
                            break

                    # If none fit exactly, fallback to min font and compute lines (may overflow)
                    if not chosen_lines_per_entry:
                        candidate = min_font
                        chosen_font = candidate
                        chosen_line_height = candidate * 1.2
                        lines_per_entry = []
                        all_lines_count = 0
                        for name_text, times_text in shift_entries:
                            full_text = f"{name_text} {times_text}"
                            wrapped_lines = wrap_text_to_width(full_text, font_name, candidate, max_text_w)
                            lines_per_entry.append(wrapped_lines)
                            all_lines_count += len(wrapped_lines)
                        chosen_lines_per_entry = lines_per_entry

                    # Render lines, truncating with '+N more' if needed
                    c.setFont(font_name, chosen_font)
                    y_text = y_start
                    max_lines_fit = int((y_start - bottom_limit) // chosen_line_height)
                    rendered_lines = 0
                    total_lines = sum(len(lines) for lines in chosen_lines_per_entry)

                    for lines in chosen_lines_per_entry:
                        for line in lines:
                            if rendered_lines >= max_lines_fit:
                                break
                            c.drawString(x0 + padding_x, y_text, line)
                            y_text -= chosen_line_height
                            rendered_lines += 1
                        if rendered_lines >= max_lines_fit:
                            break
                    if total_lines > rendered_lines:
                        remaining = total_lines - rendered_lines
                        more_text = f"+{remaining} more"
                        # place indicator on the next line if space, otherwise replace last
                        if rendered_lines < max_lines_fit:
                            c.drawString(x0 + padding_x, y_text, more_text)
                        else:
                            last_y = y_start - (rendered_lines - 1) * chosen_line_height
                            c.drawString(x0 + padding_x, last_y, more_text)

        c.save()
        messagebox.showinfo("PDF Saved", f"Schedule saved as PDF successfully.")

    # Auto-Update System Methods
    def check_for_updates_on_startup(self):
        """Check for updates when the application starts."""
        def update_callback(latest_version, download_url, release_notes):
            if latest_version and version_compare(latest_version, APP_VERSION) > 0:
                # New version available
                self.show_update_available_dialog(latest_version, download_url, release_notes)
        
        # Check in background
        check_for_updates(update_callback)
    
    def show_update_available_dialog(self, latest_version, download_url, release_notes):
        """Show dialog when update is available."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Update Available")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        self.center_dialog(dialog, 500, 400)
        
        # Header
        header_frame = tk.Frame(dialog, bg="#49D3E6", height=60)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, text="🔄 Update Available", 
                font=("Arial", 16, "bold"), 
                bg="#49D3E6", fg="white").pack(expand=True)
        
        # Content
        content_frame = tk.Frame(dialog, padx=20, pady=20)
        content_frame.pack(fill="both", expand=True)
        
        # Version info
        info_text = f"A new version ({latest_version}) is available!\nYour current version: {APP_VERSION}"
        tk.Label(content_frame, text=info_text, font=("Arial", 11)).pack(pady=(0, 15))
        
        # Release notes
        if release_notes:
            tk.Label(content_frame, text="What's New:", font=("Arial", 10, "bold")).pack(anchor="w")
            
            notes_frame = tk.Frame(content_frame)
            notes_frame.pack(fill="both", expand=True, pady=(5, 15))
            
            notes_text = tk.Text(notes_frame, height=8, wrap="word", font=("Arial", 9))
            scrollbar = tk.Scrollbar(notes_frame, orient="vertical", command=notes_text.yview)
            notes_text.configure(yscrollcommand=scrollbar.set)
            
            notes_text.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            notes_text.insert("1.0", release_notes)
            notes_text.config(state="disabled")
        
        # Buttons
        button_frame = tk.Frame(content_frame)
        button_frame.pack(fill="x", pady=(10, 0))
        
        def download_and_install():
            dialog.destroy()
            self.show_update_progress_dialog(download_url)
        
        def skip_update():
            dialog.destroy()
        
        tk.Button(button_frame, text="Download & Install", 
                 command=download_and_install, 
                 bg="#49D3E6", fg="white", 
                 font=("Arial", 10, "bold")).pack(side="right", padx=(10, 0))
        
        tk.Button(button_frame, text="Skip This Update", 
                 command=skip_update).pack(side="right")
    
    def show_update_progress_dialog(self, download_url):
        """Show progress dialog during update download."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Downloading Update")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        self.center_dialog(dialog, 400, 200)
        
        # Prevent closing during download
        dialog.protocol("WM_DELETE_WINDOW", lambda: None)
        
        # Header
        header_frame = tk.Frame(dialog, bg="#49D3E6", height=50)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, text="Downloading Update...", 
                font=("Arial", 14, "bold"), 
                bg="#49D3E6", fg="white").pack(expand=True)
        
        # Content
        content_frame = tk.Frame(dialog, padx=20, pady=20)
        content_frame.pack(fill="both", expand=True)
        
        # Progress info
        status_label = tk.Label(content_frame, text="Preparing download...", font=("Arial", 10))
        status_label.pack(pady=(0, 10))
        
        # Progress bar
        progress = ttk.Progressbar(content_frame, mode='determinate', length=300)
        progress.pack(pady=(0, 10))
        
        progress_label = tk.Label(content_frame, text="0%", font=("Arial", 9))
        progress_label.pack()
        
        def progress_callback(percent):
            progress['value'] = percent
            progress_label.config(text=f"{percent:.1f}%")
            status_label.config(text="Downloading...")
            dialog.update()
        
        def completion_callback(temp_file_path, error):
            if error:
                dialog.destroy()
                messagebox.showerror("Download Failed", f"Failed to download update:\n{error}")
                return
            
            # Download complete, ask to install
            dialog.destroy()
            
            response = messagebox.askyesno(
                "Install Update", 
                "Download complete! The application will close and restart to apply the update.\n\nContinue with installation?",
                icon="question"
            )
            
            if response:
                success = apply_update(temp_file_path)
                if success:
                    # Application will restart, so we exit here
                    self.root.quit()
                else:
                    # Clean up temp file if update failed
                    try:
                        os.remove(temp_file_path)
                    except:
                        pass
            else:
                # Clean up temp file if user declined
                try:
                    os.remove(temp_file_path)
                except:
                    pass
        
        # Start download
        download_update(download_url, progress_callback, completion_callback)
    
    def manual_check_for_updates(self):
        """Manually check for updates (called from menu)."""
        # Show checking dialog
        checking_dialog = tk.Toplevel(self.root)
        checking_dialog.title("Checking for Updates")
        checking_dialog.resizable(False, False)
        checking_dialog.transient(self.root)
        checking_dialog.grab_set()
        
        self.center_dialog(checking_dialog, 300, 150)
        
        tk.Label(checking_dialog, text="Checking for updates...", 
                font=("Arial", 12)).pack(expand=True, pady=20)
        
        # Prevent closing
        checking_dialog.protocol("WM_DELETE_WINDOW", lambda: None)
        
        def update_callback(latest_version, download_url, release_notes):
            checking_dialog.destroy()
            
            if latest_version:
                if version_compare(latest_version, APP_VERSION) > 0:
                    # New version available
                    self.show_update_available_dialog(latest_version, download_url, release_notes)
                else:
                    # Up to date
                    messagebox.showinfo("No Updates", 
                                       f"You're running the latest version ({APP_VERSION})!")
            else:
                # Error occurred
                messagebox.showerror("Update Check Failed", 
                                   "Could not check for updates. Please check your internet connection.")
        
        check_for_updates(update_callback)

def show_splash_screen(root):
    """Display a simple fade-in splash screen."""
    # Create splash window
    splash = tk.Toplevel()
    splash.overrideredirect(True)  # Remove window decorations
    
    # Set size and center on screen
    width = 400
    height = 200
    screen_width = splash.winfo_screenwidth()
    screen_height = splash.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    splash.geometry(f"{width}x{height}+{x}+{y}")
    splash.configure(bg="#49D3E6")
    
    # Create title label
    title_label = tk.Label(splash, text="Work Scheduler", 
                           font=("Arial", 32, "bold"), 
                           bg="#49D3E6", fg="white")
    title_label.pack(expand=True, pady=(60, 10))
    
    # Create subtitle label
    subtitle_label = tk.Label(splash, text="Brought to you by WILLSTER",
                             font=("Arial", 13),
                             bg="#49D3E6", fg="white")
    subtitle_label.pack(pady=(0, 20))
    
    # Fade in effect
    splash.attributes("-alpha", 0.0)
    alpha = [0.0]
    
    def fade_in():
        if alpha[0] < 1.0:
            alpha[0] += 0.05
            splash.attributes("-alpha", alpha[0])
            splash.after(30, fade_in)
        else:
            splash.after(1500, fade_out)  # Show for 1.5 seconds
    
    def fade_out():
        if alpha[0] > 0.0:
            alpha[0] -= 0.05
            splash.attributes("-alpha", alpha[0])
            splash.after(30, fade_out)
        else:
            splash.destroy()
            root.deiconify()
    
    fade_in()
    splash.update()

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Work Scheduler")
    
    # Hide main window initially
    root.withdraw()
    
    # Set theme for better looking widgets
    style = ttk.Style()
    if "clam" in style.theme_names():
        style.theme_use("clam")
    
    # Show splash screen first
    show_splash_screen(root)
    
    # Create app after a delay
    def create_app():
        app = WorkSchedulerApp(root)
    
    root.after(100, create_app)
    root.mainloop()
