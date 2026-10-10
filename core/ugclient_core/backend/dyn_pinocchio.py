"""UGClient's own payload-aware Pinocchio dynamics (doc §9).

Payload follows UFACTORY Studio: total tool+workpiece mass, COM relative to the flange
(the arm's ``ee_link``). It is added to the inertia of the last joint of a copy of the
pure-arm model; ``gravity_split`` = (with payload) − (arm only).
"""

from __future__ import annotations

import numpy as np
import pinocchio as pin


class PinocchioDynamics:
    def __init__(self, model: pin.Model, ee_link: str) -> None:
        self.arm = pin.Model(model)
        self.arm_data = self.arm.createData()
        fid = self.arm.getFrameId(ee_link)
        self.ee_joint = self.arm.frames[fid].parentJoint
        self.ee_placement = self.arm.frames[fid].placement.copy()
        self.full = pin.Model(self.arm)
        self.full_data = self.full.createData()
        self.mass = 0.0

    def set_payload(self, mass: float, com_flange_m: np.ndarray, inertia: np.ndarray | None = None) -> None:
        if not np.isfinite(mass) or mass < 0:
            raise ValueError("mass_kg must be >= 0")
        c = np.asarray(com_flange_m, dtype=np.float64).reshape(3)
        I_c = np.zeros((3, 3))
        if inertia is not None:
            ixx, iyy, izz, ixy, ixz, iyz = np.asarray(inertia, dtype=np.float64).reshape(6)
            I_c = np.array([[ixx, ixy, ixz], [ixy, iyy, iyz], [ixz, iyz, izz]])
        R = self.ee_placement.rotation
        Y = pin.Inertia(float(mass), self.ee_placement.act(c), R @ I_c @ R.T)
        self.full = pin.Model(self.arm)
        self.full.inertias[self.ee_joint] = self.arm.inertias[self.ee_joint] + Y
        self.full_data = self.full.createData()
        self.mass = float(mass)

    def gravity(self, q: np.ndarray) -> np.ndarray:
        return pin.computeGeneralizedGravity(self.full, self.full_data, q).copy()

    def gravity_split(self, q: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        arm = pin.computeGeneralizedGravity(self.arm, self.arm_data, q).copy()
        return arm, self.gravity(q) - arm

    def rnea(self, q: np.ndarray, qd: np.ndarray, qdd: np.ndarray) -> np.ndarray:
        return pin.rnea(self.full, self.full_data, q, qd, qdd).copy()

    def mass_matrix(self, q: np.ndarray) -> np.ndarray:
        M = pin.crba(self.full, self.full_data, q)
        return np.triu(M) + np.triu(M, 1).T
