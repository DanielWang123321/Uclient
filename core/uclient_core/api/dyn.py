from __future__ import annotations

from typing import Any

import numpy as np

from .. import units
from ..errors import IK_NOT_CONVERGED, RpcError
from ..session import RobotSession, SessionStore
from .kin import q_param, sol_to_api, solve_ik


def torque_report(
    s: RobotSession, tau: np.ndarray, arm: np.ndarray | None = None, payload: np.ndarray | None = None
) -> dict[str, Any]:
    limits = np.asarray(s.info.effort_limits_nm, dtype=np.float64)  # read at runtime from ufactory_genesis
    util = np.abs(tau) / limits
    out: dict[str, Any] = {
        "tau_nm": tau.tolist(),
        "effort_limits_nm": limits.tolist(),
        "utilization": util.tolist(),
        "over_limit": (util > 1.0).tolist(),
    }
    if arm is not None and payload is not None:
        out["tau_arm_nm"] = arm.tolist()
        out["tau_payload_nm"] = payload.tolist()
    return out


def gravity(params: dict[str, Any], store: SessionStore) -> dict[str, Any]:
    s = store.get(params.get("session_id"))
    q = q_param(s, params)
    arm, pl = s.dyn.gravity_split(q)
    return torque_report(s, arm + pl, arm, pl)


def rnea(params: dict[str, Any], store: SessionStore) -> dict[str, Any]:
    s = store.get(params.get("session_id"))
    q = q_param(s, params)
    qd = q_param(s, params, "qd_dps")
    qdd = q_param(s, params, "qdd_dps2")
    return torque_report(s, s.dyn.rnea(q, qd, qdd))


def mass_matrix(params: dict[str, Any], store: SessionStore) -> dict[str, Any]:
    s = store.get(params.get("session_id"))
    return {"M": s.dyn.mass_matrix(q_param(s, params)).tolist()}


def check_pose(params: dict[str, Any], store: SessionStore) -> dict[str, Any]:
    """U1 in one call: all IK solutions + gravity torques per solution + recommended index."""
    s = store.get(params.get("session_id"))
    sols = solve_ik(s, {**params, "mode": "all"})
    if not sols:
        raise RpcError(IK_NOT_CONVERGED, "no IK solution found (target may be unreachable)")
    results = []
    for sol in sols:
        arm, pl = s.dyn.gravity_split(sol.q)
        results.append(
            {
                **sol_to_api(sol),
                **torque_report(s, arm + pl, arm, pl),
                "flange_pose": units.pose_si_to_api(s.kin.fk(sol.q, "flange")),
            }
        )
    return {
        "solutions": results,
        "recommended": 0,
        "reachable": True,
        "payload": s.payload,
        "tcp_offset": units.pose_si_to_api(s.tcp_offset_si),
    }
