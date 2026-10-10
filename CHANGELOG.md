# Changelog

All notable changes to Uclient are documented here. Format: [Keep a Changelog](https://keepachangelog.com/), versioning: SemVer.

## [Unreleased]

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
