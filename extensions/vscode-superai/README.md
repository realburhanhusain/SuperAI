# SuperAI VS Code Extension (N2)

Scaffold that shells out to the `superai` CLI.

## Commands

- **SuperAI: Run Task** → `superai run "<task>" --format json`
- **SuperAI: Doctor** → `superai doctor --quick`
- **SuperAI: Chat** → `superai chat "<msg>" --new`

## Setup

1. Install SuperAI CLI: `pip install -e ".[dev]"` from the SuperAI repo.
2. Open this folder in VS Code: `extensions/vscode-superai`
3. Press F5 to launch Extension Development Host, or package with `vsce`.

## Config

- `superai.cliPath` — path to the `superai` executable (default: `superai` on PATH)
