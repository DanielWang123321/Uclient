import json
from pathlib import Path

import pytest

from ugclient_core.rpc import Connection
from ugclient_core.session import SessionStore

GOLDEN = Path(__file__).parent / "golden"


@pytest.fixture
def golden():
    return json.loads((GOLDEN / "uf850_case_a.json").read_text(encoding="utf-8"))


class Client:
    def __init__(self):
        self.conn = Connection("t0k", SessionStore())
        self.n = 0
        assert "result" in self.raw("system.hello", {"token": "t0k"})

    def raw(self, method, params=None):
        self.n += 1
        return self.conn.handle_obj({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params or {}})

    def call(self, method, **params):
        r = self.raw(method, params)
        assert "result" in r, r
        return r["result"]


@pytest.fixture
def client():
    return Client()
