"""WebSocket server bound to 127.0.0.1 on a random port.

Handshake: the first stdout line is ``{"port": <int>, "token": "<hex>"}``; the Tauri shell
reads it and forwards it to the frontend, which connects directly over WebSocket.
"""

from __future__ import annotations

import asyncio
import json
import secrets
import sys

from websockets.asyncio.server import ServerConnection, serve

from .rpc import Connection
from .session import SessionStore


async def run(host: str = "127.0.0.1", port: int = 0, token: str | None = None) -> None:
    token = token or secrets.token_hex(16)
    store = SessionStore()
    stop = asyncio.Event()

    async def handler(ws: ServerConnection) -> None:
        conn = Connection(token, store, on_shutdown=stop.set)
        async for msg in ws:
            text = msg if isinstance(msg, str) else msg.decode("utf-8", "replace")
            resp = conn.handle_text(text)
            if resp is not None:
                await ws.send(resp)

    async with serve(handler, host, port, max_size=8 * 1024 * 1024) as server:
        bound = server.sockets[0].getsockname()[1]
        sys.stdout.write(json.dumps({"port": bound, "token": token}) + "\n")
        sys.stdout.flush()
        await stop.wait()
