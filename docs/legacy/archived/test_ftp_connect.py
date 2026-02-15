#!/usr/bin/env python3
"""Test FTP connectivity from ARPANET to PDP-10."""
import socket

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)
    try:
        print(f"Connecting to 172.20.0.40:21...")
        s.connect(('172.20.0.40', 21))
        banner = s.recv(1024).decode('utf-8', errors='ignore')
        print(f"FTP banner: {banner.strip()}")
        s.send(b'QUIT\r\n')
        print("QUIT sent")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        s.close()

if __name__ == "__main__":
    main()
