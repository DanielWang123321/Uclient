#!/usr/bin/env python3
"""Copy the robot visual assets the frontend needs from the pinned ufactory_genesis checkout.

Only URDFs and Draco GLBs are copied (no collision/visual STL); attribution: see NOTICE.
Output: apps/desktop/public/robot-assets/urdf/ (git-ignored, regenerated at build time).
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "third_party" / "ufactory_genesis" / "assets" / "urdf"
DST = ROOT / "apps" / "desktop" / "public" / "robot-assets" / "urdf"


def main() -> int:
    if not SRC.is_dir():
        print(f"missing {SRC}; run scripts/fetch_ufg.py first", file=sys.stderr)
        return 1
    if DST.exists():
        shutil.rmtree(DST)
    n = size = 0
    for f in SRC.rglob("*"):
        if not f.is_file():
            continue
        rel = f.relative_to(SRC)
        keep = f.suffix == ".urdf" or (f.suffix == ".glb" and "visual_glb" in rel.parts)
        if not keep:
            continue
        out = DST / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, out)
        n += 1
        size += f.stat().st_size
    shutil.copy2(SRC.parents[1] / "NOTICE", DST.parent / "NOTICE.ufactory_genesis")
    print(f"synced {n} files ({size / 1e6:.1f} MB) -> {DST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
