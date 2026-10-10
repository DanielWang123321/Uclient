# Changelog

All notable changes to UGClient (formerly Uclient) are documented here. Format: [Keep a Changelog](https://keepachangelog.com/), versioning: SemVer.

## [Unreleased]

## [0.1.1] - 2026-10-10

### Changed
- Renamed the product to **UGClient** (UFACTORY Genesis Client, formerly Uclient): repository `DanielWang123321/ugclient`, deb package and binary `ugclient`, Python package `uclient_core` -> `ugclient_core` (sidecar `ugclient-core`), app identifier `io.github.danielwang123321.ugclient`, env vars `UGCLIENT_*`. Project files are now `*.ugclient.json`; legacy `*.uclient.json` files still load.
- Pinned ufactory_genesis to `be49519` (official UFACTORY joint torque limits, PR #3). Utilization percentages change (UF850 U1: J2 37.5% -> 19.6%, J3 34.0% -> 12.6%); absolute torques are unchanged.
- "Rated" torque renamed to "max torque" everywhere (these are UFACTORY maximum joint torques, see https://docs.supportarticle.ufactory.cc/zhHans/support_articles/hardware/ufactory-joint-parameters.html): UI column "% of max torque" / "占最大扭矩 %", CSV column `rated_nm` -> `max_torque_nm`. The API field `effort_limits_nm` is unchanged.

### Fixed
- End effectors (Gripper G2, BIO Gripper G2, Lite6 gripper / vacuum gripper) could not be added: their GLB meshes were not bundled.
- Mounting an end effector now sets its default TCP from the ufactory_genesis URDF tcp joint (G2 z 172 mm, Lite6 gripper z 83.6 mm, BIO G2 [159.5, 0, 59.5, 0, 0, 0] official UFACTORY value, Lite6 vacuum [0, 0, 61.1, 0, 0, 0] official UFACTORY value). The v0.1.0 "Gripper G2" preset of 101.1 mm was a grasp-planning offset, not the TCP, and is removed from projects on load.

## [0.1.0] - 2026-10-10

First development release. Uclient is a personal project, not an official UFACTORY product.

### Added
- `uclient-core` Python sidecar: JSON-RPC 2.0 over WebSocket on 127.0.0.1 with one-time token auth and API version negotiation.
- Pinocchio backends behind an adapter layer: FK, Jacobian, multi-solution damped-least-squares IK, payload-aware gravity torque (arm/payload split), RNEA and mass matrix.
- `check.pose`: TCP pose (Studio conventions, mm/°) to all IK solutions with joint torques and rated-torque utilisation.
- Supported models: UF850, xArm5/6/7 (`_1305` only), Lite6. Rated torques read at runtime from ufactory_genesis.
- Tauri v2 desktop app (Vue 3 + Element Plus, Chinese/English): Studio-like check page, joint sliders, IK solution picker, torque table, CSV export, three.js URDF viewport with TCP axes and payload COM marker.
- Linux deb packaging; CI for Linux and Windows unit tests; U1 golden test (UF850, 3 kg payload).
