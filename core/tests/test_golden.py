"""U1 golden case and cross-checks (design doc §11)."""

import numpy as np
import pinocchio as pin
import pytest

from uclient_core import units


def _wrapdiff(a, b):
    return (np.asarray(a) - np.asarray(b) + 180.0) % 360.0 - 180.0


def _load(client, golden):
    s = client.call("robot.load", robot=golden["robot"])
    client.call("tcp.set", session_id=s["session_id"], offset=golden["tcp_offset"])
    client.call("payload.set", session_id=s["session_id"], **golden["payload"])
    return s


def test_gravity_at_golden_q(client, golden):
    s = _load(client, golden)
    r = client.call("dyn.gravity", session_id=s["session_id"], q_deg=golden["expected"]["q_deg"])
    tol = golden["tolerance"]["tau_nm"]
    # expected values are rounded to 3 decimals in the reference report
    np.testing.assert_allclose(r["tau_nm"], golden["expected"]["tau_nm"], atol=tol + 5e-4)
    for got, exp in zip(r["tau_payload_nm"], golden["expected"]["tau_payload_nm"]):
        if exp is not None:
            assert abs(got - exp) <= tol + 5e-4
    np.testing.assert_allclose(np.add(r["tau_arm_nm"], r["tau_payload_nm"]), r["tau_nm"], atol=1e-9)
    # utilisation is computed from the runtime max joint torques, never hard-coded
    np.testing.assert_allclose(r["utilization"], np.abs(r["tau_nm"]) / np.asarray(r["effort_limits_nm"]))


def test_check_pose_finds_golden_solution(client, golden):
    s = _load(client, golden)
    r = client.call("check.pose", session_id=s["session_id"], target_pose=golden["target_pose"])
    exp_q = golden["expected"]["q_deg"]
    match = [
        x for x in r["solutions"] if np.all(np.abs(_wrapdiff(x["q_deg"], exp_q)) < golden["tolerance"]["q_deg"] + 5e-4)
    ]
    assert match, [x["q_deg"] for x in r["solutions"]]
    np.testing.assert_allclose(
        match[0]["tau_nm"], golden["expected"]["tau_nm"], atol=golden["tolerance"]["tau_nm"] + 5e-4
    )
    rec = r["solutions"][r["recommended"]]
    assert rec["branch"]["elbow"] == "up"
    np.testing.assert_allclose(rec["tau_nm"], golden["expected"]["tau_nm"], atol=golden["tolerance"]["tau_nm"] + 5e-4)


def test_tcp_offset_moves_flange(client, golden):
    """TCP input -> flange conversion direction (G2 TCP: 172 mm along tool z)."""
    s = _load(client, golden)
    client.call("tcp.set", session_id=s["session_id"], offset=[0, 0, 172.0, 0, 0, 0])
    r = client.call("check.pose", session_id=s["session_id"], target_pose=golden["target_pose"])
    flange = r["solutions"][0]["flange_pose"]
    # tool z points down (roll = -180), so the flange sits 172 mm above the TCP
    np.testing.assert_allclose(flange[:3], [830, 0, 372.0], atol=1e-3)


def test_payload_matches_jacobian_transpose(client, golden):
    s = _load(client, golden)
    sess = client.conn.store.get(s["session_id"])
    q = units.deg_to_rad(golden["expected"]["q_deg"])
    _, tau_pl = sess.dyn.gravity_split(q)
    kin = sess.kin
    m = golden["payload"]["mass_kg"]
    com = units.mm_to_m(golden["payload"]["com_mm"])
    model = pin.Model(kin.model)
    f = model.frames[kin.flange_id]
    fid = model.addFrame(
        pin.Frame("com", f.parentJoint, f.parentFrame, f.placement * pin.SE3(np.eye(3), com), pin.FrameType.OP_FRAME)
    )
    data = model.createData()
    J = pin.computeFrameJacobian(model, data, q, fid, pin.LOCAL_WORLD_ALIGNED)[:3]
    tau_jt = -J.T @ (m * model.gravity.linear)
    np.testing.assert_allclose(tau_pl, tau_jt, atol=1e-6)


