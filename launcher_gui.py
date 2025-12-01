import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import subprocess
import sys
import os
import webbrowser
from pathlib import Path

class CloudStorageLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Cloud Storage System - Control Panel")
        self.root.geometry("900x700")
        self.root.configure(bg='#f0f0f0')
        
        # Process tracking
        self.processes = {
            'network': None,
            'backend': None,
            'nodes': []
        }
        
        self.create_ui()
        
    def create_ui(self):
        # Title
        title_frame = tk.Frame(self.root, bg='#2c3e50', height=80)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)
        
        tk.Label(
            title_frame, 
            text="☁️ Cloud Storage System", 
            font=('Arial', 24, 'bold'),
            fg='white',
            bg='#2c3e50'
        ).pack(pady=20)
        
        # Main container
        main_frame = tk.Frame(self.root, bg='#f0f0f0')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Left panel - Controls
        control_frame = tk.LabelFrame(
            main_frame, 
            text="System Controls", 
            font=('Arial', 12, 'bold'),
            bg='white',
            padx=15,
            pady=15
        )
        control_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        # Network Server
        tk.Label(
            control_frame,
            text="1. Network Server (Port 9000)",
            font=('Arial', 10, 'bold'),
            bg='white'
        ).pack(anchor='w', pady=(0, 5))
        
        network_frame = tk.Frame(control_frame, bg='white')
        network_frame.pack(fill='x', pady=(0, 15))
        
        self.network_btn = tk.Button(
            network_frame,
            text="▶ Start Network Server",
            command=self.start_network,
            bg='#27ae60',
            fg='white',
            font=('Arial', 10, 'bold'),
            width=20,
            cursor='hand2'
        )
        self.network_btn.pack(side='left', padx=(0, 5))
        
        self.network_status = tk.Label(
            network_frame,
            text="⚫ Stopped",
            font=('Arial', 9),
            bg='white'
        )
        self.network_status.pack(side='left')
        
        # Storage Nodes
        tk.Label(
            control_frame,
            text="2. Storage Nodes",
            font=('Arial', 10, 'bold'),
            bg='white'
        ).pack(anchor='w', pady=(0, 5))
        
        node_frame = tk.Frame(control_frame, bg='white')
        node_frame.pack(fill='x', pady=(0, 5))
        
        tk.Label(node_frame, text="Capacity (GB):", bg='white').pack(side='left')
        self.node_capacity = tk.Spinbox(
            node_frame, 
            from_=1, 
            to=100, 
            width=10,
            font=('Arial', 9)
        )
        self.node_capacity.delete(0, 'end')
        self.node_capacity.insert(0, '5')
        self.node_capacity.pack(side='left', padx=5)
        
        tk.Button(
            node_frame,
            text="➕ Add Storage Node",
            command=self.add_storage_node,
            bg='#3498db',
            fg='white',
            font=('Arial', 9, 'bold'),
            cursor='hand2'
        ).pack(side='left')
        
        # Active nodes display
        self.nodes_listbox = tk.Listbox(control_frame, height=4, font=('Arial', 9))
        self.nodes_listbox.pack(fill='x', pady=(5, 15))
        
        # Backend API
        tk.Label(
            control_frame,
            text="3. Backend API (Port 5000)",
            font=('Arial', 10, 'bold'),
            bg='white'
        ).pack(anchor='w', pady=(0, 5))
        
        backend_frame = tk.Frame(control_frame, bg='white')
        backend_frame.pack(fill='x', pady=(0, 15))
        
        self.backend_btn = tk.Button(
            backend_frame,
            text="▶ Start Backend API",
            command=self.start_backend,
            bg='#e67e22',
            fg='white',
            font=('Arial', 10, 'bold'),
            width=20,
            cursor='hand2'
        )
        self.backend_btn.pack(side='left', padx=(0, 5))
        
        self.backend_status = tk.Label(
            backend_frame,
            text="⚫ Stopped",
            font=('Arial', 9),
            bg='white'
        )
        self.backend_status.pack(side='left')
        
        # Web Interface
        tk.Label(
            control_frame,
            text="4. Open Web Interface",
            font=('Arial', 10, 'bold'),
            bg='white'
        ).pack(anchor='w', pady=(0, 5))
        
        tk.Button(
            control_frame,
            text="🌐 Open in Browser",
            command=self.open_browser,
            bg='#9b59b6',
            fg='white',
            font=('Arial', 10, 'bold'),
            width=20,
            cursor='hand2'
        ).pack(anchor='w', pady=(0, 20))
        
        # Quick Start Button
        tk.Button(
            control_frame,
            text="🚀 Quick Start All",
            command=self.quick_start,
            bg='#e74c3c',
            fg='white',
            font=('Arial', 12, 'bold'),
            cursor='hand2'
        ).pack(fill='x', pady=10)
        
        # Stop All Button
        tk.Button(
            control_frame,
            text="⏹ Stop All Services",
            command=self.stop_all,
            bg='#95a5a6',
            fg='white',
            font=('Arial', 10, 'bold'),
            cursor='hand2'
        ).pack(fill='x')
        
        # Right panel - Logs
        log_frame = tk.LabelFrame(
            main_frame,
            text="System Activity Log",
            font=('Arial', 12, 'bold'),
            bg='white',
            padx=10,
            pady=10
        )
        log_frame.pack(side='right', fill='both', expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            font=('Consolas', 9),
            bg='#1e1e1e',
            fg='#00ff00',
            insertbackground='white'
        )
        self.log_text.pack(fill='both', expand=True)
        
        self.log("✅ Control Panel Ready")
        self.log("👉 Click 'Quick Start All' to begin!")
        
    def log(self, message):
        """Add message to log"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update()
        
    def start_network(self):
        """Start network server"""
        if self.processes['network']:
            self.log("⚠️  Network server already running")
            return
            
        try:
            self.log("🔄 Starting network server...")
            self.processes['network'] = subprocess.Popen(
                [sys.executable, 'network_server.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            self.network_status.config(text="🟢 Running", fg='green')
            self.network_btn.config(state='disabled')
            self.log("✅ Network server started on port 9000")
            
            # Start output reader thread
            threading.Thread(
                target=self.read_output,
                args=(self.processes['network'], "NETWORK"),
                daemon=True
            ).start()
            
        except Exception as e:
            self.log(f"❌ Failed to start network server: {e}")
            messagebox.showerror("Error", f"Failed to start network server:\n{e}")
            
    def add_storage_node(self):
        """Add a storage node"""
        if not self.processes['network']:
            messagebox.showwarning(
                "Warning",
                "Please start the Network Server first!"
            )
            return
            
        try:
            capacity = self.node_capacity.get()
            self.log(f"🔄 Starting storage node ({capacity}GB)...")
            
            process = subprocess.Popen(
                [sys.executable, 'storage_node.py', 'localhost', capacity],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            self.processes['nodes'].append(process)
            self.nodes_listbox.insert(tk.END, f"Node {len(self.processes['nodes'])} - {capacity}GB")
            self.log(f"✅ Storage node {len(self.processes['nodes'])} added ({capacity}GB)")
            
            # Start output reader thread
            threading.Thread(
                target=self.read_output,
                args=(process, f"NODE-{len(self.processes['nodes'])}"),
                daemon=True
            ).start()
            
        except Exception as e:
            self.log(f"❌ Failed to add storage node: {e}")
            messagebox.showerror("Error", f"Failed to add storage node:\n{e}")
            
    def start_backend(self):
        """Start backend API"""
        if self.processes['backend']:
            self.log("⚠️  Backend API already running")
            return
            
        if not self.processes['network']:
            messagebox.showwarning(
                "Warning",
                "Please start the Network Server first!"
            )
            return
            
        try:
            self.log("🔄 Starting backend API...")
            self.processes['backend'] = subprocess.Popen(
                [sys.executable, 'backend_api.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            self.backend_status.config(text="🟢 Running", fg='green')
            self.backend_btn.config(state='disabled')
            self.log("✅ Backend API started on port 5000")
            
            # Start output reader thread
            threading.Thread(
                target=self.read_output,
                args=(self.processes['backend'], "BACKEND"),
                daemon=True
            ).start()
            
        except Exception as e:
            self.log(f"❌ Failed to start backend API: {e}")
            messagebox.showerror("Error", f"Failed to start backend API:\n{e}")
            
    def read_output(self, process, name):
        """Read process output"""
        while process.poll() is None:
            line = process.stdout.readline()
            if line:
                self.log(f"[{name}] {line.strip()}")
                
    def open_browser(self):
        """Open web interface"""
        if not self.processes['backend']:
            messagebox.showwarning(
                "Warning",
                "Please start the Backend API first!"
            )
            return
            
        self.log("🌐 Opening web interface...")
        webbrowser.open('http://localhost:5000')
        
    def quick_start(self):
        """Start everything"""
        self.log("🚀 Quick Start initiated...")
        
        # Start network
        self.start_network()
        self.root.after(2000, self._quick_start_nodes)
        
    def _quick_start_nodes(self):
        """Start nodes after network"""
        # Add 2 nodes
        self.node_capacity.delete(0, 'end')
        self.node_capacity.insert(0, '5')
        self.add_storage_node()
        
        self.root.after(1000, lambda: self._add_second_node())
        
    def _add_second_node(self):
        self.node_capacity.delete(0, 'end')
        self.node_capacity.insert(0, '10')
        self.add_storage_node()
        
        self.root.after(2000, self._quick_start_backend)
        
    def _quick_start_backend(self):
        """Start backend after nodes"""
        self.start_backend()
        self.log("✅ All services started!")
        self.log("👉 Click 'Open in Browser' to use your cloud storage!")
        
    def stop_all(self):
        """Stop all services"""
        self.log("🛑 Stopping all services...")
        
        # Stop network
        if self.processes['network']:
            self.processes['network'].terminate()
            self.processes['network'] = None
            self.network_status.config(text="⚫ Stopped", fg='black')
            self.network_btn.config(state='normal')
            self.log("✅ Network server stopped")
            
        # Stop nodes
        for node in self.processes['nodes']:
            node.terminate()
        self.processes['nodes'] = []
        self.nodes_listbox.delete(0, tk.END)
        self.log(f"✅ All storage nodes stopped")
        
        # Stop backend
        if self.processes['backend']:
            self.processes['backend'].terminate()
            self.processes['backend'] = None
            self.backend_status.config(text="⚫ Stopped", fg='black')
            self.backend_btn.config(state='normal')
            self.log("✅ Backend API stopped")
            
        self.log("✅ All services stopped")
        
    def on_closing(self):
        """Handle window close"""
        if messagebox.askokcancel("Quit", "Stop all services and exit?"):
            self.stop_all()
            self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = CloudStorageLauncher(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()