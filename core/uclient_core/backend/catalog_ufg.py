"""RobotCatalog backed by ufactory_genesis (read-only use of upstream modules).

Only ``ufactory.robots`` and ``ufactory.config`` are imported, never torch/genesis.
Rated torques (``effort_limits_nm``) are read at runtime from the upstream runtime
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
                    _default_tcp(cfg, end_effector, visual, profile.ee_link),
                    strict=True,
                )
            ),
        )

    def versions(self) -> dict[str, str]:
        return {"ufactory_genesis_version": _ufg_version(), "ufactory_genesis_commit": _ufg_commit()}


#: End effectors whose tool-tip offset comes from the upstream runtime config (gripper.adapter must match).
_RUNTIME_TCP = {"gripper_g2": "g2", "lite6_gripper": "lite6"}
#: TCP frames defined in the upstream combo URDFs.
_URDF_TCP_FRAMES = ("bio_gripper_g2_tcp_link", "link_tcp")


def _default_tcp(cfg, end_effector: str, visual_urdf: Path, ee_link: str) -> tuple[tuple[float, ...], str]:
    """Default TCP offset for an end effector, read from ufactory_genesis (never hard-coded).

    G2 / Lite6 gripper: ``gripper.tool_tip_offset_z_m`` of the runtime config (e.g. 101.1 mm for G2).
    Otherwise: the TCP frame of the combo visual URDF relative to the flange, if any (Bio G2).
    Lite6 vacuum gripper: upstream defines no TCP, so the flange (zero offset) is used.
    """
    if end_effector == "none":
        return (0.0,) * 6, "none"
    adapter = _RUNTIME_TCP.get(end_effector)
    if adapter is not None and getattr(cfg.gripper, "adapter", None) == adapter:
        return (0.0, 0.0, round(float(cfg.gripper.tool_tip_offset_z_m) * 1000.0, 6), 0.0, 0.0, 0.0), "runtime_config"
    import numpy as np
    import pinocchio as pin
    from ufactory.kinematics.tcp_offset import matrix_to_rpy

    model = pin.buildModelFromUrdf(str(visual_urdf))
    data = model.createData()
    pin.framesForwardKinematics(model, data, pin.neutral(model))
    for name in _URDF_TCP_FRAMES:
        if model.existFrame(name):
            T = data.oMf[model.getFrameId(ee_link)].actInv(data.oMf[model.getFrameId(name)])
            xyz = [round(float(v) * 1000.0, 3) for v in T.translation]
            rpy = [round(float(np.degrees(a)), 3) + 0.0 for a in matrix_to_rpy(T.rotation)]
            return tuple(xyz + rpy), f"urdf:{name}"
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
