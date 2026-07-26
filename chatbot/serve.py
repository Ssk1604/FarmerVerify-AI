# chatbot/serve.py
"""
Simple HTTP server to serve the chatbot UI.
Run: python chatbot/serve.py
Then open: http://localhost:3000
"""

import http.server
import socketserver
import os
from pathlib import Path

PORT = 3000
CHATBOT_DIR = Path(__file__).parent

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(CHATBOT_DIR), **kwargs)

    def log_message(self, format, *args):
        print(f"  {args[0]} {args[1]}")

if __name__ == "__main__":
    os.chdir(CHATBOT_DIR)
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"")
        print(f"  🌳 FarmerVerify AI Chatbot")
        print(f"  ──────────────────────────")
        print(f"  Open: http://localhost:{PORT}")
        print(f"  Backend must run on: http://localhost:8000")
        print(f"  Press Ctrl+C to stop")
        print(f"")
        httpd.serve_forever()