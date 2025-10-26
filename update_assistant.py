#!/usr/bin/env python3
"""
Employee Scheduler Update Assistant
A simple step-by-step guide to help users update their Employee Scheduler application.
"""

import os
import sys
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox
import requests
from pathlib import Path

# Configuration
GITHUB_REPO = "WAM2021/Employee_Scheduler"
UPDATE_CHECK_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
GITHUB_RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases/latest"

class UpdateAssistant:
    def __init__(self, root):
        self.root = root
        self.root.title("Employee Scheduler Update Assistant")
        self.root.geometry("600x500")
        self.root.resizable(False, False)
        
        # Center the window
        self.center_window()
        
        # Variables
        self.current_step = 0
        self.latest_version = None
        self.download_url = None
        self.current_exe_path = None
        
        # Find current executable
        self.find_current_executable()
        
        self.create_widgets()
        self.check_for_updates()
        
    def center_window(self):
        """Center the window on the screen."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def find_current_executable(self):
        """Try to find the current Employee Scheduler executable."""
        # Check current directory first
        current_dir = os.getcwd()
        possible_names = [
            "Employee_Scheduler*.exe",
            "WorkScheduler.exe",
            "Employee*.exe"
        ]
        
        # Check common locations
        search_dirs = [
            current_dir,
            os.path.dirname(sys.executable) if hasattr(sys, 'frozen') else current_dir,
            os.path.join(os.path.expanduser("~"), "Desktop"),
            os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop"),
            os.path.join(os.path.expanduser("~"), "Downloads")
        ]
        
        for search_dir in search_dirs:
            if os.path.exists(search_dir):
                for file in os.listdir(search_dir):
                    if file.lower().startswith("employee") and file.lower().endswith(".exe"):
                        self.current_exe_path = os.path.join(search_dir, file)
                        return
    
    def create_widgets(self):
        """Create the GUI widgets."""
        # Header
        header_frame = tk.Frame(self.root, bg="#49D3E6", height=80)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="🔄 Update Assistant", 
                              font=("Arial", 18, "bold"), 
                              bg="#49D3E6", fg="white")
        title_label.pack(expand=True)
        
        # Main content area
        self.content_frame = tk.Frame(self.root, padx=30, pady=20)
        self.content_frame.pack(fill="both", expand=True)
        
        # Status area
        self.status_label = tk.Label(self.content_frame, text="Checking for updates...", 
                                    font=("Arial", 12, "bold"))
        self.status_label.pack(pady=(0, 20))
        
        # Content area for step instructions
        self.step_frame = tk.Frame(self.content_frame)
        self.step_frame.pack(fill="both", expand=True)
        
        # Button frame
        button_frame = tk.Frame(self.content_frame)
        button_frame.pack(fill="x", pady=(20, 0))
        
        # Configure button style
        button_config = {
            "font": ("Arial", 11, "bold"),
            "height": 2,
            "width": 12,
            "relief": "raised",
            "bd": 2
        }
        
        self.prev_button = tk.Button(button_frame, text="← Previous", 
                                    command=self.previous_step, state=tk.DISABLED,
                                    bg="#6c757d", fg="white", **button_config)
        self.prev_button.pack(side="left", padx=(0, 10))
        
        self.next_button = tk.Button(button_frame, text="Next →", 
                                    command=self.next_step, state=tk.DISABLED,
                                    bg="#007bff", fg="white", **button_config)
        self.next_button.pack(side="right", padx=(10, 0))
        
        self.close_button = tk.Button(button_frame, text="Close", 
                                     command=self.root.quit,
                                     bg="#dc3545", fg="white", **button_config)
        self.close_button.pack(side="right")
    
    def check_for_updates(self):
        """Check for available updates."""
        try:
            response = requests.get(UPDATE_CHECK_URL, timeout=10)
            if response.status_code == 200:
                release_data = response.json()
                self.latest_version = release_data.get('tag_name', '').lstrip('v')
                
                # Find the .exe asset
                for asset in release_data.get('assets', []):
                    if asset['name'].endswith('.exe'):
                        self.download_url = asset['browser_download_url']
                        break
                
                if self.latest_version:
                    self.status_label.config(text=f"New version available: {self.latest_version}")
                    self.show_step_0()
                else:
                    self.status_label.config(text="No updates available")
                    self.show_no_updates()
            else:
                self.status_label.config(text="Could not check for updates")
                self.show_error()
                
        except Exception as e:
            self.status_label.config(text="Error checking for updates")
            self.show_error()
    
    def clear_step_frame(self):
        """Clear the current step content."""
        for widget in self.step_frame.winfo_children():
            widget.destroy()
    
    def show_no_updates(self):
        """Show message when no updates are available."""
        self.clear_step_frame()
        
        message = tk.Label(self.step_frame, 
                          text="✅ You already have the latest version of Employee Scheduler!",
                          font=("Arial", 14), wraplength=500, justify="center")
        message.pack(expand=True)
        
        self.next_button.config(state=tk.DISABLED)
        self.prev_button.config(state=tk.DISABLED)
    
    def show_error(self):
        """Show error message."""
        self.clear_step_frame()
        
        message = tk.Label(self.step_frame, 
                          text="❌ Could not check for updates.\nPlease check your internet connection and try again.",
                          font=("Arial", 12), wraplength=500, justify="center")
        message.pack(expand=True)
        
        retry_button = tk.Button(self.step_frame, text="Retry", 
                               command=self.check_for_updates,
                               bg="#49D3E6", fg="white", font=("Arial", 11, "bold"),
                               height=2, width=10, relief="raised", bd=3)
        retry_button.pack(pady=10)
        
        self.next_button.config(state=tk.DISABLED)
        self.prev_button.config(state=tk.DISABLED)
    
    def show_step_0(self):
        """Step 0: Introduction and overview."""
        self.current_step = 0
        self.clear_step_frame()
        
        title = tk.Label(self.step_frame, text="📱 Update Available!", 
                        font=("Arial", 16, "bold"))
        title.pack(pady=(0, 15))
        
        info_text = f"""A new version ({self.latest_version}) of Employee Scheduler is available!
        
