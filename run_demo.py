import os
import sys
import subprocess
import platform
import socket
import tempfile
import time
import tkinter as tk
from tkinter import simpledialog, messagebox

def clear_screen():
    """Clear terminal screen cross-platform"""
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

def create_macos_launch_script(title, command):
    """Create a temporary shell script for macOS terminal launch"""
    try:
        # Create a temporary shell script
        script_content = f'''#!/bin/bash
# P2P File Sharing - {title}
echo "Starting {title}..."
echo "Command: {command}"
echo "----------------------------------------"
cd "{os.getcwd()}"
{command}
echo ""
echo "----------------------------------------"
echo "Process completed. This window will close in 10 seconds..."
sleep 10
'''
        
        # Create temporary file
        fd, script_path = tempfile.mkstemp(suffix='.sh', prefix=f'p2p_{title.replace(" ", "_")}_')
        with os.fdopen(fd, 'w') as f:
            f.write(script_content)
        
        # Make executable
        os.chmod(script_path, 0o755)
        return script_path
        
    except Exception as e:
        print(f"❌ Failed to create launch script: {e}")
        return None

def run_command(title, command):
    """Cross-platform command execution with robust error handling"""
    system_name = platform.system().lower()
    
    print(f"🚀 Launching: {title}")
    print(f"💻 Command: {command}")
    
    try:
        if "windows" in system_name:
            # Windows - use start cmd /k (existing working method)
            safe_cmd = f'start "{title}" cmd /k "{command}"'
            process = subprocess.Popen(safe_cmd, shell=True)
            print("✅ Windows terminal launched successfully!")
            return True
            
        elif "darwin" in system_name:  # macOS
            # macOS - multiple methods with fallbacks
            
            # Method 1: Try using open -a Terminal with script (most reliable)
            script_path = create_macos_launch_script(title, command)
            if script_path:
                try:
                    # Try to open in Terminal app
                    terminal_cmd = ['open', '-a', 'Terminal', script_path]
                    process = subprocess.Popen(terminal_cmd, 
                                             stdout=subprocess.PIPE, 
                                             stderr=subprocess.PIPE)
                    time.sleep(2)  # Give it a moment to launch
                    
                    # Check if process started successfully
                    if process.poll() is None:
                        print("✅ macOS Terminal launched successfully!")
                        return True
                    else:
                        stdout, stderr = process.communicate()
                        if stderr:
                            print(f"⚠️  Terminal launch warning: {stderr.decode()}")
                        # Continue to fallback methods
                except Exception as e:
                    print(f"⚠️  Terminal app method failed: {e}")
            
            # Method 2: Try using osascript (AppleScript)
            try:
                # Escape quotes for AppleScript
                escaped_command = command.replace('"', '\\"')
                apple_script = f'''
                tell application "Terminal"
                    activate
                    do script "cd \\"{os.getcwd()}\\" && {escaped_command} && echo \\"\\\\nProcess completed. Press Ctrl+C to exit or close window.\\" && sleep 30"
                end tell
                '''
                
                process = subprocess.Popen(['osascript', '-e', apple_script],
                                         stdout=subprocess.PIPE, 
                                         stderr=subprocess.PIPE)
                time.sleep(2)
                
                if process.poll() is None:
                    print("✅ macOS Terminal launched via AppleScript!")
                    return True
                else:
                    stdout, stderr = process.communicate()
                    if stderr:
                        print(f"⚠️  AppleScript method warning: {stderr.decode()}")
            except Exception as e:
                print(f"⚠️  AppleScript method failed: {e}")
            
            # Method 3: Try using xterm (if available)
            try:
                xterm_cmd = ['xterm', '-title', title, '-e', f'bash -c "{command}; echo \\"\\nPress Enter to close...\\"; read"']
                process = subprocess.Popen(xterm_cmd,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
                time.sleep(1)
                
                if process.poll() is None:
                    print("✅ Launched using xterm!")
                    return True
            except Exception as e:
                print(f"⚠️  xterm method failed: {e}")
            
            # Final fallback: Manual instructions
            print("\n❌ Could not automatically open a new terminal window.")
            print("📝 Please manually open Terminal and run this command:")
            print(f"   cd \"{os.getcwd()}\"")
            print(f"   {command}")
            return False
            
        else:  # Linux and other Unix-like systems
            # Try common Linux terminals
            terminals = [
                ['gnome-terminal', '--title', title, '--', 'bash', '-c', f'{command}; echo ""; echo "Press Enter to close..."; read'],
                ['konsole', '--title', title, '-e', 'bash', '-c', f'{command}; echo ""; echo "Press Enter to close..."; read'],
                ['xterm', '-title', title, '-e', 'bash', '-c', f'{command}; echo ""; echo "Press Enter to close..."; read'],
            ]
            
            for terminal_cmd in terminals:
                try:
                    process = subprocess.Popen(terminal_cmd,
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)
                    time.sleep(1)
                    
                    if process.poll() is None:
                        print(f"✅ Launched using {terminal_cmd[0]}!")
                        return True
                except Exception as e:
                    continue
            
            # Fallback for Linux
            print("\n❌ Could not automatically open a new terminal window.")
            print("📝 Please manually open a terminal and run this command:")
            print(f"   {command}")
            return False
            
    except Exception as e:
        print(f"❌ Unexpected error launching terminal: {e}")
        print(f"📝 Please manually run: {command}")
        return False
    
    return True

def run_tracker_gui():
    """Run tracker with GUI"""
    python_exec = f'"{sys.executable}"'
    cmd = f'{python_exec} tracker_gui.py'
    return run_command("Tracker GUI", cmd)

def run_peer_gui():
    """Run peer with GUI - get parameters via dialog"""
    # Check if we can use GUI for input
    try:
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        
        # Get peer display name
        display_name = simpledialog.askstring("Peer Setup", "Enter your display name:", 
                                             initialvalue=f"Peer_{os.getpid()}")
        if not display_name:
            print("❌ Display name is required!")
            return False
            
        # Get tracker IP
        tracker_ip = simpledialog.askstring("Peer Setup", "Enter Tracker IP:", 
                                           initialvalue="127.0.0.1")
        if not tracker_ip:
            print("❌ Tracker IP is required!")
            return False
        
        root.destroy()
        
    except Exception as e:
        print("⚠️  GUI input not available, using command line input...")
        display_name = input("Enter your display name (e.g., John's Laptop): ").strip()
        if not display_name:
            display_name = f"Peer_{os.getpid()}"
        
        tracker_ip = input("Enter Tracker IP [127.0.0.1]: ").strip()
        if not tracker_ip:
            tracker_ip = "127.0.0.1"
    
    # Create shared directory
    shared_dir = create_shared_directory()
    
    # Run peer GUI
    python_exec = f'"{sys.executable}"'
    cmd = f'{python_exec} peer_gui.py --peer-id "{display_name}" --tracker {tracker_ip}:9000 --shared-dir "{shared_dir}"'
    return run_command(f"Peer - {display_name}", cmd)

def run_tracker_cli():
    """Run tracker in CLI mode"""
    python_exec = f'"{sys.executable}"'
    cmd = f'{python_exec} tracker.py'
    return run_command("Tracker CLI", cmd)

def run_peer_cli():
    """Run peer in CLI mode"""
    try:
        display_name = input("Enter your display name (e.g., John's Laptop): ").strip()
        if not display_name:
            display_name = f"Peer_{os.getpid()}"
        
        tracker_ip = input("Enter Tracker IP: ").strip()
        if not tracker_ip:
            print("❌ Tracker IP is required!")
            return False
    except KeyboardInterrupt:
        print("\n❌ Input cancelled.")
        return False
    
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
    
    return run_command(f"Peer CLI - {display_name}", cmd)

def check_python_installation():
    """Check if Python is properly installed and accessible"""
    try:
        result = subprocess.run([sys.executable, '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return True
        else:
            print(f"⚠️  Python check returned: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Python check failed: {e}")
        return False

def main():
    clear_screen()
    print("="*70)
    print("        P2P FILE SHARING SYSTEM - CROSS-PLATFORM LAUNCHER")
    print("="*70)
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Python: {sys.version.split()[0]}")
    print()
    
    # Check Python installation
    if not check_python_installation():
        print("❌ Python installation issue detected!")
        print("💡 Please ensure Python is properly installed and in PATH")
        input("Press Enter to continue anyway...")
    
    print("Available Options:")
    print("1) Tracker (GUI) - Visual interface for tracker")
    print("2) Peer (GUI)    - Visual interface for peer") 
    print("3) Tracker (CLI) - Command line interface for tracker")
    print("4) Peer (CLI)    - Command line interface for peer")
    print("5) Exit")
    print()
    
    # Show local IP for convenience
    local_ip = get_local_ip()
    print(f"🌐 Your local IP address: {local_ip}")
    print("   Share this IP with other devices for tracker connection")
    print()

    try:
        choice = input("Enter 1-5: ").strip()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        return

    success = False
    
    if choice == "1":
        print("\n🚀 Starting TRACKER (GUI)...")
        create_shared_directory()
        success = run_tracker_gui()
        
    elif choice == "2":
        print("\n🚀 Starting PEER (GUI)...")
        success = run_peer_gui()
        
    elif choice == "3":
        print("\n🚀 Starting TRACKER (CLI)...")
        create_shared_directory()
        success = run_tracker_cli()
        
    elif choice == "4":
        print("\n🚀 Starting PEER (CLI)...")
        success = run_peer_cli()
        
    elif choice == "5":
        print("👋 Goodbye!")
        return
        
    else:
        print("❌ Invalid option.")
        return

    # Platform-specific final messages
    system_name = platform.system().lower()
    
    if success:
        print("\n✅ Launch successful!")
        if "darwin" in system_name:
            print("💡 On macOS: The new Terminal window should appear shortly.")
            print("   If it doesn't appear, check your Dock for Terminal app.")
        elif "windows" in system_name:
            print("💡 On Windows: New command prompt window should be open.")
        else:
            print("💡 Terminal window should be launched.")
    else:
        print("\n⚠️  Some issues occurred during launch.")
        print("💡 Please follow the manual instructions above.")
    
    print("\n📋 General Instructions:")
    print("   - To stop any component, close its window or press Ctrl+C")
    print("   - For multi-device testing, ensure all devices are on same network")
    print("   - Firewall may block connections - allow Python if prompted")
    
    if "darwin" in system_name:
        print("\n🍎 macOS Specific Notes:")
        print("   - If Terminal doesn't open, check System Preferences > Security & Privacy")
        print("   - Ensure Terminal has permission to run shell scripts")
        print("   - You may need to manually allow the app in Accessibility settings")
    
    print("\nPress Enter to close this launcher...")
    try:
        input()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("💡 Please ensure all dependencies are installed and try again.")
        input("Press Enter to exit...")