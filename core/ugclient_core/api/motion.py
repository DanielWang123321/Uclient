"""Simulated jogging helpers for the motion control bar (API units: mm, deg).

Simulation only: these return joint targets; nothing talks to a real robot.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pinocchio as pin

from .. import units
from ..backend.kin_pinocchio import pose_si_to_se3
from ..errors import IK_UNREACHABLE, JOINT_LIMIT, RpcError, invalid_params
from ..session import SessionStore
from ._params import number
from .kin import q_param

LINEAR_AXES = {"x": 0, "y": 1, "z": 2}
ROT_AXES = {"roll": 0, "pitch": 1, "yaw": 2}
#: A jog increment must not make any joint jump more than this (guards against IK branch flips).
MAX_JOINT_JUMP_DEG = 15.0
ALIGN_TOL_DEG = 0.05


def jog_target(T: pin.SE3, axis: str, delta: float) -> pin.SE3:
    """Apply a base-frame increment (m or rad) to a TCP pose."""
    R, p = T.rotation.copy(), T.translation.copy()
    if axis in LINEAR_AXES:
        p[LINEAR_AXES[axis]] += delta
    elif axis in ROT_AXES:
        w = np.zeros(3)
        w[ROT_AXES[axis]] = delta
        R = pin.exp3(w) @ R  # rotate about the fixed base axis, TCP position kept
    else:
        raise invalid_params(f"unknown axis {axis!r}")
    return pin.SE3(R, p)


def jog_tcp(params: dict[str, Any], store: SessionStore) -> dict[str, Any]:
    """One base-frame TCP increment from ``q_deg``; returns the new joints (nearest IK)."""
    s = store.get(params.get("session_id"))
    q = q_param(s, params)
    axis = str(params.get("axis", ""))
    delta = number(params, "delta")
    d_si = delta / 1000.0 if axis in LINEAR_AXES else np.radians(delta)
    kin = s.kin
    target = jog_target(kin.fk_se3(q, "tcp"), axis, d_si)
    q_new, (em, er) = kin._dls(target, kin.tcp_id, q.copy(), iters=100)
    ok = np.all(np.isfinite(q_new)) and em <= 1e-5 and er <= np.radians(0.01)
    if not ok:
        raise RpcError(IK_UNREACHABLE, "target unreachable (workspace boundary, singularity or joint limit)")
    at_limit = (q_new <= kin.lower + 1e-9) | (q_new >= kin.upper - 1e-9)
    if np.any(at_limit & (np.abs(q_new - q) > 1e-9)):  # a joint was pushed onto its limit by this move
        raise RpcError(JOINT_LIMIT, "joint limit reached")
    if np.max(np.abs(np.degrees(q_new - q))) > MAX_JOINT_JUMP_DEG:
        raise RpcError(IK_UNREACHABLE, "target needs a large joint jump (near a singularity)")
    return {"q_deg": units.rad_to_deg(q_new).tolist(), "tcp_pose": units.pose_si_to_api(kin.fk(q_new, "tcp"))}


def _wrist_dls(kin, q: np.ndarray, idx: list[int], target_R: np.ndarray, z_only: bool, iters: int = 200):
    q = q.copy()
    for _ in range(iters):
        R = kin.fk_se3(q, "tcp").rotation
        if z_only:
            z, zt = R[:, 2], target_R[:, 2]
            err_w = np.cross(z, zt)  # world-frame rotation taking z towards zt
            if np.linalg.norm(err_w) < 1e-9 and z @ zt < 0:
                err_w = np.array([np.pi, 0.0, 0.0])  # exactly upside down: any perpendicular axis works
        else:
            err_w = R @ pin.log3(R.T @ target_R)
        if np.linalg.norm(err_w) < 1e-10:
            break
        J = pin.computeFrameJacobian(kin.model, kin.data, q, kin.tcp_id, pin.LOCAL_WORLD_ALIGNED)[3:, idx]
        dq = np.linalg.solve(J.T @ J + 1e-6 * np.eye(len(idx)), J.T @ err_w)
        if not np.all(np.isfinite(dq)):
            break
        q[idx] = np.clip(q[idx] + dq, kin.lower[idx], kin.upper[idx])
    return q, _orient_err(kin, q, target_R, z_only)


def _orient_err(kin, q: np.ndarray, target_R: np.ndarray, z_only: bool) -> float:
    R = kin.fk_se3(q, "tcp").rotation
    if z_only:
        return float(np.arccos(np.clip(R[:, 2] @ target_R[:, 2], -1, 1)))
    return float(np.linalg.norm(pin.log3(R.T @ target_R)))


def _wrist_variants(kin, qs: np.ndarray, idx: list[int]):
    """Same-orientation alternatives: the other wrist branch (J4+-180, -J5, J6+-180) and +-360 turns."""
    bases = [qs]
    if len(idx) == 3:
        for s4 in (np.pi, -np.pi):
            for s6 in (np.pi, -np.pi):
                b = qs.copy()
                b[idx] = [qs[idx[0]] + s4, -qs[idx[1]], qs[idx[2]] + s6]
                bases.append(b)
    for b in bases:
        for t0 in (0, 2 * np.pi, -2 * np.pi):
            for t2 in (0, 2 * np.pi, -2 * np.pi):
                c = b.copy()
                c[idx[0]] += t0
                c[idx[-1]] += t2
                if np.all(c >= kin.lower - 1e-9) and np.all(c <= kin.upper + 1e-9):
                    yield c


def align(params: dict[str, Any], store: SessionStore) -> dict[str, Any]:
    """Point the tool z-axis straight down (roll 180, pitch 0, current yaw) moving only the last three joints.

    The TCP position may change. 5-axis arms only have two wrist joints, so only the z-axis is aligned.
    """
    s = store.get(params.get("session_id"))
    q = q_param(s, params)
    kin = s.kin
    # "Keep the current yaw" = keep the heading of the tool x-axis in the base XY plane. For a pose that
    # is already near roll 180 / pitch 0 this equals the RPY yaw, and unlike the RPY yaw it stays well
    # defined when the tool points sideways (pitch near +-90, where roll and yaw are degenerate).
    x_axis = kin.fk_se3(q, "tcp").rotation[:, 0]
    yaw = np.arctan2(x_axis[1], x_axis[0]) if np.hypot(x_axis[0], x_axis[1]) > 1e-3 else kin.fk(q, "tcp")[5]
    target_R = pose_si_to_se3(np.array([0, 0, 0, np.pi, 0.0, yaw])).rotation
    n = min(3, kin.dof - 3)
    idx = list(range(kin.dof - n, kin.dof))
    z_only = n < 3
    seeds = [q.copy()]
    for k in range(1, 8):
        seed = q.copy()
        seed[idx] += np.radians(np.array([(k & 1) * 180, (k >> 1 & 1) * 90, (k >> 2 & 1) * 180])[:n])
        seeds.append(seed)
    best = None
    for seed in seeds:
        seed[idx] = np.clip(seed[idx], kin.lower[idx], kin.upper[idx])
        qs, err = _wrist_dls(kin, seed, idx, target_R, z_only)
        if err > np.radians(ALIGN_TOL_DEG):
            continue
        for cand in _wrist_variants(kin, qs, idx):
            if _orient_err(kin, cand, target_R, z_only) > np.radians(ALIGN_TOL_DEG):
                continue
            dist = float(np.linalg.norm(cand - q))
            if best is None or dist < best[1]:
                best = (cand, dist)
    if best is None:
        raise RpcError(IK_UNREACHABLE, "cannot point the tool straight down with the wrist joints alone")
    q_new = best[0]
    return {"q_deg": units.rad_to_deg(q_new).tolist(), "tcp_pose": units.pose_si_to_api(kin.fk(q_new, "tcp"))}
