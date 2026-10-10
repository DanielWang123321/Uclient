"""Select backend implementations. Switch here once ufactory_genesis ships its own APIs."""

from __future__ import annotations

from dataclasses import dataclass

import pinocchio as pin

from .catalog_ufg import UfgCatalog
from .dyn_pinocchio import PinocchioDynamics
from .interfaces import RobotInfo
from .kin_pinocchio import PinocchioKinematics

BACKEND_NAMES = {"kin": "uclient", "dyn": "uclient"}

_catalog: UfgCatalog | None = None


def catalog() -> UfgCatalog:
    global _catalog
    if _catalog is None:
        _catalog = UfgCatalog()
    return _catalog


@dataclass
class Backends:
    info: RobotInfo
    kin: PinocchioKinematics
    dyn: PinocchioDynamics


def create(info: RobotInfo) -> Backends:
    model = pin.buildModelFromUrdf(info.urdf_path)
    return Backends(info=info, kin=PinocchioKinematics(model, info.ee_link), dyn=PinocchioDynamics(model, info.ee_link))
