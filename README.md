# SuperAI

**SuperAI** is a full-featured, self-improving multi-model AI super app designed for intelligent orchestration, automation, and resilience.

It combines the best ideas from multi-agent systems, self-learning agents, and personal AI assistants into one cohesive platform.

## ✨ Key Features

- **Intelligent Multi-Model Routing** — Automatically selects the best model for each task using strengths, history, and load balancing strategies.
- **Self-Learning & Skill Evolution** — Automatically creates and improves skills based on outcomes.
- **Persistent Semantic Memory** — Powered by ChromaDB with EmbeddingGemma support.
- **External CLI Discovery** — Detects and integrates with 20+ AI CLIs (Claude Code, Aider, Grok CLI, Gemini CLI, Ollama, etc.).
- **Advanced Load Balancing** — Multiple strategies (Smart Fallback, Latency-based, Round Robin, etc.) + Circuit Breaker + Retry with backoff.
- **Encrypted & Incremental Backups** — Local encrypted backups (zstd + AES-256-GCM) with optional cloud sync.
- **Human-in-the-Loop Priority** — Manual model selection always overrides automated decisions.
- **Full CLI Tooling** — Easy commands for configuration, discovery, backup status, and more.

## 🚀 Installation

```bash
git clone https://github.com/realburhanhusain/superai.git
cd superai

pip install -e .
```

## ▶️ Quick Start

```bash
# First time setup (recommended)
superai init

# List available models
superai list-models

# Set your preferred supervisor model
superai set-supervisor grok-4.5

# Check backup status
superai backup-status
```

## 📦 Core CLI Commands

| Command                        | Description |
|--------------------------------|-------------|
| `superai init`                 | Initialize SuperAI + optional encrypted backup setup |
| `superai discover`             | Discover installed AI CLIs and models |
| `superai list-models [--refresh]` | List all known models (with optional web refresh) |
| `superai set-supervisor <model>` | Set default supervisor model |
| `superai set-strategy <strategy>` | Change load balancing strategy |
| `superai backup-status`        | View backup statistics |
| `superai backup-verify`        | Verify integrity of latest backup |

> See [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for the full command list.

## 🛡️ Backup & Security

SuperAI automatically creates **encrypted and compressed** local backups on clean exit.

- Backups are stored in `./backups/`
- Encryption key is saved in `config/.backup_key` (back this up!)
- Optional cloud sync via `rclone` (supports S3, GCS, Azure, Google Drive, Dropbox, etc.)

## 🧠 Architecture Highlights

- `ModelRegistry` — Curated list of latest + historical models across vendors
- `ModelRouter` + `LoadBalancer` — Intelligent routing with multiple strategies and resilience
- `LearningEngine` — Self-improvement through outcome feedback
- `SecureBackupManager` — Encrypted incremental backups with cloud support

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

---

**Built with ❤️ using Grok** — July 2026
