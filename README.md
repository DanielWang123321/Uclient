# UGClient

**UGClient = UFACTORY Genesis Client** (formerly *Uclient*).

> **UGClient is currently a personal project in development. It is not an official UFACTORY product and is not affiliated with or endorsed by UFACTORY.**

[中文说明](README.zh.md)

UGClient is an open-source desktop client (Tauri v2 + Vue 3) for **kinematics, dynamics and 3D visualization** of UFACTORY robot arms. It is built on [`ufactory_genesis`](https://github.com/xArm-Developer/ufactory_genesis) and [Pinocchio](https://github.com/stack-of-tasks/pinocchio). Terms and units follow UFACTORY Studio (mm / °, TCP Offset, TCP Payload). **All motion is simulated:** UGClient does not connect to real robots, and it does not do reinforcement learning.

Supported models: **UF850, xArm5/6/7 (`_1305` revision only), Lite6**. Platform: **Linux** (deb package). Windows 10+ packaging is planned; macOS is not supported.

![Main view: UF850 with the motion bar](docs/images/main-view.png)

## Features

**Layout.** The light 3D scene fills the window. Dark rounded panels float on top of it:
- Left panel: robot model, end effector, TCP offset and TCP payload. Connection status and the Settings button are at the bottom.
- Right panel (read-only): simulated state, mode, payload, mounting, TCP pose and joint angles.
- Top toolbar: reset view, and Base / TCP / COM toggles. The 中/EN language switch and a red STOP button sit at the top right.
- Bottom: the collapsible motion bar.

**Motion bar (simulation only).**
- J1-J6 sliders with joint limits, a value box and -/+ buttons.
- Z-/Z+ and Yaw-/Yaw+ buttons, plus round XYZ (X+/X-/Y+/Y-) and RPY (P+/P-/R+/R-) jog pads. TCP jogging is in the base frame and uses the engine's IK.
- A **click** moves one step (default 1 mm / 1°, configurable). **Press and hold** for more than 300 ms moves continuously until you release.
- The speed slider defaults to 50 %. 100 % is 230 mm/s linear and 40 °/s for joints and rotation.
- **Home** (all joints to 0) and **Align** (only the last three joints turn so the tool points straight down) use the same click/hold behavior. A click takes one joint-space step toward the target; a hold moves continuously until release or arrival.
- **STOP**, or releasing a held button, stops motion and sets the simulated state to 4. States are 2 = ready, 1 = moving, 4 = stopped.
- Reaching a joint limit, the safety boundary, or an unreachable target stops motion and shows a message.

**3D view.** Base and TCP coordinate axes are drawn as X red, Y green, Z blue. The payload center of mass is shown when a payload is set.

**Settings** (saved locally):
- Jog: click step for linear axes (mm) and for angular axes and joints (°).
- Safety boundary, saved per robot model: TCP X/Y/Z min and max in the base frame, and per-joint min and max. Joint values can't go outside the model's limits. Jog, Home and Align stop at the boundary.
- General: language, default robot model, and restoring the last session at startup.
- About: versions, license and the personal-project note.

![Settings: safety boundary](docs/images/settings.png)

**Engine API without a GUI yet.** The Python engine still provides payload-aware gravity torque (`dyn.gravity`, arm/payload split, % of max torque), `check.pose` (TCP pose to all IK solutions with torques), `kin.ik`, `kin.fk`, `kin.jacobian`, `dyn.rnea` and `dyn.mass_matrix`. See [schema/api.v1.json](schema/api.v1.json). The app currently has no torque table, CSV export or IK form.

## Status

Early development (see [docs/DESIGN.md](docs/DESIGN.md) §14).

| Area | State |
|---|---|
| Python engine (`core/`): JSON-RPC 2.0 over WebSocket on 127.0.0.1, token auth | done |
| FK, Jacobian, multi-solution IK (pure Pinocchio, damped least squares) | done |
| Payload-aware gravity torque, RNEA, mass matrix (API only, no GUI yet) | done |
| Tauri shell: engine lifecycle, port/token handshake, crash restart | done |
| Main view: floating panels, simulated motion bar, RGB axes, settings | done |
| Linux deb packaging in CI | done (unsigned development builds) |
| Torque view, trajectory and torque-over-time curves, workspace and calibration | planned |

Results come from **static models**: nominal URDF inertia, with no friction, gearbox efficiency or per-unit calibration. Maximum joint torques ([UFACTORY joint parameters](https://docs.supportarticle.ufactory.cc/zhHans/support_articles/hardware/ufactory-joint-parameters.html)) are read at runtime from `ufactory_genesis`, pinned to commit `be49519`, which carries the official UFACTORY joint torque limits.

## Development (Linux)

Requirements: Python 3.12, Node 22 + pnpm, Rust stable, and the Tauri system packages (`libwebkit2gtk-4.1-dev librsvg2-dev libappindicator3-dev patchelf`).

```bash
# 1. Python sidecar + pinned ufactory_genesis (never modified, cloned into third_party/)
python3.12 -m venv .venv
python scripts/fetch_ufg.py
.venv/bin/pip install -e third_party/ufactory_genesis -e "core[dev]"
.venv/bin/python -m pytest core/tests

# 2. Frontend assets and tests
.venv/bin/python scripts/sync_assets.py         # robot URDF + GLB -> apps/desktop/public/robot-assets
cd apps/desktop && pnpm install && pnpm test

# 3. Run the desktop app against the dev sidecar
UGCLIENT_CORE_CMD="$PWD/../../.venv/bin/python -m ugclient_core" pnpm tauri dev

# 4. Package (deb)
cd ../.. && .venv/bin/python scripts/build_sidecar.py   # PyInstaller onedir + smoke test
cd apps/desktop && pnpm tauri build --config src-tauri/tauri.bundle.conf.json
```

You can also run the frontend in a browser: start `python -m ugclient_core`, then open `http://localhost:1420/?port=<port>&token=<token>` using the handshake line it prints.

## Repository layout

```
apps/desktop/        Vue 3 + TS + Element Plus frontend, three.js viewport, Tauri shell (src-tauri/)
core/ugclient_core/   Python sidecar: server, api/, units.py, backend/ adapter layer
schema/api.v1.json   JSON-RPC API description
scripts/             fetch_ufg.py, sync_assets.py, build_sidecar.py
docs/DESIGN.md       Design document (Chinese)
```

## License

MIT © 2026 Daniel Wang. Robot model assets come from `ufactory_genesis` and its upstream xArm ROS packages; see [NOTICE](NOTICE).
