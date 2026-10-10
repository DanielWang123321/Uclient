"""Uclient's own Pinocchio kinematics: FK, Jacobian, damped-least-squares IK (doc §9).

ufactory_genesis has no Pinocchio-only IK yet; this lives here behind the adapter layer.
"""

from __future__ import annotations

import numpy as np
import pinocchio as pin
from ufactory.kinematics.tcp_offset import pose_to_matrix

from .interfaces import IkSolution

N_SEEDS = 32
DEDUP_RAD = 1e-3


def pose_si_to_se3(pose: np.ndarray) -> pin.SE3:
    """[x,y,z m, r,p,y rad] -> SE3 using upstream fixed-axis XYZ RPY convention."""
    p = np.asarray(pose, dtype=np.float64)
    T = pose_to_matrix(np.concatenate([p[:3] * 1000.0, p[3:]]))
    return pin.SE3(T[:3, :3].copy(), T[:3, 3] / 1000.0)


def se3_to_pose_si(M: pin.SE3) -> np.ndarray:
    from ufactory.kinematics.tcp_offset import matrix_to_rpy

    return np.array([*M.translation, *matrix_to_rpy(M.rotation)], dtype=np.float64)


class PinocchioKinematics:
    def __init__(self, model: pin.Model, ee_link: str) -> None:
        self.model = pin.Model(model)
        ee = self.model.getFrameId(ee_link)
        self.ee_joint = self.model.frames[ee].parentJoint
        self.ee_placement = self.model.frames[ee].placement.copy()
        self.flange_id = self.model.addFrame(
            pin.Frame("flange", self.ee_joint, ee, self.ee_placement, pin.FrameType.OP_FRAME)
        )
        self.tcp_id = self.model.addFrame(
            pin.Frame("tcp", self.ee_joint, ee, self.ee_placement, pin.FrameType.OP_FRAME)
        )
        self.data = self.model.createData()
        self.dof = self.model.nq
        self.lower = self.model.lowerPositionLimit.copy()
        self.upper = self.model.upperPositionLimit.copy()
        self.link_frames = [
            f.name for f in self.model.frames if f.type == pin.FrameType.BODY and f.name.startswith("link")
        ]

    # -- TCP -----------------------------------------------------------------
    def set_tcp(self, offset_si: np.ndarray) -> None:
        self.model.frames[self.tcp_id].placement = self.ee_placement * pose_si_to_se3(offset_si)
        self.data = self.model.createData()

    def _fid(self, frame: str) -> int:
        if frame == "tcp":
            return self.tcp_id
        if frame == "flange":
            return self.flange_id
        if self.model.existFrame(frame):
            return self.model.getFrameId(frame)
        raise ValueError(f"unknown frame {frame!r}")

    # -- FK / Jacobian -------------------------------------------------------
    def _update(self, q: np.ndarray) -> None:
        pin.forwardKinematics(self.model, self.data, q)
        pin.updateFramePlacements(self.model, self.data)

    def fk_se3(self, q: np.ndarray, frame: str = "tcp") -> pin.SE3:
        self._update(q)
        return self.data.oMf[self._fid(frame)].copy()

    def fk(self, q: np.ndarray, frame: str = "tcp") -> np.ndarray:
        return se3_to_pose_si(self.fk_se3(q, frame))

    def frames(self, q: np.ndarray) -> dict[str, np.ndarray]:
        self._update(q)
        return {n: se3_to_pose_si(self.data.oMf[self.model.getFrameId(n)]) for n in self.link_frames}

    def jacobian(self, q: np.ndarray, frame: str = "tcp") -> np.ndarray:
        return pin.computeFrameJacobian(self.model, self.data, q, self._fid(frame), pin.LOCAL_WORLD_ALIGNED)

    # -- IK ------------------------------------------------------------------
    def _wrap(self, q: np.ndarray) -> np.ndarray:
        out = q.copy()
        for i, a in enumerate(q):
            w = (a + np.pi) % (2 * np.pi) - np.pi
            if self.lower[i] <= w <= self.upper[i]:
                out[i] = w
        return out

    def _dls(self, target: pin.SE3, fid: int, q: np.ndarray, iters: int = 300) -> tuple[np.ndarray, np.ndarray]:
        lam = 1e-6
        err = np.full(6, np.inf)
        for _ in range(iters):
            self._update(q)
            err = pin.log6(self.data.oMf[fid].actInv(target)).vector
            if np.linalg.norm(err) < 1e-10:
                break
            J = pin.computeFrameJacobian(self.model, self.data, q, fid, pin.LOCAL)
            n = J.shape[1]
            dq = np.linalg.solve(J.T @ J + lam * np.eye(n), J.T @ err)
            if not np.all(np.isfinite(dq)):
                break
            q = np.clip(q + dq, self.lower, self.upper)
        self._update(q)
        M = self.data.oMf[fid]
        return q, np.array(
            [
                np.linalg.norm(target.translation - M.translation),
                np.linalg.norm(pin.log3(M.rotation.T @ target.rotation)),
            ]
        )

    def branch(self, q: np.ndarray) -> tuple[str, str]:
        self._update(q)
        p2 = self.data.oMi[2].translation
        p3 = self.data.oMi[3].translation
        pw = self.data.oMi[min(5, self.model.njoints - 1)].translation
        a, b = pw - p2, p3 - p2
        na = np.linalg.norm(a)
        perp = b - (a @ b) / (na * na) * a if na > 1e-9 else b
        elbow = "up" if perp[2] >= 0 else "down"
        wi = 4 if self.dof >= 6 else 3
        wrist = "flip" if q[wi] < 0 else "noflip"
        return elbow, wrist

    def ik(
        self,
        target_pose_si: np.ndarray,
        frame: str = "tcp",
        seed: np.ndarray | None = None,
        mode: str = "all",
        tol_m: float = 1e-5,
        tol_rad: float = np.radians(0.01),
    ) -> list[IkSolution]:
        target = pose_si_to_se3(target_pose_si)
        fid = self._fid(frame)
        seeds: list[np.ndarray] = []
        if seed is not None:
            seeds.append(np.clip(np.asarray(seed, dtype=np.float64), self.lower, self.upper))
        seeds.append(np.clip(np.zeros(self.dof), self.lower, self.upper))
        if mode == "all":
            rng = np.random.default_rng(0)
            lo, hi = np.maximum(self.lower, -np.pi), np.minimum(self.upper, np.pi)
            seeds += [rng.uniform(lo, hi) for _ in range(N_SEEDS)]
        sols: list[IkSolution] = []
        for s in seeds:
            q, (em, er) = self._dls(target, fid, s)
            if not (np.all(np.isfinite(q)) and em <= tol_m and er <= tol_rad):
                continue
            q = self._wrap(q)
            if np.any(q < self.lower - 1e-9) or np.any(q > self.upper + 1e-9):
                continue
            if any(np.allclose(q, o.q, atol=DEDUP_RAD) for o in sols):
                continue
            elbow, wrist = self.branch(q)
            margin = float(np.min(np.minimum(q - self.lower, self.upper - q)))
            sols.append(
                IkSolution(q=q, err_m=float(em), err_rad=float(er), elbow=elbow, wrist=wrist, limit_margin_rad=margin)
            )
            if mode == "nearest":
                break
        ref = seeds[0]
        # Recommended first: elbow up, wrist not flipped, base joint closest to the seed, then overall distance.
        sols.sort(
            key=lambda s: (
                s.elbow != "up",
                s.wrist != "noflip",
                round(abs(float(s.q[0] - ref[0])), 6),
                float(np.linalg.norm(s.q - ref)),
            )
        )
        return sols
