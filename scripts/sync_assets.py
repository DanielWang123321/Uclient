#!/usr/bin/env python3
"""Copy the robot visual assets the frontend needs from the pinned ufactory_genesis checkout.

Copies every URDF plus every GLB referenced by a ``<visual>`` element of the visual/combo URDFs (Draco GLBs, including
end-effector meshes that live outside ``visual_glb/``, e.g. ``gripper_g2/meshes/visual/*.glb``).
Collision meshes are not copied. Fails if a visual mesh referenced by a URDF is missing.
Output: apps/desktop/public/robot-assets/urdf/ (git-ignored, regenerated at build time).
Attribution: see NOTICE.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "third_party" / "ufactory_genesis" / "assets" / "urdf"
DST = ROOT / "apps" / "desktop" / "public" / "robot-assets" / "urdf"


def visual_meshes(urdf: Path) -> list[Path]:
    root = ET.parse(urdf).getroot()
    out = []
    for vis in root.iter("visual"):
        for mesh in vis.iter("mesh"):
            fn = mesh.get("filename", "")
            if fn and "://" not in fn:
                out.append((urdf.parent / fn).resolve())
    return out


def sync(src: Path = SRC, dst: Path = DST) -> tuple[int, int]:
    if dst.exists():
        shutil.rmtree(dst)
    files: set[Path] = set()
    missing: list[str] = []
    for urdf in src.rglob("*.urdf"):
        files.add(urdf.resolve())
        if "visual" not in urdf.name:  # only the visual/combo URDFs are rendered by the app
            continue
        for m in visual_meshes(urdf):
            if m.suffix != ".glb":
                continue
            if m.is_file():
                files.add(m)
            else:
                missing.append(f"{urdf.relative_to(src)} -> {m}")
    for f in src.rglob("visual_glb/*.glb"):
        files.add(f.resolve())
    src_r = src.resolve()
    size = 0
    for f in sorted(files):
        out = dst / f.relative_to(src_r)
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, out)
        size += f.stat().st_size
    if missing:
        raise FileNotFoundError("visual meshes missing upstream:\n  " + "\n  ".join(missing))
    notice = src.parents[1] / "NOTICE"
    if notice.is_file():
        shutil.copy2(notice, dst.parent / "NOTICE.ufactory_genesis")
    return len(files), size


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", type=Path, default=DST)
    a = ap.parse_args()
    if not SRC.is_dir():
        print(f"missing {SRC}; run scripts/fetch_ufg.py first", file=sys.stderr)
        return 1
    n, size = sync(SRC, a.dest)
    print(f"synced {n} files ({size / 1e6:.1f} MB) -> {a.dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
