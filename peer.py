"""
peer.py
Peer program. Usage:
    python peer.py --peer-id "Display Name" --port 5001 --shared-dir ./shared_directory --tracker 127.0.0.1:9000

Features:
- Register with tracker upon start
- Start a server thread to serve file requests
- Offer a simple interactive CLI to lookup and download files
- Supports compression and SHA-256 integrity check
"""

import socket
import threading
import argparse
import os
import json
import time
import uuid
import random
from utils import (
    calculate_sha256,
    compress_file_gzip,
    decompress_file_gzip,
    send_json,
    recv_json,
    send_file,
    recv_file,
    CHUNK_SIZE,
    show_download_progress,
)

TRACKER_DEFAULT = "127.0.0.1:9000"


def register_with_tracker(tracker_host, tracker_port, peer_id, peer_ip, peer_port, files):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((tracker_host, tracker_port))
    payload = {"type": "register", "peer_id": peer_id, "ip": peer_ip, "port": peer_port, "files": files}
    send_json(s, payload)
    # read ack
    f = s.makefile("rb")
    resp = recv_json(f)
    f.close()
    s.close()
    return resp


def lookup_filename(tracker_host, tracker_port, filename):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((tracker_host, tracker_port))
    payload = {"type": "lookup", "filename": filename}
    send_json(s, payload)
    f = s.makefile("rb")
    resp = recv_json(f)
    f.close()
    s.close()
    return resp.get("owners", [])


def handle_peer_connection(conn, addr, shared_dir, enable_compression=True):
    def log_message(message):
        print(f"[Server to {addr[0]}:{addr[1]}] {message}")
    
    # 1. Sanitize the path to prevent Directory Traversal
    shared_dir_abs = os.path.abspath(shared_dir)
    sock_file = conn.makefile("rb")
    
    try:
        req = recv_json(sock_file)
        if req.get("type") != "request_file":
            send_json(conn, {"type": "error", "msg": "expected request_file"})
            return
        
        filename = req.get("filename")
        # Ensure the filename is treated as a filename, not a path
        safe_filename = os.path.basename(filename) 
        src_path = os.path.abspath(os.path.join(shared_dir_abs, safe_filename))

        # Check if the resolved path is still within the shared_dir
        if not src_path.startswith(shared_dir_abs):
            log_message(f"❌ SECURITY ALERT: Attempted path traversal: {filename}")
            send_json(conn, {"type": "error", "msg": "Access denied"})
            return

        # 2. Validate file existence and type
        if not os.path.exists(src_path) or not os.path.isfile(src_path):
            log_message(f"❌ ERROR: File '{safe_filename}' not found or invalid")
            send_json(conn, {"type": "error", "msg": "file not found"})
            return

        compress = req.get("compress", enable_compression)
        
        # 3. Robust Temp File Handling
        tmp_name = src_path + ".gz" if compress else None
        
        try:
            if compress:
                log_message(f"🗜️ COMPRESSION: Starting compression...")
                compress_file_gzip(src_path, tmp_name, log_callback=log_message)
                to_send_path = tmp_name
            else:
                to_send_path = src_path
                log_message("⚡ SKIPPING: Sending original file")

            filesize = os.path.getsize(to_send_path)
            fhash = calculate_sha256(src_path, log_callback=log_message)

            meta = {"type": "file_meta", "filename": safe_filename, "compressed": compress, "filesize": filesize, "hash": fhash}
            send_json(conn, meta)
            
            log_message("🚀 TRANSFER: Starting file data transfer...")
            send_file(conn, to_send_path, log_callback=log_message)
            log_message("✅ SUCCESS: File transfer completed")

        finally:
            # Always ensure temporary file is removed if it was created
            if tmp_name and os.path.exists(tmp_name):
                os.remove(tmp_name)
                log_message("🧹 CLEANUP: Temporary file removed")
            
    except Exception as e:
        log_message(f"❌ ERROR in peer connection: {e}")
        try:
            send_json(conn, {"type": "error", "msg": str(e)})
        except:
            pass
    finally:
        sock_file.close()
        conn.close()

def peer_server(listen_host, listen_port, shared_dir, enable_compression=True):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((listen_host, listen_port))
    server.listen(8)
    print(f"🎯 Peer server listening on {listen_host}:{listen_port}, sharing: {shared_dir}")
    print(f"⚙️ Compression enabled: {enable_compression}")
    while True:
        conn, addr = server.accept()
        print(f"🔗 New peer connection from {addr}")
        threading.Thread(target=handle_peer_connection, args=(conn, addr, shared_dir, enable_compression), daemon=True).start()


