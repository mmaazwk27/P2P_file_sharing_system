"""
peer_gui.py
GUI for the peer with light navy blue theme
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import os
import time
from peer import (
    register_with_tracker, 
    lookup_filename, 
    download_from_peer,
    list_shared_files,
    get_local_ip,
    peer_server
)

class PeerGUI:
    def __init__(self, root, peer_id, tracker_host, tracker_port, shared_dir):
        self.root = root
        self.peer_id = peer_id
        self.tracker_host = tracker_host
        self.tracker_port = tracker_port
        self.shared_dir = shared_dir
        
        self.root.title(f"P2P File Sharing - {peer_id}")
        self.root.geometry("900x750")
        self.root.configure(bg='#E8EAF6')  # Light navy blue background
        
        # Set theme colors
        self.primary_color = '#3F51B5'    # Navy Blue
        self.secondary_color = '#5C6BC0'  # Medium Blue
        self.accent_color = '#7986CB'     # Light Blue
        self.success_color = '#4CAF50'    # Green
        self.text_color = '#333333'
        self.bg_color = '#E8EAF6'
        
        self.local_ip = get_local_ip()
        self.setup_gui()
        self.start_peer_server()
        self.register_with_tracker()
        
    def setup_gui(self):
        # Header
        header_frame = tk.Frame(self.root, bg=self.primary_color, height=70)
        header_frame.pack(fill='x', padx=10, pady=10)
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text=f"PEER: {self.peer_id}", 
                              font=('Arial', 16, 'bold'), 
                              bg=self.primary_color, fg='white')
        title_label.pack(expand=True)
        
        # Peer info frame
        info_frame = tk.LabelFrame(self.root, text="Peer Information", 
                                  font=('Arial', 11, 'bold'),
                                  bg=self.bg_color, fg=self.text_color,
                                  relief='ridge', bd=2)
        info_frame.pack(fill='x', padx=10, pady=5)
        
        info_text = f"Display Name: {self.peer_id} | IP: {self.local_ip} | Shared Directory: {self.shared_dir}"
        info_label = tk.Label(info_frame, text=info_text, font=('Arial', 10),
                             bg=self.bg_color, fg=self.text_color)
        info_label.pack(padx=10, pady=5)
        
        # Main content frame
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Left frame - Shared Files
        left_frame = tk.LabelFrame(main_frame, text="My Shared Files", 
                                  font=('Arial', 11, 'bold'),
                                  bg=self.bg_color, fg=self.text_color,
                                  relief='ridge', bd=2)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
        
        # Shared files listbox with scrollbar
        self.shared_files_listbox = tk.Listbox(left_frame, bg='white', fg=self.text_color,
                                              font=('Arial', 10), height=10)
        shared_scrollbar = tk.Scrollbar(left_frame, orient='vertical')
        self.shared_files_listbox.configure(yscrollcommand=shared_scrollbar.set)
        shared_scrollbar.config(command=self.shared_files_listbox.yview)
        
        self.shared_files_listbox.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        shared_scrollbar.pack(side='right', fill='y', pady=5)
        
        # File management buttons
        file_buttons_frame = tk.Frame(left_frame, bg=self.bg_color)
        file_buttons_frame.pack(fill='x', padx=5, pady=5)
        
        refresh_files_btn = tk.Button(file_buttons_frame, text="🔄 Refresh", 
                                     command=self.refresh_shared_files,
                                     bg=self.secondary_color, fg='white',
                                     font=('Arial', 9), padx=10)
        refresh_files_btn.pack(side='left', padx=2)
        
        add_file_btn = tk.Button(file_buttons_frame, text="➕ Add File", 
                                command=self.add_file_to_shared,
                                bg=self.success_color, fg='white',
                                font=('Arial', 9), padx=10)
        add_file_btn.pack(side='left', padx=2)
        
        # Right frame - File Search & Download
        right_frame = tk.LabelFrame(main_frame, text="File Search & Download", 
                                   font=('Arial', 11, 'bold'),
                                   bg=self.bg_color, fg=self.text_color,
                                   relief='ridge', bd=2)
        right_frame.pack(side='right', fill='both', expand=True, padx=(5, 0))
        
        # Search frame
        search_frame = tk.Frame(right_frame, bg=self.bg_color)
        search_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Label(search_frame, text="Filename:", bg=self.bg_color, 
                fg=self.text_color, font=('Arial', 10)).pack(side='left')
        
        self.search_entry = tk.Entry(search_frame, width=30, font=('Arial', 10))
        self.search_entry.pack(side='left', padx=5)
        self.search_entry.bind('<Return>', lambda e: self.search_file())
        
        search_btn = tk.Button(search_frame, text="🔍 Search", 
                              command=self.search_file,
                              bg=self.primary_color, fg='white',
                              font=('Arial', 10, 'bold'), padx=15)
        search_btn.pack(side='left', padx=5)
        
        # Search results
        results_frame = tk.Frame(right_frame, bg=self.bg_color)
        results_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        tk.Label(results_frame, text="Available Owners:", bg=self.bg_color,
                fg=self.text_color, font=('Arial', 10, 'bold')).pack(anchor='w')
        
        # Treeview for search results
        columns = ('Display Name', 'IP Address', 'Port')
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show='headings', height=8)
        
        self.results_tree.heading('Display Name', text='Display Name')
        self.results_tree.heading('IP Address', text='IP Address')
        self.results_tree.heading('Port', text='Port')
        
        self.results_tree.column('Display Name', width=150)
        self.results_tree.column('IP Address', width=120)
        self.results_tree.column('Port', width=80)
        
        tree_scroll = ttk.Scrollbar(results_frame, orient='vertical', command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=tree_scroll.set)
        
        self.results_tree.pack(side='left', fill='both', expand=True)
        tree_scroll.pack(side='right', fill='y')
        
        # Download controls
        download_frame = tk.Frame(right_frame, bg=self.bg_color)
        download_frame.pack(fill='x', padx=10, pady=10)
        
        self.download_btn = tk.Button(download_frame, text="⬇️ Download Selected", 
                                     command=self.download_selected,
                                     bg=self.success_color, fg='white',
                                     font=('Arial', 10, 'bold'), padx=15,
                                     state='disabled')
        self.download_btn.pack(side='left', padx=5)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(download_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(side='left', fill='x', expand=True, padx=10)
        
        self.progress_label = tk.Label(download_frame, text="Ready", bg=self.bg_color,
                                      fg=self.text_color, font=('Arial', 9))
        self.progress_label.pack(side='left', padx=5)
        
        # Logs frame
        logs_frame = tk.LabelFrame(self.root, text="Activity Logs", 
                                  font=('Arial', 11, 'bold'),
                                  bg=self.bg_color, fg=self.text_color,
                                  relief='ridge', bd=2)
        logs_frame.pack(fill='x', padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(logs_frame, height=8, 
                                                 bg='white', fg=self.text_color,
                                                 font=('Consolas', 9))
        self.log_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Control buttons
        control_frame = tk.Frame(self.root, bg=self.bg_color)
        control_frame.pack(fill='x', padx=10, pady=10)
        
        clear_logs_btn = tk.Button(control_frame, text="🗑️ Clear Logs", 
                                  command=self.clear_logs,
                                  bg='#E57373', fg='white',
                                  font=('Arial', 10), padx=15)
        clear_logs_btn.pack(side='left', padx=5)
        
        disconnect_btn = tk.Button(control_frame, text="🔌 Disconnect", 
                                  command=self.disconnect,
                                  bg='#F44336', fg='white',
                                  font=('Arial', 10, 'bold'), padx=20)
        disconnect_btn.pack(side='right', padx=5)
        
        # Initial setup
        self.refresh_shared_files()
        self.log_message("Peer GUI Started")
        self.log_message(f"Connected to tracker: {self.tracker_host}:{self.tracker_port}")
        
    def log_message(self, message):
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        
    def refresh_shared_files(self):
        self.shared_files_listbox.delete(0, tk.END)
        files = list_shared_files(self.shared_dir)
        for file in files:
            self.shared_files_listbox.insert(tk.END, file)
            
    def add_file_to_shared(self):
        file_path = filedialog.askopenfilename(title="Select file to share")
        if file_path:
            filename = os.path.basename(file_path)
            dest_path = os.path.join(self.shared_dir, filename)
            
            if not os.path.exists(dest_path):
                import shutil
                shutil.copy2(file_path, dest_path)
                self.log_message(f"Added file to shared directory: {filename}")
                self.refresh_shared_files()
                # Re-register with tracker to update file list
                self.register_with_tracker()
            else:
                messagebox.showwarning("File Exists", f"File '{filename}' already exists in shared directory")
                
    def search_file(self):
        filename = self.search_entry.get().strip()
        if not filename:
            messagebox.showwarning("Input Error", "Please enter a filename to search")
            return
            
        self.log_message(f"Searching for file: {filename}")
        self.progress_label.config(text="Searching...")
        
        # Clear previous results
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
            
        def search_thread():
            try:
                owners = lookup_filename(self.tracker_host, self.tracker_port, filename)
                self.root.after(0, self.display_search_results, filename, owners)
            except Exception as e:
                self.root.after(0, self.search_error, str(e))
                
        threading.Thread(target=search_thread, daemon=True).start()
        
    def display_search_results(self, filename, owners):
        if not owners:
            self.log_message(f"No owners found for file: {filename}")
            self.progress_label.config(text="No owners found")
            messagebox.showinfo("Search Results", f"No peers are sharing '{filename}'")
            return
            
        for owner in owners:
            self.results_tree.insert('', 'end', values=(
                owner['peer_id'], owner['ip'], owner['port']
            ))
            
        self.log_message(f"Found {len(owners)} owner(s) for '{filename}'")
        self.progress_label.config(text=f"Found {len(owners)} owners")
        self.download_btn.config(state='normal')
        
    def search_error(self, error_msg):
        self.log_message(f"Search error: {error_msg}")
        self.progress_label.config(text="Search failed")
        messagebox.showerror("Search Error", f"Failed to search file: {error_msg}")
        
    def download_selected(self):
        selection = self.results_tree.selection()
        if not selection:
            messagebox.showwarning("Selection Error", "Please select an owner from the list")
            return
            
        item = self.results_tree.item(selection[0])
        owner_info = {
            'peer_id': item['values'][0],
            'ip': item['values'][1],
            'port': item['values'][2]
        }
        
        filename = self.search_entry.get().strip()
        if not filename:
            messagebox.showwarning("Input Error", "No filename specified")
            return
            
        self.log_message(f"Downloading '{filename}' from {owner_info['peer_id']}")
        
        def download_thread():
            try:
                self.root.after(0, self.update_progress, 0, "Starting download...")
                
                # Mock progress updates (in real implementation, this would be based on actual progress)
                for i in range(10, 101, 10):
                    time.sleep(0.5)  # Simulate download time
                    self.root.after(0, self.update_progress, i, f"Downloading... {i}%")
                    
                success = download_from_peer(owner_info, filename, ".", enable_compression=True, verify_hash=True)
                
                if success:
                    self.root.after(0, self.download_success, filename, owner_info['peer_id'])
                else:
                    self.root.after(0, self.download_error, filename)
                    
            except Exception as e:
                self.root.after(0, self.download_error, filename, str(e))
                
        threading.Thread(target=download_thread, daemon=True).start()
        
    def update_progress(self, value, message):
        self.progress_var.set(value)
        self.progress_label.config(text=message)
        
    def download_success(self, filename, owner):
        self.log_message(f"Successfully downloaded '{filename}' from {owner}")
        self.progress_label.config(text="Download completed!")
        messagebox.showinfo("Download Complete", f"File '{filename}' downloaded successfully!")
        self.progress_var.set(0)
        
    def download_error(self, filename, error_msg="Unknown error"):
        self.log_message(f"Failed to download '{filename}': {error_msg}")
        self.progress_label.config(text="Download failed")
        messagebox.showerror("Download Error", f"Failed to download '{filename}': {error_msg}")
        self.progress_var.set(0)
        
    def clear_logs(self):
        self.log_text.delete(1.0, tk.END)
        self.log_message("Logs cleared")
        
    def start_peer_server(self):
        # Start peer server in background thread
        def start_server():
            try:
                peer_server("0.0.0.0", self.get_dynamic_port(), self.shared_dir, enable_compression=True)
            except Exception as e:
                self.log_message(f"Server error: {e}")
                
        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()
        
    def get_dynamic_port(self):
        import random
        return random.randint(5000, 6000)
        
    def register_with_tracker(self):
        def register_thread():
            try:
                files = list_shared_files(self.shared_dir)
                # Use a dynamic port for the peer server
                port = self.get_dynamic_port()
                resp = register_with_tracker(self.tracker_host, self.tracker_port, 
                                           self.peer_id, self.local_ip, port, files)
                self.root.after(0, self.log_message, f"Registered with tracker: {resp}")
            except Exception as e:
                self.root.after(0, self.log_message, f"Registration failed: {e}")
                
        threading.Thread(target=register_thread, daemon=True).start()
        
    def disconnect(self):
        if messagebox.askyesno("Disconnect", "Are you sure you want to disconnect?"):
            self.log_message("Disconnecting from P2P network...")
            self.root.after(1000, self.root.destroy)

def main():
    # This would be called from run_demo.py with parameters
    root = tk.Tk()
    
    # Default values for testing
    peer_id = "TestPeer"
    tracker_host = "127.0.0.1"
    tracker_port = 9000
    shared_dir = "shared_directory"
    
    app = PeerGUI(root, peer_id, tracker_host, tracker_port, shared_dir)
    root.mainloop()

if __name__ == "__main__":
    main()