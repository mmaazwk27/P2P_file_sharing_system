"""
tracker_gui.py
GUI for the tracker with light orange theme
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
import json
from tracker import run_tracker, index, index_lock

class TrackerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("P2P File Sharing - Tracker")
        self.root.geometry("1000x700")
        self.root.configure(bg='#FFF5E6')  # Light orange background
        
        # Set theme colors
        self.primary_color = '#FFA726'  # Orange
        self.secondary_color = '#FFB74D'  # Light Orange
        self.accent_color = '#FF9800'   # Dark Orange
        self.text_color = '#333333'
        self.bg_color = '#FFF5E6'
        
        self.setup_gui()
        self.running = True
        self.start_tracker_thread()
        self.start_ui_updater()
        
    def setup_gui(self):
        # Header
        header_frame = tk.Frame(self.root, bg=self.primary_color, height=80)
        header_frame.pack(fill='x', padx=10, pady=10)
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="P2P TRACKER SERVER", 
                              font=('Arial', 20, 'bold'), 
                              bg=self.primary_color, fg='white')
        title_label.pack(expand=True)
        
        # Main content frame
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Left frame - Connected Peers
        left_frame = tk.LabelFrame(main_frame, text="Connected Peers", 
                                  font=('Arial', 12, 'bold'),
                                  bg=self.bg_color, fg=self.text_color,
                                  relief='ridge', bd=2)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
        
        # Treeview for peers
        columns = ('Display Name', 'IP Address', 'Port', 'Shared Files')
        self.peers_tree = ttk.Treeview(left_frame, columns=columns, show='headings', height=15)
        
        # Configure columns
        self.peers_tree.heading('Display Name', text='Display Name')
        self.peers_tree.heading('IP Address', text='IP Address')
        self.peers_tree.heading('Port', text='Port')
        self.peers_tree.heading('Shared Files', text='Shared Files')
        
        self.peers_tree.column('Display Name', width=150)
        self.peers_tree.column('IP Address', width=120)
        self.peers_tree.column('Port', width=80)
        self.peers_tree.column('Shared Files', width=300)
        
        # Scrollbar for treeview
        tree_scroll = ttk.Scrollbar(left_frame, orient='vertical', command=self.peers_tree.yview)
        self.peers_tree.configure(yscrollcommand=tree_scroll.set)
        
        self.peers_tree.pack(side='left', fill='both', expand=True)
        tree_scroll.pack(side='right', fill='y')
        
        # Right frame - Logs
        right_frame = tk.LabelFrame(main_frame, text="Activity Logs", 
                                   font=('Arial', 12, 'bold'),
                                   bg=self.bg_color, fg=self.text_color,
                                   relief='ridge', bd=2)
        right_frame.pack(side='right', fill='both', expand=True, padx=(5, 0))
        
        # Log text area
        self.log_text = scrolledtext.ScrolledText(right_frame, height=20, width=60,
                                                 bg='white', fg=self.text_color,
                                                 font=('Consolas', 10))
        self.log_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Stats frame
        stats_frame = tk.Frame(self.root, bg=self.bg_color)
        stats_frame.pack(fill='x', padx=10, pady=5)
        
        self.stats_label = tk.Label(stats_frame, text="Peers Connected: 0 | Files Indexed: 0",
                                   font=('Arial', 12, 'bold'), 
                                   bg=self.secondary_color, fg='white')
        self.stats_label.pack(fill='x', ipady=5)
        
        # Control buttons
        button_frame = tk.Frame(self.root, bg=self.bg_color)
        button_frame.pack(fill='x', padx=10, pady=10)
        
        refresh_btn = tk.Button(button_frame, text="🔄 Refresh Now", 
                               command=self.update_peers_list,
                               bg=self.accent_color, fg='white',
                               font=('Arial', 11, 'bold'), padx=20, pady=5)
        refresh_btn.pack(side='left', padx=5)
        
        clear_logs_btn = tk.Button(button_frame, text="🗑️ Clear Logs", 
                                  command=self.clear_logs,
                                  bg='#E57373', fg='white',
                                  font=('Arial', 11, 'bold'), padx=20, pady=5)
        clear_logs_btn.pack(side='left', padx=5)
        
        exit_btn = tk.Button(button_frame, text="⏹️ Stop Tracker", 
                            command=self.stop_tracker,
                            bg='#F44336', fg='white',
                            font=('Arial', 11, 'bold'), padx=20, pady=5)
        exit_btn.pack(side='right', padx=5)
        
        self.log_message("Tracker GUI Started")
        self.log_message("Waiting for peer connections...")
        
    def log_message(self, message):
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        
    def update_peers_list(self):
        # Clear existing items
        for item in self.peers_tree.get_children():
            self.peers_tree.delete(item)
            
        with index_lock:
            # Get all unique peers
            all_peers = {}
            for filename, owners in index.items():
                for owner in owners:
                    peer_key = (owner['peer_id'], owner['ip'], owner['port'])
                    if peer_key not in all_peers:
                        all_peers[peer_key] = []
                    all_peers[peer_key].append(filename)
            
            # Add peers to treeview
            for (peer_id, ip, port), files in all_peers.items():
                files_str = ", ".join(files[:5])  # Show first 5 files
                if len(files) > 5:
                    files_str += f" ... (+{len(files)-5} more)"
                
                self.peers_tree.insert('', 'end', values=(peer_id, ip, port, files_str))
                
        # Update stats
        peer_count = len(all_peers)
        file_count = len(index)
        self.stats_label.config(text=f"Peers Connected: {peer_count} | Files Indexed: {file_count}")
        
    def clear_logs(self):
        self.log_text.delete(1.0, tk.END)
        self.log_message("Logs cleared")
        
    def start_tracker_thread(self):
        self.tracker_thread = threading.Thread(target=run_tracker, daemon=True)
        self.tracker_thread.start()
        self.log_message("Tracker server started on port 9000")
        
    def start_ui_updater(self):
        def update_ui():
            while self.running:
                self.update_peers_list()
                time.sleep(5)  # Update every 5 seconds
                
        self.ui_thread = threading.Thread(target=update_ui, daemon=True)
        self.ui_thread.start()
        
    def stop_tracker(self):
        self.running = False
        self.log_message("Tracker is shutting down...")
        self.root.after(2000, self.root.destroy)

def main():
    root = tk.Tk()
    app = TrackerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()