def download_from_peer(peer_info, filename, dest_dir, enable_compression=True, verify_hash=True):
    ip = peer_info["ip"]
    port = int(peer_info["port"])
    peer_id = peer_info["peer_id"]
    
    def log_message(message):
        print(f"[Download from {peer_id}] {message}")
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(30)  # 30 second timeout for larger files
        log_message(f"🔗 CONNECTING: Connecting to {ip}:{port}")
        s.connect((ip, port))
        
        # request file
        req = {"type": "request_file", "filename": filename, "compress": enable_compression}
        log_message(f"📨 REQUEST: Requesting file '{filename}' with compression: {enable_compression}")
        send_json(s, req)
        
        f = s.makefile("rb")
        meta = recv_json(f)
        
        if meta.get("type") == "error":
            error_msg = meta.get("msg")
            log_message(f"❌ PEER ERROR: {error_msg}")
            f.close()
            s.close()
            return False
            
        if meta.get("type") != "file_meta":
            log_message(f"❌ UNEXPECTED RESPONSE: {meta}")
            f.close()
            s.close()
            return False

        compressed = meta.get("compressed", False)
        filesize = int(meta.get("filesize", 0))
        expected_hash = meta.get("hash")
        
        log_message(f"📊 METADATA RECEIVED:")
        log_message(f"   - Filename: {filename}")
        log_message(f"   - Compressed: {compressed}")
        log_message(f"   - Size: {filesize} bytes")
        log_message(f"   - Expected Hash: {expected_hash[:16]}...")
        
        # prepare paths
        tmp_name = os.path.join(dest_dir, f".tmp_{filename}_{int(time.time())}.dat")
        
        try:
            log_message("📥 DOWNLOAD: Starting file download...")
            # Download with progress bar
            remaining = filesize
            received = 0
            
            with open(tmp_name, "wb") as file_obj:
                while remaining > 0:
                    chunk_size = min(CHUNK_SIZE, remaining)
                    chunk = f.read(chunk_size)
                    if not chunk:
                        raise ConnectionError("Connection closed before all bytes received")
                    
                    file_obj.write(chunk)
                    received += len(chunk)
                    remaining -= len(chunk)
                    
                    # Show progress bar
                    show_download_progress(received, filesize)
            
            log_message("✅ DOWNLOAD: File download completed!")
            
        except Exception as e:
            log_message(f"❌ DOWNLOAD ERROR: {e}")
            f.close()
            s.close()
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
            return False

        f.close()
        s.close()

        if verify_hash:
            log_message("🔍 VERIFYING: Starting file integrity verification...")
            
            # if compressed, decompress to final
            if compressed:
                log_message("📤 DECOMPRESSION: Starting file decompression...")
                final_path = os.path.join(dest_dir, filename)
                decompress_file_gzip(tmp_name, final_path, log_callback=log_message)
                os.remove(tmp_name)
                
                # compute hash of final file
                log_message("🔍 HASHING: Calculating hash of decompressed file...")
                computed_hash = calculate_sha256(final_path, log_callback=log_message)
                
                if computed_hash != expected_hash:
                    log_message("❌ HASH MISMATCH: File integrity check failed!")
                    log_message(f"   Expected: {expected_hash}")
                    log_message(f"   Got: {computed_hash}")
                    return False
                else:
                    log_message("✅ HASH VERIFICATION: File integrity verified successfully!")
            else:
                final_path = os.path.join(dest_dir, filename)
                os.replace(tmp_name, final_path)
                
                log_message("🔍 HASHING: Calculating hash of received file...")
                computed_hash = calculate_sha256(final_path, log_callback=log_message)
                
                if computed_hash != expected_hash:
                    log_message("❌ HASH MISMATCH: File integrity check failed!")
                    log_message(f"   Expected: {expected_hash}")
                    log_message(f"   Got: {computed_hash}")
                    return False
                else:
                    log_message("✅ HASH VERIFICATION: File integrity verified successfully!")
        else:
            log_message("⚠️ SKIPPING: Hash verification disabled")
            if compressed:
                final_path = os.path.join(dest_dir, filename)
                decompress_file_gzip(tmp_name, final_path, log_callback=log_message)
                os.remove(tmp_name)
            else:
                final_path = os.path.join(dest_dir, filename)
                os.replace(tmp_name, final_path)

        log_message(f"🎉 SUCCESS: File '{filename}' successfully downloaded -> {final_path}")
        return True
        
    except Exception as e:
        log_message(f"❌ CONNECTION ERROR: {e}")
        s.close()
        return False


def list_shared_files(shared_dir):
    return [f for f in os.listdir(shared_dir) if os.path.isfile(os.path.join(shared_dir, f))]


