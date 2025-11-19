import os
import sys
import subprocess
import platform
import socket

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

def main():
    clear_screen()
    print("="*60)
    print("        DYNAMIC P2P FILE SHARING LAUNCHER")
    print("="*60)
    print("1) Tracker")
    print("2) Peer")
    print()
    
    # Show local IP for convenience
    local_ip = get_local_ip()
    print(f"Your local IP address: {local_ip}")
    print("Share this IP with other devices for tracker connection")
    print()

    choice = input("Enter 1 or 2: ").strip()
    python_exec = f'"{sys.executable}"'

    tracker_port = 9000

    if choice == "1":
        print("\n🚀 Starting TRACKER...")
        create_shared_directory()
        cmd = f'{python_exec} tracker.py'
        run_command("Tracker", cmd)
        return

    elif choice == "2":
        print("\n🚀 Starting PEER...")
        
        # Get peer display name
        display_name = input("Enter your display name (e.g., John's Laptop): ").strip()
        if not display_name:
            display_name = f"Peer_{os.getpid()}"
        
        # Get tracker IP
        tracker_ip = input("Enter Tracker IP: ").strip()
        if not tracker_ip:
            print("❌ Tracker IP is required!")
            return
        
        # Create shared directory
        shared_dir = create_shared_directory()
        
        # Use dynamic port
        import random
        peer_port = random.randint(5000, 6000)
        
        cmd = (
            f'{python_exec} peer.py '
            f'--peer-id "{display_name}" '
            f'--host 0.0.0.0 '
            f'--port {peer_port} '
            f'--shared-dir "{shared_dir}" '
            f'--tracker {tracker_ip}:{tracker_port}'
        )
        
        run_command(f"Peer - {display_name}", cmd)
        return

    else:
        print("❌ Invalid option.")

if __name__ == "__main__":
    main()