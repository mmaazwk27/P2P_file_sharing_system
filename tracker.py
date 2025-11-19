"""
tracker.py
Simple TCP tracker that keeps a mapping: filename -> list of peers.
Protocol: JSON-lines messages terminated by newline.

Messages (from peer to tracker):
- register: { "type":"register", "peer_id": "...", "ip":"...", "port":5001, "files": ["a.txt","b.bin"] }
- lookup:   { "type":"lookup", "filename":"a.txt" }

Tracker responses:
- register_ack: { "type":"register_ack", "status":"ok" }
- lookup_response: { "type":"lookup_response", "owners":[ {"peer_id":"p1","ip":"...","port":...}, ... ] }

This is a minimal example for demo on localhost.
"""

import socket
import threading
import json
from typing import Dict, List

TRACKER_HOST = "0.0.0.0"  # Listen on all interfaces
TRACKER_PORT = 9000

# filename -> list of peer dicts {peer_id, ip, port}
index: Dict[str, List[dict]] = {}
index_lock = threading.Lock()

# Global variable to track if we should log to GUI
gui_log_callback = None

def set_gui_log_callback(callback):
    """Set callback for logging to GUI"""
    global gui_log_callback
    gui_log_callback = callback

def log_message(message):
    """Log message to console and GUI if available"""
    print(f"Tracker: {message}")
    if gui_log_callback:
        gui_log_callback(message)

def handle_client(conn, addr):
    log_message(f"Connection from {addr}")
    sock_file = conn.makefile("rb")
    try:
        while True:
            line = sock_file.readline()
            if not line:
                break
            msg = json.loads(line.decode("utf-8"))
            mtype = msg.get("type")
            if mtype == "register":
                peer_id = msg.get("peer_id")
                ip = msg.get("ip")
                port = int(msg.get("port"))
                files = msg.get("files", [])
                log_message(f"Registering peer '{peer_id}' at {ip}:{port} with files: {files}")
                with index_lock:
                    for fname in files:
                        owners = index.setdefault(fname, [])
                        # avoid duplicates
                        if not any(o["peer_id"] == peer_id and o["port"] == port for o in owners):
                            owners.append({"peer_id": peer_id, "ip": ip, "port": port})
                            log_message(f"Added {fname} -> '{peer_id}'")
                resp = {"type": "register_ack", "status": "ok"}
                conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))
            elif mtype == "lookup":
                filename = msg.get("filename")
                log_message(f"Lookup request for '{filename}' from {addr}")
                with index_lock:
                    owners = index.get(filename, [])
                log_message(f"Found {len(owners)} owners for '{filename}'")
                resp = {"type": "lookup_response", "owners": owners}
                conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))
            elif mtype == "unregister":
                # optional: remove peer entries for provided files
                peer_id = msg.get("peer_id")
                log_message(f"Unregistering peer '{peer_id}'")
                with index_lock:
                    for fname, owners in list(index.items()):
                        index[fname] = [o for o in owners if o["peer_id"] != peer_id]
                        if not index[fname]:
                            del index[fname]
                conn.sendall((json.dumps({"type": "unregister_ack"}) + "\n").encode("utf-8"))
            else:
                conn.sendall((json.dumps({"type":"error","err":"unknown_type"}) + "\n").encode("utf-8"))
    except Exception as e:
        log_message(f"Connection error: {e}")
    finally:
        sock_file.close()
        conn.close()
        log_message(f"Connection closed from {addr}")


def run_tracker(host=TRACKER_HOST, port=TRACKER_PORT):
    log_message(f"Starting tracker on {host}:{port}")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(10)
    try:
        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        log_message("Tracker shutting down...")
    finally:
        server.close()


if __name__ == "__main__":
    run_tracker()