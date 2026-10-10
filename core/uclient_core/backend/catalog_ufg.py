"""RobotCatalog backed by ufactory_genesis (read-only use of upstream modules).

Only ``ufactory.robots`` and ``ufactory.config`` are imported, never torch/genesis.
Maximum joint torques (``effort_limits_nm``, UFACTORY joint parameters:
https://docs.supportarticle.ufactory.cc/zhHans/support_articles/hardware/ufactory-joint-parameters.html)
are read at runtime from the upstream runtime
config and are never hard-coded in Uclient (design doc §9).
"""

from __future__ import annotations

import subprocess
from importlib import metadata
from pathlib import Path

from ufactory.config.assets import RepositoryAssetStore
from ufactory.config.loader import load_runtime_config
from ufactory.robots.paths import robot_urdf, robot_visual_glb_urdf
from ufactory.robots.registry import PROJECT_ROOT, ROBOT_PROFILES, get_robot_profile, joint_names

from .interfaces import RobotInfo

#: Models supported by Uclient (doc §1): xArm only in its _1305 revision, plus UF850 and Lite6.
SUPPORTED_KEYS: tuple[str, ...] = ("uf850", "xarm5_1305", "xarm6_1305", "xarm7_1305", "lite6")

_EE_FLAGS = {
    "gripper_g2": "with_gripper_g2",
    "bio_gripper_g2": "with_bio_gripper_g2",
    "lite6_gripper": "with_lite6_gripper",
    "lite6_vacuum_gripper": "with_lite6_vacuum_gripper",
}


def asset_root() -> Path:
    return Path(PROJECT_ROOT)


class UfgCatalog:
    def __init__(self) -> None:
        self._store = RepositoryAssetStore(root=asset_root())
        self._cache: dict[tuple[str, str], RobotInfo] = {}

    def list_keys(self) -> list[str]:
        return [k for k in SUPPORTED_KEYS if k in ROBOT_PROFILES]

    def end_effectors(self, key: str) -> tuple[str, ...]:
        p = get_robot_profile(key)
        out = ["none"]
        if p.supports_gripper_g2 and p.gripper_g2_visual_urdf:
            out.append("gripper_g2")
        if p.supports_bio_gripper_g2 and p.bio_gripper_g2_visual_urdf:
            out.append("bio_gripper_g2")
        if p.supports_lite6_gripper and p.lite6_gripper_visual_urdf:
            out.append("lite6_gripper")
        if p.supports_lite6_vacuum_gripper and p.lite6_vacuum_gripper_visual_urdf:
            out.append("lite6_vacuum_gripper")
        return tuple(out)

    def info(self, key: str, end_effector: str = "none") -> RobotInfo:
        if (key, end_effector) not in self._cache:
            self._cache[(key, end_effector)] = self._info(key, end_effector)
        return self._cache[(key, end_effector)]

    def _info(self, key: str, end_effector: str) -> RobotInfo:
        if key not in self.list_keys():
            raise KeyError(key)
        profile = get_robot_profile(key)
        ees = self.end_effectors(key)
        if end_effector not in ees:
            raise ValueError(f"end effector {end_effector!r} not available for {key}")
        kwargs = {_EE_FLAGS[end_effector]: True} if end_effector != "none" else {}
        visual = Path(robot_visual_glb_urdf(key, **kwargs))
        cfg = load_runtime_config(key, asset_store=self._store)
        return RobotInfo(
            key=key,
            robot_name=profile.robot_name,
            dof=profile.dof,
            ee_link=profile.ee_link,
            joint_names=tuple(joint_names(profile)),
            urdf_path=robot_urdf(key),  # pure arm URDF: payload is modelled separately (doc §6.1)
            visual_urdf_relpath=visual.relative_to(asset_root() / "assets").as_posix(),
            effort_limits_nm=tuple(float(x) for x in cfg.arm.effort_limits_nm),
            home_q_rad=tuple(float(x) for x in cfg.arm.home_qpos_rad),
            end_effectors=ees,
            end_effector=end_effector,
            **dict(
                zip(
                    ("default_tcp_offset", "default_tcp_source"),
                    _default_tcp(end_effector, visual, profile.ee_link),
                    strict=True,
                )
            ),
        )

    def versions(self) -> dict[str, str]:
        return {"ufactory_genesis_version": _ufg_version(), "ufactory_genesis_commit": _ufg_commit()}


#: Official end-effector TCP offsets [x, y, z mm, r, p, y deg] that ufactory_genesis does not provide.
#: BIO Gripper G2: official UFACTORY value per maintainer (same on all arms); the upstream URDF
#: tcp frame differs slightly (e.g. y -1.8 mm / yaw -0.4 deg on xArm) and is not used.
OFFICIAL_TCP_OFFSETS: dict[str, tuple[float, ...]] = {
    "bio_gripper_g2": (159.5, 0.0, 59.5, 0.0, 0.0, 0.0),
    # Lite6 vacuum gripper: official UFACTORY value per maintainer (upstream URDF has no tcp frame).
    "lite6_vacuum_gripper": (0.0, 0.0, 61.1, 0.0, 0.0, 0.0),
}
#: TCP frames defined in the upstream combo URDFs.
_URDF_TCP_FRAMES = ("link_tcp",)


def _default_tcp(end_effector: str, visual_urdf: Path, ee_link: str) -> tuple[tuple[float, ...], str]:
    """Default TCP offset of an end effector.

    ``OFFICIAL_TCP_OFFSETS`` first (BIO G2, Lite6 vacuum); otherwise the tcp frame of the ufactory_genesis combo
    URDF (``link_tcp`` for G2 / Lite6 gripper), read at runtime and expressed in the flange frame.
    ``gripper.tool_tip_offset_z_m`` (runtime config) is a grasp-planning offset, not the TCP,
    and is deliberately not used.
    Without either source the flange (zero offset) is used.
    """
    if end_effector == "none":
        return (0.0,) * 6, "none"
    if end_effector in OFFICIAL_TCP_OFFSETS:
        return OFFICIAL_TCP_OFFSETS[end_effector], "official"
    import xml.etree.ElementTree as ET

    import numpy as np
    import pinocchio as pin
    from ufactory.kinematics.tcp_offset import matrix_to_rpy

    model = pin.buildModelFromUrdf(str(visual_urdf))
    data = model.createData()
    pin.framesForwardKinematics(model, data, pin.neutral(model))
    for name in _URDF_TCP_FRAMES:
        if model.existFrame(name):
            T = data.oMf[model.getFrameId(ee_link)].actInv(data.oMf[model.getFrameId(name)])
            xyz = [round(float(v) * 1000.0, 3) + 0.0 for v in T.translation]
            rpy = [round(float(np.degrees(a)), 3) + 0.0 for a in matrix_to_rpy(T.rotation)]
            joint = next(
                (
                    j.get("name")
                    for j in ET.parse(visual_urdf).getroot().iter("joint")
                    if j.find("child") is not None and j.find("child").get("link") == name
                ),
                name,
            )
            return tuple(xyz + rpy), f"urdf:{visual_urdf.name}#{joint}"
    return (0.0,) * 6, "none"


def _ufg_version() -> str:
    try:
        return metadata.version("genesis-ufactory")
    except metadata.PackageNotFoundError:
        f = asset_root() / "UFG_VERSION"
        return f.read_text().strip() if f.is_file() else "unknown"


def _ufg_commit() -> str:
    f = asset_root() / "UFG_COMMIT"  # written by the PyInstaller build
    if f.is_file():
        return f.read_text().strip()[:7]
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short=7", "HEAD"],
            cwd=asset_root(),
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"
