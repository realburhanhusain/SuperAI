# SuperAI Quick Reference Card

## Installation

```bash
pip install -e .
```

## First Time Setup

```bash
superai init
```

During init you can:
- Enable automatic encrypted backup + cloud sync
- Set your rclone remote for cloud backups (non-interactively via env vars also supported)

## Core CLI Commands

| Command                              | Description                                      | Example |
|--------------------------------------|--------------------------------------------------|--------|
| `superai init`                       | First-time initialization + optional backup setup | `superai init` |
| `superai discover`                   | Discover installed AI CLIs and models            | `superai discover` |
| `superai list-models [--refresh]`    | List all known models (refresh from web)         | `superai list-models --refresh` |
| `superai set-supervisor <model>`     | Set default supervisor model persistently        | `superai set-supervisor grok-4.5` |
| `superai set-strategy <strategy>`    | Change load balancing strategy                   | `superai set-strategy latency_based` |
| `superai backup-status`              | Show backup statistics and status                | `superai backup-status` |
| `superai backup-verify [--latest]`   | Verify integrity of latest or specific backup    | `superai backup-verify` |
| `superai backup`                     | Manually trigger encrypted incremental backup    | `superai backup` |

## Backup & Restore

| Action                    | Command                                      | Notes |
|---------------------------|----------------------------------------------|-------|
| **Automatic Backup**      | Enabled on clean exit (after `init`)         | Encrypted + compressed |
| **Manual Backup**         | `superai backup`                             | Creates encrypted local backup |
| **Cloud Sync**            | Automatic if configured during `init`        | Uses rclone |
| **View Status**           | `superai backup-status`                      | Shows last backup, size, cloud config |
| **Verify Integrity**      | `superai backup-verify`                      | Checks decryption + tar structure |
| **Restore**               | `superai restore` (or via `SecureBackupManager`) | Requires encryption key |

**Local Backup Location:**
```
./backups/superai_secure_YYYYMMDD_HHMMSS.tar.zst.enc
```

**Encryption Key Location:**
```
config/.backup_key
```
**Important:** Back up this file securely. Without it, encrypted backups cannot be restored.

## Load Balancing Strategies

Available strategies (change with `superai set-strategy`):

- `smart_fallback` (default)
- `round_robin`
- `latency_based`
- `cost_based`

## Environment Variables (for scripting / non-interactive use)

| Variable                    | Purpose |
|-----------------------------|---------|
| `SUPERAI_CLOUD_REMOTE`      | rclone remote name |
| `SUPERAI_CLOUD_PATH`        | Path inside remote (default: `superai-backups/`) |
| `SUPERAI_BACKUP_DIR`        | Override local backup directory |

## Key Features

- **Model Routing**: Intelligent selection with human override priority
- **Load Balancing**: Multiple strategies + Circuit Breaker + Retry with backoff
- **Self-Learning**: Automatic skill creation and improvement
- **Memory**: Persistent semantic memory (ChromaDB)
- **Security**: Encrypted local backups + cloud sync of encrypted data
- **Automation**: Backup on exit, model discovery on start

## Important Notes

- `rclone` must be installed for cloud sync features.
- The encryption key (`config/.backup_key`) is critical — back it up.
- Human/manual model selection always overrides automated routing.

---
**SuperAI v0.1** — July 2026
