# P2P_file_sharing_system


PyP2P is a minimalist, educational P2P (Peer-to-Peer) file-sharing system built using Python's standard library. It demonstrates the fundamentals of distributed systems, socket programming, and data integrity verification.

## 🚀 Features

* **Centralized Indexing:** Uses a Tracker to manage peer registration and file lookup.
* **Socket Communication:** Implements custom TCP-based protocols for metadata exchange and file transfers.
* **Data Integrity:** Employs SHA-256 hashing to verify file consistency post-transfer.
* **Optimization:** Supports optional Gzip compression for efficient bandwidth usage.
* **Security:** Implements directory sanitization to prevent Path Traversal vulnerabilities.
* **Cross-Device Ready:** Built to handle local network IP discovery for peer-to-peer connectivity.

## 🏗️ System Architecture

1. **Tracker (`tracker.py`):** Acts as the central directory. Peers register their shared files here, and other peers query this server to find available file owners.
2. **Peer (`peer.py`):** Acts as both a client and a server. It hosts local files for others to download and provides a CLI for users to search and download from other peers.

## 🛠️ Getting Started

### Prerequisites
* Python 3.x (No external dependencies required).

### Running the Demo
1. Clone the repository.
2. Run the demo launcher:
   ```bash
   python run_demo.py
3. Follow the on-screen prompts to start either the Tracker or a Peer.

## 🛡️ Security Disclaimer
This project is for educational purposes only. It lacks enterprise-grade encryption and authentication. Please ensure that the shared_directory does not contain sensitive personal data.

## 📄 License
This project is licensed under the Apache License 2.0. See the LICENSE file for details.