def get_local_ip():
    """Get the local IP address that can be used by other devices"""
    try:
        # Connect to a public IP to determine our local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--peer-id", required=True, help="Display name for this peer")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (use 0.0.0.0 for cross-device)")
    parser.add_argument("--port", type=int, default=5001)
    parser.add_argument("--tracker", default=TRACKER_DEFAULT, help="tracker_host:port")
    parser.add_argument("--shared-dir", default="shared_directory")
    parser.add_argument("--no-compress", action="store_true", help="disable compression")
    args = parser.parse_args()

    peer_id = args.peer_id
    host = args.host
    port = args.port
    shared_dir = args.shared_dir
    enable_compression = not args.no_compress

    if not os.path.exists(shared_dir):
        os.makedirs(shared_dir, exist_ok=True)

    tracker_host, tracker_port = args.tracker.split(":")
    tracker_port = int(tracker_port)

    # Get the actual IP address that other devices can use to connect to this peer
    public_ip = get_local_ip()
    print(f"🔧 PEER CONFIGURATION:")
    print(f"   Display Name: {peer_id}")
    print(f"   Local IP: {public_ip}")
    print(f"   Binding: {host}:{port}")
    print(f"   Shared Directory: {shared_dir}")
    print(f"   Compression: {'ENABLED' if enable_compression else 'DISABLED'}")

    # Start server thread
    threading.Thread(target=peer_server, args=(host, port, shared_dir, enable_compression), daemon=True).start()

    # Register with tracker - use the public IP so other peers can connect
    files = list_shared_files(shared_dir)
    print(f"📋 FILES TO SHARE: {files}")
    print(f"🔗 REGISTERING: Connecting to tracker at {tracker_host}:{tracker_port}")
    try:
        resp = register_with_tracker(tracker_host, tracker_port, peer_id, public_ip, port, files)
        print(f"✅ REGISTRATION: Tracker response: {resp}")
    except Exception as e:
        print(f"❌ REGISTRATION ERROR: Could not register with tracker: {e}")

    # Simple CLI loop
    print("\n🎯 PEER CLI READY")
    print("Commands: list_local | lookup <filename> | download <filename> | exit")
    print("You can add files to the 'shared_directory' folder and they will be available for sharing.")
    
    while True:
        try:
            cmd = input("\npeer> ").strip()
        except EOFError:
            break
        if not cmd:
            continue
        parts = cmd.split()
        if parts[0] == "list_local":
            files = list_shared_files(shared_dir)
            if files:
                print("📁 YOUR SHARED FILES:")
                for f in files:
                    file_path = os.path.join(shared_dir, f)
                    file_size = os.path.getsize(file_path)
                    print(f"   - {f} ({file_size} bytes)")
            else:
                print("📁 No files in shared directory. Add files to 'shared_directory' folder.")
        elif parts[0] == "lookup" and len(parts) >= 2:
            filename = " ".join(parts[1:])
            print(f"🔍 LOOKUP: Searching for '{filename}'...")
            owners = lookup_filename(tracker_host, tracker_port, filename)
            if not owners:
                print(f"❌ LOOKUP: No owners found for '{filename}'")
            else:
                print(f"✅ LOOKUP: Found {len(owners)} owner(s) for '{filename}':")
                for o in owners:
                    print(f"   - {o['peer_id']} @ {o['ip']}:{o['port']}")
        elif parts[0] == "download" and len(parts) >= 2:
            filename = " ".join(parts[1:])
            print(f"📥 DOWNLOAD: Looking up '{filename}'...")
            owners = lookup_filename(tracker_host, tracker_port, filename)
            if not owners:
                print(f"❌ DOWNLOAD: No owners found for '{filename}'")
            else:
                print(f"✅ DOWNLOAD: Found {len(owners)} owner(s) for '{filename}':")
                for i, owner in enumerate(owners):
                    print(f"   {i+1}. {owner['peer_id']} @ {owner['ip']}:{owner['port']}")
                
                # Try each owner until one works
                success = False
                for owner in owners:
                    print(f"\n🔄 ATTEMPTING: Download from {owner['peer_id']}...")
                    if download_from_peer(owner, filename, dest_dir=".", enable_compression=enable_compression, verify_hash=True):
                        success = True
                        break
                    else:
                        print(f"❌ FAILED: Download from {owner['peer_id']}")
                
                if not success:
                    print("❌ DOWNLOAD: Failed to download from all available owners")
        elif parts[0] == "exit":
            print("👋 Exiting peer. Goodbye!")
            break
        else:
            print("❌ UNKNOWN COMMAND: Use: list_local | lookup <filename> | download <filename> | exit")


if __name__ == "__main__":
    main()