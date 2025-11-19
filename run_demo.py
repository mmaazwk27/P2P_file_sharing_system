import os
import sys
import subprocess
import platform
import socket
import tkinter as tk
from tkinter import simpledialog

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def create_shared_directory():
    """Create shared_directory folder without sample files"""
    shared_dir = "shared_directory"
    os.makedirs(shared_dir, exist_ok=True)
    print(f"✔ Shared directory ready: {shared_dir}")
    return shared_dir

def get_local_ip():
    """Get the local IP address that can be used by other devices"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"

def run_command(title, command):
    system = platform.system().lower()

    if "windows" in system:
        safe_cmd = f'start "{title}" cmd /k "{command}"'
        subprocess.Popen(safe_cmd, shell=True)
    else:
        subprocess.Popen(command, shell=True)

    print(f"▶ Launched: {command}")

def run_tracker_gui():
    """Run tracker with GUI"""
    python_exec = f'"{sys.executable}"'
    cmd = f'{python_exec} tracker_gui.py'
    run_command("Tracker GUI", cmd)

def run_peer_gui():
    """Run peer with GUI - get parameters via dialog"""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    # Get peer display name
    display_name = simpledialog.askstring("Peer Setup", "Enter your display name:", 
                                         initialvalue=f"Peer_{os.getpid()}")
    if not display_name:
        print("❌ Display name is required!")
        return
        
    # Get tracker IP
    tracker_ip = simpledialog.askstring("Peer Setup", "Enter Tracker IP:", 
                                       initialvalue="127.0.0.1")
    if not tracker_ip:
        print("❌ Tracker IP is required!")
        return
    
    root.destroy()
    
    # Create shared directory
    shared_dir = create_shared_directory()
    
    # Run peer GUI
    python_exec = f'"{sys.executable}"'
    cmd = f'{python_exec} peer_gui.py --peer-id "{display_name}" --tracker {tracker_ip}:9000 --shared-dir "{shared_dir}"'
    run_command(f"Peer - {display_name}", cmd)

def main():
    clear_screen()
    print("="*60)
    print("        P2P FILE SHARING SYSTEM - LAUNCHER")
    print("="*60)
    print("1) Tracker (GUI)")
    print("2) Peer (GUI)")
    print("3) Tracker (CLI)")
    print("4) Peer (CLI)")
    print()
    
    # Show local IP for convenience
    local_ip = get_local_ip()
    print(f"Your local IP address: {local_ip}")
    print("Share this IP with other devices for tracker connection")
    print()

    choice = input("Enter 1-4: ").strip()

    if choice == "1":
        print("\n🚀 Starting TRACKER (GUI)...")
        create_shared_directory()
        run_tracker_gui()
        
    elif choice == "2":
        print("\n🚀 Starting PEER (GUI)...")
        run_peer_gui()
        
    elif choice == "3":
        print("\n🚀 Starting TRACKER (CLI)...")
        create_shared_directory()
        python_exec = f'"{sys.executable}"'
        cmd = f'{python_exec} tracker.py'
        run_command("Tracker CLI", cmd)
        
    elif choice == "4":
        print("\n🚀 Starting PEER (CLI)...")
        display_name = input("Enter your display name (e.g., John's Laptop): ").strip()
        if not display_name:
            display_name = f"Peer_{os.getpid()}"
        
        tracker_ip = input("Enter Tracker IP: ").strip()
        if not tracker_ip:
            print("❌ Tracker IP is required!")
            return
        
        shared_dir = create_shared_directory()
        
        import random
        peer_port = random.randint(5000, 6000)
        
        python_exec = f'"{sys.executable}"'
        cmd = (
            f'{python_exec} peer.py '
            f'--peer-id "{display_name}" '
            f'--host 0.0.0.0 '
            f'--port {peer_port} '
            f'--shared-dir "{shared_dir}" '
            f'--tracker {tracker_ip}:9000'
        )
        
        run_command(f"Peer CLI - {display_name}", cmd)
        
    else:
        print("❌ Invalid option.")

if __name__ == "__main__":
    main()