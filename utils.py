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
import sys
from typing import Tuple

CHUNK_SIZE = 64 * 1024  # 64KB


def calculate_sha256(file_path: str, log_callback=None) -> str:
    """Calculate SHA-256 hash of file with logging"""
    if log_callback:
        log_callback(f"🔍 HASHING: Calculating SHA-256 for {os.path.basename(file_path)}")
    
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    
    hash_result = h.hexdigest()
    
    if log_callback:
        log_callback(f"✅ HASHING: SHA-256 calculated: {hash_result[:16]}...")
    
    return hash_result


def compress_file_gzip(src_path: str, dst_path: str, log_callback=None) -> None:
    """Compress src_path into dst_path (gzip) with logging"""
    if log_callback:
        original_size = os.path.getsize(src_path)
        log_callback(f"🗜️ COMPRESSION: Starting compression of {os.path.basename(src_path)}")
        log_callback(f"   Original size: {original_size} bytes")
    
    with open(src_path, "rb") as f_in, gzip.open(dst_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    
    if log_callback:
        compressed_size = os.path.getsize(dst_path)
        compression_ratio = (compressed_size / original_size) * 100
        log_callback(f"✅ COMPRESSION: Completed - {compression_ratio:.1f}% of original size")
        log_callback(f"   Compressed: {compressed_size} bytes")


def decompress_file_gzip(src_path: str, dst_path: str, log_callback=None) -> None:
    """Decompress gzip file with logging"""
    if log_callback:
        compressed_size = os.path.getsize(src_path)
        log_callback(f"📤 DECOMPRESSION: Starting decompression of {os.path.basename(src_path)}")
        log_callback(f"   Compressed size: {compressed_size} bytes")
    
    with gzip.open(src_path, "rb") as f_in, open(dst_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    
    if log_callback:
        decompressed_size = os.path.getsize(dst_path)
        log_callback(f"✅ DECOMPRESSION: Completed - {decompressed_size} bytes")


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


def send_file(sock: socket.socket, file_path: str, log_callback=None) -> None:
    """Send a file in chunks. Assumes receiver expects raw bytes after metadata."""
    filesize = os.path.getsize(file_path)
    if log_callback:
        log_callback(f"📤 SENDING: Starting file transfer ({filesize} bytes)")
    
    with open(file_path, "rb") as f:
        total_sent = 0
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            sock.sendall(chunk)
            total_sent += len(chunk)
            
            if log_callback and total_sent % (CHUNK_SIZE * 10) == 0:  # Log every ~640KB
                progress = (total_sent / filesize) * 100
                log_callback(f"📤 SENDING: {progress:.1f}% complete ({total_sent}/{filesize} bytes)")
    
    if log_callback:
        log_callback("✅ SENDING: File transfer completed")


def recv_file(sock_file, dest_path: str, expected_size: int = None, log_callback=None) -> None:
    """
    Receive raw bytes from socket file-like and write to dest_path.
    If expected_size is provided it tries to read exactly that many bytes.
    """
    remaining = expected_size
    if log_callback:
        log_callback(f"📥 RECEIVING: Starting file reception ({expected_size} bytes expected)")
    
    with open(dest_path, "wb") as f:
        if remaining is None:
            # Read until socket closes (not used typically)
            total_received = 0
            while True:
                chunk = sock_file.read(CHUNK_SIZE)
                if not chunk:
                    break
                f.write(chunk)
                total_received += len(chunk)
                
                if log_callback and total_received % (CHUNK_SIZE * 10) == 0:
                    log_callback(f"📥 RECEIVING: {total_received} bytes received so far...")
        else:
            # Read exact number of bytes
            total_received = 0
            while remaining > 0:
                chunk = sock_file.read(min(CHUNK_SIZE, remaining))
                if not chunk:
                    raise ConnectionError("Connection closed before all bytes received")
                f.write(chunk)
                total_received += len(chunk)
                remaining -= len(chunk)
                
                if log_callback and total_received % (CHUNK_SIZE * 10) == 0:
                    progress = (total_received / expected_size) * 100
                    log_callback(f"📥 RECEIVING: {progress:.1f}% complete ({total_received}/{expected_size} bytes)")
    
    if log_callback:
        actual_size = os.path.getsize(dest_path)
        log_callback(f"✅ RECEIVING: File reception completed ({actual_size} bytes)")
        if expected_size and actual_size != expected_size:
            log_callback(f"⚠️ RECEIVING: Size mismatch! Expected {expected_size}, got {actual_size}")


def show_download_progress(received, total, bar_length=40):
    """
    Show a visual progress bar for file downloads.
    """
    if total == 0:
        return
    
    percent = float(received) / total
    arrow = '=' * int(round(percent * bar_length) - 1) + '>'
    spaces = ' ' * (bar_length - len(arrow))
    
    progress_bar = f"[{arrow}{spaces}] {percent:.1%} ({received}/{total} bytes)"
    sys.stdout.write('\r' + progress_bar)
    sys.stdout.flush()
    
    if received >= total:
        sys.stdout.write('\n')