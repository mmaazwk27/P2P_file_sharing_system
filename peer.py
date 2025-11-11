"""
peer.py
Peer program. Usage:
    python peer.py --peer-id p1 --port 5001 --shared-dir ./sample_files --tracker 127.0.0.1:9000

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
from utils import (
    calculate_sha256,
    compress_file_gzip,
    decompress_file_gzip,
    send_json,
    recv_json,
    send_file,
    recv_file,
    CHUNK_SIZE,
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
        # fhash = calculate_sha256(src_path) if not compress else calculate_sha256(to_send_path)
        
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
    server.bind((listen_host, listen_port))
    server.listen(8)
    print(f"Peer server listening on {listen_host}:{listen_port}, sharing: {shared_dir}")
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_peer_connection, args=(conn, addr, shared_dir, enable_compression), daemon=True).start()


def download_from_peer(peer_info, filename, dest_dir, enable_compression=True, verify_hash=True):
    ip = peer_info["ip"]
    port = int(peer_info["port"])
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
    # prepare paths
    tmp_name = os.path.join(dest_dir, f".tmp_{filename}_{int(time.time())}.dat")
    try:
        recv_file(f, tmp_name, expected_size=filesize)
    except Exception as e:
        print("Receive error:", e)
        f.close()
        s.close()
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
        return False

    f.close()
    s.close()

    # if compressed, decompress to final
    if compressed:
        final_path = os.path.join(dest_dir, filename)
        decompress_file_gzip(tmp_name, final_path)
        os.remove(tmp_name)
        # compute hash of final file
        if verify_hash:
            computed_hash = calculate_sha256(final_path)
            # note: sender sent hash either of compressed file or original depending; we used compressed hash in protocol when compress True.
            if computed_hash != expected_hash:
                print("Hash mismatch after decompression!")
                return False
    else:
        final_path = os.path.join(dest_dir, filename)
        os.replace(tmp_name, final_path)
        if verify_hash:
            computed_hash = calculate_sha256(final_path)
            if computed_hash != expected_hash:
                print("Hash mismatch!")
                return False

    print(f"Downloaded {filename} -> {final_path} (OK)")
    return True


def list_shared_files(shared_dir):
    return [f for f in os.listdir(shared_dir) if os.path.isfile(os.path.join(shared_dir, f))]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--peer-id", default=str(uuid.uuid4())[:8])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5001)
    parser.add_argument("--tracker", default=TRACKER_DEFAULT, help="tracker_host:port")
    parser.add_argument("--shared-dir", default="sample_files")
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

    # Start server thread
    threading.Thread(target=peer_server, args=(host, port, shared_dir, enable_compression), daemon=True).start()

    # Register with tracker
    files = list_shared_files(shared_dir)
    print("Registering with tracker:", tracker_host, tracker_port)
    try:
        resp = register_with_tracker(tracker_host, tracker_port, peer_id, host, port, files)
        print("Tracker response:", resp)
    except Exception as e:
        print("Could not register with tracker:", e)

    # Simple CLI loop
    print("Peer CLI ready. Commands: list_local | lookup <filename> | download <filename> | exit")
    while True:
        try:
            cmd = input("peer> ").strip()
        except EOFError:
            break
        if not cmd:
            continue
        parts = cmd.split()
        if parts[0] == "list_local":
            for f in list_shared_files(shared_dir):
                print("-", f)
        elif parts[0] == "lookup" and len(parts) >= 2:
            filename = " ".join(parts[1:])
            owners = lookup_filename(tracker_host, tracker_port, filename)
            if not owners:
                print("No owners found for", filename)
            else:
                print("Owners:")
                for o in owners:
                    print(f" - {o['peer_id']} @ {o['ip']}:{o['port']}")
        elif parts[0] == "download" and len(parts) >= 2:
            filename = " ".join(parts[1:])
            owners = lookup_filename(tracker_host, tracker_port, filename)
            if not owners:
                print("No owners found for", filename)
            else:
                # pick first owner for simplicity
                owner = owners[0]
                download_from_peer(owner, filename, dest_dir=".", enable_compression=enable_compression, verify_hash=True)
        elif parts[0] == "exit":
            print("Exiting peer.")
            break
        else:
            print("Unknown command. Use: list_local | lookup <filename> | download <filename> | exit")


if __name__ == "__main__":
    main()
