# SuperAI - Detailed Features

This document provides an in-depth overview of all major features in SuperAI.

## 1. Multi-Model Orchestration

- **Supervisor-Worker Pattern**: A central supervisor decomposes complex tasks and delegates subtasks to specialized workers.
- **Model-Agnostic Design**: Any LLM from any provider (or local model) can act as the supervisor or worker.
- **Recursive Task Decomposition**: The supervisor can break down tasks into smaller subtasks recursively.
- **Parallel Execution**: Supports delegating multiple subtasks simultaneously for efficiency.
- **Structured JSON Communication**: All inter-agent communication uses well-defined JSON schemas for reliability.

## 2. Intelligent Model Routing & Load Balancing

- **Task Classification**: Automatically classifies tasks (coding, reasoning, research, summarization, etc.).
- **Multiple Routing Strategies**:
  - Smart Fallback (default)
  - Latency-based
  - Round Robin
  - Cost-based
  - Parallel Voting (extensible)
- **Circuit Breaker Pattern**: Automatically detects and isolates failing or slow providers.
- **Retry with Exponential Backoff**: Handles transient failures gracefully.
- **Human Override Priority**: Manual model selection by the user always takes precedence.
- **Learned Performance Routing**: Uses historical outcomes from the LearningEngine to improve future routing decisions.

## 3. Comprehensive Model & CLI Discovery

- **Dynamic Discovery**: Automatically detects installed AI CLIs on the system (Claude Code, Aider, Cursor, Grok CLI, Gemini CLI, Continue, LM Studio, etc.).
- **Broad Provider Support**: Supports 17+ providers including xAI, Anthropic, OpenAI, Google, DeepSeek, Qwen, Mistral, Meta, NVIDIA, Groq, Together AI, Fireworks, Perplexity, and more.
- **Latest + Historical Models**: Maintains both cutting-edge and still-useful older models.
- **Multi-Vendor Deduplication**: Intelligently handles models available from multiple providers.
- **Web-based Auto-Refresh**: `list-models --refresh` fetches the latest available models.
- **Model Version Pinning**: Allows pinning specific model versions for reproducibility.

## 4. Self-Learning & Memory System

- **Memory Palace (ChromaDB)**: Persistent semantic memory with vector search and rich metadata tagging.
- **LearningEngine**: Automatically extracts patterns and insights from every task outcome.
- **Skills System** (inspired by OpenClaw & Hermes-Agent):
  - Markdown-based, human-readable skills
  - Autonomous creation of new skills from successful experiences
  - Self-improvement of existing skills over time
- **Context Injection**: The supervisor receives relevant skills, memory, and learned patterns automatically.

## 5. Secure & Automated Backup System

- **Fully Automated**: Creates backups automatically on clean application exit.
- **Encryption**: Uses AES-256-GCM for strong authenticated encryption.
- **Compression**: Zstandard (zstd) for excellent speed + compression ratio with low resource usage.
- **Incremental**: Only changed files are processed.
- **Cloud Sync**: Automatically syncs encrypted backups to cloud storage via `rclone`.
- **Broad Cloud Support**: AWS S3, Google Cloud Storage, Azure Blob Storage, Google Drive, Dropbox, and 40+ other backends.
- **Backup Verification**: Built-in commands to check backup integrity.
- **Non-interactive Mode**: Fully scriptable via environment variables.

## 6. CLI & User Experience

- Rich, discoverable command-line interface
- Commands for initialization, discovery, model management, routing strategy, and backup operations
- Terminal dashboard with live status
- Web dashboard support (FastAPI-based)
- Non-interactive/scriptable mode for automation and CI/CD

## 7. Resilience & Observability

- Circuit Breaker + Retry logic across all model providers
- Latency tracking and performance monitoring
- Structured logging
- Feedback loop from outcomes back into the LearningEngine and routing decisions

## 8. Extensibility

- Easy to add new model providers and external CLIs
- Pluggable load balancing strategies
- Foundation prepared for reinforcement learning-based routing improvements
- Clean modular architecture for future extensions

---

**SuperAI** is designed to be a production-ready, self-improving multi-model AI platform that combines the best ideas from tools like Claude Code, Aider, OpenClaw, Hermes-Agent, and Mempalace into one cohesive system.