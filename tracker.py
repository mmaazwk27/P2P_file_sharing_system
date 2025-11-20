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


def handle_client(conn, addr):
    print(f"🔗 TRACKER: New connection from {addr}")
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
                print(f"📝 REGISTER: Peer '{peer_id}' at {ip}:{port} with files: {files}")
                
                with index_lock:
                    for fname in files:
                        owners = index.setdefault(fname, [])
                        # avoid duplicates
                        if not any(o["peer_id"] == peer_id and o["port"] == port for o in owners):
                            owners.append({"peer_id": peer_id, "ip": ip, "port": port})
                            print(f"✅ INDEX: Added {fname} -> '{peer_id}'")
                
                resp = {"type": "register_ack", "status": "ok"}
                conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))
                print(f"✅ REGISTER: Acknowledgment sent to {peer_id}")
                
            elif mtype == "lookup":
                filename = msg.get("filename")
                print(f"🔍 LOOKUP: Request for '{filename}' from {addr}")
                
                with index_lock:
                    owners = index.get(filename, [])
                
                print(f"✅ LOOKUP: Found {len(owners)} owners for '{filename}'")
                resp = {"type": "lookup_response", "owners": owners}
                conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))
                print(f"✅ LOOKUP: Response sent with {len(owners)} owners")
                
            elif mtype == "unregister":
                # optional: remove peer entries for provided files
                peer_id = msg.get("peer_id")
                print(f"🗑️ UNREGISTER: Removing peer '{peer_id}'")
                
                with index_lock:
                    files_removed = []
                    for fname, owners in list(index.items()):
                        original_count = len(owners)
                        index[fname] = [o for o in owners if o["peer_id"] != peer_id]
                        if len(index[fname]) < original_count:
                            files_removed.append(fname)
                        if not index[fname]:
                            del index[fname]
                            
                print(f"✅ UNREGISTER: Removed peer '{peer_id}' from {len(files_removed)} files")
                conn.sendall((json.dumps({"type": "unregister_ack"}) + "\n").encode("utf-8"))
                
            else:
                print(f"❌ UNKNOWN: Unknown message type '{mtype}' from {addr}")
                conn.sendall((json.dumps({"type":"error","err":"unknown_type"}) + "\n").encode("utf-8"))
                
    except Exception as e:
        print(f"❌ TRACKER ERROR: Connection error from {addr}: {e}")
    finally:
        sock_file.close()
        conn.close()
        print(f"🔌 TRACKER: Connection closed from {addr}")


def run_tracker(host=TRACKER_HOST, port=TRACKER_PORT):
    print(f"🚀 TRACKER: Starting on {host}:{port}")
    print("📊 TRACKER: Ready to accept peer connections...")
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(10)
    
    try:
        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("\n🛑 TRACKER: Shutting down...")
    finally:
        server.close()


if __name__ == "__main__":
    run_tracker()