# High-Quality CLI Help & Shell Completion (M081 & M082)

## Overview

SuperAI provides comprehensive `--help` output with rich formatting, usage epilogs, and subcommand descriptions (M081) alongside shell completion script generation and installation (M082).

---

## Subcommands & Features

### 1. High-Quality `--help` & Epilogs (M081)
Root help includes examples. Groups (`completion`, `git`, `prompt-injection`, memory surfaces)
carry usage examples in their help strings. Not every deep subcommand has a full epilog yet.

Example:
```bash
superai --help
superai exit-codes
superai completion --help
superai git --help
superai memory-eval --help
```

---

### 2. Shell Completion (M082)

SuperAI uses **official Typer/Click env complete** (`_SUPERAI_COMPLETE=<shell>_source`),
not a fake one-liner stub.

#### Install Completion

```bash
# Typer built-in:
superai --install-completion

# Explicit profile append:
superai completion install --shell zsh
superai completion install --shell bash
superai completion install --shell powershell   # limited native completer
```

#### View Shell Completion Loader

```bash
superai completion show --shell bash
# → eval "$(_SUPERAI_COMPLETE=bash_source superai)"
superai completion show --shell zsh
```

**Honesty:** PowerShell native completion is limited; install prints an honest note.
Install failures no longer claim success (exit mapped).

---

## Verification & Testing

Unit tests for CLI help texts and completion command outputs are defined in `tests/test_cli_help_and_completion_m081_m082.py`.
