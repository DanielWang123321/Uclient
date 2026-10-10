# Architecture (short)

See [DESIGN.md](DESIGN.md) for the full design (Chinese). Summary:

```
Vue 3 UI (WebView) ──WebSocket JSON-RPC 2.0 (127.0.0.1, token)──▶ ugclient-core (Python, Pinocchio)
      ▲                                                                  │
      │ engine_handshake {port, token}                                   │ read-only
Tauri shell (Rust): spawns sidecar, reads first stdout line,     ufactory_genesis @ pinned commit
restarts it on crash (max 3), save dialog / file writes          (robot registry, runtime config, URDF)
```

- `core/ugclient_core/units.py` is the only place converting API units (mm, °) to SI (m, rad).
- `core/ugclient_core/backend/` isolates upstream: `catalog_ufg.py` reads models and maximum joint torques from
  ufactory_genesis at runtime; `kin_pinocchio.py` / `dyn_pinocchio.py` are UGClient's own FK/IK and
  payload-aware dynamics until upstream offers them; `factory.py` is the switch point.
- The frontend never computes kinematics; `SceneController` (three.js, Z-up) only renders the `q` returned by the sidecar.
