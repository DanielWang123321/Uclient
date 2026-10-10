"""Simulated jogging for the motion control bar: base-frame TCP jog and wrist Align."""

import numpy as np
import pinocchio as pin
import pytest

from ugclient_core import errors
from ugclient_core.backend.kin_pinocchio import pose_si_to_se3
from ugclient_core.units import pose_api_to_si, wrap_deg

Q0 = [0, -30, -60, 0, 60, 0]


@pytest.fixture
def sess(client):
    return client.call("robot.load", robot="uf850")["session_id"]


def fk(client, sid, q):
    return np.array(client.call("kin.fk", session_id=sid, q_deg=q)["tcp_pose"])


def rot(pose_api):
    return pose_si_to_se3(pose_api_to_si(pose_api)).rotation


@pytest.mark.parametrize("axis,i", [("x", 0), ("y", 1), ("z", 2)])
def test_linear_jog_moves_one_mm_in_base_frame(client, sess, axis, i):
    p0 = fk(client, sess, Q0)
    r = client.call("motion.jog_tcp", session_id=sess, q_deg=Q0, axis=axis, delta=1.0)
    p1 = fk(client, sess, r["q_deg"])
    d = p1 - p0
    assert d[i] == pytest.approx(1.0, abs=1e-3)
    assert np.linalg.norm(np.delete(d[:3], i)) < 1e-3
    assert np.allclose(p1[3:], p0[3:], atol=1e-3)
    assert np.max(np.abs(np.array(r["q_deg"]) - Q0)) < 2.0


@pytest.mark.parametrize("axis", ["roll", "pitch", "yaw"])
def test_rotation_jog_keeps_position_and_turns_one_degree(client, sess, axis):
    p0 = fk(client, sess, Q0)
    r = client.call("motion.jog_tcp", session_id=sess, q_deg=Q0, axis=axis, delta=-1.0)
    p1 = fk(client, sess, r["q_deg"])
    assert np.allclose(p1[:3], p0[:3], atol=1e-3)
    rel = rot(p1) @ rot(p0).T  # base-frame increment
    w = np.zeros(3)
    w[["roll", "pitch", "yaw"].index(axis)] = np.radians(-1.0)
    assert np.allclose(rel, pin.exp3(w), atol=1e-6)


def test_jog_outside_workspace_is_unreachable(client, sess):
    stretched = [0, 85, -10, 0, 0, 0]
    r = client.raw("motion.jog_tcp", {"session_id": sess, "q_deg": stretched, "axis": "x", "delta": 500.0})
    assert r["error"]["code"] in (errors.IK_UNREACHABLE, errors.JOINT_LIMIT)


def test_jog_bad_axis(client, sess):
    r = client.raw("motion.jog_tcp", {"session_id": sess, "q_deg": Q0, "axis": "w", "delta": 1.0})
    assert r["error"]["code"] == errors.INVALID_PARAMS


@pytest.mark.parametrize("q", [[20, -10, -50, 30, 40, -70], [0, 0, 0, 0, 0, 0], [10, -20, -40, 0, 70, 30]])
def test_align_points_tool_down_moving_only_wrist(client, sess, q):
    yaw0 = fk(client, sess, q)[5]
    r = client.call("motion.align", session_id=sess, q_deg=q)
    qn = np.array(r["q_deg"])
    assert np.allclose(qn[:3], q[:3], atol=1e-9)
    p = fk(client, sess, qn.tolist())
    assert abs(wrap_deg(p[3] - 180)) < 0.1 and abs(p[4]) < 0.1
    assert abs(wrap_deg(p[5] - yaw0)) < 0.1


def test_align_xarm7_moves_last_three(client):
    sid = client.call("robot.load", robot="xarm7_1305")["session_id"]
    q = [0, 10, 0, 40, 0, 30, 0]
    qn = client.call("motion.align", session_id=sid, q_deg=q)["q_deg"]
    assert np.allclose(qn[:4], q[:4])


def test_align_from_sideways_tool_keeps_x_heading(client, sess):
    q = [-1.1, -56.9, -98.4, -13.1, 49.2, 8.6]  # tool horizontal: pitch ~ -90, RPY yaw ill-defined
    qn = client.call("motion.align", session_id=sess, q_deg=q)["q_deg"]
    p = fk(client, sess, qn)
    assert abs(wrap_deg(p[3] - 180)) < 0.1 and abs(p[4]) < 0.1
    assert np.allclose(qn[:3], q[:3])


def test_align_picks_the_nearest_wrist_branch(client, sess):
    q = [-1.42, -55.05, -92.84, -15.72, 53.26, 9.56]
    qn = client.call("motion.align", session_id=sess, q_deg=q)["q_deg"]
    assert abs(qn[3]) < 5  # not the J4 = -180 branch
    assert np.linalg.norm(np.array(qn) - q) < 150
