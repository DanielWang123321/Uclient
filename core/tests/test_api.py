"""API validation, error codes, version negotiation, units (design doc §11)."""

import numpy as np
import pytest

from uclient_core import errors, units
from uclient_core.rpc import Connection
from uclient_core.session import SessionStore


def test_auth_required():
    c = Connection("secret", SessionStore())
    r = c.handle_obj({"jsonrpc": "2.0", "id": 1, "method": "robot.list"})
    assert r["error"]["code"] == errors.AUTH_FAILED
    r = c.handle_obj({"jsonrpc": "2.0", "id": 2, "method": "system.hello", "params": {"token": "nope"}})
    assert r["error"]["code"] == errors.AUTH_FAILED


def test_api_major_mismatch():
    c = Connection("t", SessionStore())
    r = c.handle_obj(
        {"jsonrpc": "2.0", "id": 1, "method": "system.hello", "params": {"token": "t", "api_version": "2.0"}}
    )
    assert r["error"]["code"] == errors.API_VERSION_MISMATCH


def test_hello_and_ping(client):
    assert client.call("ping") == "pong"
    h = client.call("system.hello", token="t0k")
    assert h["api_version"] == "1.0" and h["pinocchio_version"] == "4.0.0"
    assert h["backend"] == {"kin": "uclient", "dyn": "uclient"}


def test_robot_list_supported_models(client):
    keys = [r["key"] for r in client.call("robot.list")]
    assert keys == ["uf850", "xarm5_1305", "xarm6_1305", "xarm7_1305", "lite6"]


def test_robot_info_reads_rated_torques_from_ufactory_genesis(client):
    from ufactory.config.loader import load_runtime_config

    info = client.call("robot.info", robot="uf850")
    assert info["effort_limits_nm"] == list(load_runtime_config("uf850").arm.effort_limits_nm)
    assert info["visual_urdf_relpath"] == "urdf/uf850/uf850_visual.glb.urdf"
    assert info["dof"] == 6 and info["joint_names"][0] == "joint1"


@pytest.mark.parametrize("bad", ["xarm6", "xarm6_1300", "nope"])
def test_unknown_robot(client, bad):
    assert client.raw("robot.info", {"robot": bad})["error"]["code"] == errors.ROBOT_NOT_FOUND


def test_bad_params(client):
    s = client.call("robot.load", robot="lite6")
    r = client.raw("dyn.gravity", {"session_id": s["session_id"], "q_deg": [0, 0, 0]})
    assert r["error"]["code"] == errors.INVALID_PARAMS
    r = client.raw("payload.set", {"session_id": s["session_id"], "mass_kg": -1, "com_mm": [0, 0, 0]})
    assert r["error"]["code"] == errors.INVALID_PARAMS
    assert client.raw("dyn.gravity", {"session_id": "x", "q_deg": [0] * 6})["error"]["code"] == errors.SESSION_NOT_FOUND
    assert client.raw("nope.nope")["error"]["code"] == errors.METHOD_NOT_FOUND


def test_invalid_request_and_parse_error():
    c = Connection("t", SessionStore())
    assert '"code": -32700' in c.handle_text("{not json")
    assert c.handle_obj({"id": 1, "method": "x"})["error"]["code"] == errors.INVALID_REQUEST


def test_units_roundtrip():
    p = [830.0, -12.5, 200.0, -180.0, 10.0, 45.0]
    np.testing.assert_allclose(units.pose_si_to_api(units.pose_api_to_si(p)), p)
    np.testing.assert_allclose(units.rad_to_deg(units.deg_to_rad([1, 2, 3])), [1, 2, 3])


def test_unreachable_pose(client):
    s = client.call("robot.load", robot="lite6")
    r = client.raw("kin.ik", {"session_id": s["session_id"], "target_pose": [5000, 0, 0, 0, 0, 0]})
    assert r["error"]["code"] == errors.IK_NOT_CONVERGED


def test_schema_lists_every_method():
    import json
    from pathlib import Path

    from uclient_core.rpc import METHODS

    schema = json.loads((Path(__file__).resolve().parents[2] / "schema" / "api.v1.json").read_text(encoding="utf-8"))
    assert set(METHODS) | {"system.hello", "system.shutdown", "ping"} == set(schema["methods"])