This assistant will guide you through the simple update process step-by-step.

Don't worry - it's easy! Just follow the instructions and you'll have the latest version in no time.

The process involves:
1. Downloading the new version
2. Closing the old version
3. Replacing the old file with the new one
4. Starting the updated application

Ready to get started?"""
        
        info_label = tk.Label(self.step_frame, text=info_text,
                             font=("Arial", 11), wraplength=500, justify="left")
        info_label.pack(pady=10)
        
        self.next_button.config(state=tk.NORMAL, text="Start Update →")
        self.prev_button.config(state=tk.DISABLED)
    
    def show_step_1(self):
        """Step 1: Download the new version."""
        self.current_step = 1
        self.clear_step_frame()
        
        title = tk.Label(self.step_frame, text="📥 Step 1: Download New Version", 
                        font=("Arial", 16, "bold"))
        title.pack(pady=(0, 15))
        
        instructions = """Click the button below to open your web browser and download the latest version.

Your browser will take you to the GitHub releases page where you can download the new Employee_Scheduler.exe file.

💡 Tip: The file will usually download to your Downloads folder."""
        
        info_label = tk.Label(self.step_frame, text=instructions,
                             font=("Arial", 11), wraplength=500, justify="left")
        info_label.pack(pady=10)
        
        download_button = tk.Button(self.step_frame, text="🌐 Open Download Page", 
                                   command=self.open_download_page,
                                   bg="#28a745", fg="white", font=("Arial", 12, "bold"),
                                   height=2, width=20, relief="raised", bd=3)
        download_button.pack(pady=20)
        
        note_label = tk.Label(self.step_frame, text="After downloading, click 'Next' to continue.",
                             font=("Arial", 10), fg="gray")
        note_label.pack(pady=10)
        
        self.next_button.config(state=tk.NORMAL, text="Next →")
        self.prev_button.config(state=tk.NORMAL)
    
    def show_step_2(self):
        """Step 2: Close the current application."""
        self.current_step = 2
        self.clear_step_frame()
        
        title = tk.Label(self.step_frame, text="❌ Step 2: Close Employee Scheduler", 
                        font=("Arial", 16, "bold"))
        title.pack(pady=(0, 15))
        
        instructions = """Now you need to close the Employee Scheduler application (if it's running).

🔍 Look for the Employee Scheduler window and close it by:
• Clicking the ❌ in the top-right corner, OR
• Right-clicking the icon in your taskbar and selecting "Close"

⚠️ Important: The application MUST be closed before you can replace the file!"""
        
        info_label = tk.Label(self.step_frame, text=instructions,
                             font=("Arial", 11), wraplength=500, justify="left")
        info_label.pack(pady=10)
        
        if self.current_exe_path:
            current_location = tk.Label(self.step_frame, 
                                       text=f"📍 Current location: {self.current_exe_path}",
                                       font=("Arial", 9), fg="blue", wraplength=500)
            current_location.pack(pady=10)
        
        self.next_button.config(state=tk.NORMAL, text="Next →")
        self.prev_button.config(state=tk.NORMAL)
    
    def show_step_3(self):
        """Step 3: Replace the old file."""
        self.current_step = 3
        self.clear_step_frame()
        
        title = tk.Label(self.step_frame, text="🔄 Step 3: Replace the Old File", 
                        font=("Arial", 16, "bold"))
        title.pack(pady=(0, 15))
        
        instructions = """Now replace the old Employee Scheduler file with the new one:

1. 📂 Open your Downloads folder (or wherever you saved the new file)
2. 🖱️ Right-click on the new Employee_Scheduler.exe file
3. ✂️ Select "Cut" from the menu
4. 📁 Navigate to where your old Employee Scheduler is located
5. 🗑️ Delete the old Employee_Scheduler.exe file
6. 📋 Right-click in the folder and select "Paste"

✅ That's it! The old file has been replaced with the new version."""
        
        info_label = tk.Label(self.step_frame, text=instructions,
                             font=("Arial", 11), wraplength=500, justify="left")
        info_label.pack(pady=10)
        
        if self.current_exe_path:
            folder_button = tk.Button(self.step_frame, text="📂 Open Current Location", 
                                     command=self.open_current_folder,
                                     bg="#17a2b8", fg="white", font=("Arial", 11, "bold"),
                                     height=2, width=18, relief="raised", bd=3)
            folder_button.pack(pady=10)
        
        self.next_button.config(state=tk.NORMAL, text="Next →")
        self.prev_button.config(state=tk.NORMAL)
    
    def show_step_4(self):
        """Step 4: Start the updated application."""
        self.current_step = 4
        self.clear_step_frame()
        
        title = tk.Label(self.step_frame, text="🎉 Step 4: All Done!", 
                        font=("Arial", 16, "bold"))
        title.pack(pady=(0, 15))
        
        instructions = f"""Congratulations! You've successfully updated Employee Scheduler to version {self.latest_version}!

🚀 To start using the updated application:
• Double-click on the Employee_Scheduler.exe file in its folder
• Or create a desktop shortcut for easy access

✨ Enjoy the new features and improvements!

You can now close this Update Assistant."""
        
        info_label = tk.Label(self.step_frame, text=instructions,
                             font=("Arial", 11), wraplength=500, justify="left")
        info_label.pack(pady=10)
        
        close_button = tk.Button(self.step_frame, text="🎯 Close Assistant", 
                                command=self.root.quit,
                                bg="#28a745", fg="white", font=("Arial", 12, "bold"),
                                height=2, width=16, relief="raised", bd=3)
        close_button.pack(pady=20)
        
        self.next_button.config(state=tk.DISABLED)
        self.prev_button.config(state=tk.NORMAL)
    
    def open_download_page(self):
        """Open the GitHub releases page in the default browser."""
        webbrowser.open(GITHUB_RELEASES_URL)
    
    def open_current_folder(self):
        """Open the folder containing the current executable."""
        if self.current_exe_path:
            folder_path = os.path.dirname(self.current_exe_path)
            os.startfile(folder_path)
    
    def next_step(self):
        """Go to the next step."""
        if self.current_step == 0:
            self.show_step_1()
        elif self.current_step == 1:
            self.show_step_2()
        elif self.current_step == 2:
            self.show_step_3()
        elif self.current_step == 3:
            self.show_step_4()
    
    def previous_step(self):
        """Go to the previous step."""
        if self.current_step == 1:
            self.show_step_0()
        elif self.current_step == 2:
            self.show_step_1()
        elif self.current_step == 3:
            self.show_step_2()
        elif self.current_step == 4:
            self.show_step_3()

def main():
    """Main entry point."""
    root = tk.Tk()
    app = UpdateAssistant(root)
    root.mainloop()

if __name__ == "__main__":
    main()