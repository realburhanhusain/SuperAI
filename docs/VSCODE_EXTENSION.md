# SuperAI VS Code Extension — W7 Full Depth

**Item:** Not-important polish **W7** — VS Code extension depth  
**Status:** Production-ready VS Code surface for SuperAI CLI  
**Path:** `extensions/vscode-superai/`  
**Version:** 1.0.0  
**Tests:** `extensions/vscode-superai/test/run.js` · `tests/test_vscode_extension_w7.py`

---

## Purpose

W7 makes SuperAI usable **inside VS Code** without replacing the CLI product:

- Command Palette actions for daily SuperAI workflows
- Editor **selection → ask / review**
- Integrated **agent terminal**
- Output channel + status bar feedback
- Configurable CLI path, timeout, mock mode

This is a **CLI host extension** (reliable, testable), not a fork of Claude Code / Cursor.

---

## Install & run

### Prerequisites

1. SuperAI CLI installed (`pip install -e ".[dev]"` from repo root).
2. VS Code ≥ 1.85.

### Extension Development Host

```powershell
cd extensions/vscode-superai
code .
# Press F5
```

### Settings (User or Workspace)

```json
{
  "superai.cliPath": "superai",
  "superai.timeoutMs": 180000,
  "superai.mockMode": true,
  "superai.autoShowOutput": true,
  "superai.pythonPath": "C:/path/to/SuperAI/src"
}
```

Use `mockMode` + `pythonPath` for offline demos without provider keys.

---

## Commands (full list)

| Command ID | Title | CLI |
|------------|-------|-----|
| `superai.ask` | Ask (NL) | `ask … --format json` |
| `superai.askSelection` | Ask about Selection | ask with selection body |
| `superai.do` | Do (one-shot) | `do …` |
| `superai.runTask` | Run Task | `run … --format json` |
| `superai.review` | Review (dry-run) | `review … --dry-run --format json` |
| `superai.reviewSelection` | Review Selection | review with selection |
| `superai.doctor` | Doctor | `doctor --quick` |
| `superai.status` | Status --cost | `status --cost` |
| `superai.chat` | Chat | `chat … --new` |
| `superai.members` | List Members | `members --available` |
| `superai.smokePreflight` | Smoke Preflight | `smoke-preflight` |
| `superai.pluginCatalog` | Plugin Marketplace | `plugin-catalog` |
| `superai.progress` | Progress | `progress` |
| `superai.v6Status` | V6 Status | `v6-status` |
| `superai.explainRun` | Explain Run | `explain-run <id>` |
| `superai.openAgentTerminal` | Open Agent Terminal | terminal: `superai agent` |
| `superai.insertLastOutput` | Insert Last Output | editor insert |
| `superai.agentTuiHint` | Agent TUI hint | info message |

### Keybindings (defaults)

| Keys | Command |
|------|---------|
| Ctrl/Cmd+Shift+A | Ask |
| Ctrl/Cmd+Shift+Alt+A | Ask Selection |
| Ctrl/Cmd+Shift+D | Doctor |

### Context menu

When text is selected: **Ask about Selection**, **Review Selection**.

---

## Architecture

```text
VS Code UI
   │
   ▼
extension.js  ── activate / commands / status bar / terminal
   │
   ▼
lib/cli.js    ── buildArgs / runSuperaiCli / parseCliOutput / formatResult
   │
   ▼
superai CLI (child_process.execFile)
```

### Why this design

- **Testable:** `lib/cli.js` has no `vscode` dependency → Node unit tests without Electron.
- **Safe process spawn:** `execFile` + argv array (no shell injection).
- **Workspace-aware:** `cwd` = first workspace folder.
- **Observable:** dedicated Output channel `SuperAI`.

---

## Testing

### Node (primary)

```powershell
cd extensions/vscode-superai
npm test
# or: node test/run.js
```

Coverage:

- `buildArgs` for all W7 actions
- `parseCliOutput` JSON/text/empty
- `formatResult`
- `package.json` contributes commands/keybindings/menus
- `activate`/`deactivate` with stubbed `vscode` module

### Python wrapper (repo CI-friendly)

```powershell
$env:PYTHONPATH="src"
pytest tests/test_vscode_extension_w7.py -q
```

Runs the Node suite via subprocess and asserts docs/package presence.

---

## Definition of done (W7)

| Criterion | Evidence |
|-----------|----------|
| Production-ready code | `extension.js` + `lib/cli.js` + full `package.json` contributes |
| Thorough documentation | This file + `extensions/vscode-superai/README.md` + NOT_IMPORTANT W7 |
| Fully tested | `test/run.js` (Node) + `tests/test_vscode_extension_w7.py` |

### Explicit non-goals

- LSP server / go-to-definition product (V6 N231+)
- In-editor token streaming UI (use agent terminal / output channel)
- Publishing to Marketplace (optional `vsce package` later)

---

## Files

| Path | Role |
|------|------|
| `extensions/vscode-superai/extension.js` | VS Code activation & commands |
| `extensions/vscode-superai/lib/cli.js` | CLI argv + process runner |
| `extensions/vscode-superai/package.json` | Extension manifest |
| `extensions/vscode-superai/test/run.js` | Node unit tests |
| `extensions/vscode-superai/README.md` | Extension readme |
| `docs/VSCODE_EXTENSION.md` | Full product documentation |
| `tests/test_vscode_extension_w7.py` | Pytest harness |

---

## Related SuperAI surfaces

- CLI: `superai ask|do|agent|doctor|status|plugin-catalog|…`
- Plugin marketplace: `docs/PLUGIN_MARKETPLACE.md`
- Agent TUI: `docs/SUPERAI_AGENT.md`
