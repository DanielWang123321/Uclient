# Uclient

> **Uclient 目前是个人项目，处于开发阶段，不是 UFACTORY 官方产品，与 UFACTORY 无隶属或背书关系。**

[English](README.md)

Uclient 是一个开源桌面客户端（Tauri v2 + Vue 3），基于 [`ufactory_genesis`](https://github.com/xArm-Developer/ufactory_genesis) 和 [Pinocchio](https://github.com/stack-of-tasks/pinocchio)，为 UFACTORY 机械臂提供**运动学、动力学计算和 3D 可视化**。术语和单位与 UFACTORY Studio 保持一致（mm / °、TCP Offset、TCP Payload）。不连接真机，不做强化学习。

支持机型：**UF850、xArm5/6/7（仅 `_1305` 版本）、Lite6**。平台：**Linux**（Windows 10+ 打包计划在 M5 里程碑加入；暂不支持 macOS）。

![校核页：UF850 U1 用例](docs/images/check-u1.png)

## 当前状态

早期开发（里程碑 M0/M1，见 [docs/DESIGN.md](docs/DESIGN.md) §14）。

| 模块 | 状态 |
|---|---|
| Python 计算引擎（`core/`）：127.0.0.1 上的 WebSocket JSON-RPC 2.0，token 认证 | ✅ |
| FK、雅可比、多解 IK（纯 Pinocchio，阻尼最小二乘） | ✅ |
| 负载感知重力扭矩（本体/负载分解）、RNEA、质量矩阵 | ✅ |
| `check.pose`：TCP 位姿 → 全部 IK 解 + 扭矩（U1 金标准用例） | ✅ |
| Tauri 壳：引擎生命周期、端口/token 握手、崩溃重启 | ✅ |
| 校核页：机型/TCP/负载面板、关节滑块、IK、扭矩表、CSV、3D 视图 | ✅ 初版 |
| CI 中打 Linux deb 包 | ✅（未签名的开发构建） |
| 轨迹与 τ(t) 曲线（M3）、工作空间与标定（M4） | ⏳ |

计算结果是**静态模型**：URDF 名义惯性参数，不含摩擦、减速器效率和单机标定。最大关节扭矩（[UFACTORY 关节参数](https://docs.supportarticle.ufactory.cc/zhHans/support_articles/hardware/ufactory-joint-parameters.html)）运行时从 `ufactory_genesis` 读取（当前锁定 commit `be49519`，已包含 UFACTORY 官方关节扭矩限值）。

## 开发（Linux）

需要 Python 3.12、Node 22 + pnpm、Rust stable，以及 Tauri 系统依赖（`libwebkit2gtk-4.1-dev librsvg2-dev libappindicator3-dev patchelf`）。

```bash
# 1. Python 引擎 + 锁定版本的 ufactory_genesis（只读使用，克隆到 third_party/）
python3.12 -m venv .venv
python scripts/fetch_ufg.py
.venv/bin/pip install -e third_party/ufactory_genesis -e "core[dev]"
.venv/bin/python -m pytest core/tests

# 2. 前端资源与测试
.venv/bin/python scripts/sync_assets.py
cd apps/desktop && pnpm install && pnpm test

# 3. 用开发版引擎运行桌面应用
UCLIENT_CORE_CMD="$PWD/../../.venv/bin/python -m uclient_core" pnpm tauri dev

# 4. 打包（deb）
cd ../.. && .venv/bin/python scripts/build_sidecar.py
cd apps/desktop && pnpm tauri build --config src-tauri/tauri.bundle.conf.json
```

## 许可证

MIT © 2026 Daniel Wang。机器人模型资源来自 `ufactory_genesis` 及其上游 xArm ROS 描述包，详见 [NOTICE](NOTICE)。
