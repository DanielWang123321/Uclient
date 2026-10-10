#!/usr/bin/env python3
"""Clone ufactory_genesis at the commit pinned in core/pyproject.toml into third_party/.

Upstream only supports a source checkout (+ ``pip install -e``), so we never vendor it in git.
Usage: python scripts/fetch_ufg.py [--source <git url or local path>]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "third_party" / "ufactory_genesis"


def pin() -> dict[str, str]:
    data = tomllib.loads((ROOT / "core" / "pyproject.toml").read_text(encoding="utf-8"))
    return data["tool"]["uclient"]["ufactory_genesis"]


def run(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def main() -> int:
    p = pin()
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=p["repository"])
    a = ap.parse_args()
    if not (DEST / ".git").exists():
        DEST.parent.mkdir(parents=True, exist_ok=True)
        run("git", "clone", "--quiet", a.source, str(DEST))
    head = run("git", "rev-parse", "HEAD", cwd=DEST)
    if not head.startswith(p["commit"]):
        run("git", "fetch", "--quiet", "origin", cwd=DEST)
        run("git", "checkout", "--quiet", "--detach", p["commit"], cwd=DEST)
        head = run("git", "rev-parse", "HEAD", cwd=DEST)
    print(f"ufactory_genesis @ {head[:12]} -> {DEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
