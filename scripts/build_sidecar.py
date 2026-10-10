#!/usr/bin/env python3
"""Build the uclient-core sidecar with PyInstaller (--onedir) into dist-sidecar/uclient-core/,
then smoke-test it: handshake, token auth and the U1 golden case over WebSocket."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UFG = ROOT / "third_party" / "ufactory_genesis"
EXTRA = ROOT / "build" / "sidecar-extra"
DIST = ROOT / "dist-sidecar"
EXE = DIST / "uclient-core" / ("uclient-core.exe" if sys.platform == "win32" else "uclient-core")


def build() -> None:
    EXTRA.mkdir(parents=True, exist_ok=True)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=UFG, capture_output=True, text=True, check=True)
    (EXTRA / "UFG_COMMIT").write_text(commit.stdout.strip() + "\n")
    from importlib import metadata

    (EXTRA / "UFG_VERSION").write_text(metadata.version("genesis-ufactory") + "\n")
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--distpath", str(DIST),
         "--workpath", str(ROOT / "build" / "pyinstaller"), str(ROOT / "core" / "uclient-core.spec")],
        check=True,
    )


def smoke() -> None:
    from websockets.sync.client import connect

    golden = json.loads((ROOT / "core" / "tests" / "golden" / "uf850_case_a.json").read_text(encoding="utf-8"))
    p = subprocess.Popen([str(EXE)], stdout=subprocess.PIPE, text=True)
    try:
        hs = json.loads(p.stdout.readline())
        n = 0

        def call(ws, method, **params):
            nonlocal n
            n += 1
            ws.send(json.dumps({"jsonrpc": "2.0", "id": n, "method": method, "params": params}))
            r = json.loads(ws.recv())
            if "error" in r:
                raise RuntimeError(f"{method}: {r['error']}")
            return r["result"]

        with connect(f"ws://127.0.0.1:{hs['port']}") as ws:
            hello = call(ws, "system.hello", token=hs["token"])
            print("hello:", hello)
            assert "torch" not in json.dumps(hello)
            s = call(ws, "robot.load", robot=golden["robot"])
            call(ws, "tcp.set", session_id=s["session_id"], offset=golden["tcp_offset"])
            call(ws, "payload.set", session_id=s["session_id"], **golden["payload"])
            r = call(ws, "check.pose", session_id=s["session_id"], target_pose=golden["target_pose"])
            tau = r["solutions"][r["recommended"]]["tau_nm"]
            print("U1 tau:", [round(t, 3) for t in tau])
            for got, exp in zip(tau, golden["expected"]["tau_nm"], strict=True):
                assert abs(got - exp) <= golden["tolerance"]["tau_nm"] + 5e-4, (tau, golden["expected"]["tau_nm"])
            for key in ("xarm5_1305", "xarm6_1305", "xarm7_1305", "lite6"):
                call(ws, "robot.load", robot=key)
            call(ws, "system.shutdown")
        p.wait(timeout=20)
        size = sum(f.stat().st_size for f in EXE.parent.rglob("*") if f.is_file())
        print(f"sidecar smoke test OK; onedir size {size / 1e6:.1f} MB")
    finally:
        p.kill()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke-only", action="store_true")
    a = ap.parse_args()
    if not a.smoke_only:
        build()
    smoke()
