import os
import sys
import subprocess
import platform

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def create_sample_files(peer_name, folder_name):
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    filename = os.path.join(folder_name, f"{peer_name}_sample.txt")
    if not os.path.exists(filename):
        with open(filename, "w") as f:
            f.write(f"This is a sample file from {peer_name}\n")
    print(f"Created sample folder: {folder_name}")

def run_command(title, command):
    system_name = platform.system().lower()
    if "windows" in system_name:
        # open in a new CMD window
        subprocess.Popen(["start", "cmd", "/k", command], shell=True)
    else:
        # run in same terminal
        subprocess.Popen(command, shell=True)
    print(f"Launched: {command}")

def main():
    clear_screen()
    print("=" * 60)
    print("      P2P FILE SHARING DEMO LAUNCHER")
    print("=" * 60)
    print("\nChoose your role:")
    print(" 1) Tracker")
    print(" 2) Peer A")
    print(" 3) Peer B")
    print()

    role_input = input("Enter 1 / 2 / 3: ").strip()
    if role_input == "1":
        role = "tracker"
    elif role_input == "2":
        role = "peerA"
    elif role_input == "3":
        role = "peerB"
    else:
        print("Invalid choice.")
        return

    python_exec = sys.executable or "python"
    tracker_port = 9000
    peer_a_port = 5001
    peer_b_port = 5002

    # Ask for tracker IP if peer role
    tracker_ip = None
    if role != "tracker":
        tracker_ip = input("Enter Tracker IP (e.g., 192.168.10.12): ").strip()

    # Run according to role
    if role == "tracker":
        print("\nStarting Tracker...")
        create_sample_files("PeerA", "sample_files")
        cmd = f'{python_exec} tracker.py'
        run_command("Tracker", cmd)

    elif role.lower() == "peera":
        print("\n Starting Peer A...")
        create_sample_files("PeerA", "sample_files")
        cmd = f'{python_exec} peer.py --peer-id PeerA --port {peer_a_port} --shared-dir sample_files --tracker {tracker_ip}:{tracker_port}'
        run_command("Peer A", cmd)

    elif role.lower() == "peerb":
        print("\n Starting Peer B...")
        create_sample_files("PeerB", "sample_files_b")
        cmd = f'{python_exec} peer.py --peer-id PeerB --port {peer_b_port} --shared-dir sample_files_b --tracker {tracker_ip}:{tracker_port}'
        run_command("Peer B", cmd)

    print("\n All components launched (where applicable).")
    print("  If you're running on multiple machines, ensure they share the same Wi-Fi.")
    print("  To stop, close the opened windows or press Ctrl+C.\n")

if __name__ == "__main__":
    main()
