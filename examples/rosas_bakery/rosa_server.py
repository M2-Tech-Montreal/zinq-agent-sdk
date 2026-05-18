#!/usr/bin/env python3
"""Mock bakery server — simulates Rosa's backend.

Run:
    openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=34.58.243.153"
    python rosa_server.py
"""

import json
import ssl
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

SPECIALS = [
    {"name": "Monday Combo", "items": "Espresso + Croissant", "price": 5.50},
    {"name": "Baker's Dozen", "items": "12 bagels for the price of 10", "price": 40.00},
    {"name": "Soup & Bread", "items": "Tomato soup + sourdough slice", "price": 9.00},
]

INVENTORY = {
    "espresso": 50, "cappuccino": 50, "latte": 50,
    "croissant": 12, "pain au chocolat": 8,
    "everything bagel": 15, "sourdough loaf": 5,
    "egg & cheese sandwich": 10, "avocado toast": 8,
}

orders = []


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        user_id = body.get("userId", "unknown")

        if self.path == "/specials":
            result = {"specials": SPECIALS, "date": datetime.now().strftime("%A, %B %d")}

        elif self.path == "/inventory":
            result = {
                item: {"available": count > 0, "count": count}
                for item, count in INVENTORY.items()
            }

        elif self.path == "/orders":
            order_id = f"R-{len(orders) + 1001}"
            orders.append({"id": order_id, "userId": user_id, "time": datetime.now().isoformat()})
            result = {"orderId": order_id, "estimatedReady": "15 min", "status": "confirmed"}
            print(f"[ORDER] {order_id} for user {user_id}")

        elif self.path == "/wait-time":
            result = {"minutes": 15, "ordersAhead": len(orders) % 5}

        else:
            result = {"error": "unknown endpoint"}

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

    def log_message(self, fmt, *args):
        print(f"[{datetime.now():%H:%M:%S}] [ROSA-SERVER] {fmt % args}")


def main():
    import os
    port = int(os.environ.get("ROSA_SERVER_PORT", "8081"))

    # Self-signed SSL — generate with:
    # openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=localhost"
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    try:
        context.load_cert_chain("cert.pem", "key.pem")
    except FileNotFoundError:
        print("ERROR: cert.pem and key.pem not found. Generate with:")
        print('  openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=localhost"')
        return

    server = HTTPServer(("0.0.0.0", port), Handler)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    print(f"[ROSA-SERVER] Running on https://0.0.0.0:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
