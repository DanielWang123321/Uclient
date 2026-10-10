"""End-to-end over a real WebSocket: stdout handshake, token auth, JSON-RPC."""

import json
import subprocess
import sys

from websockets.sync.client import connect


def test_sidecar_handshake_and_rpc():
    p = subprocess.Popen([sys.executable, "-m", "uclient_core"], stdout=subprocess.PIPE, text=True)
    try:
        hs = json.loads(p.stdout.readline())
        assert isinstance(hs["port"], int) and len(hs["token"]) == 32
        with connect(f"ws://127.0.0.1:{hs['port']}") as ws:
            ws.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}))
            assert json.loads(ws.recv())["error"]["code"] == 1001
            ws.send(json.dumps({"jsonrpc": "2.0", "id": 2, "method": "system.hello", "params": {"token": hs["token"]}}))
            assert json.loads(ws.recv())["result"]["api_version"] == "1.0"
            ws.send(json.dumps({"jsonrpc": "2.0", "id": 3, "method": "ping"}))
            assert json.loads(ws.recv())["result"] == "pong"
            ws.send(json.dumps({"jsonrpc": "2.0", "id": 4, "method": "system.shutdown"}))
            assert json.loads(ws.recv())["result"] == {"ok": True}
        assert p.wait(timeout=10) == 0
    finally:
        p.kill()
