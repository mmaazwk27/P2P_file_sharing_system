#!/bin/bash
# ============================================================
#  P2P File Sharing Demo Launcher (macOS / Linux / Android)
# ============================================================

echo "=========================================================="
echo "   P2P FILE SHARING DEMO - MULTI MACHINE MODE"
echo "=========================================================="
echo

read -p "Enter role (tracker / peerA / peerB): " ROLE

PROJECT_DIR=$(pwd)
PYTHON_EXE=python3
TRACKER_PORT=9000
PEER_A_PORT=5001
PEER_B_PORT=5002

if [ "$ROLE" != "tracker" ]; then
  read -p "Enter Tracker IP (e.g., 192.168.10.12): " TRACKER_IP
fi

# ---- TRACKER MODE ----
if [ "$ROLE" = "tracker" ]; then
  echo "Starting TRACKER server..."
  mkdir -p "$PROJECT_DIR/sample_files"
  echo "This is Peer A sample file" > "$PROJECT_DIR/sample_files/fileA.txt"
  $PYTHON_EXE tracker.py
  exit 0
fi

# ---- PEER A ----
if [ "$ROLE" = "peerA" ] || [ "$ROLE" = "peera" ]; then
  echo "Starting PEER A..."
  mkdir -p "$PROJECT_DIR/sample_files"
  echo "This is Peer A sample file" > "$PROJECT_DIR/sample_files/fileA.txt"
  $PYTHON_EXE peer.py --peer-id PeerA --port $PEER_A_PORT --shared-dir sample_files --tracker $TRACKER_IP:$TRACKER_PORT
  exit 0
fi

# ---- PEER B ----
if [ "$ROLE" = "peerB" ] || [ "$ROLE" = "peerb" ]; then
  echo "Starting PEER B..."
  mkdir -p "$PROJECT_DIR/sample_files_b"
  echo "This is Peer B sample file" > "$PROJECT_DIR/sample_files_b/fileB.txt"
  $PYTHON_EXE peer.py --peer-id PeerB --port $PEER_B_PORT --shared-dir sample_files_b --tracker $TRACKER_IP:$TRACKER_PORT
  exit 0
fi

echo "Invalid role. Use: tracker / peerA / peerB"
