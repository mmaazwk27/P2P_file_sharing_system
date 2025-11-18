"""
utils.py
Shared helpers: hashing, compression, file send/receive helpers.
Uses standard library only.
"""

import hashlib
import gzip
import shutil
import os
import json
import socket
from typing import Tuple

CHUNK_SIZE = 64 * 1024  # 64KB


def calculate_sha256(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()


def compress_file_gzip(src_path: str, dst_path: str) -> None:
    """Compress src_path into dst_path (gzip)."""
    with open(src_path, "rb") as f_in, gzip.open(dst_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)


def decompress_file_gzip(src_path: str, dst_path: str) -> None:
    """Decompress gzip file."""
    with gzip.open(src_path, "rb") as f_in, open(dst_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)


def send_json(sock: socket.socket, obj: dict) -> None:
    """Send a JSON object terminated by newline. Uses socket sendall."""
    raw = json.dumps(obj, separators=(",", ":")).encode("utf-8") + b"\n"
    sock.sendall(raw)


def recv_json(sock_file) -> dict:
    """
    Receive a JSON object from a socket file-like (makefile('rb')).
    Reads one line and parses JSON.
    """
    line = sock_file.readline()
    if not line:
        raise ConnectionError("No data received while expecting JSON")
    return json.loads(line.decode("utf-8"))


def send_file(sock: socket.socket, file_path: str) -> None:
    """Send a file in chunks. Assumes receiver expects raw bytes after metadata."""
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            sock.sendall(chunk)


def recv_file(sock_file, dest_path: str, expected_size: int = None) -> None:
    """
    Receive raw bytes from socket file-like and write to dest_path.
    If expected_size is provided it tries to read exactly that many bytes.
    """
    remaining = expected_size
    with open(dest_path, "wb") as f:
        if remaining is None:
            # Read until socket closes (not used typically)
            while True:
                chunk = sock_file.read(CHUNK_SIZE)
                if not chunk:
                    break
                f.write(chunk)
        else:
            # Read exact number of bytes
            while remaining > 0:
                chunk = sock_file.read(min(CHUNK_SIZE, remaining))
                if not chunk:
                    raise ConnectionError("Connection closed before all bytes received")
                f.write(chunk)
                remaining -= len(chunk)