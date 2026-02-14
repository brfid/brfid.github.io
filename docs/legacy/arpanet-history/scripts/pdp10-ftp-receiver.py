#!/usr/bin/env python3
"""Simple TCP file receiver for PDP-10 container.

Listens on port 21 and saves received data to a file.
This provides a pragmatic FTP-like endpoint for host-to-host transfer testing.

Usage:
    python3 pdp10-ftp-receiver.py [--port PORT] [--output FILE]
"""

import argparse
import socket
import threading
import datetime


def handle_client(conn: socket.socket, addr: tuple, output_file: str) -> None:
    """Handle a single client connection."""
    print(f"[{datetime.datetime.now().isoformat()}] Connection from {addr}")
    
    try:
        with open(output_file, 'wb') as f:
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                f.write(data)
                print(f"  Received {len(data)} bytes")
        
        print(f"  File saved to {output_file}")
        # Send acknowledgment
        conn.sendall(b"226 Transfer complete\r\n")
    except Exception as e:
        print(f"  Error: {e}")
        conn.sendall(f"550 Error: {e}\r\n".encode())
    finally:
        conn.close()
        print(f"  Connection closed")


def main() -> int:
    parser = argparse.ArgumentParser(description="Simple TCP file receiver")
    parser.add_argument("--port", type=int, default=21, help="Port to listen on")
    parser.add_argument("--output", default="/machines/data/received.txt", help="Output file path")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    args = parser.parse_args()
    
    print(f"Starting FTP receiver on {args.host}:{args.port}")
    print(f"Output file: {args.output}")
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((args.host, args.port))
    server.listen(5)
    
    print("Ready for connections...")
    
    try:
        while True:
            conn, addr = server.accept()
            thread = threading.Thread(
                target=handle_client,
                args=(conn, addr, args.output)
            )
            thread.daemon = True
            thread.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server.close()
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
