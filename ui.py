import tkinter as tk
from tkinter import ttk, messagebox
from database import MySQLHandler
from config import ConfigManager
from typing import Optional, Dict

class DatabasePanel(ttk.LabelFrame):
    def __init__(self, parent, title: str, is_source: bool = True, config: Dict = None):
        super().__init__(parent, text=title, padding=15)
        self.db_handler: Optional[MySQLHandler] = None
        self.is_source = is_source
        self.config = config or {}
        
        # Configure grid weights
        self.columnconfigure(1, weight=1)
        for i in range(6):
            self.rowconfigure(i, weight=1)
        
        # Server details
        ttk.Label(self, text="Host:").grid(row=0, column=0, sticky="e", padx=10, pady=5)
        self.host_entry = ttk.Entry(self, width=30)
        self.host_entry.insert(0, self.config.get('host', 'localhost'))
        self.host_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        
        ttk.Label(self, text="Port:").grid(row=1, column=0, sticky="e", padx=10, pady=5)
        self.port_entry = ttk.Entry(self, width=30)
        self.port_entry.insert(0, self.config.get('port', '3306'))
        self.port_entry.grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        
        ttk.Label(self, text="Username:").grid(row=2, column=0, sticky="e", padx=10, pady=5)
        self.user_entry = ttk.Entry(self, width=30)
        self.user_entry.insert(0, self.config.get('username', 'root'))
        self.user_entry.grid(row=2, column=1, sticky="ew", padx=10, pady=5)
        
        ttk.Label(self, text="Password:").grid(row=3, column=0, sticky="e", padx=10, pady=5)
        self.pass_entry = ttk.Entry(self, show="*", width=30)
        if self.config.get('password'):
            self.pass_entry.insert(0, self.config['password'])
        self.pass_entry.grid(row=3, column=1, sticky="ew", padx=10, pady=5)
        
        # Test connection button
        self.test_btn = ttk.Button(self, text="Test Connection", command=self.test_connection)
        self.test_btn.grid(row=4, column=0, columnspan=2, pady=15)
        
        # Database selection (only for source)
        if is_source:
            ttk.Label(self, text="Database:").grid(row=5, column=0, sticky="e", padx=10, pady=5)
            self.db_combo = ttk.Combobox(self, state="disabled", width=27)
            self.db_combo.grid(row=5, column=1, sticky="ew", padx=10, pady=5)
            # Set last used database if available
            if self.config.get('last_database'):
                self.db_combo['values'] = [self.config['last_database']]
                self.db_combo.set(self.config['last_database'])
        else:
            ttk.Label(self, text="New DB Name:").grid(row=5, column=0, sticky="e", padx=10, pady=5)
            self.db_entry = ttk.Entry(self, state="disabled", width=30)
            self.db_entry.grid(row=5, column=1, sticky="ew", padx=10, pady=5)
            if self.config.get('last_database'):
                self.db_entry.configure(state='normal')
                self.db_entry.insert(0, self.config['last_database'])
                self.db_entry.configure(state='disabled')
    
    def get_config(self) -> Dict:
        """Get current configuration"""
        config = {
            'host': self.host_entry.get(),
            'port': self.port_entry.get(),
            'username': self.user_entry.get(),
            'password': self.pass_entry.get(),
            'last_database': self.db_combo.get() if self.is_source else self.db_entry.get()
        }
        return config
    
    def test_connection(self):
        try:
            self.db_handler = MySQLHandler()
            success, message = self.db_handler.connect(
                host=self.host_entry.get(),
                port=int(self.port_entry.get()),
                user=self.user_entry.get(),
                password=self.pass_entry.get()
            )
            
            if success:
                messagebox.showinfo("Success", message)
                if self.is_source:
                    databases = self.db_handler.get_databases()
                    self.db_combo['values'] = databases
                    self.db_combo['state'] = 'readonly'
                else:
                    self.db_entry['state'] = 'normal'
            else:
                messagebox.showerror("Error", message)
                self.db_handler = None
                if self.is_source:
                    self.db_combo['state'] = 'disabled'
                else:
                    self.db_entry['state'] = 'disabled'
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid port number")

class MigrationTool:
    def __init__(self, root):
        self.root = root
        self.root.title("MySQL Database Migration Tool")
        self.root.geometry("1280x720")
        self.root.resizable(False, False)
        
        # Load configuration
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()
        
        # Configure style
        style = ttk.Style()
        style.configure('TLabelframe', padding=10)
        style.configure('TButton', padding=5)
        
        # Main container with padding
        main_frame = ttk.Frame(root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="MySQL Database Migration Tool",
            font=('Helvetica', 16, 'bold')
        )
        title_label.pack(pady=(0, 20))
        
        # Panel container
        panel_frame = ttk.Frame(main_frame)
        panel_frame.pack(fill=tk.BOTH, expand=True)
        
        # Source and destination panels
        self.source_panel = DatabasePanel(
            panel_frame, 
            "Source Database", 
            is_source=True,
            config=self.config['source']
        )
        self.source_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        
        self.dest_panel = DatabasePanel(
            panel_frame, 
            "Destination Database", 
            is_source=False,
            config=self.config['destination']
        )
        self.dest_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        
        # Migration button
        self.migrate_btn = ttk.Button(
            main_frame, 
            text="Start Migration",
            command=self.start_migration,
            style='TButton'
        )
        self.migrate_btn.pack(side=tk.BOTTOM, pady=20)
        
        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def save_config(self, save_passwords: bool = None):
        """Save current configuration"""
        current_config = {
            'source': self.source_panel.get_config(),
            'destination': self.dest_panel.get_config()
        }
        self.config_manager.save_config(current_config, save_passwords)
    
    def on_closing(self):
        """Handle window closing event"""
        if self.source_panel.pass_entry.get() or self.dest_panel.pass_entry.get():
            save_passwords = messagebox.askyesno(
                "Save Passwords",
                "Would you like to save the passwords for the next session?\n\n"
                "Note: Passwords are stored with basic encoding, not encryption."
            )
        else:
            save_passwords = False
        
        self.save_config(save_passwords)
        self.root.destroy()
    
    def start_migration(self):
        if not self.source_panel.db_handler or not self.dest_panel.db_handler:
            messagebox.showerror("Error", "Please test both connections first")
            return
        
        source_db = self.source_panel.db_combo.get()
        dest_db = self.dest_panel.db_entry.get()
        
        if not source_db:
            messagebox.showerror("Error", "Please select a source database")
            return
            
        if not dest_db:
            messagebox.showerror("Error", "Please enter a destination database name")
            return
        
        if messagebox.askyesno("Confirm Migration", 
                             f"Are you sure you want to migrate database '{source_db}' to '{dest_db}'?"):
            success, message = self.source_panel.db_handler.migrate_database(
                source_db,
                self.dest_panel.db_handler,
                dest_db
            )
            
            if success:
                messagebox.showinfo("Success", message)
                # Save configuration after successful migration
                self.save_config()
            else:
                messagebox.showerror("Error", message)
