# High-Quality CLI Help & Shell Completion (M081 & M082)

## Overview

SuperAI provides comprehensive `--help` output with rich formatting, usage epilogs, and subcommand descriptions (M081) alongside shell completion script generation and installation (M082).

---

## Subcommands & Features

### 1. High-Quality `--help` & Epilogs (M081)
All subcommands include rich docstrings, parameter descriptions, and examples.

Example:
```bash
superai --help
superai daemon --help
superai split-tui --help
superai exit-codes
```

---

### 2. Shell Completion (M082)

SuperAI supports automatic tab-completion across **Bash**, **Zsh**, **Fish**, and **PowerShell**.

#### Install Completion

```bash
# Automatic installation for your current active shell:
superai --install-completion

# Explicit shell selection:
superai completion install --shell zsh
superai completion install --shell powershell
```

#### View Shell Completion Script

```bash
superai completion show --shell bash
superai completion show --shell zsh
```

---

## Verification & Testing

Unit tests for CLI help texts and completion command outputs are defined in `tests/test_cli_help_and_completion_m081_m082.py`.
