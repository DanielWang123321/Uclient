from __future__ import annotations

from typing import Any

from ufactory.config.assets import AssetLayoutError

from .. import units
from ..backend import factory
from ..errors import ASSET_ERROR, ROBOT_NOT_FOUND, RpcError, invalid_params
from ..session import SessionStore
from ._params import number, vec


def robot_list(_: dict[str, Any], store: SessionStore) -> list[dict[str, Any]]:
    cat = factory.catalog()
    out = []
    for k in cat.list_keys():
        info = cat.info(k)
        out.append(
            {"key": k, "robot_name": info.robot_name, "dof": info.dof, "end_effectors": list(info.end_effectors)}
        )
    return out


def _describe(info) -> dict[str, Any]:
    return {
        "key": info.key,
        "robot_name": info.robot_name,
        "dof": info.dof,
        "joint_names": list(info.joint_names),
        "effort_limits_nm": list(info.effort_limits_nm),
        "visual_urdf_relpath": info.visual_urdf_relpath,
        "home_q_deg": units.rad_to_deg(info.home_q_rad).tolist(),
        "end_effectors": list(info.end_effectors),
        "end_effector": info.end_effector,
        "default_tcp_offset": list(info.default_tcp_offset),
        "default_tcp_source": info.default_tcp_source,
    }


def robot_info(params: dict[str, Any], store: SessionStore) -> dict[str, Any]:
    key = params.get("robot")
    ee = params.get("end_effector", "none")
    cat = factory.catalog()
    if key not in cat.list_keys():
        raise RpcError(ROBOT_NOT_FOUND, f"unknown robot {key!r}", {"supported": cat.list_keys()})
    try:
        return _describe(cat.info(key, ee))
    except ValueError as e:
        raise invalid_params(str(e)) from None


def robot_load(params: dict[str, Any], store: SessionStore) -> dict[str, Any]:
    desc = robot_info(params, store)
    if params.get("calibration"):
        raise invalid_params("calibration import is not implemented yet (milestone M4)")
    try:
        s = store.create(desc["key"], params.get("end_effector", "none"))
    except AssetLayoutError as e:
        raise RpcError(ASSET_ERROR, str(e)) from None
    lo, hi = units.rad_to_deg(s.kin.lower), units.rad_to_deg(s.kin.upper)
    return {
        **desc,
        "session_id": s.session_id,
        "limits_deg": [[float(a), float(b)] for a, b in zip(lo, hi)],
        "default_q_deg": [0.0] * desc["dof"],
    }


def tcp_set(params: dict[str, Any], store: SessionStore) -> dict[str, Any]:
    s = store.get(params.get("session_id"))
    off = vec(params, "offset", 6)
    s.tcp_offset_si = units.pose_api_to_si(off)
    s.kin.set_tcp(s.tcp_offset_si)
    return {"ok": True}


def payload_set(params: dict[str, Any], store: SessionStore) -> dict[str, Any]:
    s = store.get(params.get("session_id"))
    mass = number(params, "mass_kg")
    if mass < 0:
        raise invalid_params("mass_kg must be >= 0")
    com = vec(params, "com_mm", 3)
    inertia = params.get("inertia_kgm2")
    inertia_arr = vec(params, "inertia_kgm2", 6) if inertia is not None else None
    s.dyn.set_payload(mass, units.mm_to_m(com), inertia_arr)
    s.payload = {"mass_kg": mass, "com_mm": com.tolist()}
    return {"ok": True}
