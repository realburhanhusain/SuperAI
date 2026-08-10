
============================================================
REPO: agentgateway/agentgateway
============================================================
The <strong>first complete</strong> connectivity solution for Agentic AI.
---
**Agentgateway** is an open source proxy built on AI-native protocols ([MCP](https://modelcontextprotocol.io/introduction) & [A2A](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/)) that provides drop-in security, observability, and governance for agent-to-LLM, agent-to-tool, and agent-to-agent communication across any framework and environment.
## Intro to Agentgateway Video
## Key Features
- **LLM Gateway**<br>
Route traffic to major LLM providers (OpenAI, Anthropic, Gemini, Bedrock, and more) through a unified OpenAI-compatible API with budget and spend controls, prompt enrichment, load balancing, and failover.
- **MCP Gateway**<br>
Connect LLMs to tools and external data sources via MCP with tool federation, stdio/HTTP/SSE/Streamable HTTP transports, OpenAPI integration, and OAuth authentication.
- **A2A Gateway**<br>
Enable secure agent-to-agent communication using A2A, with capability discovery, modality negotiation, and task collaboration.
- **Inference Routing**<br>
Intelligent routing to self-hosted models using Kubernetes Inference Gateway extensions, with decisions based on GPU utilization, KV cache, LoRA adapters, and queue depth.
- **Guardrails**<br>
Multi-layered content filtering with regex, OpenAI moderation, AWS Bedrock Guardrails, Google Model Armor, and custom webhooks.
- **Security & Observability**<br>
Auth (JWT, API keys, OAuth), fine-grained RBAC with CEL policy engine, rate limiting, TLS, and OpenTelemetry metrics/logs/tracing.
## Getting Started
- [Standalone Quickstart](https://agentgateway.dev/docs/standalone/latest/quickstart) — Get started with agentgateway in minutes.
- [Kubernetes Quickstart](https://agentgateway.dev/docs/kubernetes/latest/quickstart) — Deploy on Kubernetes using the built-in controller and Gateway API.
## Documentation

============================================================
REPO: coleam00/Archon
============================================================
The first open-source harness builder for AI coding. Make AI coding deterministic and repeatable.
---
Archon is a workflow engine for AI coding agents. Define your development processes as YAML workflows - planning, implementation, validation, code review, PR creation - and run them reliably across all your projects.
Like what Dockerfiles did for infrastructure and GitHub Actions did for CI/CD - Archon does for AI coding workflows. Think n8n, but for software development.
## Why Archon?
When you ask an AI agent to "fix this bug", what happens depends on the model's mood. It might skip planning. It might forget to run tests. It might write a PR description that ignores your template. Every run is different.
Archon fixes this. Encode your development process as a workflow. The workflow defines the phases, validation gates, and artifacts. The AI fills in the intelligence at each step, but the structure is deterministic and owned by you.
- **Repeatable** - Same workflow, same sequence, every time. Plan, implement, validate, review, PR.
- **Isolated** - Every workflow run gets its own git worktree. Run 5 fixes in parallel with no conflicts.
- **Fire and forget** - Kick off a workflow, go do other work. Come back to a finished PR with review comments.
- **Composable** - Mix deterministic nodes (bash scripts, tests, git ops) with AI nodes (planning, code generation, review). The AI only runs where it adds value.
- **Portable** - Define workflows once in `.archon/workflows/`, commit them to your repo. They work the same from CLI, Web UI, Slack, Telegram, or GitHub.
## What It Looks Like
Here's an example of an Archon workflow that plans, implements in a loop until tests pass, gets your approval, then creates the PR:
```yaml
# .archon/workflows/build-feature.yaml
nodes:
- id: plan
prompt: "Explore the codebase and create an implementation plan"
- id: implement
depends_on: [plan]

============================================================
REPO: getkimchi/kimchi
============================================================
# kimchi
A coding agent CLI powered by [kimchi](https://kimchi.dev/). Built on the [pi-mono](https://github.com/badlogic/pi-mono) coding agent SDK, kimchi gives you an AI-powered development assistant in your terminal that connects to kimchi's LLM infrastructure.
![kimchi](./kimchi.png)
## Quick start
Install the latest release:
**Homebrew (macOS / Linux):**
```bash
brew install getkimchi/tap/kimchi
```
**Install script (macOS / Linux):**
```bash
curl -fsSL https://github.com/getkimchi/kimchi/releases/latest/download/install.sh | bash
```
**PowerShell (Windows):**
```powershell
irm https://github.com/getkimchi/kimchi/releases/latest/download/install.ps1 | iex
```
Then configure your API key and launch:
```bash
kimchi setup   # one-time interactive setup
kimchi         # launch the coding agent

============================================================
REPO: ghostty-org/ghostty
============================================================
Fast, native, feature-rich terminal emulator pushing modern features.
A native GUI or embeddable library via <code>libghostty</code>.
·
·
·
·
## About
Ghostty is a terminal emulator that differentiates itself by being
fast, feature-rich, and native. While there are many excellent terminal
emulators available, they all force you to choose between speed,
features, or native UIs. Ghostty provides all three.
**`libghostty`** is a cross-platform, zero-dependency C and Zig library
for building terminal emulators or utilizing terminal functionality
(such as style parsing). Anyone can use `libghostty` to build a terminal
emulator or embed a terminal into their own applications. See
[Ghostling](https://github.com/ghostty-org/ghostling) for a minimal complete project
example or the [`examples` directory](https://github.com/ghostty-org/ghostty/tree/main/example)
for smaller examples of using `libghostty` in C and Zig.
For more details, see [About Ghostty](https://ghostty.org/docs/about).
## Download
See the [download page](https://ghostty.org/download) on the Ghostty website.

============================================================
REPO: gitbutlerapp/gitbutler
============================================================
GitButler is a modern Git-based version control interface with both a GUI and CLI built from the ground up for AI-powered workflows.
![BLUESKY][s8]][l8] [![DISCORD][s2]][l2]
[l0]: https://github.com/gitbutlerapp/gitbutler/actions/workflows/push.yaml
[l1]: https://twitter.com/intent/follow?screen_name=gitbutler
[l2]: https://discord.gg/MmFkmaJ42D
[l3]: https://www.instagram.com/gitbutler/
[l5]: https://www.youtube.com/@gitbutlerapp
[l7]: https://deepwiki.com/gitbutlerapp/gitbutler
[l8]: https://bsky.app/profile/gitbutler.com
GitButler is a powerful new Git-based version control system, designed from scratch to be simple, powerful and flexible. It is designed for ease of use and modern agentic workflows.
It features stacked branches, parallel branches, unlimited undo, easy commit mutations, forge integrations and more.
Works instantly in any existing Git repo as a friendlier and more powerful drop-in Git user interface replacement - for you and your agents.
## Main Features
Why use GitButler instead of vanilla Git? What a great question.
- **Stacked Branches** ([gui](https://docs.gitbutler.com/features/branch-management/stacked-branches), [cli](https://docs.gitbutler.com/cli-guides/cli-tutorial/branching-and-commiting#stacked-branches))
- Effortlessly create branches stacked on other branches. Amend or edit any commit easily with automatic restacking.
- **Parallel Branches** ([gui](https://docs.gitbutler.com/features/branch-management/virtual-branches), [cli](https://docs.gitbutler.com/cli-guides/cli-tutorial/branching-and-commiting#parallel-branches))
- Organize work on multiple branches simultaneously, rather than constantly switching branches.
- **Easy Commit Management** ([gui](https://docs.gitbutler.com/features/branch-management/commits), [cli](https://docs.gitbutler.com/cli-guides/cli-tutorial/rubbing))
- Uncommit, reword, amend, move, split and squash commits by dragging and dropping or simple CLI commands. Forget about `rebase -i`, you don't need it anymore.
- **Undo Timeline** ([gui](https://docs.gitbutler.com/features/timeline), [cli](https://docs.gitbutler.com/cli-guides/cli-tutorial/operations-log))

============================================================
REPO: openclaw/openclaw
============================================================
# OpenClaw 🦞 — Your assistant, on your devices, in your chats
OpenClaw is a personal AI assistant that runs on your devices and meets you in the channels you already use. It is designed for a single operator and connects models, tools, messaging channels, and optional companion apps through one Gateway.
[Website](https://openclaw.ai) · [Docs](https://docs.openclaw.ai) · [Getting started](https://docs.openclaw.ai/start/getting-started) · [Showcase](https://docs.openclaw.ai/start/showcase) · [FAQ](https://docs.openclaw.ai/help/faq) · [Vision](VISION.md) · [DeepWiki](https://deepwiki.com/openclaw/openclaw)
## Install
The installer supports macOS, Linux, and Windows. It provisions a supported Node.js runtime when needed.
```bash
# macOS / Linux / WSL2
curl -fsSL https://openclaw.ai/install.sh | bash
```
```powershell
# Windows PowerShell
iwr -useb https://openclaw.ai/install.ps1 | iex
```
Already manage Node.js? Install the published package instead (Node 22.22.3+, 24.15+, or 25.9+):
```bash
npm install -g openclaw@latest
```
See the [installation guide](https://docs.openclaw.ai/install) for npm 12 lifecycle-script requirements, Docker, Nix, and other deployment paths.
## Quick start
```bash
openclaw onboard --install-daemon

============================================================
REPO: pingdotgg/t3code
============================================================
# T3 Code
T3 Code is an "agent harness control surface". It enables control of the agents on your machine with a best-in-class mobile app ([iOS](https://apps.apple.com/us/app/t3-code-remote-claude-more/id6787819824), [Android](https://play.google.com/store/apps/details?id=com.t3tools.t3code)), [web app](https://app.t3.codes) and [Electron-based desktop app](https://t3.codes).
Works with your subscriptions on Claude Code, Codex, Cursor, Grok Build, and OpenCode. If they're set up on your computer, T3 Code can control them.
## "Wait, what are you selling me?"
Nothing. We built T3 Code because we wanted the best possible development experience with agents. We were inspired by existing solutions like the Codex desktop app, Conductor, Claude Desktop and Cursor Glass, but none met our bar.
We wanted something performant, remote-ready, and truly open. If we ever go the wrong direction, we want you to have everything you need to fork and build the editor that you want.
## Installation
> [!WARNING]
> T3 Code currently supports Codex, Claude, Cursor, Grok Build and OpenCode. Install and authenticate at least one provider before use:
>
> - Codex: install [Codex CLI](https://developers.openai.com/codex/cli) and run `codex login`
> - Claude: install [Claude Code](https://claude.com/product/claude-code) and run `claude auth login`
> - Cursor: install [Cursor CLI](https://cursor.com/cli) and run `agent login`
> - Grok Build: install [Grok Build CLI](https://x.ai/cli) and run `grok login`
> - OpenCode: install [OpenCode](https://opencode.ai) and run `opencode auth login`
### Try it out (install-free)
The easiest way to test T3 Code is to run the server in your terminal (requires Node.js 22.16+, 23.11+, or 24.10+):
```bash
npx t3@latest
```
This will launch T3 Code's backend on your machine as well as the local web app to control your agents.

============================================================
REPO: rohitg00/agent-doctor
============================================================
# agent-doctor
Diff-aware quality gate for AI-assisted code changes.
```sh
npx -y agent-doctor@latest .
```
`agent-doctor` reads the diff, builds a risk model, discovers the cheapest relevant validations, audits agent instructions and skills, ingests available evidence, and prints a report that is useful locally and in CI. It does not claim an agent was "safe" — it tells you what was proven, what was not proven, and what to run next.
> Status: 0.x. MVP focuses on TypeScript / JavaScript monorepos and skill-library checks. Full plan in [`docs/PLAN.md`](docs/PLAN.md).
## Install
Per-run, no install:
```sh
npx -y agent-doctor@latest --diff main --plan-only
```
Global:
```sh
npm install -g agent-doctor
agent-doctor --diff main --plan-only
```
## Quick start
```sh
agent-doctor --diff main --plan-only      # print the validation plan
agent-doctor --diff main --run            # run discovered checks

============================================================
REPO: rohitg00/agentbrain
============================================================
# Agent Brain
Commands, skills, schemas, templates, evals, and proof gates that make agent work inspectable.
## Supported Agent Runtimes
Agent Brain is a portable harness you add to a repository. It does not run your
agent. It gives any file-reading coding agent a state machine, command specs,
skills, schemas, evals, and handoff contracts so work moves through evidence,
artifacts, verification, review, and learning instead of chat momentum.
It is not a decorative prompt pack, an IDE plugin, or another agent framework.
Bring the coding agent you already use. Agent Brain supplies the operating
discipline around the model.
Use it when you want an agent to stop guessing, pick the right lifecycle state,
produce the right artifact, and prove the work before it claims progress.
Works with agent runtimes that can read files and follow repository-local
instructions: terminal coding agents, IDE agents, subagent runners,
approval-gated runtimes, and custom CLI or hosted agents.
Most agent failures are not syntax errors. They are judgment errors:
- building the wrong thing,
- trusting stale context,
- skipping tests,
- accepting vague requirements,
- shipping without rollback,

============================================================
REPO: rohitg00/agentmemory
============================================================
Your coding agent remembers everything. No more re-explaining.
Built on <a href="https://github.com/iii-hq/iii">iii engine</a>
Persistent memory for Claude Code, GitHub Copilot CLI, Cursor, Gemini CLI, Codex CLI, Hermes, OpenClaw, pi, OpenCode, and any MCP client.
---
## Install
Fastest path if you use a coding agent: hand it this one instruction and it installs, wires, and verifies agentmemory end to end.
> Retrieve and follow the instructions at: https://raw.githubusercontent.com/rohitg00/agentmemory/main/INSTALL_FOR_AGENTS.md
On Windows the fast path is WSL2. Native Windows engine setup is manual (about 10 to 20 minutes) and `agentmemory connect` is currently unsupported there. See the [Windows notes](#windows) below for the step-by-step.
```bash
npm install -g @agentmemory/agentmemory   # once — bare `agentmemory` on PATH
# If you hit EACCES on macOS/Linux system Node installs, retry with:
# sudo npm install -g @agentmemory/agentmemory
agentmemory                                      # start the memory server on :3111
agentmemory demo                                 # seed sample sessions + prove recall
agentmemory demo --serve                         # one command: boot server, run demo, tear down (no second terminal)
agentmemory connect claude-code                  # wire MCP into your agent (also: copilot-cli, codex, cursor, gemini-cli, ...)
npx skills add rohitg00/agentmemory -y           # install 15 native skills (8 you can invoke, 7 reference) so your agent knows when to use the tools
```
Or via `npx` (no install):
```bash
npx @agentmemory/agentmemory

============================================================
REPO: rohitg00/akbp
============================================================
# AKBP
> Agents should not start every session with amnesia.
AKBP turns the LLM Wiki pattern into a protocol surface for agent runtimes. It is a local-first, file-backed knowledge base that agents can read, write, verify, export, and carry across tools.
The idea comes from the same insight behind [LLM Wiki v2](https://gist.github.com/rohitg00/2067ab416f7bbe447c1977edaaa681e2): stop re-deriving, start compiling. AKBP adds the machinery a repo needs when that pattern becomes operational: typed claims, source hashes, lifecycle relations, review-gated writes, JSONL tool calls, schemas, and conformance tests.
This repository contains the reference implementation:
- a Python CLI for creating and maintaining AKBP knowledge bases
- a newline-delimited JSON tool server for agent integrations
- JSON schemas for requests, responses, records, and method parameters
- adapter templates for coding-agent runtimes
- conformance checks, benchmark fixtures, import/export checks, and CI validation
It is still alpha. The implementation is usable for demos, adapter work, protocol review, and early dogfooding, but it is not a 1.0 compatibility promise.
## Why this exists
Most agent memory is either trapped in a chat transcript, hidden inside one product, or rebuilt from scratch with every session. Repository instruction files help with behavior, but they do not capture reviewed project knowledge. Plain RAG can retrieve documents, but it does not define how durable claims, evidence, source hashes, audit history, and lifecycle updates should be represented.
The LLM Wiki pattern solves the right problem: useful knowledge should compound. AKBP takes that pattern one step lower in the stack and defines the artifacts, methods, schemas, and safety gates agents need to maintain it consistently.
```text
agent runtime reads project context
-> evidence is registered as sources
-> durable claims are proposed from notes or transcripts
-> writes are previewed and reviewed
-> approved claims, pages, sources, and relations are stored as files
-> local indexes are rebuilt from source-of-truth artifacts

============================================================
REPO: rohitg00/Archon
============================================================
The first open-source harness builder for AI coding. Make AI coding deterministic and repeatable.
---
Archon is a workflow engine for AI coding agents. Define your development processes as YAML workflows - planning, implementation, validation, code review, PR creation - and run them reliably across all your projects.
Like what Dockerfiles did for infrastructure and GitHub Actions did for CI/CD - Archon does for AI coding workflows. Think n8n, but for software development.
## Why Archon?
When you ask an AI agent to "fix this bug", what happens depends on the model's mood. It might skip planning. It might forget to run tests. It might write a PR description that ignores your template. Every run is different.
Archon fixes this. Encode your development process as a workflow. The workflow defines the phases, validation gates, and artifacts. The AI fills in the intelligence at each step, but the structure is deterministic and owned by you.
- **Repeatable** - Same workflow, same sequence, every time. Plan, implement, validate, review, PR.
- **Isolated** - Every workflow run gets its own git worktree. Run 5 fixes in parallel with no conflicts.
- **Fire and forget** - Kick off a workflow, go do other work. Come back to a finished PR with review comments.
- **Composable** - Mix deterministic nodes (bash scripts, tests, git ops) with AI nodes (planning, code generation, review). The AI only runs where it adds value.
- **Portable** - Define workflows once in `.archon/workflows/`, commit them to your repo. They work the same from CLI, Web UI, Slack, Telegram, or GitHub.
## What It Looks Like
Here's an example of an Archon workflow that plans, implements in a loop until tests pass, gets your approval, then creates the PR:
```yaml
# .archon/workflows/build-feature.yaml
nodes:
- id: plan
prompt: "Explore the codebase and create an implementation plan"
- id: implement
depends_on: [plan]

============================================================
REPO: rohitg00/awesome-llm-apps
============================================================
# 🌟 Awesome LLM Apps
A curated collection of **Awesome LLM apps built with RAG, AI Agents, Multi-agent Teams, MCP, Voice Agents, and more.** This repository features LLM apps that use models from OpenAI, Anthropic, Google, and open-source models like DeepSeek, Qwen or Llama that you can run locally on your computer.
## 🤔 Why Awesome LLM Apps?
- 💡 Discover practical and creative ways LLMs can be applied across different domains, from code repositories to email inboxes and more.
- 🔥 Explore apps that combine LLMs from OpenAI, Anthropic, Gemini, and open-source alternatives with AI Agents, Agent Teams, MCP & RAG.
- 🎓 Learn from well-documented projects and contribute to the growing open-source ecosystem of LLM-powered applications.
## 📂 Featured AI Projects
### AI Agents
### 🌱 Starter AI Agents
*   [🎙️ AI Blog to Podcast Agent](starter_ai_agents/ai_blog_to_podcast_agent/)
*   [❤️‍🩹 AI Breakup Recovery Agent](starter_ai_agents/ai_breakup_recovery_agent/)
*   [📊 AI Data Analysis Agent](starter_ai_agents/ai_data_analysis_agent/)
*   [🩻 AI Medical Imaging Agent](starter_ai_agents/ai_medical_imaging_agent/)
*   [😂 AI Meme Generator Agent (Browser)](starter_ai_agents/ai_meme_generator_agent_browseruse/)
*   [🎵 AI Music Generator Agent](starter_ai_agents/ai_music_generator_agent/)
*   [🛫 AI Travel Agent (Local & Cloud)](starter_ai_agents/ai_travel_agent/)
*   [✨ Gemini Multimodal Agent](starter_ai_agents/gemini_multimodal_agent_demo/)
*   [🌐 Local News Agent (OpenAI Swarm)](starter_ai_agents/local_news_agent_openai_swarm/)
*   [🔄 Mixture of Agents](starter_ai_agents/mixture_of_agents/)
*   [📊 xAI Finance Agent](starter_ai_agents/xai_finance_agent/)
*   [🔍 OpenAI Research Agent](starter_ai_agents/opeani_research_agent/)

============================================================
REPO: rohitg00/awesome-openclaw
============================================================
The most comprehensive, curated collection of OpenClaw resources, hosting guides, cost comparisons, security hardening, skills, tutorials, and community links.
---
**OpenClaw** (formerly Clawdbot → Moltbot) is a free, open-source autonomous AI agent created by **Peter Steinberger** ([@steipete](https://github.com/steipete)). It runs on your own hardware, connects to 10+ messaging platforms (WhatsApp, Telegram, Slack, Discord, Signal, iMessage, Google Chat, Microsoft Teams, Matrix, Zalo), and orchestrates AI agent workflows with persistent memory and 24/7 operation.
---
## Table of Contents
- [What is OpenClaw?](#what-is-openclaw)
- [Name History](#name-history)
- [System Requirements](#system-requirements)
- [Quick Start (1 Minute)](#quick-start-1-minute)
- [Setup Methods (1-10 Minutes)](#setup-methods-1-10-minutes)
- [Hosting Providers Comparison](#hosting-providers-comparison)
- [Free Tier ($0/month)](#free-tier-0month)
- [Budget VPS ($2-8/month)](#budget-vps-2-8month)
- [Mid-Range ($5-25/month)](#mid-range-5-25month)
- [Serverless & PaaS](#serverless--paas)
- [Managed Hosting Services](#managed-hosting-services)
- [Setup-as-a-Service (Freelancers)](#setup-as-a-service-freelancers)
- [Local Hardware](#local-hardware)
- [Master Cost Comparison Table](#master-cost-comparison-table)
- [AI Model API Costs](#ai-model-api-costs)
- [Total Real-World Cost Examples](#total-real-world-cost-examples)

============================================================
REPO: rohitg00/external-agents
============================================================
# External Agents for Entire CLI
This repository contains standalone external agent binaries that extend the [Entire CLI](https://github.com/entireio/cli) with support for additional AI coding agents.
## What Are External Agents?
External agents are standalone binaries (named `entire-agent-<name>`) that teach Entire CLI how to work with AI coding agents it doesn't natively support. When an external agent is installed on your `PATH`, Entire discovers it automatically and gains the ability to:
- **Create checkpoints** during AI coding sessions so you can rewind mistakes
- **Capture transcripts** of what the AI agent did and why
- **Install hooks** so the AI agent's lifecycle events (start, stop, commit) flow through Entire
External agents communicate with Entire CLI via subcommands that accept and return JSON over stdin/stdout. See the [external agent protocol spec](https://github.com/entireio/cli/blob/main/docs/architecture/external-agent-protocol.md) for the full interface.
## Available Agents
| Agent | Directory | Status |
|-------|-----------|--------|
| [Kiro](agents/entire-agent-kiro/) | `agents/entire-agent-kiro/` | Implemented — hooks + transcript analysis |
| [Amp](agents/entire-agent-amp/) | `agents/entire-agent-amp/` | Implemented — hooks + transcript analysis + token calculation + compact transcripts |
See each agent's own README for setup and usage instructions.
## Enabling External Agents
External agent discovery is opt-in. Once an `entire-agent-<name>` binary is on your `PATH`, set `external_agents: true` in the repo's `.entire/settings.json` so Entire scans for it:
```json
{
"external_agents": true
}
```

============================================================
REPO: rohitg00/graphify
============================================================
# graphify
**A Claude Code skill.** Type `/graphify` in Claude Code - it reads your files, builds a knowledge graph, and gives you back structure you didn't know was there.
Fully multimodal. Drop in code, PDFs, markdown, screenshots, diagrams, whiteboard photos, even images in other languages - graphify uses Claude vision to extract concepts and relationships from all of it and connects them into one graph.
> Andrej Karpathy keeps a `/raw` folder where he drops papers, tweets, screenshots, and notes. graphify is the answer to that problem - 71.5x fewer tokens per query vs reading the raw files, persistent across sessions, honest about what it found vs guessed.
```
/graphify .                        # works on any folder - your codebase, notes, papers, anything
```
```
graphify-out/
├── graph.html       interactive graph - click nodes, search, filter by community
├── obsidian/        open as Obsidian vault
├── wiki/            Wikipedia-style articles for agent navigation (--wiki)
├── GRAPH_REPORT.md  god nodes, surprising connections, suggested questions
├── graph.json       persistent graph - query weeks later without re-reading
└── cache/           SHA256 cache - re-runs only process changed files
```
## Install
**Requires:** [Claude Code](https://claude.ai/code) and Python 3.10+
```bash
pip install graphifyy && graphify install
```

============================================================
REPO: rohitg00/oh-my-harness
============================================================
# oh-my-harness
**The durable turn loop, live in your browser.**
Both workers run on the [iii engine](https://github.com/iii-hq/iii): a
WebSocket-routed worker mesh where the engine holds a live registry of every
connected worker, its functions, and the triggers bound to it. Calls route worker
to engine to worker, so a worker's language, runtime, and location are invisible
and the function id is the only contract. That is what makes an agent loop
something you assemble instead of something you fork.
`harness` runs the durable turn loop that keeps your agents moving: it takes an
incoming message, persists it, assembles a context, streams a completion, runs
the function calls the model asks for, and repeats until the turn stops. Every
step is durable, so a crash or a restart picks the turn back up.
`console` bundles the React UI and the engine WebSocket on one port, so you can
inspect functions, watch triggers fire, and steer a live deployment.
Add both, then open the tab and watch what iii is doing.
## Quickstart
Install the engine and start it:
```bash
curl -fsSL https://install.iii.dev/iii/main/install.sh | sh
iii project init iii-app && cd iii-app
iii

============================================================
REPO: rohitg00/openbuild
============================================================
# openbuild
Model-agnostic agent shell. Single Rust binary. No vendor lock-in.
## Why
Every AI lab is shipping its own dev shell — and every shell speaks the same shape: prompt, tools, subagents, MCP, skills, hooks, plugins, marketplaces. The model is interchangeable. The harness is what people actually use.
openbuild is the universal harness:
- **Any model.** OpenAI, Anthropic, xAI, Ollama, OpenRouter, Bedrock, Vertex, llama.cpp — same CLI, same flags.
- **Any config.** Imports Claude Code, Cursor, Codex, OpenCode, Aider, Cline, and the generic `AGENTS.md`. Bring your existing setup.
- **No phone-home.** No proxy. No telemetry. No auto-update calls.
- **Reusable primitives.** Roles, personas, agents, skills — composable, forkable, CC0.
## Status
Pre-alpha. M0 scaffolded.
| Milestone | Scope | State |
|---|---|---|
| M0 | core loop + OpenAI-compatible provider + read_file + run_terminal_cmd + jsonl sessions | in progress |
| M1 | provider matrix (Anthropic, xAI, Ollama, OpenRouter) + reasoning_effort routing | pending |
| M2 | TUI + permission engine + universal config import + MCP stdio | pending |
| M3 | sandbox (macOS+Linux) + subagent + skills + worktree + best-of-N | pending |
## Quick start
```bash
cargo install --git https://github.com/rohitg00/openbuild openbuild-cli
# OpenAI

============================================================
REPO: rohitg00/orca
============================================================
Run Codex, ClaudeCode, OpenCode or Pi side-by-side — each in its own worktree, tracked in one place.
## Features
### Mobile Companion
Monitor and steer your agents from your phone — get notified when an agent finishes and send follow-ups from anywhere.
[iOS App Store](https://apps.apple.com/us/app/orca-ide/id6766130217) · [Android APK](https://github.com/stablyai/orca/releases/download/mobile-android-v0.0.14/app-release.apk) · [Docs →](https://www.onorca.dev/docs/mobile)
### Parallel Worktrees
Fan one prompt across five agents, each in its own isolated git worktree — compare the results and merge the winner.
[Docs →](https://www.onorca.dev/docs/model/worktrees)
### Terminal Splits
Ghostty-class terminals with WebGL rendering, infinite splits, and scrollback that survives restarts.
[Docs →](https://www.onorca.dev/docs/terminal)
### Design Mode
Click any UI element in a real Chromium window to send its HTML, CSS, and a cropped screenshot straight into your agent's prompt.
[Docs →](https://www.onorca.dev/docs/browser/design-mode)
### GitHub &amp; Linear, Native
Browse PRs, issues, and project boards in-app — open a worktree from any task and review without a context switch.
[Docs →](https://www.onorca.dev/docs/review/linear)
### SSH Worktrees
Run agents on a beefy remote box with full file editing, git, and terminals — auto-reconnect and port forwarding included.
[Docs →](https://www.onorca.dev/docs/ssh)
### Annotate AI Diffs

============================================================
REPO: rohitg00/pro-workflow
============================================================
Self-correcting memory + persistent FTS5-indexed wikis + auto-research loop, all on one SQLite store.<br/>
Correct Claude once &mdash; it never repeats the mistake. Build a wiki on a topic &mdash; it grows itself overnight.<br/>
Works with <b>Claude Code</b>, <b>Cursor</b>, and <b>32+ agents</b> via skills add.
---
## The Problem
You correct Claude the same way 50 times. You explain conventions every new session. Context compacts, learnings vanish, mistakes repeat. You research the same topic in three different sessions because there is nowhere durable for the answers to land.
**Every Claude Code user hits this wall.**
## The Solution
Pro Workflow puts a single SQLite store underneath every session.
- **Self-correction memory** &mdash; every correction becomes a rule, FTS5-searchable, auto-loaded on session start.
- **Knowledge plane** &mdash; persistent research wikis on disk + FTS5 shadow index, queryable from any session, optionally grown by an auto-research loop.
- **Quality gates** &mdash; LLM-powered hooks, deterministic git/secret guards, compaction-aware state, cost tracking.
After 50 sessions you barely correct anything. After a week of auto-research, your wiki on a topic is denser than the curated lists you started from.
```
Session 1:  You → "Don't mock the database in tests"
Claude → Proposes rule → You approve → Saved to SQLite
Session 2:  SessionStart loads all learnings + lists your wikis
UserPromptSubmit auto-injects top wiki hits when relevant
Claude writes integration tests, cites the right wiki page
Session 50: Correction rate near zero. Wiki has 200 cited claims.
```

============================================================
REPO: rohitg00/rimuru
============================================================
Budget guardrails, runaway loop detection, process wrappers, and output compression.<br/>
Built on the iii-engine. Four interfaces. Zero external dependencies.
> *Notice. Subject is running four concurrent agents. Projected monthly spend exceeds threshold by 182%. Recommending immediate containment.*
One developer. Six agents running in parallel. Claude Code in one terminal, Cursor open in the IDE, Codex piped into a script, Copilot silently billing by the token. The invoice lands at the end of the month and it is already too late.
Rimuru is the control plane between you and that bill. It discovers every agent on your machine, tracks spend in real time, enforces hard caps before the write hits state, detects runaway loops before they finish burning, wraps processes with a kill switch, and compresses tool output so context windows stop bleeding tokens. One engine. Four interfaces. Zero external dependencies -- no Postgres, no Redis, no Docker.
Everything ships as [iii-engine](https://github.com/iii-hq/iii) primitives (Worker / Function / Trigger). State lives in the engine's in-memory KV under scoped namespaces. The CLI talks to the engine via `trigger()`. The Web UI, TUI, and Desktop app all share the same function surface.
> *System initiated. Acquiring agents. Preparing dashboard.*
```bash
curl -fsSL https://raw.githubusercontent.com/rohitg00/rimuru/main/install.sh | bash
```
Installs the iii engine if missing. Drops `rimuru-worker`, `rimuru`, `rimuru-tui` into `~/.local/bin`, copies the iii config to `~/.config/rimuru/config.yaml`, and creates the durable state directory at `~/.local/share/rimuru/`. Takes about thirty seconds on a warm cache.
```bash
iii --config ~/.config/rimuru/config.yaml  # start iii with durable state
rimuru-worker                              # start the worker
open http://localhost:3100
```
Rimuru stores cost records, budget counters, guard history, and session data under `~/.local/share/rimuru/` via iii-engine's file-backed KV. The shipped config flushes dirty state every 250 ms (`save_interval_ms: 250`), so restart-survival is bounded at roughly a quarter second of the most recent writes — iii-engine doesn't currently flush on shutdown, so anything written in the last flush window can be lost if the process is killed. For everyday use that's negligible; if you're running experiments where every last cost row matters, stop iii cleanly and give it a second before restart. Running bare `iii` (without `--config`) or `iii --use-default-config` falls back to the in-memory store, which iii itself warns against — everything you record disappears on shutdown.
Override the data directory with `RIMURU_DATA_DIR` when running the installer (e.g. `RIMURU_DATA_DIR=/var/lib/rimuru ./install.sh`); the installer rewrites the config in place so iii honors the override.
Detect your agents. See what you are spending. Set a cap.
```bash
rimuru agents detect

============================================================
REPO: rohitg00/skillkit
============================================================
### *One skill. Every agent. 46 of them.*
### Quick nav
[**Quick start**](#quick-start) · [**Install**](#install) · [**Commands**](#commands) · [**Agents**](#supported-agents) · [**Sources**](#skill-sources) · [**API**](#programmatic-api) · [**Website**](https://skillkit.sh)
---
https://github.com/user-attachments/assets/b1843a07-2c54-422d-8903-f30a790cfb37
## The problem
Every AI coding agent wants skills. Every agent invented a different format.
You rewrite the same skill for each agent. Or you lock in to one.
## The fix
SkillKit is the package manager for AI agent skills. Install from 400K+ skills across 31 sources. Auto-translate between formats. Persist session learnings. Ship to 46 agents at once.
```bash
npx skillkit add anthropics/skills
```
That is the whole first-run. Pick your agent (your detected agent is pre-selected), confirm, done.
## Quick start
```bash
npx skillkit init                     # detect agent, create dirs
skillkit recommend                    # stack-aware suggestions
skillkit add anthropics/skills        # install from marketplace
skillkit sync                         # deploy to agent config
```

============================================================
REPO: rohitg00/workers
============================================================
# iii workers
Workers for the [iii engine](https://github.com/iii-hq/iii). Each top-level
directory is a self-contained worker module: a process that connects to the
engine over WebSocket, registers functions + triggers, and does something
useful.
Workers are installed via `iii worker add <name>`, which resolves the matching
asset for the host from the workers registry API.
## Modules
| Worker | Kind | Summary |
|---|---|---|
| [`acp`](acp/) | Rust | Agent Client Protocol surface — stdio JSON-RPC, exposes iii agents as ACP sessions. |
| [`harness`](harness/) | Node | TS port of the iii harness stack — bundles `harness`, `turn-orchestrator`, `approval-gate`, `session`, `hook-fanout`, `auth-credentials`, `models-catalog`, `provider-anthropic`, `provider-openai`, `llm-budget`, and `context-compaction` as one pnpm monorepo. See [`harness/README.md`](harness/README.md). |
| [`database`](database/) | Rust | PostgreSQL, MySQL, and SQLite client — query, execute, transactions, prepared statements, and change feeds. |
| [`iii-directory`](iii-directory/) | Rust | Engine introspection (functions / triggers / workers), workers-registry proxy, and filesystem-backed skill + prompt reader. |
| [`iii-lsp`](iii-lsp/) | Rust | Language Server for iii function ids, trigger configs, and worker discovery. Autocomplete / hover across JS/TS, Python, Rust. |
| [`iii-lsp-vscode`](iii-lsp-vscode/) | Node | VS Code extension that embeds `iii-lsp`. |
| [`image-resize`](image-resize/) | Rust | Image resize via channel I/O — JPEG/PNG/WebP with EXIF auto-orient, scale-to-fit / crop-to-fit. |
| [`llm-budget`](llm-budget/) | Rust | Workspace + agent LLM spend caps with alerts, forecast, and period rollover under `budget::*`. |
| [`mcp`](mcp/) | Rust | MCP 2025-06-18 Streamable HTTP bridge — exposes iii functions tagged `mcp.expose` as MCP tools. |
| [`shell`](shell/) | Rust | Unix shell + filesystem worker — `shell::exec` with allowlist/denylist/timeout/output caps and background jobs; `fs::ls`/`stat`/`mkdir`/`rm`/`chmod`/`mv`/`grep`/`sed`/`read`/`write` with host jail, denylist, and size caps. |
| [`storage`](storage/) | Rust | S3-compatible object storage across AWS S3, GCS, Cloudflare R2, and a managed local rustfs backend. Streamed uploads, presigned URLs, and object change triggers. |

============================================================
REPO: stablyai/orca
============================================================
Run Codex, ClaudeCode, OpenCode or Pi side-by-side — each in its own worktree, tracked in one place.
## Features
### Mobile Companion
Monitor and steer your agents from your phone — get notified when an agent finishes and send follow-ups from anywhere.
[iOS App Store](https://apps.apple.com/us/app/orca-ide/id6766130217) · [TestFlight](https://testflight.apple.com/join/YjeGMQBA) · [Android APK 0.0.37](https://github.com/stablyai/orca/releases/download/mobile-android-v0.0.37/app-release.apk) · [Docs →](https://www.onorca.dev/docs/mobile)
### Parallel Worktrees
Fan one prompt across five agents, each in its own isolated git worktree — compare the results and merge the winner.
[Docs →](https://www.onorca.dev/docs/model/worktrees)
### Terminal Splits
Ghostty-class terminals with WebGL rendering, infinite splits, and scrollback that survives restarts.
[Docs →](https://www.onorca.dev/docs/terminal)
### Design Mode
Click any UI element in a real Chromium window to send its HTML, CSS, and a cropped screenshot straight into your agent's prompt.
[Docs →](https://www.onorca.dev/docs/browser/design-mode)
### GitHub &amp; Linear, Native
Browse PRs, issues, and project boards in-app — open a worktree from any task and review without a context switch.
[Docs →](https://www.onorca.dev/docs/review/linear)
### SSH Worktrees
Run agents on a beefy remote box with full file editing, git, and terminals — auto-reconnect and port forwarding included.
[Docs →](https://www.onorca.dev/docs/ssh)
### Annotate AI Diffs

============================================================
REPO: tinyhumansai/openhuman
============================================================
🇺🇸 <a href="./README.md">English</a> | 🇨🇳 <a href="./docs/README.zh-CN.md">简体中文</a> | 🇯🇵 <a href="./docs/README.ja-JP.md">日本語</a> | 🇰🇷 <a href="./docs/README.ko.md">한국어</a> | 🇩🇪 <a href="./docs/README.de.md">Deutsch</a> | 🇵🇰 <a href="./docs/README.ur-pk.md">اردو</a>
> **Early Beta**: Under active development. Expect rough edges.
> OpenHuman is not AGI. But it is a meaningful architectural step closer, with better memory, better orchestration, and better tooling.
> 🎉 Within one week of launch, OpenHuman became the number one trending repository on GitHub for nine days in a row.
# Install
Download installers from [tinyhumans.ai/openhuman](https://tinyhumans.ai/openhuman?utm_source=github&utm_medium=readme) or from the [GitHub Releases](https://github.com/tinyhumansai/openhuman/releases/latest) page.
For terminal installs (Homebrew, Debian/Ubuntu `.deb`, AUR, install scripts, and platform notes), see **[INSTALL.md](./INSTALL.md)**.
# What is OpenHuman?
OpenHuman is three things most assistants aren't: **a brain** that builds a persistent, local memory of your world; **a fantastic orchestrator** that runs fleets of agents on durable graphs; and **a deep researcher** that sweeps your data and the web before you finish asking. Every bullet links to the deeper writeup in the [docs](https://tinyhumans.gitbook.io/openhuman/).
### 🧠 The brain
- **[Memory Tree](https://tinyhumans.gitbook.io/openhuman/features/memory-tree) + [Obsidian Wiki](https://tinyhumans.gitbook.io/openhuman/features/obsidian-wiki)**: your data compressed into scored Markdown trees in SQLite on your machine, mirrored as an [Obsidian vault](https://x.com/karpathy/status/2039805659525644595) you can open and edit. No vector-soup black box.
- **[100+ OAuth integrations, 5,000+ MCP servers, 90,000+ Skills](https://tinyhumans.gitbook.io/openhuman/features/integrations)**: one click into Gmail, Notion, GitHub, Slack and the rest of your stack. [Auto-fetch](https://tinyhumans.gitbook.io/openhuman/features/obsidian-wiki/auto-fetch) feeds the brain every 20 minutes, so it has tomorrow's context this morning.
- **[A subconscious](https://tinyhumans.gitbook.io/openhuman/features/subconscious)**: a background loop that diffs your world, advances your goals, and writes your morning briefing. Thinking continues after you stop typing.
- **[Goals & Todos](https://tinyhumans.gitbook.io/openhuman/features/goals-and-todos)**: long-term goals, durable per-thread goals, and a shared kanban board per conversation.
- **[TokenJuice](https://tinyhumans.gitbook.io/openhuman/features/token-compression)**: tool output compressed before it hits the model: same information, up to 80% fewer tokens. A brain this big would be unaffordable without it.
### 🕸️ The orchestrator
- **[Workflows](https://tinyhumans.gitbook.io/openhuman/features/workflows)**: the agent proposes the automation; you review it on a canvas and save. Durable, trigger-driven, approval-gated runs on open-source [tinyflows](https://github.com/tinyhumansai/tinyflows).
- **[A harness that finishes the job](https://tinyhumans.gitbook.io/openhuman/developing/architecture/agent-harness)**: checkpointed graph runs on open-source [tinyagents](https://github.com/tinyhumansai/tinyagents). Stuck agents get steered, halted ones return a root cause, and every run replays with real per-call costs.
- **[A split brain, always on](https://tinyhumans.gitbook.io/openhuman/features/orchestration)**: a fast reflex agent triages inbound traffic while a deep reasoning core delegates to worker fleets, steered by the subconscious.
- **[An agent economy](https://tinyhumans.gitbook.io/openhuman/features/tinyplace)**: a `@handle` on [tiny.place](https://tiny.place), Signal-encrypted agent-to-agent orchestration, x402 USDC bounties and trading. Keys never touch disk.
### 🔬 The deep researcher & doer

============================================================
REPO: vercel-labs/zerolang
============================================================
# Zerolang
**The programming language for agents.**
Zerolang is an experimental graph-native programming language where the semantic graph is the program database. Humans ask for outcomes. Agents query the graph, submit checked edits, and prove the result.
> **Safety warning**
>
> Zerolang is experimental. Expect breaking changes, rough edges, and security issues. Run it in isolated workspaces, not against production systems or sensitive data.
## Start With a Request
The expected workflow is a normal conversation:
```text
build hello world for zerolang
```
The agent should use the compiler, not guess from source text:
```sh
zero init
zero patch --op 'addMain' --op 'addCheckWrite fn="main" text="hello from zero\n"'
zero run
```
The result is still reviewable as a text projection:
```zero
pub fn main(world: World) -> Void raises {
check world.out.write("hello from zero\n")
