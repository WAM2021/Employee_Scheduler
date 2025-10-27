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
APP_VERSION = "1.0.4"  # Current version of the application
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

def get_store_hours_for_date(date_str, store_hours_data):
    """Get store hours for a specific date based on day of week."""
    try:
        date_obj = datetime.strptime(date_str, DATE_FMT)
        day_name = date_obj.strftime('%A').lower()
        store_hours = store_hours_data.get(day_name)
        
        if store_hours is None:
            # Store is closed this day
            return None
        elif isinstance(store_hours, list) and len(store_hours) == 2:
            return store_hours
        else:
            # Fallback to default hours
            return ["8:30 AM", "7:00 PM"]
    except:
        # Fallback to default hours on any error
        return ["8:30 AM", "7:00 PM"]

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

def apply_update(update_file_path=None):
    """Launch the update assistant to guide the user through manual update."""
    try:
        # Create and launch the update assistant
        assistant_exe = create_update_assistant()
        if not assistant_exe:
            # Fallback: direct browser link
            import webbrowser
            webbrowser.open(f"https://github.com/{GITHUB_REPO}/releases/latest")
            messagebox.showinfo(
                "Update Available", 
                f"A new version is available!\n\n"
                f"Please download the latest version from the webpage that just opened.\n"
                f"Then replace your current Employee_Scheduler.exe file with the new one."
            )
            return True
        
        # Launch the assistant
        import subprocess
        subprocess.Popen([assistant_exe], 
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        return True
        
    except Exception as e:
        # Fallback: direct browser link
        import webbrowser
        try:
            webbrowser.open(f"https://github.com/{GITHUB_REPO}/releases/latest")
            messagebox.showinfo(
                "Update Available", 
                f"A new version is available!\n\n"
                f"Please download the latest version from the webpage that just opened.\n"
                f"Then replace your current Employee_Scheduler.exe file with the new one."
            )
        except:
            messagebox.showinfo(
                "Update Available", 
                f"A new version is available!\n\n"
                f"Please visit: https://github.com/{GITHUB_REPO}/releases/latest\n"
                f"Download the latest .exe file and replace your current one."
            )
        return True

def create_update_assistant():
    """Create the update assistant executable."""
    try:
        import tempfile
        import subprocess
        
        # Get the assistant source code
        current_dir = os.path.dirname(os.path.abspath(__file__))
        assistant_py = os.path.join(current_dir, "update_assistant.py")
        
        if not os.path.exists(assistant_py):
            return None
        
        # Create temporary directory for the assistant
        temp_dir = tempfile.mkdtemp()
        assistant_exe = os.path.join(temp_dir, "Update_Assistant.exe")
        
        # Build the assistant using PyInstaller
        build_cmd = [
            "pyinstaller",
            "--onefile",
            "--windowed",
            "--name", "Update_Assistant",
            "--distpath", temp_dir,
            "--workpath", os.path.join(temp_dir, "build"),
            "--specpath", temp_dir,
            assistant_py
        ]
        
        # Run PyInstaller
        result = subprocess.run(build_cmd, capture_output=True, text=True, cwd=current_dir)
        
        if result.returncode == 0 and os.path.exists(assistant_exe):
            return assistant_exe
        else:
            return None
            
    except Exception as e:
        return None

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
        
        # Dark Mode Color Palette - Professional and Eye-friendly
        self.colors = {
            'primary': '#60a5fa',        # Bright blue (readable on dark)
            'primary_dark': '#3b82f6',   # Slightly darker blue for hover
            'secondary': '#6b7280',      # Medium gray
            'background': '#111827',     # Dark background (almost black)
            'surface': '#1f2937',        # Dark surface containers
            'surface_alt': '#374151',    # Lighter dark surface for alternatives
            'text_primary': '#f9fafb',   # Light text (almost white)
            'text_secondary': '#d1d5db',  # Medium light gray text
            'text_muted': '#9ca3af',     # Muted gray text
            'success': '#10b981',        # Bright green
            'warning': '#f59e0b',        # Bright orange
            'danger': '#ef4444',         # Bright red
            'border': '#4b5563',         # Dark border color
            'accent': '#8b5cf6'          # Bright purple accent
        }
        
        # Add error handling for color access
        def get_color(self, key, fallback='#ffffff'):
            """Safely get a color from the palette with fallback"""
            return self.colors.get(key, fallback)
        
        # Bind the method to the instance
        self.get_color = get_color.__get__(self, type(self))
        
        # Set modern background for main window
        self.root.configure(bg=self.colors['background'])
        
        # Configure modern styles
        self.style = ttk.Style()
        
        # Configure Notebook (tabs) with dark mode styling
        self.style.configure('TNotebook', 
                           background=self.colors['surface'], 
                           borderwidth=0,
                           tabmargins=[2, 5, 2, 0])
        self.style.configure('TNotebook.Tab', 
                           background=self.colors['surface_alt'],
                           foreground=self.colors['text_secondary'],
                           padding=[20, 10],
                           borderwidth=0)
        self.style.map('TNotebook.Tab',
                      background=[('selected', self.colors['primary']),
                                ('active', self.colors['primary_dark'])],
                      foreground=[('selected', 'white'),
                                ('active', 'white')])
        
        # Dark mode Combobox styling
        self.style.configure('TCombobox',
                           fieldbackground=self.colors['surface'],
                           background=self.colors['surface'],
                           bordercolor=self.colors['border'],
                           arrowcolor=self.colors['text_secondary'],
                           focuscolor=self.colors['primary'],
                           foreground=self.colors['text_primary'])
        self.style.map('TCombobox',
            fieldbackground=[('disabled', self.colors['surface_alt']),
                           ('readonly', self.colors['surface'])],
            selectbackground=[('disabled', self.colors['surface_alt']),
                            ('readonly', self.colors['primary'])],
            selectforeground=[('disabled', self.colors['text_muted']),
                            ('readonly', 'white')],
            foreground=[('disabled', self.colors['text_muted']),
                       ('readonly', self.colors['text_primary'])])
        
        # Dark mode Button styling
        self.style.configure('TButton',
                           background=self.colors['surface_alt'],
                           foreground=self.colors['text_primary'],
                           bordercolor=self.colors['border'],
                           focuscolor=self.colors['primary'])
        self.style.map('TButton',
                      background=[('active', self.colors['primary']),
                                ('pressed', self.colors['primary_dark'])],
                      foreground=[('active', 'white'),
                                ('pressed', 'white')])
        
        # Dark mode Frame styling  
        self.style.configure('TFrame',
                           background=self.colors['surface'],
                           bordercolor=self.colors['border'])
        
        # Dark mode Label styling
        self.style.configure('TLabel',
                           background=self.colors['surface'],
                           foreground=self.colors['text_primary'])
        
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
        
        self.store_hours_tab_widgets = {
            'headers': [],
            'labels': []
        }
        
        # Ctrl+drag state for copying shifts
        self.ctrl_drag_data = {"active": False, "source_day": None, "source_shifts": None, "source_widget": None}
        
        # Initialize clipboard for copy/paste functionality
        self.copied_shifts = None

        # Data
        self.data = load_data()
        if "schedule" not in self.data:
            self.data["schedule"] = {}
            
        # Initialize application settings
        self.init_settings()
            
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
        self.store_hours_tab = tk.Frame(self.notebook)
        
        # Make tabs responsive
        self.employee_tab.grid_rowconfigure(0, weight=1)
        self.employee_tab.grid_columnconfigure(1, weight=3)  # Make center column expand more
        self.schedule_tab.grid_rowconfigure(1, weight=1)
        self.schedule_tab.grid_columnconfigure(0, weight=1)
        self.store_hours_tab.grid_rowconfigure(0, weight=1)
        self.store_hours_tab.grid_columnconfigure(0, weight=1)

        # Add tabs to notebook
        self.notebook.add(self.employee_tab, text="Employee Manager")
        self.notebook.add(self.schedule_tab, text="Schedule (Month View)")
        self.notebook.add(self.store_hours_tab, text="Store Hours")

        # Build UI
        self.setup_employee_tab()
        self.setup_schedule_tab()
        self.setup_store_hours_tab()
        
        # Show splash screen if enabled
        if self.get_setting('show_splash_screen', True):
            self.show_splash_screen()
        else:
            # If splash screen is disabled, show the main window immediately
            self.root.deiconify()
        
        # Check for updates on startup (in background)
        self.check_for_updates_on_startup()
        
        # Check if this was started after an update
        self.check_for_update_completion()
        
        # Bind resize event
        self.root.bind("<Configure>", self.on_window_resize)
        
    def create_modern_button(self, parent, text, command=None, style='primary', width=None):
        """Create a modern styled button with hover effects"""
        if style == 'primary':
            bg_color = self.colors['primary']
            hover_color = self.colors['primary_dark']
            text_color = 'white'
        elif style == 'secondary':
            bg_color = self.colors['secondary']
            hover_color = self.colors['text_primary']
            text_color = 'white'
        elif style == 'success':
            bg_color = self.colors['success']
            hover_color = '#047857'
            text_color = 'white'
        elif style == 'danger':
            bg_color = self.colors['danger']
            hover_color = '#b91c1c'
            text_color = 'white'
        else:  # default/surface
            bg_color = self.colors['surface']
            hover_color = self.colors['surface_alt']
            text_color = self.colors['text_primary']
            
        base_font_size = self.calculate_font_size()
        
        btn = tk.Button(parent, 
                       text=text,
                       command=command,
                       bg=bg_color,
                       fg=text_color,
                       font=("Segoe UI", base_font_size, "normal"),
                       relief='flat',
                       borderwidth=0,
                       pady=8,
                       padx=16,
                       cursor='hand2')
        
        if width:
            btn.configure(width=width)
            
        # Add hover effects
        def on_enter(e):
            btn.configure(bg=hover_color)
        def on_leave(e):
            btn.configure(bg=bg_color)
            
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        return btn
        
    def create_modern_frame(self, parent, padding=15):
        """Create a modern styled frame with subtle shadow effect"""
        frame = tk.Frame(parent, 
                        bg=self.colors['surface'],
                        relief='flat',
                        bd=1,
                        highlightbackground=self.colors['border'],
                        highlightthickness=1)
        return frame
            
    def center_dialog(self, dialog, width=None, height=None):
        """Center a dialog window relative to the main window and apply modern styling"""
        # Apply modern styling to dialog
        dialog.configure(bg=self.colors['background'])
        
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
        
        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Preferences", command=self.show_settings_dialog)
        settings_menu.add_separator()
        settings_menu.add_command(label="Reset to Defaults", command=self.reset_settings_to_defaults)
        
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
        
    def show_splash_screen(self):
        """Show a simple splash screen on startup"""
        # Create simple splash window
        splash = tk.Toplevel(self.root)
        splash.title("Work Scheduler")
        splash.resizable(False, False)
        splash.overrideredirect(True)  # Remove window decorations
        
        # Center splash on screen
        splash_width = 400
        splash_height = 300
        screen_width = splash.winfo_screenwidth()
        screen_height = splash.winfo_screenheight()
        x = (screen_width - splash_width) // 2
        y = (screen_height - splash_height) // 2
        splash.geometry(f"{splash_width}x{splash_height}+{x}+{y}")
        
        splash.configure(bg=self.colors['background'])
        splash.attributes("-topmost", True)
        
        # Header section
        header_frame = tk.Frame(splash, bg=self.colors['primary'], height=100)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, text="📅", font=("Arial", 32), 
                bg=self.colors['primary'], fg="white").pack(pady=(20, 5))
        
        tk.Label(header_frame, text="Work Scheduler", 
                font=("Arial", 18, "bold"), 
                bg=self.colors['primary'], fg="white").pack()
        
        # Content section
        content_frame = tk.Frame(splash, bg=self.colors['background'], pady=30)
        content_frame.pack(fill="both", expand=True)
        
        tk.Label(content_frame, text="Starting Employee Scheduler...", 
                font=("Arial", 12), 
                bg=self.colors['background'], fg=self.colors['text_primary']).pack(pady=20)
        
        # Progress bar
        progress_frame = tk.Frame(content_frame, bg=self.colors['border'], height=6, width=250)
        progress_frame.pack(pady=10)
        progress_frame.pack_propagate(False)
        
        progress_bar = tk.Frame(progress_frame, bg=self.colors['primary'], height=4)
        progress_bar.pack(side="left", fill="y", padx=1, pady=1)
        
        # Bottom section
        bottom_frame = tk.Frame(splash, bg=self.colors['background'], height=60)
        bottom_frame.pack(fill="x", side="bottom")
        bottom_frame.pack_propagate(False)
        
        tk.Label(bottom_frame, text=f"Version {APP_VERSION}", 
                font=("Arial", 9), 
                bg=self.colors['background'], fg=self.colors['text_secondary']).pack(pady=(10, 5))
        
        tk.Label(bottom_frame, text="Brought to you by WILLSTER", 
                font=("Arial", 9), 
                bg=self.colors['background'], fg=self.colors['text_secondary']).pack()
        
        # Don't show again option
        dont_show_var = tk.BooleanVar()
        dont_show_cb = tk.Checkbutton(bottom_frame, text="Don't show again", 
                                     variable=dont_show_var,
                                     font=("Arial", 8),
                                     bg=self.colors['background'],
                                     fg=self.colors['text_secondary'],
                                     selectcolor=self.colors['surface'])
        dont_show_cb.pack(side="bottom", pady=5)
        
        def on_dont_show_changed():
            if dont_show_var.get():
                self.set_setting('show_splash_screen', False)
        
        dont_show_var.trace('w', lambda *args: on_dont_show_changed())
        
        # Animate progress bar
        def animate_progress():
            current_width = progress_bar.winfo_width()
            if current_width < 240:  # Target width
                progress_bar.configure(width=current_width + 6)
                splash.after(50, animate_progress)
            else:
                # Animation complete, close splash
                splash.after(1000, close_and_show)
        
        # Timer to close and show main window
        def close_and_show():
            splash.destroy()
            self.root.deiconify()
            self.root.lift()
            
        # Start animation and set backup timer
        splash.after(100, animate_progress)
        splash.after(3000, close_and_show)  # Backup timer
    
    def close_splash_and_show_main(self, splash):
        """Helper method to properly close splash and show main window"""
        try:
            splash.grab_release()
        except:
            pass
        splash.destroy()
        # Show the main window
        self.root.deiconify()
        self.root.lift()  # Bring to front
        self.root.focus_force()  # Give it focus
        
    def show_changelog_dialog(self, old_version, new_version):
        """Show changelog dialog after an update"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Update Complete!")
        dialog.geometry("500x400")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_reqwidth() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_reqheight() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Header
        header_frame = tk.Frame(dialog, bg="#4CAF50", height=60)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, text="🎉 Update Complete!", font=("Arial", 16, "bold"), 
                bg="#4CAF50", fg="white").pack(expand=True)
        
        # Content
        content_frame = tk.Frame(dialog, padx=20, pady=20)
        content_frame.pack(fill="both", expand=True)
        
        # Update info
        update_text = f"Successfully updated from v{old_version} to v{new_version}!"
        tk.Label(content_frame, text=update_text, font=("Arial", 12, "bold")).pack(pady=(0, 15))
        
        # Changelog
        tk.Label(content_frame, text="What's New:", font=("Arial", 11, "bold")).pack(anchor="w")
        
        changelog_frame = tk.Frame(content_frame, relief="sunken", bd=1)
        changelog_frame.pack(fill="both", expand=True, pady=(5, 15))
        
        changelog_text = tk.Text(changelog_frame, wrap="word", font=("Arial", 9), 
                               height=10, bg="#f8f9fa", state="normal")
        scrollbar = tk.Scrollbar(changelog_frame, orient="vertical", command=changelog_text.yview)
        changelog_text.configure(yscrollcommand=scrollbar.set)
        
        # Initially show loading message
        changelog_text.insert("1.0", "Loading release notes...")
        changelog_text.config(state="disabled")
        
        changelog_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Buttons frame
        button_frame = tk.Frame(content_frame)
        button_frame.pack(fill="x", pady=(10, 0))
        
        def close_and_cleanup():
            """Close dialog and clean up old executable"""
            dialog.destroy()
            self.cleanup_old_executable()
        
        tk.Button(button_frame, text="Continue", command=close_and_cleanup, 
                 bg="#4CAF50", fg="white", font=("Arial", 10, "bold")).pack(side="right")
        
        # Fetch release notes asynchronously
        def fetch_release_notes_callback(latest_version, download_url, release_notes):
            """Callback to update changelog with fetched release notes"""
            try:
                changelog_text.config(state="normal")
                changelog_text.delete("1.0", tk.END)
                
                if release_notes and release_notes.strip():
                    # Format the GitHub markdown for better display
                    formatted_notes = self.format_github_markdown(release_notes)
                    changelog_text.insert("1.0", formatted_notes)
                else:
                    # Fallback content if no release notes available
                    fallback_content = f"""✨ Employee Scheduler v{new_version}

🎉 Successfully updated from v{old_version} to v{new_version}!

🔧 Improvements and fixes included in this release.

📋 For detailed release notes, visit:
https://github.com/{GITHUB_REPO}/releases/tag/v{new_version}