@pytest.mark.parametrize("key", ["uf850", "xarm5_1305", "xarm6_1305", "xarm7_1305", "lite6"])
def test_rnea_static_equals_gravity_and_fk_ik_roundtrip(client, key):
    s = client.call("robot.load", robot=key)
    sid, dof = s["session_id"], s["dof"]
    client.call("payload.set", session_id=sid, mass_kg=1.5, com_mm=[10, -5, 40])
    rng = np.random.default_rng(1)
    lo, hi = np.array(s["limits_deg"]).T
    q = rng.uniform(np.maximum(lo, -170) * 0.6, np.minimum(hi, 170) * 0.6)
    g = client.call("dyn.gravity", session_id=sid, q_deg=q.tolist())
    rn = client.call("dyn.rnea", session_id=sid, q_deg=q.tolist(), qd_dps=[0] * dof, qdd_dps2=[0] * dof)
    np.testing.assert_allclose(rn["tau_nm"], g["tau_nm"], atol=1e-9)
    # rnea(q, qd, qdd) == M qdd + rnea(q, qd, 0)
    sess = client.conn.store.get(sid)
    qr, qd, qdd = units.deg_to_rad(q), rng.normal(size=dof), rng.normal(size=dof)
    np.testing.assert_allclose(
        sess.dyn.rnea(qr, qd, qdd), sess.dyn.mass_matrix(qr) @ qdd + sess.dyn.rnea(qr, qd, np.zeros(dof)), atol=1e-8
    )
    if dof == 6:  # 6-DOF: pose-complete IK must recover the original configuration among all solutions
        pose = client.call("kin.fk", session_id=sid, q_deg=q.tolist())["tcp_pose"]
        sols = client.call("kin.ik", session_id=sid, target_pose=pose)["solutions"]
        for x in sols:
            back = client.call("kin.fk", session_id=sid, q_deg=x["q_deg"])["tcp_pose"]
            np.testing.assert_allclose(back[:3], pose[:3], atol=0.02)


@pytest.mark.parametrize("key", ["uf850", "xarm7_1305"])
def test_tcp_frame_matches_upstream_pose_flange_to_tcp(client, key):
    from ufactory.kinematics.tcp_offset import pose_flange_to_tcp

    s = client.call("robot.load", robot=key)
    sid = s["session_id"]
    q = [10.0, -20.0, -30.0, 15.0, 40.0, -25.0, 5.0][: s["dof"]]
    for off in ([0, 0, 0, 0, 0, 0], [10, -5, 172.0, 5, -10, 30]):
        client.call("tcp.set", session_id=sid, offset=off)
        r = client.call("kin.fk", session_id=sid, q_deg=q)
        fl = np.array(r["flange_pose"])
        expect = pose_flange_to_tcp([*fl[:3], *np.radians(fl[3:])], [*off[:3], *np.radians(off[3:])])
        np.testing.assert_allclose(r["tcp_pose"][:3], expect[:3], atol=1e-6)
        np.testing.assert_allclose(_wrapdiff(r["tcp_pose"][3:], np.degrees(expect[3:])), 0, atol=1e-6)


def test_official_torque_limits_and_utilization(client, golden):
    """ufactory_genesis be49519 carries the official UF850 limits; U1 utilization J2 19.6 %, J3 12.6 %."""
    s = _load(client, golden)
    limits = s["effort_limits_nm"]
    np.testing.assert_allclose(limits, [382.5, 382.5, 243.525, 117.3, 38.25, 38.25])
    tau = np.array(golden["expected"]["tau_nm"])
    util = np.abs(tau) / np.array(limits)
    np.testing.assert_allclose(util[1:3], [0.19597, 0.12579], atol=5e-5)
    for key in ("uf850", "xarm5_1305", "xarm6_1305", "xarm7_1305", "lite6"):
        info = client.call("robot.info", robot=key)
        assert len(info["effort_limits_nm"]) == info["dof"]
        assert all(v > 0 for v in info["effort_limits_nm"])
