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
    """
    Protocol for peer->peer communication (simple JSON messages followed by raw bytes for file).
    Messages:
    - request_file: {"type":"request_file", "filename":"a.txt", "compress":True}
    - Sender responds with metadata: {"type":"file_meta","filename":"a.txt","compressed":True,"filesize":12345,"hash":"..."}
      followed by raw file bytes of given size.
    - On errors, respond with {"type":"error","msg":"..."}
    """
    sock_file = conn.makefile("rb")
    try:
        req = recv_json(sock_file)
        if req.get("type") != "request_file":
            send_json(conn, {"type": "error", "msg": "expected request_file"})
            return
        filename = req.get("filename")
        compress = req.get("compress", enable_compression)
        src_path = os.path.join(shared_dir, filename)
        if not os.path.exists(src_path):
            send_json(conn, {"type": "error", "msg": "file not found"})
            return

        # If compress requested, create a temp gz file
        if compress:
            tmp_name = src_path + ".gz"
            compress_file_gzip(src_path, tmp_name)
            to_send_path = tmp_name
        else:
            to_send_path = src_path

        filesize = os.path.getsize(to_send_path)
        fhash = calculate_sha256(src_path)  # always hash original file

        meta = {"type": "file_meta", "filename": filename, "compressed": compress, "filesize": filesize, "hash": fhash}
        send_json(conn, meta)
        # now stream raw bytes
        send_file(conn, to_send_path)
        # cleanup tmp if created
        if compress and os.path.exists(tmp_name):
            os.remove(tmp_name)
    except Exception as e:
        try:
            send_json(conn, {"type": "error", "msg": str(e)})
        except Exception:
            pass
        print("Error in peer connection:", e)
    finally:
        try:
            sock_file.close()
        except Exception:
            pass
        conn.close()


def peer_server(listen_host, listen_port, shared_dir, enable_compression=True):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((listen_host, listen_port))
    server.listen(8)
    print(f"Peer server listening on {listen_host}:{listen_port}, sharing: {shared_dir}")
    while True:
        conn, addr = server.accept()
        print(f"Peer connection from {addr}")
        threading.Thread(target=handle_peer_connection, args=(conn, addr, shared_dir, enable_compression), daemon=True).start()


def download_from_peer(peer_info, filename, dest_dir, enable_compression=True, verify_hash=True):
    ip = peer_info["ip"]
    port = int(peer_info["port"])
    peer_id = peer_info["peer_id"]
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(30)  # 30 second timeout for larger files
        s.connect((ip, port))
        # request file
        req = {"type": "request_file", "filename": filename, "compress": enable_compression}
        send_json(s, req)
        f = s.makefile("rb")
        meta = recv_json(f)
        if meta.get("type") == "error":
            print("Peer error:", meta.get("msg"))
            f.close()
            s.close()
            return False
        if meta.get("type") != "file_meta":
            print("Unexpected response", meta)
            f.close()
            s.close()
            return False

        compressed = meta.get("compressed", False)
        filesize = int(meta.get("filesize", 0))
        expected_hash = meta.get("hash")
        
        print(f"📥 Downloading '{filename}' from {peer_id}...")
        print(f"   Size: {filesize} bytes | Compressed: {compressed}")
        
        # prepare paths
        tmp_name = os.path.join(dest_dir, f".tmp_{filename}_{int(time.time())}.dat")
        
        try:
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
            
            print("✅ Download completed!")
            
        except Exception as e:
            print(f"\n❌ Receive error: {e}")
            f.close()
            s.close()
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
            return False

        f.close()
        s.close()

        print("🔍 Verifying file integrity...")
        
        # if compressed, decompress to final
        if compressed:
            final_path = os.path.join(dest_dir, filename)
            decompress_file_gzip(tmp_name, final_path)
            os.remove(tmp_name)
            # compute hash of final file
            if verify_hash:
                computed_hash = calculate_sha256(final_path)
                if computed_hash != expected_hash:
                    print("❌ Hash mismatch after decompression!")
                    print(f"   Expected: {expected_hash}")
                    print(f"   Got: {computed_hash}")
                    return False
                else:
                    print("✅ Hash verification passed!")
        else:
            final_path = os.path.join(dest_dir, filename)
            os.replace(tmp_name, final_path)
            if verify_hash:
                computed_hash = calculate_sha256(final_path)
                if computed_hash != expected_hash:
                    print("❌ Hash mismatch!")
                    print(f"   Expected: {expected_hash}")
                    print(f"   Got: {computed_hash}")
                    return False
                else:
                    print("✅ Hash verification passed!")

        print(f"🎉 Successfully downloaded '{filename}' from {peer_id} -> {final_path}")
        return True
    except Exception as e:
        print(f"❌ Connection error to {peer_id} at {ip}:{port}: {e}")
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
    print(f"Peer Display Name: {peer_id}")
    print(f"Local IP address: {public_ip}")
    print(f"Binding to: {host}:{port}")
    print(f"Shared directory: {shared_dir}")

    # Start server thread
    threading.Thread(target=peer_server, args=(host, port, shared_dir, enable_compression), daemon=True).start()

    # Register with tracker - use the public IP so other peers can connect
    files = list_shared_files(shared_dir)
    print("Registering with tracker:", tracker_host, tracker_port)
    print(f"Files to share: {files}")
    try:
        resp = register_with_tracker(tracker_host, tracker_port, peer_id, public_ip, port, files)
        print("Tracker response:", resp)
    except Exception as e:
        print("Could not register with tracker:", e)

    # Simple CLI loop
    print("\nPeer CLI ready. Commands: list_local | lookup <filename> | download <filename> | exit")
    print("You can add files to the 'shared_directory' folder and they will be available for sharing.")
    while True:
        try:
            cmd = input("peer> ").strip()
        except EOFError:
            break
        if not cmd:
            continue
        parts = cmd.split()
        if parts[0] == "list_local":
            files = list_shared_files(shared_dir)
            if files:
                print("Your shared files:")
                for f in files:
                    print(f" - {f}")
            else:
                print("No files in shared directory. Add files to 'shared_directory' folder.")
        elif parts[0] == "lookup" and len(parts) >= 2:
            filename = " ".join(parts[1:])
            owners = lookup_filename(tracker_host, tracker_port, filename)
            if not owners:
                print("No owners found for", filename)
            else:
                print(f"Owners of '{filename}':")
                for o in owners:
                    print(f" - {o['peer_id']} @ {o['ip']}:{o['port']}")
        elif parts[0] == "download" and len(parts) >= 2:
            filename = " ".join(parts[1:])
            owners = lookup_filename(tracker_host, tracker_port, filename)
            if not owners:
                print("No owners found for", filename)
            else:
                print(f"Found {len(owners)} owner(s) for '{filename}':")
                for i, owner in enumerate(owners):
                    print(f"  {i+1}. {owner['peer_id']} @ {owner['ip']}:{owner['port']}")
                
                # Try each owner until one works
                success = False
                for owner in owners:
                    print(f"\n🔄 Attempting download from {owner['peer_id']}...")
                    if download_from_peer(owner, filename, dest_dir=".", enable_compression=enable_compression, verify_hash=True):
                        success = True
                        break
                    else:
                        print(f"❌ Failed to download from {owner['peer_id']}")
                
                if not success:
                    print("❌ Failed to download from all available owners")
        elif parts[0] == "exit":
            print("Exiting peer.")
            break
        else:
            print("Unknown command. Use: list_local | lookup <filename> | download <filename> | exit")


if __name__ == "__main__":
    main()