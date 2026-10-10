"""Backend protocols. All values are SI (m, rad, kg, N·m)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

import numpy as np

Frame = Literal["flange", "tcp"]


@dataclass(frozen=True)
class RobotInfo:
    key: str
    robot_name: str
    dof: int
    ee_link: str
    joint_names: tuple[str, ...]
    urdf_path: str
    visual_urdf_relpath: str  # relative to the asset root (contains "assets/urdf/...")
    effort_limits_nm: tuple[float, ...]
    home_q_rad: tuple[float, ...]
    end_effectors: tuple[str, ...] = field(default_factory=tuple)


class RobotCatalog(Protocol):
    def list_keys(self) -> list[str]: ...
    def info(self, key: str, end_effector: str = "none") -> RobotInfo: ...
    def versions(self) -> dict[str, str]: ...


@dataclass
class IkSolution:
    q: np.ndarray
    err_m: float
    err_rad: float
    elbow: str
    wrist: str
    limit_margin_rad: float


class KinematicsBackend(Protocol):
    dof: int
    lower: np.ndarray
    upper: np.ndarray

    def set_tcp(self, offset: np.ndarray) -> None: ...
    def fk(self, q: np.ndarray, frame: str = "tcp") -> np.ndarray: ...
    def frames(self, q: np.ndarray) -> dict[str, np.ndarray]: ...
    def jacobian(self, q: np.ndarray, frame: str = "tcp") -> np.ndarray: ...
    def ik(
        self, target: np.ndarray, frame: Frame, seed: np.ndarray | None, mode: str, tol_m: float, tol_rad: float
    ) -> list[IkSolution]: ...


class DynamicsBackend(Protocol):
    def set_payload(self, mass: float, com_flange_m: np.ndarray, inertia: np.ndarray | None) -> None: ...
    def gravity(self, q: np.ndarray) -> np.ndarray: ...
    def gravity_split(self, q: np.ndarray) -> tuple[np.ndarray, np.ndarray]: ...
    def rnea(self, q: np.ndarray, qd: np.ndarray, qdd: np.ndarray) -> np.ndarray: ...
    def mass_matrix(self, q: np.ndarray) -> np.ndarray: ...
