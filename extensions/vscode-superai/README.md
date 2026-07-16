# SuperAI VS Code Extension (W7 — full depth)

Production-ready VS Code integration for the SuperAI multi-model orchestrator CLI.

**Version:** 1.0.0  
**Docs:** [`docs/VSCODE_EXTENSION.md`](../../docs/VSCODE_EXTENSION.md)  
**Tests:** `npm test` in this folder · `pytest tests/test_vscode_extension_w7.py`

---

## Features

| Command | CLI |
|---------|-----|
| SuperAI: Ask (NL) | `superai ask … --format json` |
| SuperAI: Ask about Selection | NL ask with editor selection |
| SuperAI: Do (one-shot) | `superai do …` |
| SuperAI: Run Task | `superai run … --format json` |
| SuperAI: Review / Review Selection | `superai review … --dry-run` |
| SuperAI: Doctor | `superai doctor --quick` |
| SuperAI: Status --cost | `superai status --cost` |
| SuperAI: List Members | `superai members --available` |
| SuperAI: Smoke Preflight | `superai smoke-preflight` |
| SuperAI: Plugin Marketplace | `superai plugin-catalog` |
| SuperAI: Progress / V6 Status / Explain Run | matching CLIs |
| SuperAI: Open Agent Terminal | terminal → `superai agent` |
| SuperAI: Insert Last Output | paste last CLI stdout into editor |

Also: **status bar**, **Output channel “SuperAI”**, **context menu** on selection, **keybindings**.

---

## Setup

1. Install SuperAI CLI from the repo root:
   ```powershell
   pip install -e ".[dev]"
   # ensure `superai` is on PATH, or set superai.cliPath / superai.pythonPath
   ```
2. Open folder `extensions/vscode-superai` in VS Code (or add the whole SuperAI repo).
3. Press **F5** → Extension Development Host.

### Settings

| Setting | Default | Meaning |
|---------|---------|---------|
| `superai.cliPath` | `superai` | CLI executable |
| `superai.timeoutMs` | `180000` | Process timeout |
| `superai.mockMode` | `false` | Sets `SUPERAI_MOCK=1` |
| `superai.autoShowOutput` | `true` | Focus output channel |
| `superai.pythonPath` | `""` | Optional `PYTHONPATH` (e.g. `…/SuperAI/src`) |

---

## Development & tests

```powershell
cd extensions/vscode-superai
npm test
# or: node test/run.js
```

Pure CLI helpers (`lib/cli.js`) are unit-tested **without** a VS Code host.  
`extension.js` activate/deactivate is smoke-tested with a stubbed `vscode` module.

---

## Architecture

```text
extension.js          UI, commands, status bar, terminal
lib/cli.js            runSuperaiCli, buildArgs, parseCliOutput (testable)
package.json          contributes commands/menus/keybindings/config
```

---

## Out of scope (W7)

- Full Language Server Protocol client
- In-editor streaming token UI (CLI stream is captured in output channel)
- Marketplace publication / VSIX signing pipeline (local F5 + optional `vsce package`)
