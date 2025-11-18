import os
import sys
import subprocess
import platform
import socket 

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def create_sample_files(peer_name, folder_name):
    os.makedirs(folder_name, exist_ok=True)
    sample_file = os.path.join(folder_name, f"{peer_name}_sample.txt")
    if not os.path.exists(sample_file):
        with open(sample_file, "w") as f:
            f.write(f"This is a file from {peer_name}\n")
    
    # Create a few more sample files
    sample_file2 = os.path.join(folder_name, f"{peer_name}_document.pdf.txt")
    if not os.path.exists(sample_file2):
        with open(sample_file2, "w") as f:
            f.write(f"PDF document content from {peer_name}\n")
    
    print(f"✔ Sample files created for {peer_name} in {folder_name}")

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
        # full quoting to avoid "C:\Users\M." errors
        safe_cmd = f'start "{title}" cmd /k "{command}"'
        subprocess.Popen(safe_cmd, shell=True)
    else:
        subprocess.Popen(command, shell=True)

    print(f"▶ Launched: {command}")

def main():
    clear_screen()
    print("="*60)
    print("        P2P FILE SHARING LAUNCHER (Cross-Device Support)")
    print("="*60)
    print("1) Tracker")
    print("2) Peer A") 
    print("3) Peer B")
    print()
    
    # Show local IP for convenience
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        print(f"Your local IP address: {local_ip}")
        print("Share this IP with other devices for tracker connection")
    except:
        print("Could not determine local IP address")
    print()

    choice = input("Enter 1 / 2 / 3: ").strip()
    python_exec = f'"{sys.executable}"'  # quoted python path

    tracker_port = 9000
    peer_a_port = 5001
    peer_b_port = 5002

    if choice == "1":
        print("\n🚀 Starting TRACKER...")
        create_sample_files("PeerA", "sample_files")
        cmd = f'{python_exec} tracker.py'
        run_command("Tracker", cmd)
        return

    tracker_ip = input("Enter Tracker IP (Example: 192.168.0.10): ").strip()

    if choice == "2":
        print("\n🚀 Starting PEER A...")
        create_sample_files("PeerA", "sample_files")
        cmd = (
            f'{python_exec} peer.py '
            f'--peer-id PeerA '
            f'--host 0.0.0.0 '
            f'--port {peer_a_port} '
            f'--shared-dir "sample_files" '
            f'--tracker {tracker_ip}:{tracker_port}'
        )
        run_command("PeerA", cmd)
        return

    if choice == "3":
        print("\n🚀 Starting PEER B...")
        create_sample_files("PeerB", "sample_files_b")
        cmd = (
            f'{python_exec} peer.py '
            f'--peer-id PeerB '
            f'--host 0.0.0.0 '
            f'--port {peer_b_port} '
            f'--shared-dir "sample_files_b" '
            f'--tracker {tracker_ip}:{tracker_port}'
        )
        run_command("PeerB", cmd)
        return

    print("❌ Invalid option.")

if __name__ == "__main__":
    main()