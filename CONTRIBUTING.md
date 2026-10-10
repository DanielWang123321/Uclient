# Contributing

Thanks for your interest! UGClient is a personal project in early development.

- **Environment**: Python 3.12, Node 22 + pnpm, Rust stable. Development happens mainly on Linux; keep code cross-platform (use `pathlib` / Tauri path APIs, no POSIX-only calls in the sidecar).
- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/) in English, signed off with DCO (`git commit -s`). No CLA.
- **PRs** must pass CI, including the U1 golden test (`core/tests/golden/`).
- **New API methods**: update `schema/api.v1.json`, `apps/desktop/src/rpc/types.ts`, and both `zh.json` / `en.json` strings.
- **Upstream**: do not patch `ufactory_genesis` here; missing capabilities live behind `core/ugclient_core/backend/` (see docs/DESIGN.md §9).
