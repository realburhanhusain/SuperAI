
============================================================
REPO: Shubhamsaboo/openclaw-vertexai-memorybank
============================================================
# openclaw-vertexai-memorybank
Managed long-term memory for your OpenClaw agents, powered by [Vertex AI Memory Bank](https://docs.cloud.google.com/agent-builder/agent-engine/memory-bank/overview).
### Why you need memory beyond OpenClaw core
OpenClaw's built-in memory is per-agent and per-session. This plugin adds **user-scoped memory that works across all your agents**, so when you tell one agent your preferences, every agent remembers. Scope by user, by project, or however you want. Your agent's memory compounds over time, not resets with each session.
### Why Vertex AI Memory Bank
Fully managed with no vector database to run, no embeddings to maintain, no infrastructure to monitor. Your data stays in your GCP project, private by default. Generous free tier (1,000 retrievals/month free). The extraction and consolidation LLM handles deduplication, contradiction resolution, and fact merging automatically.
### Token-efficient and effective
Memories are extracted facts, not raw conversation logs. Only relevant memories are injected per turn via similarity search, not your entire history. The result: your agent gets better context in fewer tokens.
---
![Architecture](architecture.jpg)
> **Disclaimer**: This is **not** an officially supported Google product.
## What It Does
This plugin gives your OpenClaw agent **persistent, cross-session memory** using Vertex AI Memory Bank:
- **Auto-recall**: Before each turn, relevant memories are retrieved via similarity search and injected into context
- **Auto-capture**: After each turn, the last message pair is sent to Memory Bank for fact extraction and storage
- **Noise filtering**: Short/trivial exchanges are automatically skipped. Few-shot examples teach Memory Bank what to extract vs ignore
- **Relevance threshold**: Low-similarity memories are filtered out before injection, keeping context clean
- **File sync**: Workspace files (MEMORY.md, USER.md, SOUL.md, etc.) are automatically synced to Memory Bank with hash-based change tracking
- **Topic sync**: Memory topics, perspective, and few-shot examples are auto-configured on the Agent Engine instance at startup
- **Agent tools**: Search, forget, correct, and inspect memory stats directly from conversation
- **CLI tools**: Search, create (via consolidation pipeline), and delete memories directly from the command line
- **Managed infrastructure**: No vector DB, no local database. Vertex AI Memory Bank handles storage, embeddings, extraction, and retrieval
> **Note:** This plugin runs _alongside_ OpenClaw's built-in `memory-core`. It adds cloud-backed long-term memory on top.
## Prerequisites
1. **Google Cloud project** with billing enabled and Vertex AI API enabled
2. **Agent Engine instance** created for Memory Bank:
```bash
pip install google-cloud-aiplatform>=1.111.0
```
```python
import vertexai
client = vertexai.Client(project="YOUR_PROJECT", location="us-central1")
agent_engine = client.agent_engines.create()
print(agent_engine.api_resource.name)  # Save the reasoning engine ID
```
3. **gcloud CLI** authenticated:
```bash
gcloud auth application-default login
```
## Installation
### 1. Add plugin config to `openclaw.json`

============================================================
REPO: Dicklesworthstone/destructive_command_guard
============================================================
# dcg (Destructive Command Guard)
A high-performance hook for AI coding agents that blocks destructive commands before they execute, protecting your work from accidental deletion across Claude Code, Codex CLI, Gemini CLI, Copilot CLI, VS Code Copilot Chat, Cursor, Hermes Agent, Grok (xAI), Posit Assistant, and related tools.
**Supported:** [Claude Code](https://claude.ai/code), [Codex CLI 0.125.0+](https://github.com/openai/codex), [Gemini CLI](https://github.com/google-gemini/gemini-cli), [GitHub Copilot CLI](https://docs.github.com/en/copilot/concepts/agents/coding-agent/about-hooks), [VS Code Copilot Chat](https://code.visualstudio.com/docs/agent-customization/hooks), [Cursor IDE](https://cursor.com), [Hermes Agent](https://github.com/NousResearch/hermes-agent), [Posit Assistant](https://positron.posit.co/assistant/) (Positron/RStudio extension, standalone server, and `pa` terminal client), [Grok (xAI)](https://x.ai/news/grok-build-cli) (native `~/.grok/hooks/` plus Claude compatibility layer), [Antigravity CLI (`agy`)](https://antigravity.google) (native `~/.gemini/config/hooks.json` via `dcg install --agy`), [OpenCode](https://opencode.ai) (via [community plugin](https://github.com/aspiers/ai-config/blob/main/.config/opencode/plugins/dcg-guard.js)), [Pi](https://github.com/earendil-works/pi) (via [extension recipe](docs/pi-integration.md)), [Aider](https://aider.chat/) (limited—git hooks only), [Continue](https://continue.dev) (detection only)
```bash
curl -fsSL "https://raw.githubusercontent.com/Dicklesworthstone/destructive_command_guard/main/install.sh?$(date +%s)" | bash -s -- --easy-mode
```
```powershell
& ([scriptblock]::Create((irm "https://raw.githubusercontent.com/Dicklesworthstone/destructive_command_guard/main/install.ps1"))) -EasyMode -Verify
```
---
## TL;DR
**The Problem**: AI coding agents (Claude, Codex, Gemini, Copilot, etc.) occasionally run catastrophic commands like `git reset --hard`, `rm -rf ./src`, or `DROP TABLE users`—destroying hours of uncommitted work in seconds.
**The Solution**: dcg is a high-performance hook that intercepts destructive commands *before* they execute, blocking them with clear explanations and safer alternatives.
### Why Use dcg?
| Feature | What It Does |
|---------|--------------|
| **Zero-Config Protection** | Blocks dangerous git/filesystem commands out of the box |
| **50+ Security Packs** | Databases, Kubernetes, Docker, AWS/GCP/Azure, Terraform, and more |
| **Sub-Millisecond Latency** | SIMD-accelerated filtering—you won't notice it's there |
| **Heredoc/Inline Script Scanning** | Catches `python -c "os.remove(...)"` and embedded shell scripts |
| **Smart Context Detection** | Won't block `grep "rm -rf"` (data) but will block `rm -rf /` (execution) |
| **Rich Terminal Output** | Human-readable denial panels, rule context, and suggestions on stderr |
| **Agent-Safe Streams** | Machine-readable hook output stays on stdout while rich UI stays on stderr |
| **Native Codex Support** | Codex CLI 0.125.0+ receives a minimal stdout JSON denial that current clients enforce reliably |
| **Graceful Degradation** | Plain output for CI, pipes, dumb terminals, and no-color environments |
| **Scan Mode for CI** | Pre-commit hooks and CI integration to catch dangerous commands in code review |
| **Bounded Failure Policy** | Analysis timeouts become explicit review/block outcomes; malformed raw hook envelopes remain auditable and configurable |
| **Explain Mode** | `dcg explain "command"` shows exactly why something is blocked |
### Quick Example
```bash
# AI agent tries to run:
$ git reset --hard HEAD~5
# dcg intercepts and blocks:
════════════════════════════════════════════════════════════════
BLOCKED  dcg
────────────────────────────────────────────────────────────────
Reason:  git reset --hard destroys uncommitted changes
Command: git reset --hard HEAD~5
Tip: Consider using 'git stash' first to save your changes.
════════════════════════════════════════════════════════════════
```

============================================================
REPO: Dicklesworthstone/repo_updater
============================================================
Keep dozens (or hundreds) of repos in sync with a single command.<br/>
Clone missing repos, pull updates, detect conflicts, and get actionable resolution commands.
Meaningful exit codes for CI. JSON output for scripting. Non-interactive mode for automation.</em>
---
```bash
curl -fsSL "https://raw.githubusercontent.com/Dicklesworthstone/repo_updater/main/install.sh?ru_cb=$(date +%s)" | bash
# You can omit the `?ru_cb=...` once installed; it's just a cache-buster for the installer fetch.
```
**Or via Homebrew (macOS/Linux):**
```bash
brew install dicklesworthstone/tap/ru
```
---
## 🤖 Agent Quickstart (JSON/TOON)
**Use structured output in agent contexts.** stdout = data, stderr = diagnostics, exit 0 = success.
```bash
# Sync all repos (machine-readable)
ru sync --json
# Preview without changes
ru sync --dry-run --json
# Status only (no fetch)
ru status --no-fetch --json
# Machine-readable CLI documentation
ru robot-docs                   # All topics as JSON
ru robot-docs commands          # Command/flag reference
ru robot-docs quickstart        # Getting started guide
ru robot-docs examples          # Usage examples
ru robot-docs exit-codes        # Exit code reference
ru robot-docs formats           # Output format details
ru robot-docs schemas           # JSON schemas for command outputs
ru --schema                     # Shortcut for ru robot-docs schemas
```
## 🤖 Ready-made Blurb for AI Agents
> [!IMPORTANT]
> **Copy the blurb below to your project's `AGENTS.md`, `CLAUDE.md`, or `.cursorrules` file for AI agent integration with ru.**
````markdown
## ru Quick Reference for AI Agents
Syncs GitHub repos to local projects directory (clone missing, pull updates, detect conflicts).
```bash
ru sync                    # Sync all repos
ru sync --dry-run          # Preview only

============================================================
REPO: Dicklesworthstone/cass_memory_system
============================================================
# cass-memory
**Procedural memory for AI coding agents.**
Transforms scattered agent sessions into persistent, cross-agent memory—so every agent learns from every other agent's experience.
**One-liner install (Linux/macOS):**
```bash
curl -fsSL "https://raw.githubusercontent.com/Dicklesworthstone/cass_memory_system/main/install.sh?$(date +%s)" \
| bash -s -- --easy-mode --verify
```
**Or via package managers:**
```bash
# macOS/Linux (Homebrew)
brew install dicklesworthstone/tap/cm
# Windows (Scoop)
scoop bucket add dicklesworthstone https://github.com/Dicklesworthstone/scoop-bucket
scoop install dicklesworthstone/cm
```
---
## 🤖 Agent Quickstart (JSON)
**Always use `--json` in agent contexts.** stdout = data, stderr = diagnostics, exit 0 = success.
```bash
# 1) Get task-specific memory before you start
cm context "implement auth rate limiting" --json
# 2) See the minimum viable workflow
cm quickstart --json
# 3) Build the playbook (memory onboarding)
cm onboard status --json
cm onboard sample --fill-gaps --json
cm onboard read /path/to/session.jsonl --template --json
cm onboard mark-done /path/to/session.jsonl
```
## Table of Contents
- [Why This Exists](#-why-this-exists)
- [How It Works](#-how-it-works)
- [Key Features](#-key-features)
- [For AI Agents](#-for-ai-agents-the-most-important-section)
- [Installation](#-installation)
- [CLI Reference](#-cli-reference)
- [The ACE Pipeline](#-the-ace-pipeline)
- [Data Models](#-data-models)
- [Scoring Algorithm](#-scoring-algorithm)
- [Configuration](#-configuration)

============================================================
REPO: Dicklesworthstone/ntm
============================================================
# NTM - Named Tmux Manager
NTM turns `tmux` into a local control plane for multi-agent software development.
It combines session orchestration, graph-aware work triage, safety policy and approvals,
Agent Mail coordination, durable state capture, machine-readable robot surfaces, and a
local REST/WebSocket API in one Go binary.
```bash
curl -fsSL "https://raw.githubusercontent.com/Dicklesworthstone/ntm/main/install.sh?$(date +%s)" | bash -s -- --easy-mode
```
## TL;DR
### The Problem
Running several coding agents in parallel is easy to start and annoying to sustain.
Plain `tmux` gives you panes, but it does not give you durable coordination, work
selection, safety policy, approvals, history, replayable automation surfaces, or a
shared control model that both humans and agents can use.
### The Solution
NTM gives you a single local system for:
- spawning labeled multi-agent sessions in `tmux`
- sending work, interrupts, and follow-ups across panes
- triaging what to do next with `br` and `bv`
- coordinating agents with Agent Mail, file reservations, and assignments
- protecting dangerous operations with policy, approvals, and guards
- exposing the whole system through `--robot-*`, REST, SSE, WebSocket, and OpenAPI
- capturing state with checkpoints, timelines, audit trails, and pipeline state
### Why NTM
| Area | What NTM provides | Typical commands |
| --- | --- | --- |
| Session orchestration | Spawn, label, inspect, zoom, dashboard, palette | `ntm spawn`, `ntm dashboard`, `ntm palette` |
| Work intelligence | Graph-aware triage, next-step selection, impact analysis, assignment | `ntm work triage`, `ntm work next`, `ntm assign` |
| Coordination | Human overseer mail, inbox views, file reservations, worktrees | `ntm mail`, `ntm locks`, `ntm worktrees` |
| Safety | Destructive-command protection, policy editing, approval workflows | `ntm safety`, `ntm policy`, `ntm approve`, `ntm guards` |
| Durable operations | Checkpoints, timelines, audit logs, saved sessions, pipelines | `ntm checkpoint`, `ntm timeline`, `ntm audit`, `ntm pipeline` |
| Automation surfaces | Robot JSON, REST API, SSE/WebSocket streams, OpenAPI | `ntm --robot-snapshot`, `ntm serve`, `ntm openapi generate` |
## Quick Start
### Requirements
NTM is a pure Go project, but the runtime experience is intentionally integration-heavy.
- Required: `tmux`
- Required for agent spawning: whichever CLIs you want to run, typically Claude Code, Codex, Antigravity CLI, or Grok Build (Gemini CLI is supported as legacy)
- Optional but powerful: `br`, `bv`, Agent Mail, `cass`, `dcg`, `pt`
- Sanity check everything with `ntm deps -v`
### First Session
```bash

============================================================
REPO: Dicklesworthstone/slb
============================================================
# Simultaneous Launch Button (slb)
A cross-platform CLI that implements a **two-person rule** for running potentially destructive commands from AI coding agents.
When an agent wants to run something risky (e.g., `rm -rf`, `git push --force`, `kubectl delete`, `DROP TABLE`), `slb` requires peer review and explicit approval before execution.
## Why This Exists
Coding agents can get tunnel vision, hallucinate, or misunderstand context. A second reviewer (ideally with a different model/tooling) catches mistakes before they become irreversible.
`slb` is built for **multi-agent workflows** where many agent terminals run in parallel and a single bad command could destroy work, data, or infrastructure.
## Key Features
- **Risk-Based Classification**: Commands are automatically classified by risk level
- **Client-Side Execution**: Commands run in YOUR shell environment (inheriting AWS credentials, kubeconfig, virtualenvs, etc.)
- **Command Hash Binding**: Approvals bind to the exact command via SHA-256 hash
- **SQLite Source of Truth**: Project state lives in `.slb/state.db`
- **Agent Mail Integration**: Notify reviewers and track audit trails via MCP Agent Mail
- **TUI Dashboard**: Interactive terminal UI for human reviewers
## Risk Tiers
| Tier | Approvals | Auto-approve | Examples |
|------|-----------|--------------|----------|
| **CRITICAL** | 2+ | Never | `rm -rf /`, `DROP DATABASE`, `terraform destroy`, `git push --force` |
| **DANGEROUS** | 1 | Never | `rm -rf ./build`, `git reset --hard`, `kubectl delete`, `DROP TABLE` |
| **CAUTION** | 0 | After 30s | `rm file.txt`, `git branch -d`, `npm uninstall` |
| **SAFE** | 0 | Immediately | `rm *.log`, `git stash`, `kubectl delete pod` |
## Quick Start
### Installation
#### Recommended: Homebrew (macOS/Linux)
```bash
brew install dicklesworthstone/tap/slb
```
This method provides:
- Automatic updates via `brew upgrade`
- Dependency management
- Easy uninstall via `brew uninstall`
#### Windows: Scoop
```powershell
scoop bucket add dicklesworthstone https://github.com/Dicklesworthstone/scoop-bucket
scoop install dicklesworthstone/slb
```
#### Alternative: Direct Download
Download the latest release for your platform:
- [Linux x86_64](https://github.com/Dicklesworthstone/slb/releases/latest/download/slb-linux-amd64)
- [macOS Intel](https://github.com/Dicklesworthstone/slb/releases/latest/download/slb-darwin-amd64)
- [macOS ARM](https://github.com/Dicklesworthstone/slb/releases/latest/download/slb-darwin-arm64)
- [Windows](https://github.com/Dicklesworthstone/slb/releases/latest/download/slb-windows-amd64.exe)

============================================================
REPO: Dicklesworthstone/agentic_coding_flywheel_setup
============================================================
# Agentic Coding Flywheel Setup (ACFS)
> **From zero to fully-configured agentic coding VPS in 30 minutes.**
> A complete bootstrapping system that transforms a fresh Ubuntu VPS into a professional AI-powered development environment.
### Quick Install
```bash
curl -fsSL "https://raw.githubusercontent.com/Dicklesworthstone/agentic_coding_flywheel_setup/main/install.sh?$(date +%s)" | bash -s -- --yes --mode vibe
```
The installer is **idempotent**—if interrupted, simply re-run it. It will automatically resume from the last completed phase without prompts.
> **Production environments:** For stable, reproducible installs, pin to a tagged release or specific commit:
> ```bash
> # Preferred: use a tagged release (e.g., v0.5.0)
> curl -fsSL "https://raw.githubusercontent.com/Dicklesworthstone/agentic_coding_flywheel_setup/v0.5.0/install.sh" | bash -s -- --yes --mode vibe --ref v0.5.0
>
> # Alternative: pin to a specific commit SHA
> curl -fsSL "https://raw.githubusercontent.com/Dicklesworthstone/agentic_coding_flywheel_setup/abc1234/install.sh" | bash -s -- --yes --mode vibe --ref abc1234
> ```
> Tagged releases are tested and stable. Passing `--ref` ensures all fetched scripts use the same version.
---
## TL;DR
**ACFS** is a complete system for bootstrapping agentic coding environments:
**Why you'd care:**
- **Zero to Hero:** Takes complete beginners from "I have a laptop" to "I have Claude/Codex/Antigravity agents writing code for me on a VPS"
- **One-Liner Magic:** A single `curl | bash` command installs 30+ tools, configures everything, and sets up three AI coding agents
- **Vibe Mode:** Pre-configured for maximum velocity—passwordless sudo, dangerous agent flags enabled, optimized shell environment
- **Battle-Tested Stack:** Includes the complete Dicklesworthstone stack (10 tools + utilities) for agent orchestration, coordination, and safety
**What you get:**
- Modern shell (zsh + oh-my-zsh + powerlevel10k)
- All language runtimes (bun, uv/Python, Rust, Go)
- Three AI coding agents (Claude Code, Codex CLI, Antigravity CLI)
- Agent coordination tools (NTM, MCP Agent Mail, SLB)
- Cloud CLIs (Vault, Wrangler, Supabase, Vercel)
- And 20+ more developer tools
---
## The ACFS Experience
```mermaid
graph LR
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#e8f5e9', 'lineColor': '#90a4ae'}}}%%
subgraph user ["User's Machine"]
LAPTOP["Laptop"]
BROWSER["Browser"]
end

============================================================
REPO: herdrdev/herdr
============================================================
# herdr
English · <a href="README.zh-CN.md">简体中文</a>
---
https://github.com/user-attachments/assets/043ec09f-4bdd-41d5-aee0-8fda6b83e267
**the runtime your coding agents live on.**
- **always running** — herdr is a background server; the terminals live inside it. close the lid, drop the network, restart the machine — agents keep working and sessions come back. reattach from any terminal, or over ssh.
- **never hunt for the stuck one** — every pane is marked working, blocked, or idle. when an agent stops and needs an answer, herdr says so.
- **agent-native** — the cli and socket api are the same surface agents drive: spawn panes, prompt each other, wait until another agent is genuinely blocked. [agent skill →](https://herdr.dev/docs/agent-skill/)
- **runs what you already run** — claude code, codex, cursor, opencode, grok and the rest. herdr doesn't wrap or replace them, it just owns their terminals.
- **keyboard and mouse, both first-class** — tmux-style prefix keys *and* click, drag, split. pick per moment, not per tool.
- **plugins** — extend panes and workflows. [browse the marketplace →](https://herdr.dev/plugins/)
- **one rust binary, no electron** — runs in whatever terminal you already use.
---
## install
```bash
curl -fsSL https://herdr.dev/install.sh | sh
```
or `brew install herdr` · `mise use -g herdr` · windows beta: `powershell -ExecutionPolicy Bypass -c "irm https://herdr.dev/install.ps1 | iex"` · [binaries](https://github.com/herdrdev/herdr/releases)
then start it where the work lives:
```bash
herdr
```
run your agents, split panes, walk away. `ctrl+b q` detaches, `herdr` reattaches. [quick start →](https://herdr.dev/docs/quick-start/)
## docs
everything lives at [herdr.dev/docs](https://herdr.dev/docs/): [quick start](https://herdr.dev/docs/quick-start/) · [concepts](https://herdr.dev/docs/concepts/) · [supported agents](https://herdr.dev/docs/agents/) · [keyboard](https://herdr.dev/docs/keyboard/) · [configuration](https://herdr.dev/docs/configuration/) · [session state](https://herdr.dev/docs/session-state/) · [remote](https://herdr.dev/docs/persistence-remote/) · [integrations](https://herdr.dev/docs/integrations/) · [plugins](https://herdr.dev/docs/plugins/) · [socket api](https://herdr.dev/docs/socket-api/)
## thanks
[Terminal Trove](https://terminaltrove.com/) and every backer listed in [SPONSORS.md](./SPONSORS.md) — thank you 🐑
enterprise / partnership: hey@herdr.dev
## agent instructions
if you are an ai agent helping with this repository, read [`AGENTS.md`](./AGENTS.md) before making changes and read [`CONTRIBUTING.md`](./CONTRIBUTING.md) before opening issues or PRs.
## development
```bash
git clone https://github.com/herdrdev/herdr
cd herdr
cargo build --release
just test        # unit tests
just check       # formatting, tests, and maintenance checks
```
## license
Herdr is licensed under the [Apache License 2.0](LICENSE).

============================================================
REPO: cobusgreyling/loop-engineering
============================================================
# Loop Engineering
> **Stop prompting. Design the loop. Get a score.**
```bash
# Front door (recommended) — one binary for init + doctor + status
npx @cobusgreyling/loop init . --pattern daily-triage --tool grok
npx @cobusgreyling/loop doctor .
# Same as before (still fully supported — forks need not change)
npx @cobusgreyling/loop-init .
# Optional: also scaffold a versioned harness (harness-foundry)
npx @cobusgreyling/loop init . --with-foundry
```
`loop init` (or `loop-init`) scaffolds skills, state, and budget files, then prints your **Loop Ready** score and first loop command. `loop doctor` combines audit + sync + file checks into top-3 next actions. Swap `--tool` for `claude`, `codex`, or `opencode`. Use `--with-foundry` when you want the loop as a composable runtime stack. See [docs/cli-front-door.md](docs/cli-front-door.md).
Loop engineering replaces you as the person who prompts the agent — you design the system that does it instead.
**New here?** [Quickstart (5 min)](docs/QUICKSTART.md) · [Interactive picker](https://cobusgreyling.github.io/loop-engineering/#interactive)
For developers using Grok, Claude Code, Codex, Cursor, and other AI coding agents.
·
·
## Contents
- [Quickstart (5 min)](docs/QUICKSTART.md)
- [Quick Links](#quick-links)
- [Why This Matters](#why-this-matters)
- [The Five Building Blocks + Memory](#the-five-building-blocks--memory)
- [Patterns](#patterns)
- [Getting Started (5 minutes)](#getting-started-5-minutes)
- [Examples by Tool](#examples-by-tool)
- [Operating & Safety](#operating--safety)
- [Caveats](#caveats)
- [Help wanted](#help-wanted)
- [Contributing](#contributing)
- [Sources](#sources)
- [License](#license)
## Quick Links
| Start here | Description |
|------------|-------------|
| [Quickstart (5 min)](docs/QUICKSTART.md) | `loop init` → `loop doctor` → first loop — **start here if you just landed** |
| [CLI front door](docs/cli-front-door.md) | Unified `@cobusgreyling/loop` — old packages stay open |
| [Loop Engineering essay](https://cobusgreyling.substack.com/p/loop-engineering) | The concept, primitives, and Grok mapping — read for the why |
| [Pattern Picker](docs/pattern-picker.md) | Which loop to run first — **start here if unsure** |
| [Primitives Matrix](docs/primitives-matrix.md) | Cross-tool loop primitive mapping — bookmark this |
| [Loop Design Checklist](docs/loop-design-checklist.md) | Ship readiness rubric |
| [Patterns](patterns/README.md) | 7 production patterns + [interactive picker](https://cobusgreyling.github.io/loop-engineering/#interactive) |

============================================================
REPO: herdrdev/herdr-nix
============================================================
# herdr-nix
Official Nix packaging for Herdr's prebuilt GitHub Release binaries.
## Contents
- [Why this exists](#why-this-exists)
- [Usage](#usage)
- [Configuration / API](#configuration--api)
- [Staying current](#staying-current)
- [Contributing](#contributing)
- [Provenance](#provenance)
- [Licensing](#licensing)
## Why this exists
herdr's own [documented Nix install instructions](https://herdr.dev/docs/install/#install-with-nix)
point at its source flake (`nix run|build|profile install github:herdrdev/herdr/vX.Y.Z`) — which
builds herdr from source, pulling in the full Rust + Zig toolchain, on every install and every
update. There's no binary cache behind it, so that source build repeats for every consumer,
every time. That's especially unwelcome in a devenv context, where the shell can rebuild often.
This repo instead fetches herdr's own prebuilt, per-platform release binaries
(`herdr-linux-x86_64`, `herdr-linux-aarch64`, `herdr-macos-x86_64`, `herdr-macos-aarch64` —
published by herdr's own `release.yml` on every tagged release) and wraps them in a Nix
derivation. No compilation, no toolchain, just a hash-verified download.
After a version update passes review and CI, builds from protected `main` are pushed to the
public Cachix cache (`herdr`). Pull requests never receive cache credentials.
## Usage
### With devenv
Add the flake input and pull the `herdr` Cachix cache declaratively — devenv wires the
substituter and trusted public key for you, no manual `nix.conf` editing:
```yaml
# devenv.yaml
inputs:
herdr-nix:
url: github:herdrdev/herdr-nix
```
```nix
# devenv.nix
{ pkgs, inputs, ... }:
{
cachix.pull = [ "herdr" ];
packages = [
inputs.herdr-nix.packages.${pkgs.stdenv.system}.default
];
}

============================================================
REPO: cobusgreyling/fleet-engineering
============================================================
# Fleet Engineering
> **You don’t have an agent problem. You have a population problem. Get a Fleet Ready score.**
**Fleet engineering is replacing ad-hoc populations of agents with an accountable organization. You design the registry, identity, permissions, inbox, audit trail, and sovereign control that let many loops run safely across a team.**
```bash
npx @cobusgreyling/fleet-init .
npx @cobusgreyling/fleet-audit . --suggest
# Optional: attach a loop layer
npx @cobusgreyling/fleet-init . --with-loop daily-triage
```
A fleet is not "many agents." A fleet is a **governed population** where every action answers one sentence:
> *Which agent did it, with what authority, against what task, evidenced by what?*
## Start here (pick your pain)
| Symptom | Start with |
|---------|------------|
| "We have agents everywhere" | [Team Agent Registry](patterns/team-agent-registry.md) |
| Agents act without oversight | [Shared Inbox HITL](patterns/shared-inbox-hitl.md) |
| Token bill surprise | [Fleet Budget Guard](patterns/fleet-budget-guard.md) |
| "Who did this?" in an incident | [Cross-Agent Audit](patterns/cross-agent-audit.md) |
| Already have loops | [Fleet + Loop starter](starters/fleet-plus-loop/) |
Unsure? Use the [Pattern Picker](docs/pattern-picker.md).
## The Stack
| Layer | Unit of design | Question |
|-------|----------------|----------|
| [Context Engineering](https://cobusgreyling.medium.com/context-engineering-a34fd80ccc26) | One inference | What does the model see? |
| [Harness Engineering](https://cobusgreyling.substack.com/p/the-rise-of-ai-harness-engineering) | One agent run | How does a single run execute safely? |
| [Loop Engineering](https://github.com/cobusgreyling/loop-engineering) | One autonomous system | What keeps prompting and verifying over time? |
| **Fleet Engineering** | Many agents + loops | How do populations coordinate and govern at scale? |
## Quick Links
| Start here | Description |
|------------|-------------|
| [**Fleet Ready Score**](docs/fleet-ready-score.md) | F0–F3 scoring contract (`fleet-audit`) — same ritual as Loop Ready |
| [**Relaunch playbook**](docs/LAUNCH.md) | Growth pack: positioning, 7-day ship plan, metrics |
| [Concepts](docs/concepts.md) | Fleet vs loop vs harness — **read this first** |
| [Assistant vs Claw](https://github.com/cobusgreyling/assistant-vs-claw) | Runnable identity models (on-behalf-of vs fixed credentials) |
| [Maturity Model](docs/maturity-model.md) | F0–F3 phased rollout |
| [Five Concerns](docs/five-concerns.md) | Topology, choreography, identity, economics, sovereign control |
| [Accountability Test](docs/accountability-test.md) | The one-sentence standard for real fleets |
| [Pattern Picker](docs/pattern-picker.md) | Which fleet pattern to adopt first |
| [Failure Modes](docs/failure-modes.md) | Incident-style catalog |
| [Primitives Matrix](docs/primitives-matrix.md) | DIY vs LangSmith vs Cursor vs Claude Code vs Grok |
| [Fleet vs Frameworks](docs/fleet-vs-frameworks.md) | Governance vs LangGraph / CrewAI |

============================================================
REPO: cobusgreyling/goal-engineering
============================================================
# Goal Engineering
**Goal engineering is replacing one-shot prompts with verifiable, run-until-done objectives.** You define what "done" means, Grok Build works across turns until the condition holds — and reports progress via `/goal` and `update_goal`.
This is the **canonical public reference** for [Grok Build CLI](https://x.ai)'s `/goal` feature.
## The One-Line Definition
A **goal** is a single autonomous objective with a verifiable completion condition. Unlike a loop (which fires on a schedule), a goal **persists across turns** until Grok marks it complete, blocked, or you pause it.
```
Prompt  = one turn, one answer
Loop    = recurring discovery + triage on a cadence
Goal    = run until done (or blocked / paused)
```
## Quick Start (2 minutes)
```bash
# Unified CLI (recommended)
npx @cobusgreyling/goal doctor . --suggest
npx @cobusgreyling/goal init . --pattern tests-green --tool grok
# Or individual packages
npx @cobusgreyling/goal-audit . --suggest
npx @cobusgreyling/goal-init . --pattern tests-green --tool grok --lang python
```
In Grok Build:
```
/goal All tests pass — goal-verifier before completed: true
```
Manage the active goal:
```
/goal status    # check progress
/goal pause     # pause without clearing
/goal resume    # continue
/goal clear     # end goal mode
```
**Replay a full session:** [examples/golden-path/SESSION.md](examples/golden-path/SESSION.md)
## Contents
- [Why Goals Matter](#why-goals-matter)
- [Grok Build API](#grok-build-api)
- [The Four Primitives](#the-four-primitives)
- [Patterns](#patterns)
- [Getting Started](#getting-started-5-minutes)
- [Goal vs Loop](#goal-vs-loop)
- [Operating & Safety](#operating--safety)
- [Tools](#tools)
- [CI Integration](#ci-integration)

============================================================
REPO: cobusgreyling/llm-wiki
============================================================
# LLM Wiki
![LLM Wiki — A pattern for a knowledge base that builds and maintains itself](assets/header.jpg)
A **reference implementation** of [Andrej Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — a compounding personal knowledge base where the LLM maintains structured, interlinked markdown instead of re-deriving everything from raw chunks on every question.
> *"Obsidian is the IDE; the LLM is the programmer; the wiki is the codebase."*
## Use this template
This repo is a [GitHub template](https://github.com/cobusgreyling/llm-wiki/generate). Click **Use this template** → create your repo → then:
```bash
pip install llm-wiki
wiki init my-wiki --git
cd my-wiki
wiki init-check
```
Or install the toolkit only and scaffold locally:
```bash
pip install llm-wiki
wiki init my-wiki --git
```
## Why not RAG?
Classic RAG retrieves fragments at query time. Nothing accumulates. Ask a question that synthesizes five documents and the LLM rediscovers the pieces every time.
**LLM Wiki is different.** When you add a source, the agent reads it, extracts key information, and integrates it into a persistent wiki — updating entity pages, revising synthesis, flagging contradictions. Knowledge is **compiled once and kept current**.
| | RAG | Notes app | LLM Wiki |
|---|-----|-----------|----------|
| **Knowledge accumulates** | No — re-retrieve each query | Manual linking | Yes — agent integrates on ingest |
| **Cross-document synthesis** | Fragment assembly at query time | You connect the dots | Pre-built in synthesis + entity pages |
| **Citations** | Chunk references | None by default | Wikilinks to source pages |
| **Agent role** | Retrieve + answer | None | Maintain the wiki (ingest, lint, update) |
| **Human role** | Curate corpus | Write everything | Curate `raw/` + ask questions |
## See it in action
**Terminal demo** — CLI search, ingest status, lint, and expand in ~30 seconds:
Play locally: `asciinema play assets/demo.cast` (after `pip install asciinema`)
**Ingest flow** — one source update touches the whole wiki:
![Ingest workflow](assets/ingest-flow.svg)
**Demo graph** — two sources link to 15+ pages ([`examples/demo/`](examples/demo/)):
![Demo wiki graph](assets/demo-graph.svg)
### From a repo clone
> **Note:** This repository is the **toolkit**, not a wiki root. Example wikis live under `examples/`. Always pass `--root` or use `make` shortcuts:
```bash
git clone https://github.com/cobusgreyling/llm-wiki.git
cd llm-wiki
pip install -e ".[dev,mcp]"
make demo-search          # wiki --root examples/demo search "memex"

============================================================
REPO: cobusgreyling/agent-skills
============================================================
# Agent Skills
![Skills cross-link graph](assets/header.png)
A curated collection of [Agent Skills](https://agentskills.io/home) — Markdown-based instructions that give AI coding agents (Claude Code, Gemini CLI, Cursor, Codex, etc.) durable domain expertise instead of one-shot prompting.
Opinionated, written from production triage of real agent failures. Each skill is a short, declarative brief: when to use it, the decision flow, the anti-patterns, the hard line that gates merge.
## What makes this different
Most "awesome agent" lists catalogue frameworks and papers. These skills change agent **behaviour** on the same prompt.
- **From production triage.** Every brief encodes a failure pattern seen — or shipped — at least three times.
- **Each skill has a hard line.** One sentence that gates merge, deploy, or approval. Not advice; a rule.
- **Anti-patterns are named, not hinted at.** The skill watches for them on every prompt that fires it.
- **Decision flows are numbered and top-down.** The agent walks the checklist before recommending anything.
- **Cross-linked.** Skills point at the next decision along the path (architecture → cost → latency → eval → observability → guardrails).
If you want a survey of frameworks, start with an awesome-list. If you want briefs that change what the agent says on the same prompt, start here.
## Proof, not just briefs
Each skill ships with a `TRANSCRIPT.md` — one realistic prompt, the agent's response without the skill loaded, the agent's response with it loaded, and the diff annotated. Read those before deciding which skills to install.
Five skills ship a reproducible 20-task eval under [`eval/`](./eval/):
- [`agent-architecture-patterns`](./eval/agent-architecture-patterns/)
- [`agent-cost-modeling`](./eval/agent-cost-modeling/)
- [`guardrails-and-safety`](./eval/guardrails-and-safety/)
- [`prompt-caching`](./eval/prompt-caching/)
- [`tool-use-schema-design`](./eval/tool-use-schema-design/)
Each has methodology, prompts, rubric, anchored examples, runner, scorer, and a results template you can run against your own agent.
Browse [`FAILURES.md`](./FAILURES.md) for the failure-pattern → skill index — the production failures each skill exists to catch.
## Installation
The `SKILL.md` format is **Claude Code-native** (matches the published Agent Skills format). For other agents, the **content is portable** — only the loading mechanism differs.
| Agent | Native skill support | How to install |
|-------|----------------------|----------------|
| Claude Code | Yes (Agent Skills) | Symlink into `~/.claude/skills/` |
| Gemini CLI | No — load as context | `@`-reference each `SKILL.md` from `GEMINI.md` |
| Cursor | No — convert to Rule | Copy `SKILL.md` into `.cursor/rules/<name>.mdc`, add `alwaysApply: false` |
| Codex | No — load via system prompt | Include `SKILL.md` content under a heading in `AGENTS.md` |
### Claude Code (native)
```bash
git clone https://github.com/cobusgreyling/agent-skills.git
cd agent-skills
mkdir -p ~/.claude/skills
for s in skills/*/; do
ln -sf "$PWD/$s" ~/.claude/skills/
done
```
Restart Claude Code. Skills appear in the available-skills list and fire on matching prompts.
Selective install: symlink only the skills you want — `ln -sf "$PWD/skills/agent-architecture-patterns" ~/.claude/skills/`.

============================================================
REPO: cobusgreyling/claude-agent-teams
============================================================
![Description](images/agent-teams-claude-code.png)
# Claude Code Agent Teams — Multi-Agent Orchestration From Your Terminal
Your AI assistant just became a team lead.
---
## The First Thing That Confused Me
When I first looked at Agent Teams, I assumed each agent would be defined somewhere — a config file, a markdown spec, some kind of schema. The examples show detailed prompts describing each teammate's role, responsibilities, and file ownership. It looked like a declarative system.
It's not. There is no agent definition file. The markdown examples are just prompts you paste into Claude Code. The entire orchestration mechanism is:
1. **One config switch** in `settings.json` that turns the feature on
2. **A natural language prompt** that describes the team you want
3. **Claude Code** handles the spawning, task management, and messaging
No YAML. No agent schema. No workflow definition. You describe a team conversationally, and Claude Code builds it.
That immediately raised a second question: if the agents are defined by the prompt, why define them at all? Why not just say *"this PR needs a review, handle it"* and let Claude decide what specialists to spawn?
You can. It works. But the reason the examples are prescriptive is control.
When you define the agents, you know exactly what's running and what it costs — each teammate is a separate Claude instance. You prevent Claude from over-spawning eight teammates when three would do. You control file ownership. And you can shape the team dynamic — collaborative, adversarial, or independent.
When you let Claude decide, it might under-scope or over-scope. You lose the ability to set the structure. It's the same tradeoff as managing a real team. You *could* say "here's the problem, figure it out." But more often you want to say "I need these three roles, here's how I want you to coordinate."
In practice there's a spectrum:
- **Prescriptive:** *"Spawn 3 teammates: security, performance, tests"*
- **Guided:** *"Review this PR with multiple specialists, max 4 teammates"*
- **Open:** *"This PR needs review. Handle it."*
All three work. Prescriptive for expensive or risky tasks. Open for quick exploratory ones. Once that clicked, the rest of Agent Teams made sense.
---
In a [previous post](https://cobusgreyling.medium.com/create-custom-agentic-workflows-with-claude-code-ee49805bb28b) I walked through creating custom agentic workflows with Claude Code — a supervisor agent coordinating specialised subagents for data processing, code generation, documentation, and analysis. That setup demonstrated something important: you could describe the agentic workflow you wanted, and Claude Code would create the framework, file structure, code, and documentation.
Subagents were a meaningful step forward from single-session prompting. But they had a constraint. Subagents report results back to the main agent. They never talk to each other. If Agent A discovers something that Agent B needs, the main agent has to relay it. Every insight routes through one bottleneck.
With the release of **Opus 4.6**, Anthropic shipped something that removes that bottleneck entirely: **Agent Teams**.
---
## What Changed
I wrote about the [5 Levels of AI Agents](https://cobusgreyling.medium.com/5-levels-of-ai-agents-updated-0ddf8931a1c6) previously, and Anthropic's own position that [coding agents are becoming the universal everything agent](https://cobusgreyling.medium.com/anthropic-says-coding-agents-are-becoming-the-universal-everything-agent-039f9bb709fc). Agent Teams is the infrastructure that makes that practical.
![Description](images/5-levels-ai-agents.jpg)
The difference between subagents and Agent Teams is communication.
![Description](images/agents-vs-chains.jpg)
**Subagents** run within a single session. They do focused work and return a result. They cannot message each other, share discoveries mid-task, or coordinate without the main agent acting as intermediary.
**Agent Teams** removes that constraint. Teammates message each other directly. They share a task list. They claim work, coordinate, and even debate each other — all without routing through a lead.
|                   | Subagents                                        | Agent Teams                                         |
| :---------------- | :----------------------------------------------- | :-------------------------------------------------- |
| **Context**       | Own context window; results return to caller     | Own context window; fully independent               |
| **Communication** | Report results back to the main agent only       | Teammates message each other directly               |
| **Coordination**  | Main agent manages all work                      | Shared task list with self-coordination             |
| **Best for**      | Focused tasks where only the result matters      | Complex work requiring discussion and collaboration |
| **Token cost**    | Lower: results summarised back to main context   | Higher: each teammate is a separate Claude instance |
This matters because the most interesting problems are not decomposable into isolated subtasks. Code review requires cross-referencing security with performance. Debugging requires adversarial hypothesis testing. Feature implementation requires frontend, backend, and tests to stay in sync. These are coordination problems, and coordination requires communication between workers — not just reporting to a manager.
As I noted when covering the [Moltbook studies](https://cobusgreyling.medium.com/moltbook-the-illusion-of-an-ai-society-6bd21ee8e88d), AI agents broadcasting without conversing produces shallow outcomes. Agent Teams is Anthropic's answer to that exact problem in the development context.

============================================================
REPO: cobusgreyling/outerloop
============================================================
# outerloop
**Own the Outer Loop. Evidence → Verdict → Answerability.**
Governance primitives for agentic engineering — any harness, any team size.
Companion to [loop-engineering](https://github.com/cobusgreyling/loop-engineering) (inner loops) and [harness-foundry](https://github.com/cobusgreyling/harness-foundry) (composable harness runtime). Works standalone with Cursor, Claude Code, or custom agents.
## The loop in 60 seconds
```
Agent run  →  Evidence package  →  Human verdict  →  Ledger  →  Answerability
(inner)         (what happened)      (why ship/block)   (provenance)  (reconstruct why)
```
Humans define constraints and taste. Agents produce evidence. Humans issue verdicts with captured rationale. The system guarantees you can explain **why** something shipped.
→ [Core concepts](docs/concepts.md) (5 min) · [vs alternatives](docs/vs-alternatives.md)
## Try it now
```bash
npx @cobusgreyling/outerloop init
npx @cobusgreyling/outerloop evidence package --run-id latest
npx @cobusgreyling/outerloop verdict issue \
--evidence-id <id> --decision ship --rationale "Tests pass; scope reviewed."
npx @cobusgreyling/outerloop ledger why <id>
```
Or clone and run the full demo:
```bash
git clone https://github.com/cobusgreyling/outerloop.git
cd outerloop && pnpm install && pnpm build && pnpm demo
```
```
=== 1. Package evidence ===
Run: 2026-07-08T10:01:59Z | Risk: 4/10
Evidence ID: 97fb7345-6849-41a1-bb68-f9446bf6824b
=== 2. Issue verdict ===
✓ Verdict recorded: ship
=== 3. Reconstruct answerability ===
# Answerability Chain: 97fb7345-...
## Verdict
- Decision: **ship**
- Rationale: Report-only daily triage: no code changes, tests pass.
```
→ [QUICKSTART.md](./QUICKSTART.md)
## Choose your harness
| Persona | Get started |
|---------|-------------|
| **Any agent** | `npx @cobusgreyling/outerloop init` |
