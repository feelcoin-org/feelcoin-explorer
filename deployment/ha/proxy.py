#!/usr/bin/env python3

import json
from pathlib import Path
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PRIMARY = "http://127.0.0.1:35781"
BACKUP = "http://127.0.0.1:35795"

ALLOWED_PATHS = {
    "/get_info",
    "/get_transactions",
    "/json_rpc",
}

ALLOWED_METHODS = {
    "get_block",
    "get_block_header_by_height",
    "get_coinbase_tx_sum",
}

LOCK = threading.Lock()
STATE_FILE = Path("/var/lib/feelcoin-rpc-failover/trusted-height.json")
state = {"active": "primary", "last_switch": 0, "trusted_height": 6400}

def load_trusted_height():
    try:
        data = json.loads(STATE_FILE.read_text())
        height = data["height"]
        if type(height) is int and height >= 6400:
            return height
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None

def save_trusted_height(height):
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps({"height": height}) + "\n")
    tmp.replace(STATE_FILE)

state["trusted_height"] = load_trusted_height()


def request(url, path, body=None, timeout=3):
    req = urllib.request.Request(
        url + path,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST" if body is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def health(url):
    try:
        d = json.loads(request(url, "/get_info"))
        checkpoint_payload = json.dumps({
            "jsonrpc": "2.0",
            "id": "checkpoint",
            "method": "get_block_header_by_height",
            "params": {"height": 6400}
        }).encode()

        checkpoint = json.loads(
            request(url, "/json_rpc", checkpoint_payload, timeout=3)
        )

        verified = (
            checkpoint.get("result", {}).get("status") == "OK"
            and checkpoint.get("result", {})
                .get("block_header", {}).get("hash")
            == "65f49b8d4ace35fcf932d6be85b5e849939b9a70ed87f9cb9d4b11248bacb271"
        )

        return (
            verified
            and d.get("status") == "OK"
            and d.get("synchronized") is True
            and d.get("offline") is False
            and isinstance(d.get("height"), int)
            and d["height"] > 0
        ), d
    except Exception:
        return False, {}

def choose():
    primary_ok, primary = health(PRIMARY)

    if primary_ok:
        with LOCK:
            if (
                state["trusted_height"] is None
                or primary["height"] > state["trusted_height"]
            ):
                save_trusted_height(primary["height"])
                state["trusted_height"] = primary["height"]
            state["active"] = "primary"
        return PRIMARY

    backup_ok, backup = health(BACKUP)

    with LOCK:
        if backup_ok:
            trusted = state["trusted_height"]
            if trusted is None or backup["height"] + 5 < trusted:
                raise RuntimeError("Backup behind trusted height")
            state["active"] = "backup"
            return BACKUP

    raise RuntimeError("No healthy Feelcoin RPC node")

class Handler(BaseHTTPRequestHandler):

    def respond(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_rpc(self, body=None):
        path = self.path.split("?")[0]

        if path not in ALLOWED_PATHS:
            return self.respond(403, b'{"error":"Forbidden"}')

        if path == "/json_rpc":
            try:
                payload = json.loads(body or b"{}")
                if (
                    not isinstance(payload, dict)
                    or payload.get("method") not in ALLOWED_METHODS
                ):
                    return self.respond(403, b'{"error":"Method forbidden"}')
            except Exception:
                return self.respond(400, b'{"error":"Invalid JSON"}')

        try:
            target = choose()
            try:
                result = request(target, path, body, timeout=10)
            except Exception:
                if target != PRIMARY:
                    raise
                backup_ok, backup_info = health(BACKUP)
                if not backup_ok:
                    raise
                with LOCK:
                    trusted_height = state["trusted_height"]
                if trusted_height is None or backup_info["height"] + 5 < trusted_height:
                    raise RuntimeError("Backup too far behind")
                result = request(BACKUP, path, body, timeout=10)
            return self.respond(200, result)
        except Exception:
            return self.respond(503, b'{"error":"RPC unavailable"}')

    def do_GET(self):
        if self.path.split("?")[0] != "/get_info":
            return self.respond(403, b'{"error":"Forbidden"}')
        self.handle_rpc()

    def do_POST(self):
        if self.path.split("?")[0] == "/get_info":
            return self.respond(405, b'{"error":"Method not allowed"}')
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 1048576:
                return self.respond(413, b'{"error":"Invalid body size"}')
            body = self.rfile.read(length)
        except Exception:
            return self.respond(400, b'{"error":"Invalid body"}')
        self.handle_rpc(body)

    def log_message(self, fmt, *args):
        pass

ThreadingHTTPServer(
    ("127.0.0.1", 35790), Handler
).serve_forever()