Thank you for keeping your application up to date!"""
                    changelog_text.insert("1.0", fallback_content)
                    
                changelog_text.config(state="disabled")
            except Exception as e:
                # Fallback if there's an error updating the text
                print(f"Error updating changelog: {e}")
        
        # Fetch the latest release notes
        check_for_updates(fetch_release_notes_callback)
    
    def format_github_markdown(self, markdown_text):
        """Convert GitHub markdown to plain text suitable for Tkinter Text widget"""
        import re
        
        # Start with the original text
        text = markdown_text
        
        # Remove markdown headers (keep the text but make it stand out)
        text = re.sub(r'^#{1,6}\s*(.+)$', r'🔹 \1', text, flags=re.MULTILINE)
        
        # Convert bullet points
        text = re.sub(r'^\s*[-*+]\s+(.+)$', r'• \1', text, flags=re.MULTILINE)
        
        # Convert numbered lists
        text = re.sub(r'^\s*\d+\.\s+(.+)$', r'• \1', text, flags=re.MULTILINE)
        
        # Remove bold/italic markdown (keep the text)
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        text = re.sub(r'__(.+?)__', r'\1', text)
        text = re.sub(r'_(.+?)_', r'\1', text)
        
        # Convert code blocks to simple quotes
        text = re.sub(r'```[\s\S]*?```', r'[Code block]', text)
        text = re.sub(r'`(.+?)`', r'"\1"', text)
        
        # Clean up links (show just the text part)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        
        # Clean up excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()
        
        return text
    
    def open_day_editor_dialog(self, day_str, shifts):
        """Open a day-specific shift editor dialog"""
        from datetime import datetime
        
        # Parse the day for display
        try:
            day_dt = datetime.strptime(day_str, DATE_FMT)
            day_name = day_dt.strftime("%A")
            formatted_date = day_dt.strftime("%B %d, %Y")
        except:
            day_name = "Unknown"
            formatted_date = day_str
        
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit Schedule - {formatted_date}")
        dialog.resizable(True, True)
        dialog.transient(self.root)
        dialog.grab_set()
        
        self.center_dialog(dialog, 700, 600)  # Made larger to ensure everything fits
        
        # Header with day info
        header_frame = tk.Frame(dialog, bg="#4A90E2", height=60)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        header_content = tk.Frame(header_frame, bg="#4A90E2")
        header_content.pack(expand=True, fill="both", padx=20, pady=10)
        
        tk.Label(header_content, text=f"{day_name}", 
                font=("Segoe UI", 18, "bold"), 
                bg="#4A90E2", fg="white").pack(anchor="w")
        tk.Label(header_content, text=formatted_date, 
                font=("Segoe UI", 11), 
                bg="#4A90E2", fg="white").pack(anchor="w")
        
        # Main content frame
        content_frame = tk.Frame(dialog)
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Current shifts section
        shifts_frame = tk.LabelFrame(content_frame, text="Current Shifts", font=("Segoe UI", 10, "bold"))
        shifts_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        # Scrollable frame for shifts
        canvas = tk.Canvas(shifts_frame, height=200)
        scrollbar = ttk.Scrollbar(shifts_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")
        
        # Refresh shifts list function
        def refresh_shifts_list():
            # Clear existing widgets
            for widget in scrollable_frame.winfo_children():
                widget.destroy()
            
            # Get current shifts for this day
            month_key = f"{day_dt.year}-{day_dt.month:02d}"
            current_shifts = self.data.get("schedule", {}).get(month_key, {}).get(day_str, [])
            
            if not current_shifts:
                no_shifts_label = tk.Label(scrollable_frame, 
                                         text="No shifts scheduled for this day",
                                         font=("Segoe UI", 10),
                                         fg="gray")
                no_shifts_label.pack(pady=20)
                return

            # Create header row
            header_frame = tk.Frame(scrollable_frame, bg="#f0f0f0", padx=10, pady=5)
            header_frame.pack(fill="x", padx=5, pady=(5, 2))
            
            # Configure grid columns for header
            header_frame.grid_columnconfigure(0, weight=2, minsize=150)  # Employee name column
            header_frame.grid_columnconfigure(1, weight=2, minsize=120)  # Time column
            header_frame.grid_columnconfigure(2, weight=1, minsize=120)  # Actions column
            
            tk.Label(header_frame, text="Employee", font=("Segoe UI", 10, "bold"), 
                    bg="#f0f0f0").grid(row=0, column=0, sticky="w", padx=(5, 0))
            tk.Label(header_frame, text="Shift Hours", font=("Segoe UI", 10, "bold"), 
                    bg="#f0f0f0").grid(row=0, column=1, sticky="w", padx=(5, 0))
            tk.Label(header_frame, text="Actions", font=("Segoe UI", 10, "bold"), 
                    bg="#f0f0f0").grid(row=0, column=2, sticky="w", padx=(5, 0))

            # Display each shift in columns
            for i, shift in enumerate(current_shifts):
                shift_frame = tk.Frame(scrollable_frame, relief="solid", bd=1, padx=10, pady=6)
                shift_frame.pack(fill="x", padx=5, pady=1)
                
                # Configure grid columns for shift row
                shift_frame.grid_columnconfigure(0, weight=2, minsize=150)  # Employee name column
                shift_frame.grid_columnconfigure(1, weight=2, minsize=120)  # Time column
                shift_frame.grid_columnconfigure(2, weight=1, minsize=120)  # Actions column
                
                # Employee name (column 0)
                emp_label = tk.Label(shift_frame, 
                                   text=shift['employee'], 
                                   font=("Segoe UI", 11, "bold"),
                                   anchor="w")
                emp_label.grid(row=0, column=0, sticky="w", padx=(5, 0))
                
                # Time info (column 1)
                time_label = tk.Label(shift_frame, 
                                    text=f"{shift['start']} - {shift['end']}", 
                                    font=("Segoe UI", 10, "bold"),
                                    fg="#666",
                                    anchor="w")
                time_label.grid(row=0, column=1, sticky="w", padx=(5, 0))
                
                # Action buttons frame (column 2)
                btn_frame = tk.Frame(shift_frame)
                btn_frame.grid(row=0, column=2, sticky="w", padx=(5, 0))
                
                # Edit button
                def edit_shift(shift_index=i):
                    self.edit_shift_dialog(dialog, day_str, shift_index, refresh_shifts_list)
                
                edit_btn = tk.Button(btn_frame, text="✎", 
                                   command=edit_shift,
                                   bg="#FFA726", fg="white",
                                   font=("Segoe UI", 9),
                                   relief="flat", width=3, height=1)
                edit_btn.pack(side="left", padx=(0, 3))
                
                # Delete button
                def delete_shift(shift_index=i):
                    if messagebox.askyesno("Confirm Delete", 
                                         f"Delete shift for {shift['employee']}?"):
                        month_key = f"{day_dt.year}-{day_dt.month:02d}"
                        self.data["schedule"][month_key][day_str].pop(shift_index)
                        if not self.data["schedule"][month_key][day_str]:
                            del self.data["schedule"][month_key][day_str]
                        save_data(self.data)
                        refresh_shifts_list()
                        self.draw_calendar()
                
                delete_btn = tk.Button(btn_frame, text="🗑", 
                                     command=delete_shift,
                                     bg="#F44336", fg="white",
                                     font=("Segoe UI", 9),
                                     relief="flat", width=3, height=1)
                delete_btn.pack(side="left")
        
        # Add new shift section
        add_frame = tk.LabelFrame(content_frame, text="Add New Shift", font=("Segoe UI", 10, "bold"))
        add_frame.pack(fill="x", pady=(0, 15))
        
        add_content = tk.Frame(add_frame)
        add_content.pack(fill="x", padx=15, pady=15)  # Increased padding
        
        # Employee selection
        tk.Label(add_content, text="Employee:", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=8)
        emp_var = tk.StringVar()
        employee_names = [emp.get("name", emp.get("display_name", "Unknown")) for emp in self.data.get("employees", [])]
        # Sort employees alphabetically (case-insensitive)
        employee_names.sort(key=str.lower)
        emp_combo = ttk.Combobox(add_content, textvariable=emp_var, values=employee_names, 
                               state="readonly", width=25, font=("Segoe UI", 10))
        emp_combo.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=8)
        
        # Time selection with better spacing
        tk.Label(add_content, text="Start Time:", font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="w", pady=8)
        start_var = tk.StringVar()
        
        # Get store hours for this specific date
        store_hours = get_store_hours_for_date(day_str, self.data.get("store_hours", {}))
        if store_hours:
            start_times = generate_times(store_hours[0], store_hours[1])
            end_times = generate_times(store_hours[0], store_hours[1])
        else:
            # Store is closed, use minimal times or show message
            start_times = generate_times("6:00 AM", "11:00 PM")
            end_times = generate_times("6:00 AM", "11:59 PM")
        
        start_combo = ttk.Combobox(add_content, textvariable=start_var, 
                                 values=start_times, width=15, font=("Segoe UI", 10))
        start_combo.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=8)
        
        tk.Label(add_content, text="End Time:", font=("Segoe UI", 10, "bold")).grid(row=2, column=0, sticky="w", pady=8)
        end_var = tk.StringVar()
        end_combo = ttk.Combobox(add_content, textvariable=end_var, 
                               values=end_times, width=15, font=("Segoe UI", 10))
        end_combo.grid(row=2, column=1, sticky="w", padx=(10, 0), pady=8)
        
        # Configure grid weights for better expansion
        add_content.grid_columnconfigure(1, weight=1)
        
        # Add some helpful placeholder text
        emp_combo.set("Select Employee...")
        start_combo.set("Select Start Time...")
        end_combo.set("Select End Time...")
        
        # Add shift function
        def add_new_shift():
            emp_name = emp_var.get()
            start_time = start_var.get()
            end_time = end_var.get()
            
            if not emp_name or not start_time or not end_time:
                messagebox.showwarning("Missing Information", 
                                     "Please select employee, start time, and end time.")
                return
            
            # Use comprehensive validation
            is_valid, conflicts = self.validate_shift_scheduling(
                emp_name, day_str, start_time, end_time, show_dialog=True)
            
            if not is_valid:
                return  # User chose not to proceed or validation failed
            
            # Add the shift
            month_key = f"{day_dt.year}-{day_dt.month:02d}"
            if "schedule" not in self.data:
                self.data["schedule"] = {}
            if month_key not in self.data["schedule"]:
                self.data["schedule"][month_key] = {}
            if day_str not in self.data["schedule"][month_key]:
                self.data["schedule"][month_key][day_str] = []
            
            self.data["schedule"][month_key][day_str].append({
                "employee": emp_name,
                "start": start_time,
                "end": end_time
            })
            
            save_data(self.data)
            refresh_shifts_list()
            self.draw_calendar()
            
            # Clear form
            emp_var.set("")
            start_var.set("")
            end_var.set("")
        
        # Add button with better spacing
        add_btn = tk.Button(add_content, text="➕ Add Shift", 
                          command=add_new_shift,
                          bg="#4CAF50", fg="white",
                          font=("Segoe UI", 11, "bold"),
                          relief="flat", padx=25, pady=8)
        add_btn.grid(row=3, column=0, columnspan=2, pady=20)
        
        # Bottom buttons
        btn_frame = tk.Frame(content_frame)
        btn_frame.pack(fill="x")
        
        tk.Button(btn_frame, text="Close", 
                 command=dialog.destroy,
                 font=("Segoe UI", 10),
                 padx=20, pady=5).pack(side="right")
        
        # Initial load
        refresh_shifts_list()
        
    def edit_shift_dialog(self, parent_dialog, day_str, shift_index, refresh_callback):
        """Open edit dialog for a specific shift"""
        from datetime import datetime
        
        day_dt = datetime.strptime(day_str, DATE_FMT)
        month_key = f"{day_dt.year}-{day_dt.month:02d}"
        shift = self.data["schedule"][month_key][day_str][shift_index]
        
        # Create edit dialog
        edit_dialog = tk.Toplevel(parent_dialog)
        edit_dialog.title("Edit Shift")
        edit_dialog.resizable(False, False)
        edit_dialog.transient(parent_dialog)
        edit_dialog.grab_set()
        
        self.center_dialog(edit_dialog, 350, 200)
        
        content = tk.Frame(edit_dialog, padx=20, pady=20)
        content.pack(fill="both", expand=True)
        
        # Employee
        tk.Label(content, text="Employee:", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", pady=5)
        emp_var = tk.StringVar(value=shift['employee'])
        employee_names = [emp.get("name", emp.get("display_name", "Unknown")) for emp in self.data.get("employees", [])]
        # Sort employees alphabetically (case-insensitive)
        employee_names.sort(key=str.lower)
        emp_combo = ttk.Combobox(content, textvariable=emp_var, values=employee_names, 
                               state="readonly", width=20)
        emp_combo.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=5)
        
        # Times
        tk.Label(content, text="Start Time:", font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", pady=5)
        start_var = tk.StringVar(value=shift['start'])
        
        # Get store hours for this specific date
        store_hours = get_store_hours_for_date(day_str, self.data.get("store_hours", {}))
        if store_hours:
            start_time_values = generate_times(store_hours[0], store_hours[1])
            end_time_values = generate_times(store_hours[0], store_hours[1])
        else:
            # Store is closed, use minimal times or show message
            start_time_values = generate_times("6:00 AM", "11:00 PM")
            end_time_values = generate_times("6:00 AM", "11:59 PM")
        
        start_combo = ttk.Combobox(content, textvariable=start_var, 
                                 values=start_time_values, width=12)
        start_combo.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=5)
        
        tk.Label(content, text="End Time:", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w", pady=5)
        end_var = tk.StringVar(value=shift['end'])
        end_combo = ttk.Combobox(content, textvariable=end_var, 
                               values=end_time_values, width=12)
        end_combo.grid(row=2, column=1, sticky="w", padx=(10, 0), pady=5)
        
        content.grid_columnconfigure(1, weight=1)
        
        # Buttons
        btn_frame = tk.Frame(content)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        def save_changes():
            emp_name = emp_var.get()
            start_time = start_var.get()
            end_time = end_var.get()
            
            if not emp_name or not start_time or not end_time:
                messagebox.showwarning("Missing Information", 
                                     "Please fill all fields.")
                return
            
            # Use comprehensive validation (exclude current shift from overlap check)
            is_valid, conflicts = self.validate_shift_scheduling(
                emp_name, day_str, start_time, end_time, 
                exclude_shift_index=shift_index, show_dialog=True)
            
            if not is_valid:
                return  # User chose not to proceed or validation failed
            
            # Update shift
            self.data["schedule"][month_key][day_str][shift_index] = {
                "employee": emp_name,
                "start": start_time,
                "end": end_time
            }
            
            save_data(self.data)
            refresh_callback()
            self.draw_calendar()
            edit_dialog.destroy()
        
        tk.Button(btn_frame, text="Save Changes", 
                 command=save_changes,
                 bg="#4CAF50", fg="white",
                 font=("Segoe UI", 10, "bold"),
                 relief="flat", padx=15).pack(side="right", padx=(5, 0))
        
        tk.Button(btn_frame, text="Cancel", 
                 command=edit_dialog.destroy,
                 font=("Segoe UI", 10),
                 padx=15).pack(side="right")
        
    def init_settings(self):
        """Initialize application settings with defaults"""
        default_settings = {
            'auto_save_interval': 600,  # milliseconds (10 minutes)
            'default_shift_length': 8,  # hours
            'time_format_24h': False,   # Use 12-hour format by default
            'start_week_on_monday': True,  # Calendar week start
            'show_employee_icons': True,  # Show emoji icons
            'auto_backup': True,        # Auto backup data
            'backup_frequency': 7,      # days
            'confirm_deletions': True,  # Confirm before deleting
            'theme': 'dark',            # UI theme
            'font_scaling': 1.0,        # Font scale multiplier
            'window_geometry': '1024x768',  # Default window size
            'remember_window_state': True,  # Remember window position/size
            'pdf_company_name': 'Your Company',  # For PDF headers
            'pdf_include_logo': False,  # Include logo in PDFs
            'default_break_time': 30,   # minutes
            'overtime_threshold': 40,   # hours per week
            'show_splash_screen': True  # Show splash screen on startup
        }
        
        # Load settings from data file or use defaults
        if 'settings' not in self.data:
            self.data['settings'] = default_settings.copy()
            save_data(self.data)
        else:
            # Merge any new default settings that don't exist
            for key, value in default_settings.items():
                if key not in self.data['settings']:
                    self.data['settings'][key] = value
            save_data(self.data)
        
        self.settings = self.data['settings']
        
    def get_setting(self, key, default=None):
        """Get a setting value with optional default"""
        return self.settings.get(key, default)
        
    def set_setting(self, key, value):
        """Set a setting value and save to file"""
        self.settings[key] = value
        self.data['settings'] = self.settings
        save_data(self.data)
        
    def show_settings_dialog(self):
        """Show the settings/preferences dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Settings & Preferences")
        dialog.resizable(True, True)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Set size and center the dialog
        self.center_dialog(dialog, width=600, height=500)
        
        # Apply modern styling
        dialog.configure(bg=self.colors['background'])
        
        # Create notebook for tabbed settings
        settings_notebook = ttk.Notebook(dialog)
        settings_notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # General settings tab
        general_frame = ttk.Frame(settings_notebook, padding="15")
        settings_notebook.add(general_frame, text="General")
        
        # Schedule settings tab
        schedule_frame = ttk.Frame(settings_notebook, padding="15")
        settings_notebook.add(schedule_frame, text="Schedule")
        
        # Appearance settings tab
        appearance_frame = ttk.Frame(settings_notebook, padding="15")
        settings_notebook.add(appearance_frame, text="Appearance")
        
        # PDF settings tab
        pdf_frame = ttk.Frame(settings_notebook, padding="15")
        settings_notebook.add(pdf_frame, text="PDF Export")
        
        # Store references to setting widgets for saving
        setting_vars = {}
        
        # === GENERAL SETTINGS ===
        ttk.Label(general_frame, text="General Settings", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 15))
        
        # Auto-save interval
        auto_save_frame = ttk.Frame(general_frame)
        auto_save_frame.pack(fill="x", pady=5)
        ttk.Label(auto_save_frame, text="Auto-save interval (seconds):").pack(side="left")
        setting_vars['auto_save_interval'] = tk.IntVar(value=self.get_setting('auto_save_interval', 600) // 1000)
        auto_save_spin = ttk.Spinbox(auto_save_frame, from_=1, to=60, textvariable=setting_vars['auto_save_interval'], width=10)
        auto_save_spin.pack(side="right")
        
        # Confirm deletions
        setting_vars['confirm_deletions'] = tk.BooleanVar(value=self.get_setting('confirm_deletions', True))
        ttk.Checkbutton(general_frame, text="Confirm before deleting items", 
                       variable=setting_vars['confirm_deletions']).pack(anchor="w", pady=5)
        
        # Auto backup
        setting_vars['auto_backup'] = tk.BooleanVar(value=self.get_setting('auto_backup', True))
        ttk.Checkbutton(general_frame, text="Enable automatic data backup", 
                       variable=setting_vars['auto_backup']).pack(anchor="w", pady=5)
        
        # Remember window state
        setting_vars['remember_window_state'] = tk.BooleanVar(value=self.get_setting('remember_window_state', True))
        ttk.Checkbutton(general_frame, text="Remember window size and position", 
                       variable=setting_vars['remember_window_state']).pack(anchor="w", pady=5)
        
        # === SCHEDULE SETTINGS ===
        ttk.Label(schedule_frame, text="Schedule Settings", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 15))
        
        # Default shift length
        shift_length_frame = ttk.Frame(schedule_frame)
        shift_length_frame.pack(fill="x", pady=5)
        ttk.Label(shift_length_frame, text="Default shift length (hours):").pack(side="left")
        setting_vars['default_shift_length'] = tk.IntVar(value=self.get_setting('default_shift_length', 8))
        shift_spin = ttk.Spinbox(shift_length_frame, from_=1, to=24, textvariable=setting_vars['default_shift_length'], width=10)
        shift_spin.pack(side="right")
        
        # Break time
        break_frame = ttk.Frame(schedule_frame)
        break_frame.pack(fill="x", pady=5)
        ttk.Label(break_frame, text="Default break time (minutes):").pack(side="left")
        setting_vars['default_break_time'] = tk.IntVar(value=self.get_setting('default_break_time', 30))
        break_spin = ttk.Spinbox(break_frame, from_=0, to=120, increment=15, textvariable=setting_vars['default_break_time'], width=10)
        break_spin.pack(side="right")
        
        # Overtime threshold
        overtime_frame = ttk.Frame(schedule_frame)
        overtime_frame.pack(fill="x", pady=5)
        ttk.Label(overtime_frame, text="Overtime threshold (hours per week):").pack(side="left")
        setting_vars['overtime_threshold'] = tk.IntVar(value=self.get_setting('overtime_threshold', 40))
        overtime_spin = ttk.Spinbox(overtime_frame, from_=20, to=60, textvariable=setting_vars['overtime_threshold'], width=10)
        overtime_spin.pack(side="right")
        
        # Time format
        setting_vars['time_format_24h'] = tk.BooleanVar(value=self.get_setting('time_format_24h', False))
        ttk.Checkbutton(schedule_frame, text="Use 24-hour time format", 
                       variable=setting_vars['time_format_24h']).pack(anchor="w", pady=5)
        
        # Start week on Monday
        setting_vars['start_week_on_monday'] = tk.BooleanVar(value=self.get_setting('start_week_on_monday', True))
        ttk.Checkbutton(schedule_frame, text="Start calendar week on Monday", 
                       variable=setting_vars['start_week_on_monday']).pack(anchor="w", pady=5)
        
        # === APPEARANCE SETTINGS ===
        ttk.Label(appearance_frame, text="Appearance Settings", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 15))
        
        # Font scaling
        font_scale_frame = ttk.Frame(appearance_frame)
        font_scale_frame.pack(fill="x", pady=5)
        ttk.Label(font_scale_frame, text="Font scaling:").pack(side="left")
        setting_vars['font_scaling'] = tk.DoubleVar(value=self.get_setting('font_scaling', 1.0))
        font_scale = ttk.Scale(font_scale_frame, from_=0.8, to=1.5, variable=setting_vars['font_scaling'], 
                              orient="horizontal", length=200)
        font_scale.pack(side="right", padx=(10, 0))
        font_label = ttk.Label(font_scale_frame, text="1.0x")
        font_label.pack(side="right", padx=(5, 10))
        
        def update_font_label(*args):
            font_label.configure(text=f"{setting_vars['font_scaling'].get():.1f}x")
        setting_vars['font_scaling'].trace('w', update_font_label)
        
        # Show employee icons
        setting_vars['show_employee_icons'] = tk.BooleanVar(value=self.get_setting('show_employee_icons', True))
        ttk.Checkbutton(appearance_frame, text="Show emoji icons for employees", 
                       variable=setting_vars['show_employee_icons']).pack(anchor="w", pady=5)
        
        # Show splash screen
        setting_vars['show_splash_screen'] = tk.BooleanVar(value=self.get_setting('show_splash_screen', True))
        ttk.Checkbutton(appearance_frame, text="Show splash screen on startup", 
                       variable=setting_vars['show_splash_screen']).pack(anchor="w", pady=5)
        
        # === PDF SETTINGS ===
        ttk.Label(pdf_frame, text="PDF Export Settings", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 15))
        
        # Company name
        company_frame = ttk.Frame(pdf_frame)
        company_frame.pack(fill="x", pady=5)
        ttk.Label(company_frame, text="Company name for PDF headers:").pack(anchor="w")
        setting_vars['pdf_company_name'] = tk.StringVar(value=self.get_setting('pdf_company_name', 'Your Company'))
        ttk.Entry(company_frame, textvariable=setting_vars['pdf_company_name'], width=40).pack(anchor="w", pady=(5, 0))
        
        # Include logo
        setting_vars['pdf_include_logo'] = tk.BooleanVar(value=self.get_setting('pdf_include_logo', False))
        ttk.Checkbutton(pdf_frame, text="Include company logo in PDFs", 
                       variable=setting_vars['pdf_include_logo']).pack(anchor="w", pady=5)
        
        # Buttons frame
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        def save_settings():
            """Save all settings and close dialog"""
            try:
                # Save all settings
                self.set_setting('auto_save_interval', setting_vars['auto_save_interval'].get() * 1000)  # Convert to milliseconds
                self.set_setting('confirm_deletions', setting_vars['confirm_deletions'].get())
                self.set_setting('auto_backup', setting_vars['auto_backup'].get())
                self.set_setting('remember_window_state', setting_vars['remember_window_state'].get())
                self.set_setting('default_shift_length', setting_vars['default_shift_length'].get())
                self.set_setting('default_break_time', setting_vars['default_break_time'].get())
                self.set_setting('overtime_threshold', setting_vars['overtime_threshold'].get())
                self.set_setting('time_format_24h', setting_vars['time_format_24h'].get())
                self.set_setting('start_week_on_monday', setting_vars['start_week_on_monday'].get())
                self.set_setting('font_scaling', setting_vars['font_scaling'].get())
                self.set_setting('show_employee_icons', setting_vars['show_employee_icons'].get())
                self.set_setting('show_splash_screen', setting_vars['show_splash_screen'].get())
                self.set_setting('pdf_company_name', setting_vars['pdf_company_name'].get())
                self.set_setting('pdf_include_logo', setting_vars['pdf_include_logo'].get())
                
                # Show success message
                messagebox.showinfo("Settings Saved", "Settings have been saved successfully!")
                dialog.destroy()
                
                # Apply immediate changes that affect UI
                self.apply_settings_changes()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
        
        def cancel_settings():
            """Close dialog without saving"""
            dialog.destroy()
        
        # Buttons
        ttk.Button(button_frame, text="Save", command=save_settings).pack(side="right", padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=cancel_settings).pack(side="right")
        ttk.Button(button_frame, text="Reset to Defaults", command=lambda: self.reset_settings_in_dialog(setting_vars)).pack(side="left")
        
    def reset_settings_in_dialog(self, setting_vars):
        """Reset settings to defaults within the dialog"""
        if messagebox.askyesno("Reset Settings", "Are you sure you want to reset all settings to their default values?"):
            # Reset all variables to defaults
            setting_vars['auto_save_interval'].set(10)  # 10 seconds (will be converted to 10000ms)
            setting_vars['confirm_deletions'].set(True)
            setting_vars['auto_backup'].set(True)
            setting_vars['remember_window_state'].set(True)
            setting_vars['default_shift_length'].set(8)
            setting_vars['default_break_time'].set(30)
            setting_vars['overtime_threshold'].set(40)
            setting_vars['time_format_24h'].set(False)
            setting_vars['start_week_on_monday'].set(True)
            setting_vars['font_scaling'].set(1.0)
            setting_vars['show_employee_icons'].set(True)
            setting_vars['show_splash_screen'].set(True)
            setting_vars['pdf_company_name'].set('Your Company')
            setting_vars['pdf_include_logo'].set(False)
    
    def reset_settings_to_defaults(self):
        """Reset all settings to default values"""
        if messagebox.askyesno("Reset Settings", 
                              "Are you sure you want to reset all settings to their default values?\n\n"
                              "This action cannot be undone."):
            self.init_settings()  # This will reload defaults
            messagebox.showinfo("Settings Reset", "All settings have been reset to their default values.")
            self.apply_settings_changes()
    
    def apply_settings_changes(self):
        """Apply settings changes that affect the UI immediately"""
        try:
            # Apply font scaling if it changed
            current_scaling = getattr(self, '_current_font_scaling', 1.0)
            new_scaling = self.get_setting('font_scaling', 1.0)
            if abs(current_scaling - new_scaling) > 0.1:  # Significant change
                self._current_font_scaling = new_scaling
                # Update UI fonts - this will trigger a full UI refresh
                self.update_ui_sizes_optimized()
            
            # Other immediate changes can be added here
            
        except Exception as e:
            print(f"Error applying settings changes: {e}")
            
    def cleanup_old_executable(self):
        """Clean up the old executable file after successful update"""
        try:
            import os
            import glob
            current_dir = os.path.dirname(sys.executable) if hasattr(sys, 'frozen') else os.getcwd()
            
            # Look for backup files to clean up
            backup_files = glob.glob(os.path.join(current_dir, "*.backup"))
            old_files = glob.glob(os.path.join(current_dir, "*_old.exe"))
            
            for file_path in backup_files + old_files:
                try:
                    os.remove(file_path)
                    print(f"Cleaned up: {file_path}")
                except:
                    pass  # Ignore cleanup errors
                    
        except Exception as e:
            print(f"Cleanup error (non-critical): {e}")
            pass  # Non-critical error
            
    def check_for_update_completion(self):
        """Check if app was updated by looking for update log and show success message"""
        try:
            import os
            current_dir = os.path.dirname(sys.executable) if hasattr(sys, 'frozen') else os.getcwd()
            log_file = os.path.join(current_dir, 'update_log.txt')
            
            # Check if update log exists and was modified recently (within last 5 minutes)
            if os.path.exists(log_file):
                import time
                file_mod_time = os.path.getmtime(log_file)
                current_time = time.time()
                
                # If log file was modified within last 5 minutes, likely an update just happened
                if (current_time - file_mod_time) < 300:  # 5 minutes
                    # Check if log contains successful update
                    try:
                        with open(log_file, 'r') as f:
                            log_content = f.read()
                            if "File replacement successful" in log_content and "Update completed successfully" in log_content:
                                # Schedule success message after UI loads
                                self.root.after(1000, self.show_update_success_message)
                    except:
                        pass  # Ignore errors reading log
                        
        except Exception as e:
            print(f"Error checking update completion: {e}")
            pass  # Non-critical error
            
    def show_update_success_message(self):
        """Show a simple success message when update is detected"""
        try:
            from tkinter import messagebox
            messagebox.showinfo(
                "Update Successful! 🎉", 
                f"Employee Scheduler has been successfully updated to version {APP_VERSION}!\n\n"
                "All your data and settings have been preserved.\n\n"
                "Thank you for keeping your application up to date!"
            )
        except Exception as e:
            print(f"Error showing update success: {e}")
            pass
        
    def calculate_font_size(self, base_size=10):
        """Calculate font size based on window dimensions with improved caching"""
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        
        # Return cached value if dimensions haven't changed significantly
        cache_key = (width // 25, height // 25)  # Finer grouping for better responsiveness
        if cache_key in self._cached_font_sizes:
            calculated_size = self._cached_font_sizes[cache_key]
        else:
            if width <= 100 or height <= 100:  # Window not yet properly realized
                calculated_size = base_size
            else:
                # Calculate new size based on smaller dimension for better scaling
                size = min(width, height)
                # More responsive scaling formula
                if size < 400:
                    scale_factor = 0.012  # Smaller scaling for small windows
                elif size < 800:
                    scale_factor = 0.014
                else:
                    scale_factor = 0.016  # Larger scaling for big windows
                    
                calculated_size = max(int(size * scale_factor), self.min_font_size)
                calculated_size = min(calculated_size, self.max_font_size)
                
                # Cache the result and limit cache size
                if len(self._cached_font_sizes) > 50:  # Prevent memory bloat
                    self._cached_font_sizes.clear()
                self._cached_font_sizes[cache_key] = calculated_size
        
        # Apply font scaling setting
        font_scaling = self.get_setting('font_scaling', 1.0) if hasattr(self, 'settings') else 1.0
        scaled_size = int(calculated_size * font_scaling)
        
        # Ensure the scaled size stays within bounds
        return max(min(scaled_size, self.max_font_size), self.min_font_size)
        
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
        self._resize_timer = self.root.after(150, self._on_resize_complete)
    
    def _on_resize_complete(self):
        """Complete resize operations including responsive sizing"""
        self.update_ui_sizes_optimized()
        self.update_hours_container_size()
        self.update_hover_managers_on_resize()
    
    def update_hover_managers_on_resize(self):
        """Update all hover managers after window resize"""
        try:
            # Update hover managers for all calendar cells
            if hasattr(self, 'calendar_frame') and self.calendar_frame.winfo_exists():
                for child in self.calendar_frame.winfo_children():
                    if hasattr(child, '_hover_mgr'):
                        # Trigger resize handling for each hover manager
                        child._hover_mgr.on_cell_resize()
        except:
            pass  # Silently handle any errors
    
    def update_hours_container_size(self):
        """Update the store hours layout for responsive sizing"""
        try:
            if not hasattr(self, 'content_frame') or not hasattr(self, 'hours_container'):
                return
                
            if not self.content_frame.winfo_exists():
                return
            
            # Force update of the grid layout
            self.content_frame.update_idletasks()
            
            # The grid automatically handles responsive sizing with the 3-column layout
            # Left and right spacers will scale, center content stays proportional
                
        except Exception as e:
            pass  # Silently handle any sizing errors
    #! Note: Do not rebuild tabs or UI here; it causes tab selection to reset
    # !and can lead to duplicated widgets. Resizing should only adjust sizes.

    # -------------------------
    # Employee Tab
    # -------------------------
    def setup_employee_tab(self):
        # Set tab background
        self.employee_tab.configure(bg=self.colors['background'])
        
        # Create modern frames with better spacing
        left = self.create_modern_frame(self.employee_tab)
        center = self.create_modern_frame(self.employee_tab)
        right = self.create_modern_frame(self.employee_tab)
        bottom = tk.Frame(self.employee_tab, bg=self.colors['background'])

        # Improved grid layout with better spacing
        left.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        center.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        right.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)
        bottom.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        # Configure column weights for proper resizing
        self.employee_tab.grid_columnconfigure(1, weight=3)  # Center gets more space
        self.employee_tab.grid_columnconfigure(0, weight=1)  # Left gets less space
        self.employee_tab.grid_columnconfigure(2, weight=1)  # Right gets less space
        
        # Configure row weight for vertical expansion
        self.employee_tab.grid_rowconfigure(0, weight=1)

        # Left: employee list with modern styling
        left_content = tk.Frame(left, bg=self.colors['surface'], padx=20, pady=20)
        left_content.pack(fill="both", expand=True)
        
        base_font_size = self.calculate_font_size()
        header_font_size = min(base_font_size + 3, self.max_font_size)
        
        emp_header = tk.Label(left_content, text="Employees", 
                             font=("Segoe UI", header_font_size, "bold"),
                             bg=self.colors['surface'],
                             fg=self.colors['text_primary'])
        emp_header.pack(pady=(0, 15))
        self.employee_tab_widgets['headers'].append(emp_header)
        
        # Listbox styling
        listbox_frame = tk.Frame(left_content, bg=self.colors['surface'])
        listbox_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        self.emp_listbox = tk.Listbox(listbox_frame, 
                                    width=30, height=18, 
                                    exportselection=False,
                                    font=("Segoe UI", base_font_size),
                                    bg=self.colors['surface'],
                                    fg=self.colors['text_primary'],
                                    selectbackground=self.colors['primary'],
                                    selectforeground='white',
                                    relief='flat',
                                    borderwidth=1,
                                    highlightbackground=self.colors['border'],
                                    highlightthickness=1,
                                    activestyle='none')
        self.emp_listbox.pack(fill="both", expand=True)
        self.emp_listbox.bind("<<ListboxSelect>>", self.on_employee_select)
        self.employee_tab_widgets['listbox'] = self.emp_listbox

        # Buttons with improved styling
        btn_frame = tk.Frame(left_content, bg=self.colors['surface'])
        btn_frame.pack(fill="x")
        
        add_btn = self.create_modern_button(btn_frame, "➕ Add Employee", self.add_employee, 'primary')
        add_btn.pack(fill="x", pady=2)
        self.employee_tab_widgets['buttons'].append(add_btn)
        
        edit_btn = self.create_modern_button(btn_frame, "✏️ Edit Name", self.edit_employee_name, 'secondary')
        edit_btn.pack(fill="x", pady=2)
        self.employee_tab_widgets['buttons'].append(edit_btn)
        
        remove_btn = self.create_modern_button(btn_frame, "🗑️ Remove Employee", self.remove_employee, 'danger')
        remove_btn.pack(fill="x", pady=2)
        self.employee_tab_widgets['buttons'].append(remove_btn)

        # Populate listbox
        self.refresh_employee_list()

        # Center: availability editor with modern styling
        center_content = tk.Frame(center, bg=self.colors['surface'], padx=20, pady=20)
        center_content.pack(fill="both", expand=True)
        
        avail_header = tk.Label(center_content, 
                               text="📅 Availability Schedule", 
                               font=("Segoe UI", header_font_size, "bold"),
                               bg=self.colors['surface'],
                               fg=self.colors['text_primary'])
        avail_header.grid(row=0, column=0, columnspan=4, pady=(0, 20), sticky="w")
        self.employee_tab_widgets['headers'].append(avail_header)
        
        sub_header = tk.Label(center_content,
                             text="Check days available and set working hours",
                             font=("Segoe UI", base_font_size - 1),
                             bg=self.colors['surface'],
                             fg=self.colors['text_secondary'])
        sub_header.grid(row=1, column=0, columnspan=4, pady=(0, 15), sticky="w")
        self.employee_tab_widgets['labels'].append(sub_header)
        
        self.days = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
        # day_emojis = ["🌙", "💼", "💼", "💼", "💼", "🌅", "☀️"]  # Sunday, Mon-Fri, Saturday
        
        # For each day we'll store widgets: { day: { 'var': IntVar, 'start_var': StringVar, 'end_var': StringVar, 'start_cb': Combobox, 'end_cb': Combobox } }
        self.avail_widgets = {}
        
        for i, day in enumerate(self.days):
            row = i + 2  # Start after headers
            
            # Day row container
            day_frame = tk.Frame(center_content, bg=self.colors['surface'])
            day_frame.grid(row=row, column=0, columnspan=4, sticky="ew", pady=3)
            center_content.grid_columnconfigure(0, weight=1)
            
            # Day label modern styling
            day_label = tk.Label(day_frame, 
                               text=f"{day.capitalize()}", 
                               font=("Segoe UI", base_font_size, "normal"),
                               bg=self.colors['surface'],
                               fg=self.colors['text_primary'],
                               width=12,
                               anchor="w")
            day_label.grid(row=0, column=0, sticky="w", padx=(10, 20))
            self.employee_tab_widgets['labels'].append(day_label)

            # Availability checkbox
            var = tk.IntVar(value=0)
            cb = tk.Checkbutton(day_frame, 
                              variable=var,
                              bg=self.colors['surface'],
                              fg=self.colors['text_primary'],
                              activebackground=self.colors['surface'],
                              selectcolor=self.colors['surface'],
                              font=("Segoe UI", base_font_size + 1),
                              text="Available")
            cb.grid(row=0, column=1, sticky="w", padx=(0, 15))

            # time options based on store hours for that day
            store_range = self.data.get("store_hours", {}).get(day)
            if store_range:
                times = generate_times(store_range[0], store_range[1])
            else:
                times = []

            # Start time combobox
            start_label = tk.Label(day_frame,
                                 text="Start:",
                                 font=("Segoe UI", base_font_size + 1),
                                 bg=self.colors['surface'],
                                 fg=self.colors['text_primary'])
            start_label.grid(row=0, column=2, sticky="w", padx=(0, 8))
            
            start_var = tk.StringVar()
            start_cb = ttk.Combobox(day_frame, textvariable=start_var, values=times, 
                                  state="readonly", width=10, font=("Segoe UI", base_font_size))
            start_cb.grid(row=0, column=3, padx=(0, 15))

            # End time combobox
            end_label = tk.Label(day_frame,
                               text="End:",
                               font=("Segoe UI", base_font_size + 1),
                               bg=self.colors['surface'],
                               fg=self.colors['text_primary'])
            end_label.grid(row=0, column=4, sticky="w", padx=(0, 8))
            
            end_var = tk.StringVar()
            end_cb = ttk.Combobox(day_frame, textvariable=end_var, values=times, 
                                state="readonly", width=10, font=("Segoe UI", base_font_size))
            end_cb.grid(row=0, column=5, padx=(0, 10))

            # Initial state setup
            if not store_range:
                # Store is closed this day
                cb.config(state="disabled")
                start_cb.configure(state="disabled")
                end_cb.configure(state="disabled")
                day_label.configure(fg=self.colors['text_muted'])
            else:
                # Store is open but availability not checked
                start_cb.configure(state="disabled")
                end_cb.configure(state="disabled")

            # when checkbox toggled, enable/disable comboboxes
            def make_toggle(s_cb=start_cb, e_cb=end_cb, v=var, labels=[start_label, end_label]):
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
                            
                        # Update label colors when enabled
                        for label in labels:
                            label.configure(fg=self.colors['text_primary'])
                    else:
                        # Clear and disable both comboboxes
                        s_cb.set("")
                        e_cb.set("")
                        s_cb.configure(state='disabled')  # Gray background
                        e_cb.configure(state='disabled')  # Gray background
                        
                        # Update label colors when disabled
                        for label in labels:
                            label.configure(fg=self.colors['text_muted'])
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
                'start_label': start_label,
                'end_label': end_label,
            }

        # Right: requested days off with modern styling
        right_content = tk.Frame(right, bg=self.colors['surface'], padx=20, pady=20)
        right_content.pack(fill="both", expand=True)
        
        days_off_header = tk.Label(right_content, 
                                  text="🗓️ Requested Time Off", 
                                  font=("Segoe UI", header_font_size, "bold"),
                                  bg=self.colors['surface'],
                                  fg=self.colors['text_primary'])
        days_off_header.pack(pady=(0, 15))
        self.employee_tab_widgets['headers'].append(days_off_header)

        # Listbox for days off
        listbox_frame = tk.Frame(right_content, bg=self.colors['surface'])
        listbox_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        self.days_off_list = tk.Listbox(listbox_frame, 
                                       width=30, height=12, 
                                       font=("Segoe UI", base_font_size),
                                       bg=self.colors['surface'],
                                       fg=self.colors['text_primary'],
                                       selectbackground=self.colors['primary'],
                                       selectforeground='white',
                                       relief='flat',
                                       borderwidth=1,
                                       highlightbackground=self.colors['border'],
                                       highlightthickness=1,
                                       activestyle='none')
        self.days_off_list.pack(fill="both", expand=True)

        # Buttons for days off management
        btn_frame = tk.Frame(right_content, bg=self.colors['surface'])
        btn_frame.pack(fill="x")
        
        add_day_btn = self.create_modern_button(btn_frame, "➕ Add Time Off", self.add_requested_day, 'success')
        add_day_btn.pack(fill="x", pady=2)
        self.employee_tab_widgets['buttons'].append(add_day_btn)
        
        remove_day_btn = self.create_modern_button(btn_frame, "🗑️ Remove Selected", self.remove_requested_day, 'danger')
        remove_day_btn.pack(fill="x", pady=2)
        self.employee_tab_widgets['buttons'].append(remove_day_btn)

        # Bottom: auto-save status indicator
        bottom.configure(bg=self.colors['background'])
        save_row = tk.Frame(bottom, bg=self.colors['background'])
        save_row.pack(pady=15)
        
        # Status indicator with styling
        status_frame = tk.Frame(save_row, bg=self.colors['surface_alt'], 
                               relief='flat', padx=15, pady=8)
        status_frame.pack()
        
        save_icon = tk.Label(status_frame, text="💾", 
                           font=("Segoe UI", base_font_size),
                           bg=self.colors['surface_alt'])
        save_icon.pack(side="left", padx=(0, 8))
        
        self.save_emp_lbl = tk.Label(status_frame, text="Changes save automatically", 
                                   font=("Segoe UI", base_font_size, "normal"),
                                   bg=self.colors['surface_alt'],
                                   fg=self.colors['text_secondary'])
        self.save_emp_lbl.pack(side="left")
        self.employee_tab_widgets['labels'].append(self.save_emp_lbl)
        
        self.save_indicator = tk.Label(status_frame, text="", 
                                     fg=self.colors['success'], 
                                     font=("Segoe UI", base_font_size, "bold"),
                                     bg=self.colors['surface_alt'])
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

    def validate_shift_scheduling(self, emp_name, day_str, start_time, end_time, 
                                 exclude_shift_index=None, show_dialog=True):
        """
        Comprehensive validation for shift scheduling.
        
        Args:
            emp_name: Employee name
            day_str: Date string in YYYY-MM-DD format
            start_time: Start time in HH:MM format
            end_time: End time in HH:MM format
            exclude_shift_index: Index of shift to exclude from overlap check (for editing)
            show_dialog: Whether to show conflict dialog
            
        Returns:
            tuple: (is_valid, conflicts_list)
        """
        from datetime import datetime
        
        conflicts = []
        
        # Basic time validation
        try:
            start_dt = datetime.strptime(start_time, TIME_FMT)
            end_dt = datetime.strptime(end_time, TIME_FMT)
            if end_dt <= start_dt:
                conflicts.append("End time must be after start time")
                return False, conflicts
        except Exception:
            conflicts.append("Invalid time format")
            return False, conflicts
        
        # Find employee data
        emp_data = self.find_employee_by_display(emp_name)
        if not emp_data:
            conflicts.append("Employee not found")
            return False, conflicts
        
        # Get day of week for availability check
        day_dt = datetime.strptime(day_str, DATE_FMT)
        day_name = day_dt.strftime("%A").lower()
        
        # Check requested days off (support both structured and legacy formats)
        rd_list = emp_data.get("requested_days_off", [])
        for req in rd_list:
            if isinstance(req, dict):
                rtype = req.get("type")
                rdate = req.get("date")
                if rdate != day_str:
                    continue
                if rtype == "full":
                    conflicts.append(f"{emp_name} requested this entire day off")
                elif rtype == "partial":
                    times = req.get("times", "")
                    parts = [p.strip() for p in times.split("-")]
                    if len(parts) == 2:
                        try:
                            r_start = datetime.strptime(parts[0], TIME_FMT)
                            r_end = datetime.strptime(parts[1], TIME_FMT)
                            # Check if shift overlaps with requested time off
                            if not (end_dt <= r_start or start_dt >= r_end):
                                conflicts.append(f"{emp_name} requested time off from {parts[0]} to {parts[1]}")
                        except Exception:
                            # if malformed, treat as full day off
                            conflicts.append(f"{emp_name} has a time off request for this day")
            else:
                # legacy string format - treat as full day
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
                if start_dt < avail_start:
                    conflicts.append(f"Shift starts at {start_time} but {emp_name} is only available from {availability[0]}")
                if end_dt > avail_end:
                    conflicts.append(f"Shift ends at {end_time} but {emp_name} is only available until {availability[1]}")
            except Exception:
                conflicts.append(f"{emp_name}'s availability data is invalid for {day_name}")
        
        # Check for overlap with existing shifts
        month_key = f"{day_dt.year}-{day_dt.month:02d}"
        shifts = self.data.get("schedule", {}).get(month_key, {}).get(day_str, [])
        for i, shift in enumerate(shifts):
            # Skip the shift we're editing
            if exclude_shift_index is not None and i == exclude_shift_index:
                continue
                
            if shift["employee"] == emp_name:
                try:
                    shift_start = datetime.strptime(shift["start"], TIME_FMT)
                    shift_end = datetime.strptime(shift["end"], TIME_FMT)
                    # Check if shifts overlap
                    if not (end_dt <= shift_start or start_dt >= shift_end):
                        conflicts.append(f"Overlaps with existing shift ({shift['start']} - {shift['end']})")
                except Exception:
                    conflicts.append(f"Error checking overlap with existing shift")
        
        # If there are conflicts and we should show dialog
        if conflicts and show_dialog:
            message = "⚠️ The following scheduling conflicts were found:\n\n"
            message += "\n".join(f"• {conflict}" for conflict in conflicts)
            message += "\n\n❓ Do you want to schedule this shift anyway?"
            
            import tkinter.messagebox as messagebox
            return messagebox.askyesno("Scheduling Conflicts", message), conflicts
        
        return len(conflicts) == 0, conflicts

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
        
        # Generate initial time options (will be updated when date changes)
        def update_time_options():
            selected_date = partial_day_cal.get_date().strftime(DATE_FMT)
            store_hours = get_store_hours_for_date(selected_date, self.data.get("store_hours", {}))
            if store_hours:
                times = generate_times(store_hours[0], store_hours[1])
            else:
                times = generate_times("8:30 AM", "7:00 PM")  # Default fallback
            start_cb['values'] = times
            end_cb['values'] = times
        
        # Initial time generation using current date
        current_date = partial_day_cal.get_date().strftime(DATE_FMT)
        store_hours = get_store_hours_for_date(current_date, self.data.get("store_hours", {}))
        if store_hours:
            times = generate_times(store_hours[0], store_hours[1])
        else:
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
        
        # Bind date change event to update time options
        partial_day_cal.bind("<<DateEntrySelected>>", lambda e: update_time_options())

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
        # Set tab background
        self.schedule_tab.configure(bg=self.colors['background'])
        
        # Top navigation and controls with modern styling
        top = tk.Frame(self.schedule_tab, bg=self.colors['background'], pady=15)
        top.grid(row=0, column=0, sticky="ew")
        self.schedule_tab.grid_columnconfigure(0, weight=1)

        # Navigation frame with modern styling
        nav_container = tk.Frame(top, bg=self.colors['surface'], 
                               relief='flat', padx=20, pady=15)
        nav_container.grid(row=0, column=0, sticky="ew", padx=10)
        top.grid_columnconfigure(0, weight=1)
        
        nav = tk.Frame(nav_container, bg=self.colors['surface'])
        nav.pack(fill="x")

        # Navigation buttons
        base_font_size = self.calculate_font_size()
        
        self.prev_btn = self.create_modern_button(nav, "◀ Previous Month", self.prev_month, 'secondary')
        self.prev_btn.grid(row=0, column=0, padx=(0, 15))
        
        self.month_label = tk.Label(nav, text="", 
                                   font=("Segoe UI", base_font_size + 4, "bold"),
                                   bg=self.colors['surface'],
                                   fg=self.colors['text_primary'])
        self.month_label.grid(row=0, column=1, padx=15)
        
        self.next_btn = self.create_modern_button(nav, "Next Month ▶", self.next_month, 'secondary')
        self.next_btn.grid(row=0, column=2, padx=(15, 0))
        
        # Configure navigation frame columns for center alignment
        nav.grid_columnconfigure(1, weight=1)

        # PDF button
        pdf_btn = self.create_modern_button(nav_container, "📄 Generate PDF", 
                                          self.generate_month_pdf, 'primary')
        pdf_btn.pack(side="right", padx=(10, 0))

        # Calendar frame with shadow effect
        calendar_container = tk.Frame(self.schedule_tab, bg=self.colors['background'])
        calendar_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        self.calendar_frame = tk.Frame(calendar_container, 
                                     bg=self.colors['surface'],
                                     relief='flat',
                                     bd=1,
                                     highlightbackground=self.colors['border'],
                                     highlightthickness=1,
                                     padx=10, pady=10)
        self.calendar_frame.pack(fill="both", expand=True)
        
        # Make calendar frame expand to fill space but constrain its growth
        self.schedule_tab.grid_rowconfigure(1, weight=1)
        self.schedule_tab.grid_columnconfigure(0, weight=1)

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
            # DEBUG: UI size update error
            # print(f"Error updating UI sizes: {e}")  # For debugging
            pass
    
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
                day_font = ("Arial", max(base_size - 3, 6), "bold")  # Much smaller day numbers
                
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
                    # Day numbers should be bold and much smaller
                    base_size = normal_font[1] if isinstance(normal_font, tuple) else normal_font
                    day_font = ("Arial", max(base_size - 3, 6), "bold")  # Much smaller day numbers
                    widget.configure(font=day_font)
                elif text in ["✏️", "📋", "🗑️"]:  # Action icons
                    widget.configure(font=icon_font)
                elif text and "(" in text and "-" in text:  # Shift labels (contain time)
                    # Check if this label has custom dynamic font sizing
                    if hasattr(widget, '_custom_font_size') and widget._custom_font_size:
                        # This label uses custom dynamic sizing - don't override it
                        if hasattr(widget, '_dynamic_font'):
                            widget.configure(font=widget._dynamic_font)
                    else:
                        # Use standard shift font for labels without custom sizing
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
                            day_font = ("Arial", max(base_size - 3, 6), "bold")  # Much smaller day numbers
                            widget.configure(font=day_font)
                        else:
                            widget.configure(font=normal_font)
                    else:
                        # Check if current font is bold (likely a day number)
                        if isinstance(current_font, tuple) and len(current_font) > 2 and "bold" in str(current_font):
                            base_size = normal_font[1] if isinstance(normal_font, tuple) else normal_font
                            day_font = ("Arial", max(base_size - 3, 6), "bold")  # Much smaller day numbers
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
            
            # Update store hours tab elements
            self.update_store_hours_tab_fonts(normal_font, header_font)
                
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
                
            # Update availability widgets (checkboxes and labels)
            if hasattr(self, 'avail_widgets'):
                base_font_size = self.calculate_font_size()
                checkbox_font = ("Segoe UI", base_font_size + 1)
                label_font = ("Segoe UI", base_font_size + 1)
                
                for day, widgets in self.avail_widgets.items():
                    try:
                        # Update checkbox
                        if widgets.get('checkbutton') and widgets['checkbutton'].winfo_exists():
                            widgets['checkbutton'].configure(font=checkbox_font)
                        
                        # Update start and end labels
                        if widgets.get('start_label') and widgets['start_label'].winfo_exists():
                            widgets['start_label'].configure(font=label_font)
                        if widgets.get('end_label') and widgets['end_label'].winfo_exists():
                            widgets['end_label'].configure(font=label_font)
                            
                        # Update comboboxes
                        if widgets.get('start_cb') and widgets['start_cb'].winfo_exists():
                            widgets['start_cb'].configure(font=normal_font)
                        if widgets.get('end_cb') and widgets['end_cb'].winfo_exists():
                            widgets['end_cb'].configure(font=normal_font)
                    except Exception:
                        continue
                
        except Exception as e:
            pass
            
    def update_store_hours_tab_fonts(self, normal_font, header_font):
        """Update all fonts in the store hours tab with responsive sizing"""
        try:
            if not hasattr(self, 'store_hours_tab_widgets'):
                return
                
            # Calculate responsive font sizes based on window size
            base_font_size = self.calculate_font_size()
            
            # Create responsive font sizes (similar to availability section)
            normal_responsive = ("Segoe UI", base_font_size + 1)  # Slightly larger for readability
            header_responsive = ("Segoe UI", min(base_font_size + 3, self.max_font_size), "bold")
            small_responsive = ("Segoe UI", max(base_font_size - 1, self.min_font_size))
            
            # Update column widths based on font size before updating fonts
            self._update_store_hours_column_widths(base_font_size)
            
            # Update headers (titles, day headers, etc.)
            for widget in self.store_hours_tab_widgets['headers']:
                if widget and hasattr(widget, 'configure') and widget.winfo_exists():
                    widget.configure(font=header_responsive)
            
            # Update labels (instructions, day labels, etc.)
            for widget in self.store_hours_tab_widgets['labels']:
                if widget and hasattr(widget, 'configure') and widget.winfo_exists():
                    widget.configure(font=normal_responsive)
            
            # Update store hours widgets with responsive fonts
            if hasattr(self, 'store_hours_widgets'):
                for day, widgets in self.store_hours_widgets.items():
                    # Update comboboxes
                    if 'start_cb' in widgets and widgets['start_cb'].winfo_exists():
                        widgets['start_cb'].configure(font=normal_responsive)
                    if 'end_cb' in widgets and widgets['end_cb'].winfo_exists():
                        widgets['end_cb'].configure(font=normal_responsive)
            
            # Update any checkboxes and additional labels in the hours tile
            if hasattr(self, 'hours_container'):
                for child in self.hours_container.winfo_children():
                    self._update_widget_fonts_recursive(child, normal_responsive, small_responsive)
                    
        except Exception as e:
            pass  # Silently handle any font update errors
    
    def _update_widget_fonts_recursive(self, widget, normal_font, small_font):
        """Recursively update fonts for widgets in the store hours tab"""
        try:
            widget_class = widget.winfo_class()
            
            if widget_class == 'Checkbutton':
                widget.configure(font=normal_font)
            elif widget_class == 'Label' and widget not in self.store_hours_tab_widgets.get('headers', []):
                # Use small font for auto-save indicator and similar small text
                current_text = widget.cget('text')
                if 'save' in current_text.lower() or 'changes' in current_text.lower():
                    widget.configure(font=small_font)
                else:
                    widget.configure(font=normal_font)
            
            # Recursively update children
            for child in widget.winfo_children():
                self._update_widget_fonts_recursive(child, normal_font, small_font)
                
        except Exception:
            pass  # Skip widgets that can't be updated
                    
        except Exception as e:
            pass
    
    def _update_store_hours_column_widths(self, base_font_size):
        """Update column minimum widths based on current font size"""
        try:
            if not hasattr(self, 'hours_frame') or not self.hours_frame.winfo_exists():
                return
            
            # Calculate dynamic column widths based on font size
            # Base widths are scaled by font size factor
            font_factor = base_font_size / 12.0  # 12 is our base font size reference
            
            day_width = int(120 * font_factor)      # Day column - scales with font
            open_width = int(80 * font_factor)      # Open checkbox - scales moderately  
            start_label_width = int(60 * font_factor)   # "Start:" label
            combobox_width = int(120 * font_factor)     # Combobox columns
            end_label_width = int(60 * font_factor)     # "End:" label
            
            # Update the main hours frame column configuration
            self.hours_frame.grid_columnconfigure(0, weight=1, minsize=day_width)
            self.hours_frame.grid_columnconfigure(1, weight=0, minsize=open_width)
            self.hours_frame.grid_columnconfigure(2, weight=0, minsize=start_label_width)
            self.hours_frame.grid_columnconfigure(3, weight=0, minsize=combobox_width)
            self.hours_frame.grid_columnconfigure(4, weight=0, minsize=end_label_width)
            self.hours_frame.grid_columnconfigure(5, weight=0, minsize=combobox_width)
            
            # Update all day row frames to match
            if hasattr(self, 'store_hours_widgets'):
                for day in self.store_hours_widgets.keys():
                    # Find the day row frame
                    for child in self.hours_frame.winfo_children():
                        if hasattr(child, 'winfo_class') and child.winfo_class() == 'Frame':
                            # Update day row frame columns
                            try:
                                child.grid_columnconfigure(0, weight=1, minsize=day_width)
                                child.grid_columnconfigure(1, weight=0, minsize=open_width)
                                child.grid_columnconfigure(2, weight=0, minsize=start_label_width)
                                child.grid_columnconfigure(3, weight=0, minsize=combobox_width)
                                child.grid_columnconfigure(4, weight=0, minsize=end_label_width)
                                child.grid_columnconfigure(5, weight=0, minsize=combobox_width)
                            except:
                                pass
                                
        except Exception:
            pass  # Silently handle column width update errors
            
    def update_ui_sizes(self):
        """Legacy method - redirects to optimized version"""
        self.update_ui_sizes_optimized()
        if len(self._cached_font_sizes) > 100:
            self._cached_font_sizes.clear()

    def setup_store_hours_tab(self):
        """Setup the Store Hours tab for managing store hours"""
        # Set tab background
        self.store_hours_tab.configure(bg=self.colors['background'])
        
        # Calculate font sizes for store hours tab
        base_font_size = self.calculate_font_size()
        header_font_size = min(base_font_size + 4, self.max_font_size)  # Larger header
        
        # Main container with modern styling
        main_container = tk.Frame(self.store_hours_tab, bg=self.colors['background'], padx=20, pady=20)
        main_container.pack(fill="both", expand=True)
        
        # Card-style container
        main_frame = self.create_modern_frame(main_container)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        content_frame = tk.Frame(main_frame, bg=self.colors['surface'], padx=30, pady=30)
        content_frame.pack(fill="both", expand=True)
        
        # Configure grid for centered layout (1 row x 3 columns)
        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)  # Left spacer
        content_frame.grid_columnconfigure(1, weight=2)  # Center content (wider)
        content_frame.grid_columnconfigure(2, weight=1)  # Right spacer
        
        # Left spacer
        left_spacer = tk.Frame(content_frame, bg=self.colors['surface'])
        left_spacer.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Center tile: Store Hours Configuration
        hours_tile = tk.Frame(content_frame, bg=self.colors['surface_alt'], 
                             relief='solid', bd=1, padx=20, pady=20)
        hours_tile.grid(row=0, column=1, sticky="nsew", padx=10, pady=5)
        
        # Right spacer
        right_spacer = tk.Frame(content_frame, bg=self.colors['surface'])
        right_spacer.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
        # Store references for resizing
        self.hours_container = hours_tile
        self.content_frame = content_frame
        
        # Title with icon (inside the hours tile)
        title_frame = tk.Frame(hours_tile, bg=self.colors['surface_alt'])
        title_frame.pack(fill="x", pady=(0, 20))
        
        title_icon = tk.Label(title_frame, text="🏪", 
                            font=("Segoe UI", header_font_size + 2),
                            bg=self.colors['surface_alt'])
        title_icon.pack(side="left", padx=(0, 10))
        
        title = tk.Label(title_frame, text="Store Hours Configuration", 
                        font=("Segoe UI", header_font_size, "bold"),
                        bg=self.colors['surface_alt'],
                        fg=self.colors['text_primary'])
        title.pack(side="left")
        self.store_hours_tab_widgets['headers'].append(title)

        # Instructions (inside the hours tile)
        instructions = tk.Label(hours_tile, 
                               text="Configure the days and hours your store is open. "
                               "Unchecked days are considered closed.",
                               font=("Segoe UI", base_font_size), 
                               fg=self.colors['text_secondary'],
                               bg=self.colors['surface_alt'],
                               wraplength=800)
        instructions.pack(pady=(0, 20))
        self.store_hours_tab_widgets['labels'].append(instructions)
        
        hours_frame = tk.Frame(hours_tile, bg=self.colors['surface_alt'])
        hours_frame.pack(fill="both", expand=True)
        
        # Store reference for dynamic column width updates
        self.hours_frame = hours_frame

        # Headers with better styling
        header_font = ("Segoe UI", base_font_size, "bold")
        
        # Configure column weights for proper alignment
        hours_frame.grid_columnconfigure(0, weight=1, minsize=120)  # Day column
        hours_frame.grid_columnconfigure(1, weight=0, minsize=80)   # Open checkbox column
        hours_frame.grid_columnconfigure(2, weight=0, minsize=60)   # Start label column
        hours_frame.grid_columnconfigure(3, weight=0, minsize=120)  # Start time column
        hours_frame.grid_columnconfigure(4, weight=0, minsize=60)   # End label column
        hours_frame.grid_columnconfigure(5, weight=0, minsize=120)  # End time column
        
        # Create header row that matches the day row structure
        day_header = tk.Label(hours_frame, text="Day", font=header_font,
                            bg=self.colors['surface_alt'], fg=self.colors['text_primary'],
                            anchor="w")
        day_header.grid(row=0, column=0, padx=15, sticky="w", pady=(0, 10))
        self.store_hours_tab_widgets['headers'].append(day_header)
        
        open_header = tk.Label(hours_frame, text="Open", font=header_font,
                             bg=self.colors['surface_alt'], fg=self.colors['text_primary'])
        open_header.grid(row=0, column=1, padx=15, pady=(0, 10))
        self.store_hours_tab_widgets['headers'].append(open_header)
        
        start_header = tk.Label(hours_frame, text="Start Time", font=header_font,
                              bg=self.colors['surface_alt'], fg=self.colors['text_primary'])
        start_header.grid(row=0, column=2, columnspan=2, padx=15, pady=(0, 10))
        self.store_hours_tab_widgets['headers'].append(start_header)
        
        end_header = tk.Label(hours_frame, text="End Time", font=header_font,
                            bg=self.colors['surface_alt'], fg=self.colors['text_primary'])
        end_header.grid(row=0, column=4, columnspan=2, padx=15, pady=(0, 10))
        self.store_hours_tab_widgets['headers'].append(end_header)
        
        # Store widgets for each day
        self.store_hours_widgets = {}
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        # day_emojis = ["🌙", "💼", "💼", "💼", "💼", "🌅", "☀️"]  # Sunday, Mon-Fri, Saturday
        
        # Generate time options (all possible times)
        all_times = generate_times("12:00 AM", "11:30 PM", 30)
        
        for i, day in enumerate(days):
            row = i + 1

            # Day row container
            day_row_frame = tk.Frame(hours_frame, bg=self.colors['surface_alt'])
            day_row_frame.grid(row=row, column=0, columnspan=6, sticky="ew", pady=5)
            
            # Configure the day row frame columns to match parent
            day_row_frame.grid_columnconfigure(0, weight=1, minsize=120)
            day_row_frame.grid_columnconfigure(1, weight=0, minsize=80)
            day_row_frame.grid_columnconfigure(2, weight=0, minsize=60)
            day_row_frame.grid_columnconfigure(3, weight=0, minsize=120)
            day_row_frame.grid_columnconfigure(4, weight=0, minsize=60)
            day_row_frame.grid_columnconfigure(5, weight=0, minsize=120)
            
            # Day label with emoji
            day_label = tk.Label(day_row_frame, 
                               text=f"{day.capitalize()}", 
                               font=("Segoe UI", base_font_size, "normal"),
                               bg=self.colors['surface_alt'],
                               fg=self.colors['text_primary'],
                               width=12,
                               anchor="w")
            day_label.grid(row=0, column=0, padx=15, sticky="w")
            self.store_hours_tab_widgets['labels'].append(day_label)
            
            # Open checkbox
            is_open_var = tk.IntVar()
            store_hours = self.data.get("store_hours", {})
            day_hours = store_hours.get(day)
            
            if day_hours is not None:
                is_open_var.set(1)
            
            open_cb = tk.Checkbutton(day_row_frame, 
                                   variable=is_open_var,
                                   bg=self.colors['surface_alt'],
                                   fg=self.colors['text_primary'],
                                   activebackground=self.colors['surface_alt'],
                                   selectcolor=self.colors['surface_alt'],
                                   font=("Segoe UI", base_font_size + 1),
                                   text="Open")
            open_cb.grid(row=0, column=1, padx=15)

            # Start time combobox
            start_label = tk.Label(day_row_frame,
                                 text="Start:",
                                 font=("Segoe UI", base_font_size + 1),
                                 bg=self.colors['surface_alt'],
                                 fg=self.colors['text_primary'])
            start_label.grid(row=0, column=2, sticky="w", padx=(0, 8))
            self.store_hours_tab_widgets['labels'].append(start_label)
            
            start_var = tk.StringVar()
            start_cb = ttk.Combobox(day_row_frame, textvariable=start_var, values=all_times, 
                                   state="readonly", width=10, font=("Segoe UI", base_font_size))
            start_cb.grid(row=0, column=3, padx=(0, 15))

            # End time combobox
            end_label = tk.Label(day_row_frame,
                               text="End:",
                               font=("Segoe UI", base_font_size + 1),
                               bg=self.colors['surface_alt'],
                               fg=self.colors['text_primary'])
            end_label.grid(row=0, column=4, sticky="w", padx=(0, 8))
            self.store_hours_tab_widgets['labels'].append(end_label)
            
            end_var = tk.StringVar()
            end_cb = ttk.Combobox(day_row_frame, textvariable=end_var, values=all_times, 
                                 state="readonly", width=10, font=("Segoe UI", base_font_size))
            end_cb.grid(row=0, column=5, padx=(0, 15))
            
            # Set initial values
            if day_hours is not None:
                start_cb.set(day_hours[0])
                end_cb.set(day_hours[1])
                start_cb.configure(state="readonly")
                end_cb.configure(state="readonly")
                start_label.configure(fg=self.colors['text_primary'])
                end_label.configure(fg=self.colors['text_primary'])
            else:
                start_cb.set("")
                end_cb.set("")
                start_cb.configure(state="disabled")
                end_cb.configure(state="disabled")
                start_label.configure(fg=self.colors['text_muted'])
                end_label.configure(fg=self.colors['text_muted'])
            
            # Toggle function for enabling/disabling time selectors
            def make_toggle(s_cb=start_cb, e_cb=end_cb, v=is_open_var, d=day, 
                          s_lbl=start_label, e_lbl=end_label):
                def toggle(*args):
                    if v.get():
                        # Enable and set default times
                        s_cb.set("8:30 AM")
                        e_cb.set("7:00 PM")
                        s_cb.configure(state="readonly")
                        e_cb.configure(state="readonly")
                        s_lbl.configure(fg=self.colors['text_primary'])
                        e_lbl.configure(fg=self.colors['text_primary'])
                    else:
                        # Disable and clear
                        s_cb.set("")
                        e_cb.set("")
                        s_cb.configure(state="disabled")
                        e_cb.configure(state="disabled")
                        s_lbl.configure(fg=self.colors['text_muted'])
                        e_lbl.configure(fg=self.colors['text_muted'])
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
        
        # Auto-save indicator (inside hours tile)
        save_container = tk.Frame(hours_tile, bg=self.colors['surface_alt'])
        save_container.pack(pady=(15, 0))
        
        save_frame = tk.Frame(save_container, bg=self.colors['surface_alt'], 
                            relief='flat', padx=10, pady=5)
        save_frame.pack()
        
        save_icon = tk.Label(save_frame, text="💾", 
                           font=("Segoe UI", base_font_size - 1),
                           bg=self.colors['surface_alt'])
        save_icon.pack(side="left", padx=(0, 5))
        
        tk.Label(save_frame, text="Changes save automatically", 
                font=("Segoe UI", base_font_size - 1, "normal"),
                bg=self.colors['surface_alt'],
                fg=self.colors['text_secondary']).pack(side="left")
        
        self.store_hours_indicator = tk.Label(save_frame, text="", 
                                            fg=self.colors['success'], 
                                            font=("Segoe UI", base_font_size - 1, "bold"),
                                            bg=self.colors['surface_alt'])
        self.store_hours_indicator.pack(side="left", padx=(5, 0))
        
        # Initialize auto-save timer
        self._store_hours_timer = None
        
        # Initial sizing of tile layout
        self.root.after(100, self.update_hours_container_size)
    
    def add_store_hours_settings_section(self, title, description, settings_widgets):
        """
        Helper method to add new settings sections below the store hours.
        
        Args:
            title (str): Section title
            description (str): Section description
            settings_widgets (list): List of widget creation functions
        
        Example usage:
            def create_notification_settings(parent):
                # Create notification-related widgets in parent
                pass
            
            self.add_store_hours_settings_section(
                "Notification Settings",
                "Configure email and SMS notifications",
                [create_notification_settings]
            )
        """
        if not hasattr(self, 'hours_container'):
            return
            
        # Add separator
        separator = tk.Frame(self.hours_container, height=2, bg=self.colors['border'])
        separator.pack(fill="x", pady=20)
        
        base_font_size = self.calculate_font_size()
        header_font_size = min(base_font_size + 4, self.max_font_size)
        
        # Section title
        title_label = tk.Label(self.hours_container, text=title,
                              font=("Segoe UI", header_font_size, "bold"),
                              bg=self.colors['surface_alt'],
                              fg=self.colors['text_primary'])
        title_label.pack(pady=(15, 10))
        self.store_hours_tab_widgets['headers'].append(title_label)
        
        # Section description
        if description:
            desc_label = tk.Label(self.hours_container, text=description,
                                 font=("Segoe UI", base_font_size),
                                 fg=self.colors['text_secondary'],
                                 bg=self.colors['surface_alt'],
                                 wraplength=600)
            desc_label.pack(pady=(0, 15))
            self.store_hours_tab_widgets['labels'].append(desc_label)
        
        # Add widgets
        for widget_func in settings_widgets:
            widget_func(self.hours_container)
    
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

        # Calculate font sizes once for the entire calendar with modern fonts
        base_font_size = self.calculate_font_size()
        header_font = ("Segoe UI", base_font_size, "bold")
        day_font = ("Segoe UI", max(base_font_size - 3, 6), "bold")  # Much smaller day numbers
        shift_font_size = max(int(base_font_size * 0.85), self.min_font_size)
        shift_font = ("Segoe UI", shift_font_size)

        # Header label
        month_name = datetime(self.current_year, self.current_month, 1).strftime("%B %Y")
        self.month_label.config(text=month_name, font=("Segoe UI", base_font_size + 4, "bold"))

        # Configure calendar frame to expand cells evenly with proper constraints
        for i in range(7):  # 7 columns for days
            self.calendar_frame.grid_columnconfigure(i, weight=1, minsize=140)
        for i in range(7):  # 6 rows for weeks + 1 for headers  
            if i == 0:  # Header row
                self.calendar_frame.grid_rowconfigure(i, weight=0, minsize=35)
            else:  # Calendar rows
                self.calendar_frame.grid_rowconfigure(i, weight=1, minsize=100, uniform="calendar_row")

        # Add global click handler to close menus when clicking outside cells
        def close_all_menus(event=None):
            # Import the class here to avoid circular reference
            if hasattr(self, '_temp_cell_menu_class'):
                if self._temp_cell_menu_class.active_manager:
                    self._temp_cell_menu_class.active_manager.hide_menu()
        
        self.calendar_frame.bind("<Button-1>", close_all_menus)

        # Weekday headers
        days_header = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]
        day_abbrev = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]
        for c, (dh, abbrev) in enumerate(zip(days_header, day_abbrev)):
            header_frame = tk.Frame(self.calendar_frame, 
                                  bg=self.colors['primary'],
                                  relief='flat',
                                  bd=0)
            header_frame.grid(row=0, column=c, padx=1, pady=1, sticky="nsew")
            
            lbl = tk.Label(header_frame, text=abbrev, 
                         font=header_font,
                         bg=self.colors['primary'],
                         fg='white',
                         pady=8)
            lbl.pack(fill="both", expand=True)

        # Set calendar to start on Sunday (6 = Sunday in Python's calendar module)
        cal = calendar.Calendar(firstweekday=6)
        month_days = cal.monthdayscalendar(self.current_year, self.current_month)
        # Rows for weeks start at row 1
        for r, week in enumerate(month_days, start=1):
            for c, day in enumerate(week):
                # Create modern cell frame
                cell_bg = self.colors['surface'] if day > 0 else self.colors['surface_alt']
                if day > 0:
                    # Check if this day is a weekend for different styling
                    day_of_week = c  # 0=Sunday, 6=Saturday
                    if day_of_week == 0 or day_of_week == 6:  # Weekend
                        cell_bg = self.colors['surface_alt']
                
                cell_frame = tk.Frame(self.calendar_frame, 
                                    bg=cell_bg,
                                    relief='flat',
                                    bd=1,
                                    highlightbackground=self.colors['border'],
                                    highlightthickness=1)
                cell_frame.grid(row=r, column=c, padx=1, pady=1, sticky="nsew")
                
                # Make the cell contents expand with the cell but with constraints
                cell_frame.grid_columnconfigure(0, weight=1)
                cell_frame.grid_rowconfigure(0, weight=0, minsize=25)  # Header row - fixed height
                cell_frame.grid_rowconfigure(1, weight=1)  # Content row - expandable but constrained
                cell_frame.grid_rowconfigure(2, weight=0, minsize=15)  # Bottom space for trigger icon

                # Create simple menu manager for this cell
                class CellMenuManager:
                    # Class variable to track currently active menu
                    active_manager = None
                    
                    def __init__(self, master):
                        self.master = master
                        self.menu_visible = False
                        self.day_str = None
                        self.shifts = None
                        self.parent_app = None
                        
                        # Create clean menu container
                        self.menu_frame = tk.Frame(master, bg="#2C2C2C", relief="raised", bd=2)
                        self.menu_frame.place_forget()  # Hidden initially
                        
                        # Store original cell background for vignette effect
                        self.original_bg = master.cget('bg')
                        
                        # Create menu buttons
                        self.create_menu_buttons()
                        
                        # Track widgets for click binding
                        self.cell_widgets = []
                    
                    def create_menu_buttons(self):
                        """Create clean, responsive menu buttons"""
                        button_configs = [
                            ("✎", "#4A90E2", "Edit shifts for this day", self.edit_action),
                            ("📋", "#50C878", "Copy all shifts from this day", self.handle_copy_action),
                            ("📄", "#FF8C42", "Paste copied shifts to this day", self.handle_paste_action),
                            ("🗑", "#FF6B6B", "Delete all shifts from this day", self.handle_delete_action)
                        ]
                        
                        for i, (icon, color, tooltip, action) in enumerate(button_configs):
                            btn = tk.Button(
                                self.menu_frame,
                                text=icon,
                                font=("Segoe UI", 12),
                                bg=color,
                                fg="white",
                                relief="flat",
                                bd=0,
                                width=3,
                                height=1,
                                cursor="hand2",
                                command=action
                            )
                            btn.pack(side="left", padx=2, pady=4)
                            
                            # Add hover effects and tooltip
                            btn.bind("<Enter>", lambda e, b=btn, c=color, t=tooltip: self.on_button_enter_with_tooltip(b, e, c, t))
                            btn.bind("<Leave>", lambda e, b=btn, c=color: self.on_button_leave_with_tooltip(b, e, c))
                    
                    def on_button_enter_with_tooltip(self, button, event, original_color, tooltip_text):
                        """Button hover effect with tooltip"""
                        # Lighten the color on hover
                        button.configure(bg=self.lighten_color(original_color))
                        
                        # Show tooltip
                        self.show_tooltip(button, event, tooltip_text)
                    
                    def on_button_leave_with_tooltip(self, button, event, original_color):
                        """Button leave effect with tooltip cleanup"""
                        button.configure(bg=original_color)
                        
                        # Hide tooltip
                        self.hide_tooltip(button, event)
                    
                    def show_tooltip(self, widget, event, text):
                        """Show tooltip with delay"""
                        # Cancel any existing tooltip timer
                        if hasattr(widget, 'tooltip_timer'):
                            widget.after_cancel(widget.tooltip_timer)
                        
                        # Store event coordinates for use in delayed callback
                        widget.tooltip_x = event.x_root
                        widget.tooltip_y = event.y_root
                        widget.tooltip_text_stored = text
                        
                        # Add a small delay before showing tooltip
                        widget.tooltip_timer = widget.after(500, lambda: self.do_show_tooltip(widget))
                    
                    def do_show_tooltip(self, widget):
                        """Actually create and show the tooltip"""
                        try:
                            # Check if we still have coordinates (mouse might have left)
                            if not hasattr(widget, 'tooltip_x') or not hasattr(widget, 'tooltip_text_stored'):
                                return
                            
                            tooltip = tk.Toplevel()
                            tooltip.wm_overrideredirect(True)
                            tooltip.wm_geometry(f"+{widget.tooltip_x+15}+{widget.tooltip_y+10}")
                            
                            label = tk.Label(tooltip, text=widget.tooltip_text_stored, background="#2C3E50", 
                                           fg="white", relief="solid", borderwidth=1, 
                                           font=("Segoe UI", 9), padx=8, pady=4)
                            label.pack()
                            
                            # Store tooltip reference
                            widget.tooltip = tooltip
                            
                            # Auto-hide after 4 seconds
                            tooltip.after(4000, lambda: tooltip.destroy() if tooltip.winfo_exists() else None)
                        except Exception as e:
                            # DEBUG: Tooltip error
                            # print(f"Tooltip error: {e}")  # Debug output
                            pass
                    
                    def hide_tooltip(self, widget, event):
                        """Hide tooltip and clean up"""
                        # Cancel pending tooltip if mouse leaves quickly
                        if hasattr(widget, 'tooltip_timer'):
                            widget.after_cancel(widget.tooltip_timer)
                            delattr(widget, 'tooltip_timer')
                        
                        # Clear stored data
                        if hasattr(widget, 'tooltip_x'):
                            delattr(widget, 'tooltip_x')
                        if hasattr(widget, 'tooltip_y'):
                            delattr(widget, 'tooltip_y')
                        if hasattr(widget, 'tooltip_text_stored'):
                            delattr(widget, 'tooltip_text_stored')
                        
                        # Hide existing tooltip
                        if hasattr(widget, 'tooltip'):
                            try:
                                if widget.tooltip.winfo_exists():
                                    widget.tooltip.destroy()
                            except:
                                pass
                    
                    def on_button_enter(self, button, original_color):
                        """Button hover effect"""
                        # Lighten the color on hover
                        button.configure(bg=self.lighten_color(original_color))
                    
                    def on_button_leave(self, button, original_color):
                        """Button leave effect"""
                        button.configure(bg=original_color)
                    
                    def lighten_color(self, color):
                        """Lighten a hex color"""
                        try:
                            color = color.lstrip('#')
                            rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
                            # Lighten by adding 30 to each component, max 255
                            lighter_rgb = tuple(min(255, c + 30) for c in rgb)
                            return f"#{lighter_rgb[0]:02x}{lighter_rgb[1]:02x}{lighter_rgb[2]:02x}"
                        except:
                            return color
                    
                    def show_menu(self):
                        """Show menu in center of cell"""
                        # DEBUG: Menu display debugging
                        # print(f"\n📱 SHOW_MENU called for day: {self.day_str}")
                        # print(f"📊 Menu shifts available: {len(self.shifts) if self.shifts else 0}")
                        
                        if CellMenuManager.active_manager and CellMenuManager.active_manager != self:
                            CellMenuManager.active_manager.hide_menu()
                        
                        CellMenuManager.active_manager = self
                        self.menu_visible = True
                        
                        # Apply vignette effect
                        self.apply_vignette()
                        
                        # Position menu in center of cell
                        self.position_menu()
                        self.menu_frame.tkraise()
                        
                        # DEBUG: Menu confirmation
                        # print(f"✅ Menu shown for {self.day_str}")
                    
                    def hide_menu(self):
                        """Hide menu and restore cell appearance"""
                        # DEBUG: Menu hiding debugging
                        # print(f"\n📱 HIDE_MENU called for day: {self.day_str}")
                        
                        if self.menu_visible:
                            self.menu_visible = False
                            # Safety check: only hide menu if it still exists
                            try:
                                if self.menu_frame and self.menu_frame.winfo_exists():
                                    self.menu_frame.place_forget()
                            except tk.TclError:
                                # Menu frame was already destroyed, ignore the error
                                pass
                            self.remove_vignette()
                            
                            if CellMenuManager.active_manager == self:
                                CellMenuManager.active_manager = None
                    
                    def position_menu(self):
                        """Position menu in center of cell"""
                        self.master.update_idletasks()
                        self.menu_frame.update_idletasks()
                        
                        # Get cell dimensions
                        cell_width = self.master.winfo_width()
                        cell_height = self.master.winfo_height()
                        menu_width = self.menu_frame.winfo_reqwidth()
                        menu_height = self.menu_frame.winfo_reqheight()
                        
                        # Center the menu
                        x = (cell_width - menu_width) // 2
                        y = (cell_height - menu_height) // 2
                        
                        self.menu_frame.place(x=x, y=y)
                    
                    def apply_vignette(self):
                        """Apply subtle vignette effect to cell"""
                        darkened = self.darken_color(self.original_bg)
                        self.master.configure(bg=darkened)
                    
                    def remove_vignette(self):
                        """Remove vignette effect"""
                        try:
                            if self.master and self.master.winfo_exists():
                                self.master.configure(bg=self.original_bg)
                        except tk.TclError:
                            # Master widget was already destroyed, ignore the error
                            pass
                    
                    def darken_color(self, color):
                        """Darken a color by 20%"""
                        try:
                            if color.startswith('#'):
                                color = color[1:]
                            
                            r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
                            r, g, b = int(r * 0.8), int(g * 0.8), int(b * 0.8)
                            return f"#{r:02x}{g:02x}{b:02x}"
                        except:
                            return "#E0E0E0"
                    
                    def toggle_menu(self):
                        """Toggle menu visibility"""
                        if self.menu_visible:
                            self.hide_menu()
                        else:
                            self.show_menu()
                    
                    def setup_cell_click(self, day_str, shifts, parent_app):
                        """Setup cell for click interaction"""
                        self.day_str = day_str
                        self.shifts = shifts
                        self.parent_app = parent_app
                        
                        # Bind click to entire cell
                        self.master.bind("<Button-1>", self.handle_cell_click)
                        
                        # Bind click to all child widgets too
                        self.bind_widget_clicks(self.master)
                    
                    def bind_widget_clicks(self, widget):
                        """Recursively bind clicks to all widgets in cell"""
                        try:
                            for child in widget.winfo_children():
                                if child != self.menu_frame:
                                    child.bind("<Button-1>", self.handle_cell_click)
                                    self.bind_widget_clicks(child)
                        except:
                            pass
                    
                    def handle_cell_click(self, event=None):
                        """Handle cell click to toggle menu"""
                        if event:
                            # Prevent event propagation
                            try:
                                event.widget.tk.call('break')
                            except:
                                pass
                        
                        # If there's already an active menu from another cell, hide it first
                        if CellMenuManager.active_manager and CellMenuManager.active_manager != self:
                            CellMenuManager.active_manager.hide_menu()
                        
                        # If this cell's menu is visible, hide it (click to close)
                        if self.menu_visible:
                            self.hide_menu()
                        else:
                            # Show this cell's menu
                            self.show_menu()
                        
                        return "break"
                    
                    # Action methods
                    def edit_action(self):
                        """Handle edit action"""
                        self.hide_menu()
                        if self.parent_app:
                            self.parent_app.open_day_editor_dialog(self.day_str, self.shifts)
                    
                    def create_modern_bubble_button(self, icon, primary_color, hover_color, tooltip):
                        """Create a modern bubble-style button with smooth hover effects"""
                        btn_frame = tk.Frame(self.button_container, bg=self.button_container.cget('bg'))
                        
                        # Main button with fixed icon and consistent styling
                        btn = tk.Label(btn_frame, text=icon, font=("Segoe UI", 14, "bold"), 
                                     fg="white", bg=primary_color, cursor="hand2",
                                     width=3, height=1, relief="raised", bd=2)
                        btn.pack(padx=2, pady=2)
                        
                        # Store colors and icon for hover effects (icon never changes)
                        btn.primary_color = primary_color
                        btn.hover_color = hover_color
                        btn.tooltip_text = tooltip
                        btn.original_icon = icon  # Store the original icon
                        
                        # Add shadow effect by creating a background frame
                        shadow_frame = tk.Frame(btn_frame, bg="#CCCCCC", height=2)
                        shadow_frame.pack(fill="x", padx=4)
                        
                        # Bind hover effects and tooltip together
                        btn.bind("<Enter>", lambda e: self.on_bubble_button_enter_with_tooltip(btn, e))
                        btn.bind("<Leave>", lambda e: self.on_bubble_button_leave_with_tooltip(btn, e))
                        
                        return btn_frame
                    
                    def on_bubble_button_enter_with_tooltip(self, btn, event):
                        """Handle button enter with both hover effect and tooltip"""
                        # Apply hover effect
                        self.on_button_hover_enter(btn)
                        
                        # Show tooltip
                        self.show_bubble_tooltip(btn, event, btn.tooltip_text)
                    
                    def on_bubble_button_leave_with_tooltip(self, btn, event):
                        """Handle button leave with both hover effect and tooltip cleanup"""
                        # Remove hover effect
                        self.on_button_hover_leave(btn)
                        
                        # Hide tooltip
                        self.hide_bubble_tooltip(btn, event)
                    
                    def show_bubble_tooltip(self, widget, event, text):
                        """Show tooltip with delay"""
                        # Cancel any existing tooltip timer
                        if hasattr(widget, 'tooltip_timer'):
                            widget.after_cancel(widget.tooltip_timer)
                        
                        # Store event coordinates for use in delayed callback
                        widget.tooltip_x = event.x_root
                        widget.tooltip_y = event.y_root
                        widget.tooltip_text_stored = text
                        
                        # Add a small delay before showing tooltip
                        widget.tooltip_timer = widget.after(500, lambda: self.do_show_bubble_tooltip(widget))
                    
                    def do_show_bubble_tooltip(self, widget):
                        """Actually create and show the tooltip"""
                        try:
                            # Check if we still have coordinates (mouse might have left)
                            if not hasattr(widget, 'tooltip_x') or not hasattr(widget, 'tooltip_text_stored'):
                                return
                            
                            tooltip = tk.Toplevel()
                            tooltip.wm_overrideredirect(True)
                            tooltip.wm_geometry(f"+{widget.tooltip_x+15}+{widget.tooltip_y+10}")
                            
                            label = tk.Label(tooltip, text=widget.tooltip_text_stored, background="#2C3E50", 
                                           fg="white", relief="solid", borderwidth=1, 
                                           font=("Segoe UI", 9), padx=8, pady=4)
                            label.pack()
                            
                            # Store tooltip reference
                            widget.tooltip = tooltip
                            
                            # Auto-hide after 4 seconds
                            tooltip.after(4000, lambda: tooltip.destroy() if tooltip.winfo_exists() else None)
                        except Exception as e:
                            # DEBUG: Tooltip error
                            # print(f"Tooltip error: {e}")  # Debug output
                            pass
                    
                    def hide_bubble_tooltip(self, widget, event):
                        """Hide tooltip and clean up"""
                        # Cancel pending tooltip if mouse leaves quickly
                        if hasattr(widget, 'tooltip_timer'):
                            widget.after_cancel(widget.tooltip_timer)
                            delattr(widget, 'tooltip_timer')
                        
                        # Clear stored data
                        if hasattr(widget, 'tooltip_x'):
                            delattr(widget, 'tooltip_x')
                        if hasattr(widget, 'tooltip_y'):
                            delattr(widget, 'tooltip_y')
                        if hasattr(widget, 'tooltip_text_stored'):
                            delattr(widget, 'tooltip_text_stored')
                        
                        # Hide existing tooltip
                        if hasattr(widget, 'tooltip'):
                            try:
                                if widget.tooltip.winfo_exists():
                                    widget.tooltip.destroy()
                            except:
                                pass
                    
                    def on_button_hover_enter(self, btn):
                        """Smooth hover enter effect for buttons - no size changes"""
                        btn.configure(bg=btn.hover_color, relief="solid", bd=2)
                    
                    def on_button_hover_leave(self, btn):
                        """Smooth hover leave effect for buttons - no size changes"""
                        btn.configure(bg=btn.primary_color, relief="raised", bd=2)
                        
                    def on_cell_resize(self, event=None):
                        """Handle cell resize events to update hover areas"""
                        # Only process resize events for the master cell frame
                        if event and event.widget != self.master:
                            return
                        
                        # Update trigger icon size based on new cell size
                        self.update_trigger_icon_for_size()
                        
                        # If buttons are visible, reposition them
                        if self.menu_visible:
                            try:
                                # Reposition button container
                                self.button_container.place(relx=0.5, rely=0.70, anchor="center")
                                self.button_container.lift()
                            except:
                                pass
                        elif self.hover_active:
                            # Reposition trigger icon if it's visible
                            try:
                                self.trigger_icon.place(relx=0.5, rely=0.95, anchor="s")
                                self.trigger_icon.lift()
                            except:
                                pass
                        
                        # Start continuous tracking for a short period after resize
                        self.start_continuous_tracking()
                    
                    def start_continuous_tracking(self):
                        """Start continuous mouse tracking for better resize responsiveness"""
                        if not self.continuous_tracking:
                            self.continuous_tracking = True
                            self.track_mouse_continuously()
                            # Stop continuous tracking after 2 seconds
                            if self.tracking_timer:
                                self.master.after_cancel(self.tracking_timer)
                            self.tracking_timer = self.master.after(2000, self.stop_continuous_tracking)
                    
                    def stop_continuous_tracking(self):
                        """Stop continuous mouse tracking"""
                        self.continuous_tracking = False
                        if self.tracking_timer:
                            self.master.after_cancel(self.tracking_timer)
                            self.tracking_timer = None
                    
                    def track_mouse_continuously(self):
                        """Continuously track mouse position during resize periods"""
                        if not self.continuous_tracking:
                            return
                        
                        try:
                            # Check current mouse position
                            mouse_over_cell = self.is_mouse_over_cell()
                            mouse_over_buttons = self.mouse_over_buttons()
                            
                            if mouse_over_cell and not self.hover_active:
                                # Hide trigger icon from previously active hover manager
                                if CellMenuManager.active_manager and CellMenuManager.active_manager != self:
                                    CellMenuManager.active_manager.hide_menu()
                                
                                # Set this as the active hover manager
                                CellMenuManager.active_manager = self
                                
                                self.hover_active = True
                                self.mouse_inside = True
                                self.show_trigger_icon()
                            elif not mouse_over_cell and not mouse_over_buttons and self.hover_active:
                                self.hover_active = False
                                self.mouse_inside = False
                                self.hide_trigger_icon()
                                if self.menu_visible:
                                    self.hide_menu()
                        except:
                            pass
                        
                        # Continue tracking
                        if self.continuous_tracking:
                            self.master.after(100, self.track_mouse_continuously)
                    
                    def show_buttons(self):
                        """Show buttons with instant pop-in effect and vignette"""
                        if self.menu_visible:
                            return
                        
                        self.menu_visible = True
                        
                        # Add vignette effect - darken the cell background slightly
                        self.apply_vignette()
                        
                        # Position button container at final position
                        self.button_container.place(relx=0.5, rely=0.70, anchor="center")
                        
                        # Pack buttons horizontally with spacing
                        for i, btn_frame in enumerate([self.edit_btn, self.copy_btn, self.paste_btn, self.delete_btn]):
                            if self.should_show_button(i):
                                btn_frame.pack(side="left", padx=2)
                        
                        # Ensure button container is on top
                        self.button_container.lift()
                    
                    def hide_buttons(self):
                        """Hide buttons with instant pop-out effect and remove vignette"""
                        if not self.menu_visible:
                            return
                        
                        self.menu_visible = False
                        
                        # Remove vignette effect - restore original background
                        self.remove_vignette()
                        
                        # Hide button container immediately
                        try:
                            self.button_container.place_forget()
                            # Unpack all buttons
                            for btn_frame in [self.edit_btn, self.copy_btn, self.paste_btn, self.delete_btn]:
                                btn_frame.pack_forget()
                        except:
                            pass
                    
                    def apply_vignette(self):
                        """Apply vignette effect to highlight the active cell"""
                        try:
                            # Store original colors if not already stored
                            if not hasattr(self, 'original_colors'):
                                self.original_colors = {}
                                for widget in self.widgets_to_tint:
                                    try:
                                        self.original_colors[widget] = widget.cget('bg')
                                    except:
                                        pass
                            
                            # Apply darker background to create vignette effect
                            for widget in self.widgets_to_tint:
                                try:
                                    original_color = self.original_colors.get(widget, "#F5F5F5")
                                    # Darken the color by reducing RGB values
                                    darkened_color = self.darken_color(original_color, 0.15)
                                    widget.configure(bg=darkened_color)
                                except:
                                    pass
                        except:
                            pass
                    
                    def remove_vignette(self):
                        """Remove vignette effect and restore original colors"""
                        try:
                            if hasattr(self, 'original_colors'):
                                for widget in self.widgets_to_tint:
                                    try:
                                        original_color = self.original_colors.get(widget, "#F5F5F5")
                                        widget.configure(bg=original_color)
                                    except:
                                        pass
                        except:
                            pass
                    
                    def darken_color(self, color, factor):
                        """Darken a color by the given factor (0.0 to 1.0)"""
                        try:
                            # Handle different color formats
                            if color.startswith('#'):
                                # Hex color
                                r = int(color[1:3], 16)
                                g = int(color[3:5], 16)
                                b = int(color[5:7], 16)
                            else:
                                # Named color - convert to approximate RGB
                                color_map = {
                                    'white': (255, 255, 255),
                                    'SystemButtonFace': (240, 240, 240),
                                    'lightgray': (211, 211, 211),
                                    'gray': (128, 128, 128)
                                }
                                r, g, b = color_map.get(color.lower(), (240, 240, 240))
                            
                            # Darken by reducing RGB values
                            r = int(r * (1 - factor))
                            g = int(g * (1 - factor))
                            b = int(b * (1 - factor))
                            
                            return f"#{r:02x}{g:02x}{b:02x}"
                        except:
                            return "#E0E0E0"  # Fallback darkened color
                    
                    def should_show_button(self, button_index):
                        """Determine which buttons to show based on shifts"""
                        has_shifts = self.shifts and len(self.shifts) > 0
                        has_copied_shifts = hasattr(self.parent_app, 'copied_shifts') and self.parent_app.copied_shifts
                        
                        if button_index == 0:  # Edit button - always show
                            return True
                        elif button_index == 1:  # Copy button - only if has shifts
                            return has_shifts
                        elif button_index == 2:  # Paste button - only if has copied shifts
                            return has_copied_shifts
                        elif button_index == 3:  # Delete button - only if has shifts
                            return has_shifts
                        return False
                    
                    def set_actions(self, day_str, shifts, parent_app):
                        """Set up action bindings for the new cell-click system"""
                        # DEBUG: Action setup debugging
                        # print(f"\n🔧 SET_ACTIONS called for day: {day_str}")
                        # print(f"📊 Shifts provided: {len(shifts) if shifts else 0}")
                        # if shifts:
                        #     for i, shift in enumerate(shifts):
                        #         print(f"   Shift {i+1}: {shift.get('employee', 'Unknown')} - {shift.get('start', '?')} to {shift.get('end', '?')}")
                        
                        self.day_str = day_str
                        self.shifts = shifts
                        self.parent_app = parent_app
                        
                        # DEBUG: Action confirmation
                        # print(f"✅ Actions set for {day_str} with {len(self.shifts) if self.shifts else 0} shifts")
                        
                        # Set up button actions with event stopping
                        edit_btn = self.edit_btn.winfo_children()[0]  # Get the actual button label
                        copy_btn = self.copy_btn.winfo_children()[0]
                        paste_btn = self.paste_btn.winfo_children()[0]
                        delete_btn = self.delete_btn.winfo_children()[0]
                        
                        # Edit button - open day editor
                        edit_btn.bind("<Button-1>", lambda e: self.handle_edit_action_with_stop(e))
                        
                        # Copy button - start copy operation
                        copy_btn.bind("<Button-1>", lambda e: self.handle_copy_action_with_stop(e))
                        
                        # Paste button - paste copied shifts
                        paste_btn.bind("<Button-1>", lambda e: self.handle_paste_action_with_stop(e))
                        
                        # Delete button - delete shifts with confirmation
                        delete_btn.bind("<Button-1>", lambda e: self.handle_delete_action_with_stop(e))
                    
                    def handle_cell_click(self, event):
                        """Handle clicking anywhere in the cell"""
                        # Prevent rapid double-clicks from causing issues
                        current_time = self.master.tk.call('clock', 'milliseconds')
                        if hasattr(self, 'last_click_time') and (current_time - self.last_click_time) < 200:
                            return
                        self.last_click_time = current_time
                        
                        # First, hide UI from any other active cell
                        if CellMenuManager.active_manager and CellMenuManager.active_manager != self:
                            CellMenuManager.active_manager.hide_menu()
                        
                        # Set this as the active manager
                        CellMenuManager.active_manager = self
                        
                        # Toggle buttons for this cell
                        if self.menu_visible:
                            # Hide buttons if they're visible
                            self.hide_menu()
                            # Clear active manager when hiding
                            if CellMenuManager.active_manager == self:
                                CellMenuManager.active_manager = None
                        else:
                            # Show buttons if they're not visible
                            self.show_menu()
                    
                    def is_click_on_button(self, event):
                        """Check if the click was on a button"""
                        if not self.menu_visible:
                            return False
                        
                        # Get click coordinates relative to the master widget
                        try:
                            # Convert click coordinates to master widget coordinates
                            click_x = event.x_root - self.master.winfo_rootx()
                            click_y = event.y_root - self.master.winfo_rooty()
                            
                            # Check if click is in button area
                            return self.is_point_in_button_area(click_x, click_y)
                        except:
                            return False
                    
                    def is_point_in_button_area(self, x, y):
                        """Check if a point is in the button area"""
                        try:
                            cell_width = self.master.winfo_width()
                            cell_height = self.master.winfo_height()
                            
                            if cell_width <= 0 or cell_height <= 0:
                                return False
                            
                            # Calculate button area (same as mouse_over_buttons method)
                            button_center_y = cell_height * 0.70
                            button_area_height = 40
                            
                            button_area_x1 = cell_width * 0.2
                            button_area_x2 = cell_width * 0.8
                            button_area_y1 = button_center_y - button_area_height // 2
                            button_area_y2 = button_center_y + button_area_height // 2
                            
                            return (button_area_x1 <= x <= button_area_x2 and 
                                   button_area_y1 <= y <= button_area_y2)
                        except:
                            return False
                    
                    def handle_edit_action(self):
                        """Handle edit button click"""
                        self.parent_app.open_day_editor(self.day_str)
                        self.hide_menu()  # Hide buttons after action
                        # Clear active manager after action
                        if CellMenuManager.active_manager == self:
                            CellMenuManager.active_manager = None
                    
                    def handle_copy_action(self):
                        """Handle copy button click"""
                        # DEBUG: Copy action debugging
                        # print(f"\n🖱️  COPY BUTTON CLICKED for day: {self.day_str}")
                        # print(f"📊 Available shifts: {len(self.shifts) if self.shifts else 0}")
                        
                        if self.shifts and len(self.shifts) > 0:
                            # DEBUG: Copy operation start
                            # print(f"📋 Calling copy_day_shifts with {len(self.shifts)} shifts")
                            # Start copy operation (simplified for now)
                            self.parent_app.copy_day_shifts(self.day_str, self.shifts)
                            self.hide_menu()  # Hide buttons after action
                            # Clear active manager after action
                            if CellMenuManager.active_manager == self:
                                CellMenuManager.active_manager = None
                        else:
                            # DEBUG: No shifts available
                            # print(f"❌ No shifts to copy")
                            pass
                    
                    def handle_paste_action(self):
                        """Handle paste button click"""
                        # DEBUG: Paste action debugging
                        # print(f"\n🖱️  PASTE BUTTON CLICKED for day: {self.day_str}")
                        
                        if hasattr(self.parent_app, 'copied_shifts'):
                            # DEBUG: Found copied shifts
                            # print(f"📋 Found copied_shifts attribute: {self.parent_app.copied_shifts}")
                            if self.parent_app.copied_shifts:
                                # DEBUG: Starting paste operation
                                # print(f"📥 Calling paste_day_shifts")
                                # Hide menu BEFORE calling paste to prevent widget destruction issues
                                self.hide_menu()
                                # Clear active manager after action
                                if CellMenuManager.active_manager == self:
                                    CellMenuManager.active_manager = None
                                self.parent_app.paste_day_shifts(self.day_str)
                            else:
                                # DEBUG: No shifts to paste
                                # print(f"❌ copied_shifts is empty")
                                pass
                        else:
                            # DEBUG: No copied shifts attribute
                            # print(f"❌ No copied_shifts attribute found")
                            pass
                    
                    def handle_delete_action(self):
                        """Handle delete button click with confirmation"""
                        if not self.shifts or len(self.shifts) == 0:
                            self.hide_menu()  # Hide buttons even if no shifts
                            # Clear active manager
                            if CellMenuManager.active_manager == self:
                                CellMenuManager.active_manager = None
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
                        
                        self.hide_menu()  # Hide buttons after action
                        # Clear active manager after action
                        if CellMenuManager.active_manager == self:
                            CellMenuManager.active_manager = None
                    
                    # New action methods that stop event propagation
                    def handle_edit_action_with_stop(self, event):
                        """Handle edit button click and stop event propagation"""
                        event.stopPropagation() if hasattr(event, 'stopPropagation') else None
                        self.handle_edit_action()
                        return "break"  # Tkinter way to stop event propagation
                    
                    def handle_copy_action_with_stop(self, event):
                        """Handle copy button click and stop event propagation"""
                        event.stopPropagation() if hasattr(event, 'stopPropagation') else None
                        self.handle_copy_action()
                        return "break"
                    
                    def handle_paste_action_with_stop(self, event):
                        """Handle paste button click and stop event propagation"""
                        event.stopPropagation() if hasattr(event, 'stopPropagation') else None
                        self.handle_paste_action()
                        return "break"
                    
                    def handle_delete_action_with_stop(self, event):
                        """Handle delete button click and stop event propagation"""
                        event.stopPropagation() if hasattr(event, 'stopPropagation') else None
                        self.handle_delete_action()
                        return "break"
                    
                    def add_widget(self, widget):
                        """Add widget to click tracking"""
                        self.widgets_to_tint.append(widget)
                        # Bind click events to the widget
                        widget.bind("<Button-1>", self.handle_cell_click)
                    
                    def on_mouse_motion(self, event=None):
                        """Handle mouse motion for continuous tracking"""
                        current_time = self.master.tk.call('clock', 'milliseconds')
                        
                        # Throttle motion events to avoid performance issues
                        if current_time - self.last_mouse_check < 50:  # 50ms throttle
                            return
                        
                        self.last_mouse_check = current_time
                        
                        # Check if we should show/hide UI elements based on current position
                        mouse_over_cell = self.is_mouse_over_cell()
                        
                        if mouse_over_cell and not self.hover_active:
                            # Hide trigger icon from previously active hover manager
                            if CellMenuManager.active_manager and CellMenuManager.active_manager != self:
                                CellMenuManager.active_manager.hide_menu()
                            
                            # Set this as the active hover manager
                            CellMenuManager.active_manager = self
                            
                            self.hover_active = True
                            self.mouse_inside = True
                            self.show_trigger_icon()
                        elif not mouse_over_cell and self.hover_active and not self.mouse_over_buttons():
                            self.hover_active = False
                            self.mouse_inside = False
                            self.master.after(50, self.check_hide_ui)
                    
                    def on_cell_enter(self, event=None):
                        """Handle mouse entering the cell - show trigger icon"""
                        # Force hide UI from previously active hover manager (including buttons)
                        if CellMenuManager.active_manager and CellMenuManager.active_manager != self:
                            CellMenuManager.active_manager.hide_menu()
                        
                        # Set this as the active hover manager
                        CellMenuManager.active_manager = self
                        
                        self.hover_active = True
                        self.mouse_inside = True
                        self.show_trigger_icon()
                    
                    def on_cell_leave(self, event=None):
                        """Handle mouse leaving the cell - hide trigger icon and buttons"""
                        self.hover_active = False
                        self.mouse_inside = False
                        # Shorter delay for more responsive behavior
                        self.master.after(50, self.check_hide_ui)
                    
                    def ensure_clean_state(self):
                        """Ensure UI is in a clean state before showing new elements"""
                        # Hide buttons immediately if they're visible
                        if self.menu_visible:
                            self.menu_visible = False
                            try:
                                self.button_container.place_forget()
                                for btn_frame in [self.edit_btn, self.copy_btn, self.paste_btn, self.delete_btn]:
                                    btn_frame.pack_forget()
                            except:
                                pass
                    
                    def check_hide_ui(self):
                        """Check if we should hide the UI elements with improved detection"""
                        current_time = self.master.tk.call('clock', 'milliseconds')
                        
                        # Prevent excessive checking
                        if current_time - self.last_mouse_check < self.mouse_check_interval:
                            return
                        
                        self.last_mouse_check = current_time
                        
                        # Check if mouse is still over the cell or buttons
                        mouse_over_cell = self.is_mouse_over_cell()
                        mouse_over_buttons = self.mouse_over_buttons()
                        
                        if not mouse_over_cell and not mouse_over_buttons:
                            self.hide_trigger_icon()
                            if self.menu_visible:
                                self.hide_menu()
                        elif mouse_over_cell and not self.hover_active:
                            # Mouse re-entered cell area
                            self.hover_active = True
                            self.show_trigger_icon()
                    
                    def is_mouse_over_cell(self):
                        """Check if mouse is over the cell with improved accuracy"""
                        try:
                            # Get mouse position relative to master widget
                            mouse_x = self.master.winfo_pointerx() - self.master.winfo_rootx()
                            mouse_y = self.master.winfo_pointery() - self.master.winfo_rooty()
                            
                            # Get actual cell dimensions
                            cell_width = self.master.winfo_width()
                            cell_height = self.master.winfo_height()
                            
                            # Check if within cell bounds with small margin
                            margin = 2
                            return (0 - margin <= mouse_x <= cell_width + margin and 
                                   0 - margin <= mouse_y <= cell_height + margin)
                        except:
                            return False
                    
                    def mouse_over_buttons(self):
                        """Check if mouse is over the button area with improved accuracy"""
                        try:
                            # Only check if buttons are actually visible
                            if not self.menu_visible:
                                return False
                                
                            # Get mouse position relative to master widget
                            mouse_x = self.master.winfo_pointerx() - self.master.winfo_rootx()
                            mouse_y = self.master.winfo_pointery() - self.master.winfo_rooty()
                            
                            # Get actual cell dimensions
                            cell_width = self.master.winfo_width()
                            cell_height = self.master.winfo_height()
                            
                            # Check if cell dimensions are valid
                            if cell_width <= 0 or cell_height <= 0:
                                return False
                            
                            # Calculate button area based on actual positioning (70% from top)
                            button_center_y = cell_height * 0.70
                            button_area_height = 40  # More precise button area
                            
                            button_area_x1 = cell_width * 0.2   # More conservative horizontal area
                            button_area_x2 = cell_width * 0.8
                            button_area_y1 = button_center_y - button_area_height // 2
                            button_area_y2 = button_center_y + button_area_height // 2
                            
                            return (button_area_x1 <= mouse_x <= button_area_x2 and 
                                   button_area_y1 <= mouse_y <= button_area_y2)
                        except:
                            return False
                
                # Create and configure menu manager for this cell
                hover_mgr = CellMenuManager(cell_frame)
                
                # Store reference to the class for global access (only once)
                if not hasattr(self, '_temp_cell_menu_class'):
                    self._temp_cell_menu_class = CellMenuManager
                
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
                day_label.pack(side="left", padx=1, pady=1)  # Minimal padding for tiny day numbers
                
                # Track day labels for font updates
                self.day_labels.append(day_label)
                
                # Get shifts first to determine content frame type
                month_key = f"{self.current_year}-{self.current_month:02d}"
                shifts = self.data.get("schedule", {}).get(month_key, {}).get(day_str, [])
                
                # Content frame (shifts) - no scrolling, show up to 15 shifts
                content_frame = tk.Frame(cell_frame, bg=bg_color)
                content_frame.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
                
                # Add shifts with dynamic font sizing and display limit
                num_shifts = len(shifts)
                max_display_shifts = 24  # Show up to 24 shifts in 2 columns (12 rows x 2)
                
                if num_shifts > 0:
                    # Sort shifts by start time for better organization (proper time sorting)
                    def get_sort_time(shift):
                        try:
                            # Parse the time string and convert to 24-hour format for proper sorting
                            dt = datetime.strptime(shift['start'], TIME_FMT)
                            return dt.hour * 60 + dt.minute  # Convert to minutes for easy comparison
                        except ValueError:
                            return 999999  # Put invalid times at the end
                    
                    sorted_shifts = sorted(shifts, key=get_sort_time)
                    
                    # Use larger, more readable fonts for shifts - increased further for 2-column layout
                    if num_shifts <= 4:
                        # Large readable font for low density
                        cell_shift_font = ("Segoe UI", 13)  # Was 11, now 13 (+2)
                    elif num_shifts <= 8:
                        # Medium-large readable font for medium density
                        cell_shift_font = ("Segoe UI", 12)  # Was 10, now 12 (+2)
                    else:
                        # Still very readable font for high density
                        cell_shift_font = ("Segoe UI", 11)  # Was 9, now 11 (+2)
                    
                    # Display up to max_display_shifts in 2 columns
                    shifts_to_show = sorted_shifts[:max_display_shifts]
                    
                    # Create shifts in pairs for 2-column layout
                    for i in range(0, len(shifts_to_show), 2):
                        row_frame = tk.Frame(content_frame, bg=bg_color)
                        row_frame.pack(fill="x", pady=0)
                        
                        # Configure 2 equal columns
                        row_frame.grid_columnconfigure(0, weight=1)
                        row_frame.grid_columnconfigure(1, weight=1)
                        
                        # Left column shift
                        left_shift = shifts_to_show[i]
                        left_name = left_shift['employee']
                        if len(left_name) > 12:  # Shorter for 2-column layout
                            left_name = left_name[:9] + "..."
                        left_text = f"{left_name} ({format_time_simple(left_shift['start'])}-{format_time_simple(left_shift['end'])})"
                        
                        left_label = tk.Label(row_frame, 
                                            text=left_text, 
                                            font=cell_shift_font,
                                            anchor="w", bg=bg_color,
                                            justify="left")
                        left_label._custom_font_size = True
                        left_label._dynamic_font = cell_shift_font
                        left_label.grid(row=0, column=0, sticky="w", padx=(0, 2))
                        self.schedule_labels.append((left_label, 'shift'))
                        
                        # Right column shift (if exists)
                        if i + 1 < len(shifts_to_show):
                            right_shift = shifts_to_show[i + 1]
                            right_name = right_shift['employee']
                            if len(right_name) > 12:  # Shorter for 2-column layout
                                right_name = right_name[:9] + "..."
                            right_text = f"{right_name} ({format_time_simple(right_shift['start'])}-{format_time_simple(right_shift['end'])})"
                            
                            right_label = tk.Label(row_frame, 
                                                 text=right_text, 
                                                 font=cell_shift_font,
                                                 anchor="w", bg=bg_color,
                                                 justify="left")
                            right_label._custom_font_size = True
                            right_label._dynamic_font = cell_shift_font
                            right_label.grid(row=0, column=1, sticky="w", padx=(2, 0))
                            self.schedule_labels.append((right_label, 'shift'))
                    
                    # If there are more shifts than we can display, show "+n more"
                    if num_shifts > max_display_shifts:
                        remaining_count = num_shifts - max_display_shifts
                        more_frame = tk.Frame(content_frame, bg=bg_color)
                        more_frame.pack(fill="x", pady=1)  # Minimal spacing for "+n more"
                        
                        # Create a more visually distinct "+n more" indicator
                        more_label = tk.Label(more_frame, 
                                            text=f"    +{remaining_count} more shifts...", 
                                            font=("Segoe UI", cell_shift_font[1], "italic"),
                                            anchor="w", bg=bg_color,
                                            fg="#888")
                        more_label.pack(fill="x", padx=0)  # No horizontal padding
                        
                        # Add to schedule labels for font updates
                        self.schedule_labels.append((more_label, 'more'))

                # No longer need cell-wide bindings - icons handle their own actions
                
                # Set up the three action icons (edit, copy, delete)
                hover_mgr.setup_cell_click(day_str, shifts, self)

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
        """Copy shifts from source to target day with validation"""
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
            
            # Copy shifts to target day with validation
            target_shifts = self.data["schedule"][month_key][target_day_str]
            
            shifts_added = 0
            conflicts_found = []
            skipped_duplicates = 0
            
            for shift in shifts:
                # Check if this exact shift already exists
                duplicate = False
                for existing in target_shifts:
                    if (existing["employee"] == shift["employee"] and 
                        existing["start"] == shift["start"] and 
                        existing["end"] == shift["end"]):
                        duplicate = True
                        skipped_duplicates += 1
                        break
                
                if not duplicate:
                    # Validate the shift for the target day
                    is_valid, shift_conflicts = self.validate_shift_scheduling(
                        shift["employee"], target_day_str, 
                        shift["start"], shift["end"], show_dialog=False)
                    
                    if not is_valid:
                        # Collect conflicts for this shift
                        conflicts_found.append({
                            'employee': shift["employee"],
                            'time': f"{shift['start']} - {shift['end']}",
                            'conflicts': shift_conflicts
                        })
                    
                    # Add the shift regardless of conflicts (user can decide what to do)
                    target_shifts.append(shift.copy())
                    shifts_added += 1
            
            if shifts_added > 0:
                # Save data and refresh calendar
                save_data(self.data)
                self.draw_calendar()
                
                # Show results with any conflicts
                if conflicts_found:
                    conflict_message = f"✅ Successfully copied {shifts_added} shift(s) to {target_day_str}.\n\n"
                    conflict_message += "⚠️ However, the following conflicts were detected:\n\n"
                    
                    for conflict in conflicts_found:
                        conflict_message += f"• {conflict['employee']} ({conflict['time']}):\n"
                        for issue in conflict['conflicts']:
                            conflict_message += f"  - {issue}\n"
                        conflict_message += "\n"
                    
                    conflict_message += "💡 You may want to review and adjust these shifts."
                    messagebox.showwarning("Shifts Copied with Conflicts", conflict_message)
                else:
                    success_message = f"✅ Successfully copied {shifts_added} shift(s) to {target_day_str}."
                    if skipped_duplicates > 0:
                        success_message += f"\n\n📝 Skipped {skipped_duplicates} duplicate shift(s)."
                    messagebox.showinfo("Shifts Copied", success_message)
            else:
                if skipped_duplicates > 0:
                    messagebox.showinfo("No Changes", 
                                      f"All {skipped_duplicates} shift(s) already exist on the target day.")
                else:
                    messagebox.showinfo("No Changes", "No shifts were copied.")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy shifts: {str(e)}")

    def copy_day_shifts(self, day_str, shifts):
        """Copy shifts to clipboard for later pasting"""
        try:
            # DEBUG: Copy operation debugging
            # print(f"\n🔍 COPY DEBUG: Starting copy operation")
            # print(f"📅 Source day: {day_str}")
            # print(f"📋 Number of shifts to copy: {len(shifts)}")
            
            # DEBUG: Print each shift being copied
            # for i, shift in enumerate(shifts):
            #     print(f"   Shift {i+1}: {shift.get('employee', 'Unknown')} - {shift.get('start', '?')} to {shift.get('end', '?')}")
            
            # Store shifts in a temporary clipboard
            self.copied_shifts = {
                'source_day': day_str,
                'shifts': shifts.copy()
            }
            
            # DEBUG: Copy confirmation
            # print(f"💾 Copied shifts stored in self.copied_shifts")
            # print(f"📝 Copied data: {self.copied_shifts}")
            
            day_date = datetime.strptime(day_str, "%Y-%m-%d").strftime("%A, %B %d, %Y")
            messagebox.showinfo("Shifts Copied", 
                              f"Copied {len(shifts)} shift(s) from {day_date}.\n\n"
                              f"Use the paste button on any day to add these shifts.")
            
            # DEBUG: Copy success
            # print(f"✅ COPY DEBUG: Copy operation completed successfully\n")
            
        except Exception as e:
            # DEBUG: Copy error
            # print(f"❌ COPY DEBUG: Error during copy - {str(e)}")
            messagebox.showerror("Copy Error", f"Failed to copy shifts: {str(e)}")

    def paste_day_shifts(self, target_day_str):
        """Paste copied shifts to the target day with conflict detection"""
        try:
            # DEBUG: Paste operation debugging
            # print(f"\n🔍 PASTE DEBUG: Starting paste operation")
            # print(f"📅 Target day: {target_day_str}")
            
            # Check if we have copied shifts
            if not hasattr(self, 'copied_shifts'):
                # DEBUG: No copied shifts attribute
                # print(f"❌ PASTE DEBUG: No 'copied_shifts' attribute found")
                messagebox.showwarning("No Shifts Copied", "No shifts available to paste.")
                return
            
            if not self.copied_shifts:
                # DEBUG: Empty copied shifts
                # print(f"❌ PASTE DEBUG: 'copied_shifts' is empty or None")
                messagebox.showwarning("No Shifts Copied", "No shifts available to paste.")
                return
            
            # DEBUG: Found copied shifts
            # print(f"📋 Found copied shifts: {self.copied_shifts}")
            
            source_day = self.copied_shifts['source_day']
            shifts_to_paste = self.copied_shifts['shifts']
            
            # DEBUG: Paste operation details
            # print(f"📤 Source day: {source_day}")
            # print(f"📥 Shifts to paste: {len(shifts_to_paste)}")
            
            # DEBUG: Print each shift being pasted
            # for i, shift in enumerate(shifts_to_paste):
            #     print(f"   Pasting Shift {i+1}: {shift.get('employee', 'Unknown')} - {shift.get('start', '?')} to {shift.get('end', '?')}")
            
            # Parse dates
            target_dt = datetime.strptime(target_day_str, DATE_FMT).date()
            source_dt = datetime.strptime(source_day, DATE_FMT).date()
            
            # Check for conflicts before pasting
            # DEBUG: Conflict analysis
            # print(f"🔍 Analyzing shifts for conflicts...")
            conflicting_shifts = []
            non_conflicting_shifts = []
            
            for shift in shifts_to_paste:
                # DEBUG: Individual shift checking
                # print(f"   🔍 Checking shift: {shift.get('employee', 'Unknown')} - {shift.get('start', '?')} to {shift.get('end', '?')}")
                
                # Use the existing validation method to check for conflicts
                is_valid, conflicts = self.validate_shift_scheduling(
                    shift["employee"], target_day_str, 
                    shift["start"], shift["end"], show_dialog=False)
                
                if not is_valid and conflicts:
                    # DEBUG: Conflicts found
                    # print(f"   ❌ Conflicts found: {conflicts}")
                    conflicting_shifts.append({
                        'shift': shift,
                        'conflicts': conflicts
                    })
                else:
                    # DEBUG: No conflicts
                    # print(f"   ✅ No conflicts found")
                    non_conflicting_shifts.append(shift)
            
            # If there are conflicts, show conflict resolution dialog
            if conflicting_shifts:
                # DEBUG: Conflict resolution
                # print(f"⚠️  Found {len(conflicting_shifts)} conflicting shifts")
                user_choice = self.show_paste_conflict_dialog(
                    target_day_str, conflicting_shifts, non_conflicting_shifts)
                
                if user_choice == "cancel":
                    # DEBUG: User cancelled
                    # print(f"❌ User cancelled paste operation")
                    return
                elif user_choice == "non_conflicting":
                    shifts_to_paste = non_conflicting_shifts
                    # DEBUG: Paste only non-conflicting
                    # print(f"📝 Pasting only {len(shifts_to_paste)} non-conflicting shifts")
                elif user_choice == "all":
                    # Keep all shifts (conflicting + non-conflicting)
                    # DEBUG: Paste all including conflicts
                    # print(f"⚠️  User chose to paste all shifts including conflicts")
                    pass
            else:
                # DEBUG: No conflicts found
                # print(f"✅ No conflicts found, proceeding with all shifts")
                pass
            
            # If no shifts to paste after conflict resolution, exit
            if not shifts_to_paste:
                # DEBUG: No shifts after resolution
                # print(f"❌ No shifts to paste after conflict resolution")
                messagebox.showinfo("No Shifts Pasted", "No shifts were pasted.")
                return
            
            # Get month key for target
            month_key = f"{target_dt.year}-{target_dt.month:02d}"
            # DEBUG: Target month
            # print(f"📆 Target month key: {month_key}")
            
            # Ensure schedule structure exists
            if "schedule" not in self.data:
                # DEBUG: Creating schedule structure
                # print(f"🏗️  Creating 'schedule' structure in data")
                self.data["schedule"] = {}
            if month_key not in self.data["schedule"]:
                # DEBUG: Creating month
                # print(f"🏗️  Creating month '{month_key}' in schedule")
                self.data["schedule"][month_key] = {}
            if target_day_str not in self.data["schedule"][month_key]:
                # DEBUG: Creating day
                # print(f"🏗️  Creating day '{target_day_str}' in month")
                self.data["schedule"][month_key][target_day_str] = []
            
            # Show existing shifts before pasting
            existing_shifts = self.data["schedule"][month_key][target_day_str]
            # DEBUG: Existing shifts
            # print(f"📋 Existing shifts on target day: {len(existing_shifts)}")
            # for i, shift in enumerate(existing_shifts):
            #     print(f"   Existing Shift {i+1}: {shift.get('employee', 'Unknown')} - {shift.get('start', '?')} to {shift.get('end', '?')}")
            
            # Add shifts to target day
            # DEBUG: Adding shifts
            # print(f"➕ Adding {len(shifts_to_paste)} shifts to target day")
            self.data["schedule"][month_key][target_day_str].extend(shifts_to_paste)
            
            # Show final shifts after pasting
            final_shifts = self.data["schedule"][month_key][target_day_str]
            # DEBUG: Final shifts
            # print(f"📋 Final shifts on target day: {len(final_shifts)}")
            # for i, shift in enumerate(final_shifts):
            #     print(f"   Final Shift {i+1}: {shift.get('employee', 'Unknown')} - {shift.get('start', '?')} to {shift.get('end', '?')}")
            
            # Save data and refresh calendar
            # DEBUG: Save and refresh
            # print(f"💾 Saving data to file")
            save_data(self.data)
            # print(f"🔄 Refreshing calendar display")
            self.draw_calendar()
            
            # Show success message
            target_date = target_dt.strftime("%A, %B %d, %Y")
            source_date = source_dt.strftime("%A, %B %d, %Y")
            
            if len(conflicting_shifts) > 0:
                skipped_count = len(self.copied_shifts['shifts']) - len(shifts_to_paste)
                success_msg = f"Successfully pasted {len(shifts_to_paste)} shift(s) from {source_date} to {target_date}."
                if skipped_count > 0:
                    success_msg += f"\n\n⚠️ {skipped_count} conflicting shift(s) were skipped."
                messagebox.showinfo("Shifts Pasted", success_msg)
            else:
                messagebox.showinfo("Shifts Pasted", 
                                  f"Successfully pasted {len(shifts_to_paste)} shift(s) from {source_date} to {target_date}.")
            
            # DEBUG: Paste success
            # print(f"✅ PASTE DEBUG: Paste operation completed successfully\n")
            
        except Exception as e:
            # DEBUG: Paste error
            # print(f"❌ PASTE DEBUG: Error during paste - {str(e)}")
            # import traceback
            # print(f"📊 Full traceback: {traceback.format_exc()}")
            messagebox.showerror("Paste Error", f"Failed to paste shifts: {str(e)}")

    def show_paste_conflict_dialog(self, target_day_str, conflicting_shifts, non_conflicting_shifts):
        """Show dialog for resolving paste conflicts"""
        
        # Create the dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("Shift Conflicts Detected")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        self.center_dialog(dialog, 650, 500)
        
        # Result variable to store user choice
        result = tk.StringVar(value="cancel")
        
        # Header frame
        header_frame = tk.Frame(dialog, bg="#FF8C42", height=60)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        header_container = tk.Frame(header_frame, bg="#FF8C42")
        header_container.pack(expand=True, fill="both")
        
        tk.Label(header_container, text="⚠️ Scheduling Conflicts Detected", 
                font=("Segoe UI", 16, "bold"), 
                bg="#FF8C42", fg="white").pack(expand=True)
        
        # Main content frame
        content_frame = tk.Frame(dialog, padx=20, pady=20)
        content_frame.pack(fill="both", expand=True)
        
        # Target day info
        target_date = datetime.strptime(target_day_str, DATE_FMT).strftime("%A, %B %d, %Y")
        info_text = f"Conflicts found when pasting shifts to {target_date}:"
        tk.Label(content_frame, text=info_text, font=("Segoe UI", 12, "bold"),
                wraplength=600).pack(pady=(0, 15))
        
        # Scrollable frame for conflicts
        canvas = tk.Canvas(content_frame, height=200)
        scrollbar = tk.Scrollbar(content_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Add conflicts to scrollable frame
        for i, conflict_info in enumerate(conflicting_shifts):
            shift = conflict_info['shift']
            conflicts = conflict_info['conflicts']
            
            # Shift info frame
            shift_frame = tk.Frame(scrollable_frame, relief="solid", bd=1, padx=10, pady=8)
            shift_frame.pack(fill="x", pady=(0, 10))
            
            # Shift header
            shift_header = f"❌ {shift['employee']} ({shift['start']} - {shift['end']})"
            tk.Label(shift_frame, text=shift_header, font=("Segoe UI", 11, "bold"), 
                    fg="#D32F2F", anchor="w").pack(fill="x")
            
            # Conflict details
            for conflict in conflicts:
                conflict_text = f"   • {conflict}"
                tk.Label(shift_frame, text=conflict_text, font=("Segoe UI", 10), 
                        fg="#666666", anchor="w", wraplength=550).pack(fill="x", padx=(10, 0))
        
        canvas.pack(side="left", fill="both", expand=True, pady=(0, 20))
        scrollbar.pack(side="right", fill="y", pady=(0, 20))
        
        # Summary info
        summary_frame = tk.Frame(content_frame)
        summary_frame.pack(fill="x", pady=(10, 20))
        
        total_shifts = len(conflicting_shifts) + len(non_conflicting_shifts)
        summary_text = (f"{len(conflicting_shifts)} conflicting shifts, ")        
        tk.Label(summary_frame, text=summary_text, font=("Segoe UI", 10), 
                fg="#666666", wraplength=600).pack()
        
        # Options frame
        options_frame = tk.Frame(content_frame)
        options_frame.pack(fill="x", pady=(10, 0))
        
        tk.Label(options_frame, text="Choose an option:", 
                font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 10))
        
        # Radio button options
        options = [
            ("cancel", "❌ Cancel paste", "#FF5722"),
            ("non_conflicting", f"✅ Exclude", "#4CAF50"),
            ("all", f"⚠️ Paste all", "#FF9800")
        ]
        
        for value, text, color in options:
            if value == "non_conflicting" and len(non_conflicting_shifts) == 0:
                # Disable option if no non-conflicting shifts
                rb = tk.Radiobutton(options_frame, text=text, variable=result, value=value,
                                  font=("Segoe UI", 11), fg="#CCCCCC", state="disabled")
            else:
                rb = tk.Radiobutton(options_frame, text=text, variable=result, value=value,
                                  font=("Segoe UI", 11), fg=color)
            rb.pack(anchor="w", pady=2)
        
        # Button frame
        button_frame = tk.Frame(content_frame)
        button_frame.pack(fill="x", pady=(20, 0))
        
        def on_confirm():
            dialog.destroy()
        
        def on_cancel():
            result.set("cancel")
            dialog.destroy()
        
        # Buttons
        tk.Button(button_frame, text="Cancel", command=on_cancel, 
                 font=("Segoe UI", 10), width=12).pack(side="right", padx=(10, 0))
        
        tk.Button(button_frame, text="Confirm", command=on_confirm, 
                 font=("Segoe UI", 10, "bold"), width=12, 
                 bg="#2196F3", fg="white").pack(side="right")
        
        # Wait for dialog to close
        dialog.wait_window()
        
        return result.get()

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
            
            if not emp_name or not start or not end:
                messagebox.showwarning("Missing", "Select employee, start, and end times.")
                return
            
            # Use comprehensive validation
            is_valid, conflicts = self.validate_shift_scheduling(
                emp_name, day_str, start, end, show_dialog=True)
            
            if not is_valid:
                return  # User chose not to proceed or validation failed

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
        
        def open_update_assistant():
            dialog.destroy()
            apply_update()
        
        def skip_update():
            dialog.destroy()
        
        tk.Button(button_frame, text="Get Update Guide", 
                 command=open_update_assistant, 
                 bg="#49D3E6", fg="white", 
                 font=("Arial", 10, "bold")).pack(side="right", padx=(10, 0))
        
        tk.Button(button_frame, text="Skip This Update", 
                 command=skip_update).pack(side="right")
    
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


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Work Scheduler")
    
    # Hide main window initially
    root.withdraw()
    
    # Set theme for better looking widgets
    style = ttk.Style()
    if "clam" in style.theme_names():
        style.theme_use("clam")
    
    # Create app - splash screen will be handled by the app itself
    app = WorkSchedulerApp(root)
    root.mainloop()
