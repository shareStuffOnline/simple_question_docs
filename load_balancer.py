#!/usr/bin/env python3
import socket
import threading
import json
import requests
from typing import Dict

class ServerInfo:
    def __init__(self, ip):
        self.ip = ip
        self.busy = False

class SimpleBalancer:
    """
    Minimal example: We have 2 servers: 10.0.0.19, 10.0.2.239.
    We'll pick whichever isn't busy.
    """
    def __init__(self):
        self.servers: Dict[str, ServerInfo] = {
            "10.0.0.19": ServerInfo("10.0.0.19"),
            "10.0.2.239": ServerInfo("10.0.2.239")
        }
        self.lock = threading.Lock()

    def pick_server(self):
        """Pick the first server that isn't busy. Otherwise, return None."""
        with self.lock:
            for ip, sinfo in self.servers.items():
                if not sinfo.busy:
                    sinfo.busy = True
                    return sinfo
            return None

    def release_server(self, sinfo: ServerInfo):
        """Mark server as free."""
        with self.lock:
            sinfo.busy = False

class RawHttpServer:
    """
    We'll do:
      - POST /api/generate
      - POST /api/chat
      - POST /api/embed

    Then pick a server from the balancer, open a requests.post(stream=True) to that server's
    corresponding endpoint, and as data arrives, chunk it to the client.
    """
    def __init__(self, balancer: SimpleBalancer, host="0.0.0.0", port=5000):
        self.balancer = balancer
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"[DEBUG] Server listening on {self.host}:{self.port}")

    def start(self):
        """Accept connections in a loop."""
        print("[DEBUG] Starting raw HTTP server loop...")
        while True:
            conn, addr = self.server_socket.accept()
            threading.Thread(target=self.handle_connection, args=(conn, addr), daemon=True).start()

    def handle_connection(self, conn, addr):
        """Parse the request, route based on path: /api/generate, /api/chat, or /api/embed."""
        try:
            request_data = conn.recv(65536)
            if not request_data:
                conn.close()
                return

            request_text = request_data.decode("utf-8", errors="ignore")
            lines = request_text.split("\r\n")
            request_line = lines[0] if lines else ""
            print(f"[DEBUG] Request line from {addr}: {request_line}")

            # Identify path (e.g. "POST /api/generate HTTP/1.1")
            if not request_line.startswith("POST "):
                self.send_simple_response(conn, 400, b'{"error":"Invalid Method"}')
                return

            try:
                method, path, _ = request_line.split(" ", 2)
            except ValueError:
                self.send_simple_response(conn, 400, b'{"error":"Invalid Request"}')
                return

            # We handle exactly 3 endpoints:
            if path == "/api/generate":
                self.handle_request(conn, lines, "/api/generate")
            elif path == "/api/chat":
                self.handle_request(conn, lines, "/api/chat")
            elif path == "/api/embed":
                self.handle_request(conn, lines, "/api/embed")
            else:
                self.send_simple_response(conn, 404, b'{"error":"Not Found"}')

        except Exception as e:
            print(f"[ERROR] handle_connection: {e}")
        finally:
            conn.close()

    def handle_request(self, conn, lines, endpoint):
        """Generic method to handle requests for one of the three endpoints."""
        # 1) Extract headers + body from lines
        try:
            empty_line_idx = lines.index("")
        except ValueError:
            empty_line_idx = len(lines)

        headers = {}
        for hl in lines[1:empty_line_idx]:
            if ": " in hl:
                k, v = hl.split(": ", 1)
                headers[k.lower()] = v

        content_length = int(headers.get("content-length", 0))
        body_str = "\r\n".join(lines[empty_line_idx+1:])  # entire request body

        # 2) Pick a server from the balancer
        sinfo = self.balancer.pick_server()
        if not sinfo:
            self.send_simple_response(conn, 503, b'{"error":"No server available"}')
            return

        print(f"[DEBUG] Forwarding to {sinfo.ip} for {endpoint}")

        try:
            # 3) Forward request in streaming mode
            backend_url = f"http://{sinfo.ip}:11434{endpoint}"
            with requests.post(
                backend_url,
                data=body_str.encode("utf-8"),
                headers={"Content-Type": "application/json"},
                stream=True
            ) as resp:
                
                # 4) Start chunked response to client
                status_line = f"HTTP/1.1 {resp.status_code} OK\r\n"
                conn.sendall(status_line.encode("utf-8"))
                conn.sendall(b"Content-Type: application/json\r\n")
                conn.sendall(b"Transfer-Encoding: chunked\r\n")
                conn.sendall(b"Connection: close\r\n")
                conn.sendall(b"\r\n")

                # 5) As we read chunks from the model server, forward them to the client
                for chunk in resp.iter_content(chunk_size=4096):
                    if not chunk:
                        continue
                    hex_len = f"{len(chunk):X}\r\n".encode("utf-8")
                    conn.sendall(hex_len)
                    conn.sendall(chunk)
                    conn.sendall(b"\r\n")
                
                # final zero-length chunk
                conn.sendall(b"0\r\n\r\n")

        except Exception as e:
            print(f"[ERROR] {e}")
            err_json = json.dumps({"error": str(e)}).encode("utf-8")
            self.send_simple_response(conn, 500, err_json)
        finally:
            # 6) release server
            self.balancer.release_server(sinfo)

    def send_simple_response(self, conn, status_code, body_bytes):
        """Send a simple non-chunked response and close."""
        status_text = {
            200: "OK",
            400: "Bad Request",
            404: "Not Found",
            500: "Internal Server Error",
            503: "Service Unavailable"
        }.get(status_code, "OK")

        headers = [
            f"HTTP/1.1 {status_code} {status_text}",
            "Content-Type: application/json; charset=utf-8",
            f"Content-Length: {len(body_bytes)}",
            "Connection: close",
            ""
        ]
        response_data = "\r\n".join(headers).encode("utf-8") + body_bytes
        conn.sendall(response_data)

def main():
    balancer = SimpleBalancer()
    server = RawHttpServer(balancer=balancer, host="127.0.0.1", port=5000)
    server.start()

if __name__ == "__main__":
    main()

