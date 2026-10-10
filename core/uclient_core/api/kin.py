from __future__ import annotations

from typing import Any

import numpy as np

from .. import units
from ..errors import IK_NOT_CONVERGED, RpcError, invalid_params
from ..session import RobotSession, SessionStore
from ._params import number, vec


def q_param(s: RobotSession, params: dict[str, Any], name: str = "q_deg") -> np.ndarray:
    return units.deg_to_rad(vec(params, name, s.info.dof))


def fk(params: dict[str, Any], store: SessionStore) -> dict[str, Any]:
    s = store.get(params.get("session_id"))
    q = q_param(s, params)
    out: dict[str, Any] = {
        "tcp_pose": units.pose_si_to_api(s.kin.fk(q, "tcp")),
        "flange_pose": units.pose_si_to_api(s.kin.fk(q, "flange")),
    }
    wanted = params.get("frames")
    if wanted:
        frames = s.kin.frames(q)
        out["frames"] = {n: {"pose": units.pose_si_to_api(p)} for n, p in frames.items() if n in wanted}
    return out


def jacobian(params: dict[str, Any], store: SessionStore) -> dict[str, Any]:
    s = store.get(params.get("session_id"))
    q = q_param(s, params)
    J = s.kin.jacobian(q, params.get("frame", "tcp"))
    sv = np.linalg.svd(J, compute_uv=False)
    return {
        "J": J.tolist(),
        "manipulability": float(np.prod(sv[: min(J.shape)])),
        "cond": float(sv[0] / sv[-1]) if sv[-1] > 0 else float("inf"),
    }


def solve_ik(s: RobotSession, params: dict[str, Any]):
    pose = vec(params, "target_pose", 6)
    frame = params.get("frame", "tcp")
    if frame not in ("tcp", "flange"):
        raise invalid_params("frame must be 'tcp' or 'flange'")
    mode = params.get("mode", "all")
    if mode not in ("all", "nearest"):
        raise invalid_params("mode must be 'all' or 'nearest'")
    seed = q_param(s, params, "seed_q_deg") if params.get("seed_q_deg") is not None else None
    tol_mm = number(params, "tol_mm", 0.01)
    tol_deg = number(params, "tol_deg", 0.01)
    return s.kin.ik(units.pose_api_to_si(pose), frame, seed, mode, tol_mm / 1000.0, np.radians(tol_deg))


def sol_to_api(sol) -> dict[str, Any]:
    return {
        "q_deg": units.rad_to_deg(sol.q).tolist(),
        "err_mm": sol.err_m * 1000.0,
        "err_deg": float(np.degrees(sol.err_rad)),
        "branch": {"elbow": sol.elbow, "wrist": sol.wrist},
        "limit_margin_deg": float(np.degrees(sol.limit_margin_rad)),
    }


def ik(params: dict[str, Any], store: SessionStore) -> dict[str, Any]:
    s = store.get(params.get("session_id"))
    sols = solve_ik(s, params)
    if not sols:
        raise RpcError(IK_NOT_CONVERGED, "no IK solution found (target may be unreachable)")
    return {"solutions": [sol_to_api(x) for x in sols], "reachable": True}
