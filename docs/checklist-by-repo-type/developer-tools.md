# Developer Tools Repo (CLI/SDK/Plugin)

*Part of the [Meta & Content-Purpose Repos](README.md) family: Smaller categories, sorted by what's inside rather than how code is split: a repo that only points at other repos, a published package, infrastructure-as-code, or pure documentation.*

## How to Detect This Repo Type

| Signal | How to Check |
|---|---|
| `bin` field in `package.json`, a `cmd/` directory (Go), `[project.scripts]` in `pyproject.toml`, or a VS Code extension's `package.json` with `contributes`/`engines.vscode` | `jq .bin package.json` · `grep -l project.scripts pyproject.toml` |

## Audit Checklist

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **CLI help-text/UX completeness** | every command's --help output is pinned in a test and re-checked on every change, not hand-written once and left to drift as flags get added or renamed. | `oclif (JS/TS)`, `goldie (Go)`, `trycmd (Rust)`, `Click CliRunner (Python)` |
| **Cross-platform compatibility** | the full test suite runs on Windows, macOS, and Linux in CI on every change, not just on whatever OS the maintainer happens to develop on. | `GitHub Actions (OS matrix)`, `Cirrus CI` |
| **Shell-completion script correctness** | bash/zsh/fish completions are generated straight from the live command/flag tree at build time, so a renamed flag can't leave a stale hand-maintained script behind. | `oclif plugin-autocomplete (JS/TS)`, `Cobra completion (Go)`, `clap_complete (Rust)`, `shtab (Python)` |
| **Plugin/extension API backward compatibility** | a plugin built against an older host API version is verified against the new host build before release, so an upgrade can't silently break it for everyone who already has it installed. | `IntelliJ Plugin Verifier`, `@vscode/test-electron`, `vscode-extension-tester` |
| **Installation-method coverage** | every install channel the project claims to support is actually built and smoke-installed in CI, not just documented and left untested. | `Verdaccio (JS/TS)`, `GoReleaser (Go)`, `cargo-dist (Rust)`, `cibuildwheel (Python)` |
| **Telemetry opt-out compliance** | the documented opt-out is verified to suppress every outbound call by capturing real network traffic with it set, not just trusted because the docs promise it. | `mitmproxy`, `Semgrep (custom rule)` |
