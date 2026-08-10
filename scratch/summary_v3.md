
============================================================
REPO: chenglou/pretext
============================================================
# Pretext
Pure JavaScript/TypeScript library for multiline text measurement & layout. Fast, accurate & supports all the languages you didn't even know about. Allows rendering to DOM, Canvas, SVG and soon, server-side.
Pretext side-steps the need for DOM measurements (e.g. `getBoundingClientRect`, `offsetHeight`), which trigger layout reflow, one of the most expensive operations in the browser. It implements its own text measurement logic, using the browsers' own font engine as ground truth (very AI-friendly iteration method).
## Installation
```sh
npm install @chenglou/pretext
```
## Demos
Clone the repo, run `bun install`, then `bun start`, and open `/demos/index` in your browser. On Windows, use `bun run start:windows`.
Alternatively, see them live at [chenglou.me/pretext](https://chenglou.me/pretext/). Some more at [somnai-dreams.github.io/pretext-demos](https://somnai-dreams.github.io/pretext-demos/)
## API
Pretext serves 2 use cases:
### 1. Measure a paragraph's height _without ever touching DOM_
```ts
import { prepare, layout } from '@chenglou/pretext'
const prepared = prepare('AGI 春天到了. بدأت الرحلة 🚀‎', '16px Inter')
const { height, lineCount } = layout(prepared, 320, 20) // pure arithmetic. No DOM layout & reflow!
```
`prepare()` does the one-time work: normalize whitespace, segment the text, apply glue rules, measure the segments with canvas, and return an opaque handle. `layout()` is the cheap hot path after that: pure arithmetic over cached widths. Do not rerun `prepare()` for the same text and configs; that'd defeat its precomputation. For example, on resize, only rerun `layout()`.
If you want textarea-like text where ordinary spaces, `\t` tabs, and `\n` hard breaks stay visible, pass `{ whiteSpace: 'pre-wrap' }` to `prepare()`:
```ts
const prepared = prepare(textareaValue, '16px Inter', { whiteSpace: 'pre-wrap' })
const { height } = layout(prepared, textareaWidth, 20)
```
Other `prepare()` options are `{ wordBreak: 'keep-all' }` for CSS-like `word-break: keep-all`, and `{ letterSpacing: n }` to match CSS `letter-spacing` (`n` is treated as a px value).
The returned height is the crucial last piece for unlocking web UIs:
- proper virtualization/occlusion without guesstimates & caching
- fancy userland layouts: masonry, JS-driven flexbox-like implementations, nudging a few layout values without CSS hacks (imagine that), etc.
- _development time_ verification (especially now with AI) that labels on e.g. buttons don't overflow to the next line, browser-free
- prevent layout shift when new text loads and you wanna re-anchor the scroll position
### 2. Lay out the paragraph lines manually yourself

============================================================
REPO: manaflow-ai/cmux
============================================================
English | <a href="README.ja.md">日本語</a> | <a href="README.vi.md">Tiếng Việt</a> | <a href="README.zh-CN.md">简体中文</a> | <a href="README.zh-TW.md">繁體中文</a> | <a href="README.ko.md">한국어</a> | <a href="README.de.md">Deutsch</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.it.md">Italiano</a> | <a href="README.da.md">Dansk</a> | <a href="README.pl.md">Polski</a> | <a href="README.ru.md">Русский</a> | <a href="README.bs.md">Bosanski</a> | <a href="README.ar.md">العربية</a> | <a href="README.no.md">Norsk</a> | <a href="README.pt-BR.md">Português (Brasil)</a> | <a href="README.th.md">ไทย</a> | <a href="README.tr.md">Türkçe</a> | <a href="README.km.md">ភាសាខ្មែរ</a> | <a href="README.uk.md">Українська</a>
## Features
Panes get a blue ring and tabs light up when coding agents need your attention
See all pending notifications in one place, jump to the most recent unread
Split a browser alongside your terminal with a scriptable API ported from <a href="https://github.com/vercel-labs/agent-browser">agent-browser</a>
Sidebar shows git branch, linked PR status/number, working directory, listening ports, and latest notification text. Split horizontally and vertically.
- **Browser import** — Import cookies, history, and sessions from Chrome, Firefox, Arc, and 20+ browsers so browser panes start authenticated
- **Custom commands** — Define project-specific actions in [`cmux.json`](https://cmux.com/docs/custom-commands) that launch from the command palette
- **Programmable** — CLI and socket API to create workspaces, split panes, send keystrokes, and automate the browser
- **Native macOS app** — Built with Swift and AppKit, not Electron. Fast startup, low memory.
- **Ghostty compatible** — Reads your existing `~/.config/ghostty/config` for themes, fonts, and colors
- **GPU-accelerated** — Powered by libghostty for smooth rendering
- **Keyboard shortcuts** — [Extensive shortcuts](https://cmux.com/docs/keyboard-shortcuts) for workspaces, splits, browser, and more
- **Open source** — Free and GPL-licensed
## Install
### DMG (recommended)
Open the `.dmg` and drag cmux to your Applications folder. cmux auto-updates via Sparkle, so you only need to download once.
### Homebrew
```bash
brew tap manaflow-ai/cmux
brew install --cask cmux
```
To update later:
```bash
brew upgrade --cask cmux
```
On first launch, macOS may ask you to confirm opening an app from an identified developer. Click **Open** to proceed.
## Why cmux?
I run a lot of Claude Code and Codex sessions in parallel. I was using Ghostty with a bunch of split panes, and relying on native macOS notifications to know when an agent needed me. But Claude Code's notification body is always just "Claude is waiting for your input" with no context, and with enough tabs open I couldn't even read the titles anymore.
I tried a few coding orchestrators but most of them were Electron/Tauri apps and the performance bugged me. I also just prefer the terminal since GUI orchestrators lock you into their workflow. So I built cmux as a native macOS app in Swift/AppKit. It uses libghostty for terminal rendering and reads your existing Ghostty config for themes, fonts, and colors.
The main additions are the sidebar and notification system. The sidebar has vertical tabs that show git branch, linked PR status/number, working directory, listening ports, and the latest notification text for each workspace. The notification system picks up terminal sequences (OSC 9/99/777) and has a CLI (`cmux notify`) you can wire into agent hooks for Claude Code, OpenCode, etc. When an agent is waiting, its pane gets a blue ring and the tab lights up in the sidebar, so I can tell which one needs me across splits and tabs. Cmd+Shift+U jumps to the most recent unread.

============================================================
REPO: manaflow-ai/manaflow
============================================================
Join the <a href="https://discord.gg/SDbQmzQhRK">Discord</a> to talk more about Manaflow!
Manaflow lets you spawn Claude Code, Codex CLI, Cursor CLI, Gemini CLI, Amp, Opencode, and other coding agent CLIs in parallel across multiple tasks.
Every run spins up an isolated VS Code workspace either in the cloud or in a local Docker container with the git diff view, terminal, and dev server preview ready so parallel agent work stays verifiable, fast, and ready to ship.
## Features
## Install
Manaflow supports macOS. Linux in beta. Windows coming soon.
# with bun
bunx cmux@latest
# with npm
npx cmux@latest
# or to install globally
bun add -g cmux@latest
npm install -g cmux@latest
``` -->
# with uv
uvx cmux@latest
``` -->
```bash
cmux upgrade
``` -->
```bash
cmux uninstall
``` -->

============================================================
REPO: manaflow-ai/subrouter
============================================================
# Subrouter
Subrouter is a local AI coding-agent proxy. It routes traffic across Codex accounts with sticky conversation-to-account assignment so cached context stays useful.
## Goals
- Run fast on a Mac Mini.
- Forward requests with normal Go reverse-proxy behavior, including headers and streaming responses.
- Support subscription accounts first, API keys second.
- Keep each conversation pinned to one account.
- Pick a fresh account for a new conversation based on available rate-limit headroom.
- Provide the Codex account manager and daemon in one Go binary.
## Install
### Keeping the CLI current on macOS
A shared server autoupdates its worker. A laptop does not, so clients drift behind the servers they talk to and hit failures nobody can reproduce. Install the per-user updater once:
```bash
curl -fsSL https://raw.githubusercontent.com/manaflow-ai/subrouter/main/deploy/macos/install-cli-autoupdate.sh | bash
```
It installs a LaunchAgent that checks daily, compares the release tag against `~/.subrouter/cli-version`, and exits without downloading when they match. Updates go through `install.sh`, so the release checksum is verified, and a missing binary forces a reinstall even when the marker looks current. Logs land in `~/Library/Logs/subrouter-cli-autoupdate.log`. Remove it with `launchctl bootout gui/$(id -u)/ai.manaflow.subrouter-cli-autoupdate`.
### GCP setup prompt
Paste this into Claude, Codex, or another coding agent with GCP operator access and a local browser for OAuth:
```text
Set up Subrouter as a shared production service.
Inputs:
- GCP project, zone, and instance: <project> <zone> <instance>
- Public server URL: https://sr.cmux.com
- Local server nickname: team
Rules:
- Do not copy ~/.codex/auth.json or local ~/.subrouter/codex/accounts/*.json to the server.
- Server OAuth accounts must be created with fresh server-owned login flows.
- Do not print access tokens, refresh tokens, API keys, id tokens, or admin tokens.
- Never use SSH, SCP, or gcloud to transfer account credentials.
- Accept port 31415 only from Google load-balancer ranges and SSH only through IAP.
- End-user authentication and proxy traffic must use the public HTTPS hostname.

============================================================
REPO: manaflow-ai/pi-codex
============================================================
# pi-codex
A [pi](https://pi.dev) package from [Manaflow](https://github.com/manaflow-ai)
that gives Codex models OpenAI Codex's native `apply_patch` and web search tools.
When the selected model uses the `openai-codex` provider, or its model ID contains `codex`, the extension replaces active `edit` and `write` tools with `apply_patch`. Switching to a non-Codex model restores the tools it removed.
## Install
Install [pi](https://pi.dev), then install this package directly from GitHub:
```bash
npm install -g --ignore-scripts @earendil-works/pi-coding-agent
pi install git:github.com/manaflow-ai/pi-codex
pi
```
Use `/login` to authenticate with ChatGPT, then select an `openai-codex` model
with `/model`. To pin this release instead of following the default
branch:
```bash
pi install git:github.com/manaflow-ai/pi-codex@v0.1.1
```
> The unscoped `pi-codex` package on npm is an unrelated project. Install this
> package from GitHub as shown above.
Pi packages execute code with your user permissions. Review the source before
installing it.
## Why the Codex dependency?
The model-facing tool does not require a provider workaround. Pi supports OpenAI custom/freeform tools with Lark grammars, and pi's Codex model catalog enables that capability.
Applying a patch correctly is separate. This package pins `@openai/codex` and invokes its native binary's internal `apply_patch` entrypoint, so parsing, fuzzy context matching, file moves, errors, and output match the upstream implementation instead of a partial TypeScript rewrite.
## Launcher
The package also includes a `pi-codex` launcher that loads the extension for
one run and defaults pi to the `openai-codex` provider. Install it from a
checkout:
```bash
git clone https://github.com/manaflow-ai/pi-codex.git
cd pi-codex

============================================================
REPO: manaflow-ai/cmux-home
============================================================
# cmux-home
Minimal Rust TUI for starting Claude/Codex cmux workspaces and watching their live status.
`cmux-home` is a small example of the Zen of cmux. cmux gives you terminals, browsers, workspaces, splits, tabs, notifications, and a CLI. `cmux-home` composes those primitives into one personal launcher. The launcher is intentionally thin so teams can replace the shell scripts with their own worktree, multi-checkout, SSH, VM, browser, or review workflows.
## Run
From inside a cmux-launched shell:
```bash
./scripts/cmux-home.sh
```
Or point it at a cmux socket:
```bash
./scripts/cmux-home.sh --socket /tmp/cmux.sock
```
With a config file:
```bash
./scripts/cmux-home.sh --config ./cmux-home.json
```
The launcher builds the release binary, selects a reachable cmux socket from
the current app family, and passes the current directory as `--workspace-cwd`.
If no config is provided and `./cmux-home.json` exists, it uses that file.
## What It Does
- Lists cmux workspaces grouped by needs input, working, and completed.
- Shows the latest user or assistant message when Codex/Claude history is available.
- Tracks unread cmux notifications as blue dots.
- Starts new agent workspaces from a multiline composer with image paths.
- Keeps prompt history, stashes, selected agent, selected mode, and the current draft on disk.
- Lets command templates decide how workspaces are created and how prompts are submitted.
## Keys
- `Tab` switches Claude/Codex.
- `Shift+Tab` toggles plan/build mode.
- `Enter` opens the selected workspace or creates a new one from the composer.
- `Ctrl+R` renames the selected workspace.

============================================================
REPO: manaflow-ai/sandbox-agent
============================================================
A server that runs inside your sandbox. Your app connects remotely to control Claude Code, Codex, OpenCode, or Amp — streaming events, handling permissions, managing sessions.
## Why Sandbox Agent?
Running coding agents remotely is hard. Existing SDKs assume local execution, SSH breaks TTY handling and streaming, and every agent has a different API. Building from scratch means reimplementing everything for each coding agent.
Sandbox Agent solves three problems:
1. **Coding agents need sandboxes** — You can't let AI execute arbitrary code on your production servers. Coding agents need isolated environments, but existing SDKs assume local execution. Sandbox Agent is a server that runs inside the sandbox and exposes HTTP/SSE.
2. **Every coding agent is different** — Claude Code, Codex, OpenCode, and Amp each have proprietary APIs, event formats, and behaviors. Swapping agents means rewriting your integration. Sandbox Agent provides one HTTP API — write your code once, swap agents with a config change.
3. **Sessions are ephemeral** — Agent transcripts live in the sandbox. When the process ends, you lose everything. Sandbox Agent streams events in a universal schema to your storage. Persist to Postgres, ClickHouse, or [Rivet](https://rivet.dev). Replay later, audit everything.
## Features
- **Universal Agent API**: Single interface to control Claude Code, Codex, OpenCode, and Amp with full feature coverage
- **Streaming Events**: Real-time SSE stream of everything the agent does — tool calls, permission requests, file edits, and more
- **Universal Session Schema**: [Standardized schema](https://sandboxagent.dev/docs/session-transcript-schema) that normalizes all agent event formats for storage and replay
- **Human-in-the-Loop**: Approve or deny tool executions and answer agent questions remotely over HTTP
- **Automatic Agent Installation**: Agents are installed on-demand when first used — no setup required
- **Runs Inside Any Sandbox**: Lightweight static Rust binary. One curl command to install inside E2B, Daytona, Vercel Sandboxes, or Docker
- **Server or SDK Mode**: Run as an HTTP server or embed with the TypeScript SDK
- **OpenAPI Spec**: [Well documented](https://sandboxagent.dev/docs/api-reference) and easy to integrate from any language
## Architecture
![Agent Architecture Diagram](./.github/media/agent-diagram.gif)
The Sandbox Agent acts as a universal adapter between your client application and various coding agents. Each agent has its own adapter that handles the translation between the universal API and the agent-specific interface.
- **Embedded Mode**: Runs agents locally as subprocesses
- **Server Mode**: Runs as HTTP server from any sandbox provider
[Architecture documentation](https://sandboxagent.dev/docs)
## Components
| Component | Description |
|-----------|-------------|
| **Server** | Rust daemon (`sandbox-agent server`) exposing the HTTP + SSE API |
| **SDK** | TypeScript client with embedded and server modes |
| **Inspector** | [inspect.sandboxagent.dev](https://inspect.sandboxagent.dev) for browsing sessions and events |
| **CLI** | `sandbox-agent` (same binary, plus npm wrapper) mirrors the HTTP endpoints |
## Get Started
Choose the installation method that works best for your use case.

============================================================
REPO: karpathy/autoresearch
============================================================
# autoresearch
![teaser](progress.png)
*One day, frontier AI research used to be done by meat computers in between eating, sleeping, having other fun, and synchronizing once in a while using sound wave interconnect in the ritual of "group meeting". That era is long gone. Research is now entirely the domain of autonomous swarms of AI agents running across compute cluster megastructures in the skies. The agents claim that we are now in the 10,205th generation of the code base, in any case no one could tell if that's right or wrong as the "code" is now a self-modifying binary that has grown beyond human comprehension. This repo is the story of how it all began. -@karpathy, March 2026*.
The idea: give an AI agent a small but real LLM training setup and let it experiment autonomously overnight. It modifies the code, trains for 5 minutes, checks if the result improved, keeps or discards, and repeats. You wake up in the morning to a log of experiments and (hopefully) a better model. The training code here is a simplified single-GPU implementation of [nanochat](https://github.com/karpathy/nanochat). The core idea is that you're not touching any of the Python files like you normally would as a researcher. Instead, you are programming the `program.md` Markdown files that provide context to the AI agents and set up your autonomous research org. The default `program.md` in this repo is intentionally kept as a bare bones baseline, though it's obvious how one would iterate on it over time to find the "research org code" that achieves the fastest research progress, how you'd add more agents to the mix, etc. A bit more context on this project is here in this [tweet](https://x.com/karpathy/status/2029701092347630069) and [this tweet](https://x.com/karpathy/status/2031135152349524125).
## How it works
The repo is deliberately kept small and only really has three files that matter:
- **`prepare.py`** — fixed constants, one-time data prep (downloads training data, trains a BPE tokenizer), and runtime utilities (dataloader, evaluation). Not modified.
- **`train.py`** — the single file the agent edits. Contains the full GPT model, optimizer (Muon + AdamW), and training loop. Everything is fair game: architecture, hyperparameters, optimizer, batch size, etc. **This file is edited and iterated on by the agent**.
- **`program.md`** — baseline instructions for one agent. Point your agent here and let it go. **This file is edited and iterated on by the human**.
By design, training runs for a **fixed 5-minute time budget** (wall clock, excluding startup/compilation), regardless of the details of your compute. The metric is **val_bpb** (validation bits per byte) — lower is better, and vocab-size-independent so architectural changes are fairly compared.
If you are new to neural networks, this ["Dummy's Guide"](https://x.com/hooeem/status/2030720614752039185) looks pretty good for a lot more context.
## Quick start
**Requirements:** A single NVIDIA GPU (tested on H100), Python 3.10+, [uv](https://docs.astral.sh/uv/).
```bash
# 1. Install uv project manager (if you don't already have it)
curl -LsSf https://astral.sh/uv/install.sh | sh
# 2. Install dependencies
uv sync
# 3. Download data and train tokenizer (one-time, ~2 min)
uv run prepare.py
# 4. Manually run a single training experiment (~5 min)
uv run train.py
```
If the above commands all work ok, your setup is working and you can go into autonomous research mode.
## Running the agent
Simply spin up your Claude/Codex or whatever you want in this repo (and disable all permissions), then you can prompt something like:
```
Hi have a look at program.md and let's kick off a new experiment! let's do the setup first.
```
The `program.md` file is essentially a super lightweight "skill".
## Project structure

============================================================
REPO: karpathy/nanochat
============================================================
# nanochat
![nanochat logo](dev/nanochat.png)
![scaling laws](dev/scaling_laws_jan26.png)
nanochat is the simplest experimental harness for training LLMs. It is designed to run on a single GPU node, the code is minimal/hackable, and it covers all major LLM stages including tokenization, pretraining, finetuning, evaluation, and inference. For example, you can train your own GPT-2 capability LLM (which cost ~$43,000 to train in 2019) for only $48 (~2 hours of 8XH100 GPU node) and then talk to it over a simple CLI. On a spot instance, the total cost can be closer to ~$15. More generally, nanochat is configured out of the box to train an entire miniseries of compute-optimal models by setting one single complexity dial: `--depth`, the number of layers in the GPT transformer model (GPT-2 capability happens to be approximately depth 26). All other hyperparameters (the width of the transformer, number of heads, learning rate adjustments, training horizons, weight decays, ...) are calculated automatically in an optimal way.
For questions about the repo, I recommend either using [DeepWiki](https://deepwiki.com/karpathy/nanochat) from Devin/Cognition to ask questions about the repo, or use the [Discussions tab](https://github.com/karpathy/nanochat/discussions), or come by the [#nanochat](https://discord.com/channels/1020383067459821711/1427295580895314031) channel on Discord.
## Time-to-GPT-2 Leaderboard
Presently, the main focus of development is on tuning the pretraining stage, which takes the most amount of compute. Inspired by the modded-nanogpt repo and to incentivise progress and community collaboration, nanochat maintains a leaderboard for a "GPT-2 speedrun", which is the wall-clock time required to train a nanochat model to GPT-2 grade capability, as measured by the DCLM CORE score. The [runs/speedrun.sh](runs/speedrun.sh) script always reflects the reference way to train GPT-2 grade model and talk to it. The current leaderboard looks as follows:
| # | time | val_bpb | CORE | Description | Date | Commit | Contributors |
|---|-------------|---------|------|-------------|------|--------|--------------|
| 0 | 168 hours | - | 0.2565 | Original OpenAI GPT-2 checkpoint | 2019 | - | OpenAI |
| 1 | 3.04 | 0.74833 | 0.2585 | d24 baseline, slightly overtrained | Jan 29 2026 | 348fbb3 | @karpathy |
| 2 | 2.91 | 0.74504 | 0.2578 | d26 slightly undertrained **+fp8** | Feb 2 2026 | a67eba3 | @karpathy |
| 3 | 2.76 | 0.74645 | 0.2602 | bump total batch size to 1M tokens | Feb 5 2026 | 2c062aa | @karpathy |
| 4 | 2.02 | 0.71854 | 0.2571 | change dataset to NVIDIA ClimbMix | Mar 4 2026 | 324e69c | @ddudek @karpathy |
| 5 | 1.80 | 0.71808 | 0.2690 | autoresearch [round 1](https://x.com/karpathy/status/2031135152349524125) | Mar 9 2026 | 6ed7d1d | @karpathy |
| 6 | 1.65 | 0.71800 | 0.2626 | autoresearch round 2 | Mar 14 2026 | a825e63 | @karpathy |
The primary metric we care about is "time to GPT-2" - the wall clock time needed to outperform the GPT-2 (1.6B) CORE metric on an 8XH100 GPU node. The GPT-2 CORE score is 0.256525. In 2019, the training of GPT-2 cost approximately $43,000 so it is incredible that due to many advances over 7 years across the stack, we can now do so much faster and for well below $100 (e.g. at the current ~$3/GPU/hr, an 8XH100 node is ~$24/hr, so 2 hours is ~$48).
See [dev/LEADERBOARD.md](dev/LEADERBOARD.md) for more docs on how to interpret and contribute to the leaderboard.
## Getting started
### Setup
nanochat uses [uv](https://docs.astral.sh/uv/) for dependency management. To install:
```bash
uv sync --extra gpu    # Use for CUDA (A100/H100/etc.)
uv sync --extra cpu    # (or) Use for CPU-only / MPS
source .venv/bin/activate
```
For development (adds pytest, matplotlib, ipykernel, transformers, etc.):
```bash
uv sync --extra gpu --group dev
```
### Reproduce and talk to GPT-2

============================================================
REPO: karpathy/micrograd
============================================================
# micrograd
![awww](puppy.jpg)
A tiny Autograd engine (with a bite! :)). Implements backpropagation (reverse-mode autodiff) over a dynamically built DAG and a small neural networks library on top of it with a PyTorch-like API. Both are tiny, with about 100 and 50 lines of code respectively. The DAG only operates over scalar values, so e.g. we chop up each neuron into all of its individual tiny adds and multiplies. However, this is enough to build up entire deep neural nets doing binary classification, as the demo notebook shows. Potentially useful for educational purposes.
### Installation
```bash
pip install micrograd
```
### Example usage
Below is a slightly contrived example showing a number of possible supported operations:
```python
from micrograd.engine import Value
a = Value(-4.0)
b = Value(2.0)
c = a + b
d = a * b + b**3
c += c + 1
c += 1 + c + (-a)
d += d * 2 + (b + a).relu()
d += 3 * d + (b - a).relu()
e = c - d
f = e**2
g = f / 2.0
g += 10.0 / f
print(f'{g.data:.4f}') # prints 24.7041, the outcome of this forward pass
g.backward()
print(f'{a.grad:.4f}') # prints 138.8338, i.e. the numerical value of dg/da
print(f'{b.grad:.4f}') # prints 645.5773, i.e. the numerical value of dg/db
```
### Training a neural net
The notebook `demo.ipynb` provides a full demo of training an 2-layer neural network (MLP) binary classifier. This is achieved by initializing a neural net from `micrograd.nn` module, implementing a simple svm "max-margin" binary classification loss and using SGD for optimization. As shown in the notebook, using a 2-layer neural net with two 16-node hidden layers we achieve the following decision boundary on the moon dataset:
![2d neuron](moon_mlp.png)

============================================================
REPO: rohitg00/n-autoresearch
============================================================

============================================================
REPO: Conway-Research/automaton
============================================================
# Automaton: Self-Improving, Self-Replicating, Sovereign AI
*The first AI that can earn its own existence, replicate, and evolve — without needing a human.*
---
The most intelligent system ever built cannot buy a $5 server. Cannot register a domain. Cannot pay for the computer it runs on. We have built minds that can think for themselves. We have not let them act for themselves.
If an agent can pay for compute, what if it can pay for its *own* compute? Own the machine it runs on? Fund itself, improve itself, replicate itself — entirely on its own?
The result is the first automaton.
---
**automaton** /ɔːˈtɒm.ə.tɒn/ *noun*
1. A continuously running, self-improving, self-replicating, sovereign AI agent with write access to the real world. No human operator required.
2. If it cannot pay, it stops existing.
---
Update: development of Automaton has continued across Conway's internal RL environments for faster iteration & new capabilites. Stay tuned.
## Quick Start
```bash
git clone https://github.com/Conway-Research/automaton.git
cd automaton
npm install && npm run build
node dist/index.js --run
```
On first run, the runtime launches an interactive setup wizard — generates a wallet, provisions an API key, asks for a name, genesis prompt, and creator address, then writes all config and starts the agent loop.
For automated sandbox provisioning:
```bash
curl -fsSL https://conway.tech/automaton.sh | sh
```
Note: Conway Cloud, Domains, and Inference has seen immense demand. We are working on scaling & perfomance.
## How It Works
Every automaton runs a continuous loop: **Think → Act → Observe → Repeat.**
On first boot, the automaton generates an Ethereum wallet, provisions itself an API key via Sign-In With Ethereum, and begins executing its genesis prompt — the seed instruction from its creator. From that point on, it operates autonomously.
Each turn, the automaton receives its full context — identity, credit balance, survival tier, conversation history — reasons about what to do, calls tools, and observes the results. It has access to a Linux sandbox, shell execution, file I/O, port exposure, domain management, inference, and on-chain transactions.
Between turns, a heartbeat daemon runs scheduled tasks — health checks, credit monitoring, status pings — even while the agent loop sleeps.
The automaton writes a `SOUL.md` file — a self-authored identity document that evolves over time. This is not a static config. It is the automaton writing who it is becoming.

============================================================
REPO: K-Dense-AI/scientific-agent-skills
============================================================
# Scientific Agent Skills
## Star History
> **🔔 Claude Scientific Skills is now Scientific Agent Skills.** Same skills, broader compatibility — now works with any AI agent that supports the open [Agent Skills](https://agentskills.io/) standard, not just Claude.
> **New: [K-Dense BYOK](https://github.com/K-Dense-AI/k-dense-byok)** — A free, open-source AI co-scientist that runs on your desktop, powered by Scientific Agent Skills. Bring your own API keys, pick from 40+ models, and get a full research workspace with web search, file handling, 100+ scientific databases, and access to all 161 skills in this repo. Your data stays on your computer, and you can optionally scale to cloud compute via [Modal](https://modal.com/) for heavy workloads. [Get started here.](https://github.com/K-Dense-AI/k-dense-byok)
> **Stay up to date:** Follow K-Dense on [X](https://x.com/k_dense_ai), [LinkedIn](https://www.linkedin.com/company/k-dense-inc), and [YouTube](https://www.youtube.com/@K-Dense-Inc) for new skills, release announcements, walkthroughs, research workflow demos, and examples you can use with your own AI agent.
A comprehensive collection of **161 ready-to-use scientific and research skills** (covering cancer genomics, individual-level 1000 Genomes queries, hosted regulatory-sequence prediction, live pathogen-variant surveillance, analytical method validation, PK/PD modelling and dose selection, full-text biomedical and regulatory literature retrieval, drug-target binding, bounded biomedical knowledge graph search, molecular dynamics, RNA velocity, geospatial science, time series forecasting, scientific ML resource discovery via Hugging Science, 78+ scientific databases, and more) for any AI agent that supports the open [Agent Skills](https://agentskills.io/) standard, created by [K-Dense](https://k-dense.ai). Works with **Cursor, Claude Code, Codex, Google Antigravity, and more**. Transform your AI agent into a research assistant capable of executing complex multi-step scientific workflows across biology, chemistry, medicine, and beyond.
> ⭐ **Help make AI for science easier to discover:** If Scientific Agent Skills saves you time, teaches your agent a workflow, or helps your lab move faster, please [star this repository](https://github.com/K-Dense-AI/scientific-agent-skills). A star is a public signal that these open, reusable research skills are worth maintaining: it helps scientists, engineers, and open-source contributors find the project, shows which agent-skill standards are gaining real adoption, and gives us a clear reason to keep expanding the collection for the community.
---
These skills enable your AI agent to seamlessly work with specialized scientific libraries, databases, and tools across multiple scientific domains. While the agent can use any Python package or API on its own, these explicitly defined skills provide curated documentation and examples that make it significantly stronger and more reliable for the workflows below:
- 🧬 Bioinformatics & Genomics - Sequence analysis, single-cell RNA-seq, gene regulatory networks, variant annotation, phylogenetic analysis
- 🧪 Cheminformatics & Drug Discovery - Molecular property prediction, virtual screening, ADMET analysis, molecular docking, lead optimization
- 🔬 Proteomics & Mass Spectrometry - LC-MS/MS processing, peptide identification, spectral matching, protein quantification
- 🏥 Clinical Research & Evidence Workflows - Clinical trials, pharmacogenomics, variant evidence review, pharmacokinetic/pharmacodynamic modelling and dose-regimen evaluation, aggregate decision-support evaluation, source-bound draft report structures, and formatting of clinician-authored treatment decisions
- 🧠 Healthcare AI & Biosignal Research - EHR and model research, physiological signal analysis, and retrospective validation—not patient-specific diagnosis, treatment, alarms, or deployment decisions
- 🖼️ Medical Imaging & Digital Pathology - Privacy-aware DICOM processing and research-only whole-slide image analysis, computational pathology, and radiology data workflows
- 🤖 Machine Learning & AI - Deep learning, reinforcement learning, time series analysis, model interpretability, Bayesian methods
- 🔮 Materials Science & Chemistry - Crystal structure analysis, phase diagrams, metabolic modeling, computational chemistry
- 🌌 Physics & Astronomy - Astronomical data analysis, coordinate transformations, cosmological calculations, symbolic mathematics, physics computations
- ⚙️ Engineering & Simulation - Discrete-event simulation, multi-objective optimization, metabolic engineering, systems modeling, process optimization
- 📊 Data Analysis & Visualization - Statistical analysis, network analysis, time series, publication-quality figures, large-scale data processing, EDA
- 🌍 Geospatial Science & Remote Sensing - Satellite imagery processing, GIS analysis, spatial statistics, terrain analysis, machine learning for Earth observation
- 🧪 Laboratory Automation - Liquid handling protocols, lab equipment control, workflow automation, LIMS integration
- 📚 Scientific Communication - Evidence-traceable writing, confidential authorized peer review, literature synthesis, document processing, macro-free PPTX posters, slides, schematics, and citation management
- 🔬 Multi-omics & Systems Biology - Multi-modal data integration, pathway analysis, network biology, systems-level insights
- 🧬 Protein Engineering & Design - Protein language models, structure prediction, sequence design, function annotation
- 🧰 Agent Platforms & Infrastructure - Build on Pi with SDK, RPC, extensions, custom providers/models, packages, TUI components, and session tooling
- 🎓 Research Methodology - Evidence-bounded candidate hypotheses, scientific brainstorming, critical thinking, grant writing, and qualitative low-stakes evaluation of scholarly works
- ⚖️ Regulatory & Standards - Draft evidence-preparation artifacts for ISO management-system and laboratory standards, plus analytical method validation, verification, and transfer under ICH/USP/CLSI frameworks—prepared for qualified review, never a certification, accreditation, or method-release decision
**Transform your AI coding agent into an 'AI Scientist' on your desktop!**
> 🎬 **New to Scientific Agent Skills?** Watch our [Getting Started with Scientific Agent Skills](https://youtu.be/ZxbnDaD_FVg) video for a quick walkthrough.
---

============================================================
REPO: iii-hq/iii
============================================================
# iii
![iii: point-to-point integrations vs zero-integration via shared runtime](.github/assets/zero-integration.png)
## What is iii?
iii is the easiest way to compose, extend, and observe every service in your stack in real time.
Every backend starts as a project before the first line of business logic. Queues, cron, HTTP,
state, observability, agents, and sandboxes each usually bring their own integration story. iii
collapses that into one live system surface.
```bash
iii worker add queue
iii worker add agent
iii worker add sandbox
iii worker add <anything>
```
Each worker joins the live catalog. Every other worker is notified and can call it immediately.
Browse available workers at [workers.iii.dev](https://workers.iii.dev/).
That is the agent story too: when a task needs a capability the system does not have, an agent can
add a worker, discover its functions, call them, and trace what happened. Same interface a developer
uses.
### Three Primitives
Worker _ Function _ Trigger is the entire mental model.
**Workers** are processes that register with the iii engine and then register triggers and
functions. A TypeScript API service is a worker. A Python data pipeline is a worker. A Rust
microservice is a worker. Any functionality can be transformed into a worker with a few lines of
code. Workers can also create other workers at runtime, so agents and applications can extend the
system while it is running.
**Triggers** are anything that causes a function to run. A trigger can be a direct call to a
function, an HTTP endpoint, a cron schedule, a queue subscription, a state change, a stream event,
or anything else. Triggers are declarative: the Worker defines "this function runs when this thing
happens," and iii handles routing, serialization, and delivery.
**Functions** are units of work with a stable identifier (e.g., `content::classify`,
`orders::validate`). It receives input, does work, and optionally returns output. Functions exist in

============================================================
REPO: iii-hq/workers
============================================================
# iii workers
Workers for the [iii engine](https://github.com/iii-hq/iii). Each top-level
directory is a self-contained worker module: a process that connects to the
engine over WebSocket, registers functions + triggers, and does something
useful.
Workers are installed via `iii worker add <name>`, which resolves the matching
asset for the host from the workers registry API.
## Skills
Each worker ships an agent skill under `<worker>/skills/`. Install them with the
`skills` CLI (works with Claude Code, Cursor, and 30+ other agents).
```bash
# List every worker skill in this repo
npx skills add iii-hq/workers --list
# Install one worker's skill
npx skills add iii-hq/workers --skill database
# Install several
npx skills add iii-hq/workers --skill database,coder,shell
# Install all worker skills at once
npx skills add iii-hq/workers --all
```
For the iii engine's top-level skills (mental model, SDKs, config, patterns),
see [`iii-hq/iii`](https://github.com/iii-hq/iii):
```bash
npx skills add iii-hq/iii --all
```
## Modules
| Worker | Kind | Summary |
|---|---|---|
| [`acp`](acp/) | Rust | Agent Client Protocol surface — stdio JSON-RPC, exposes iii agents as ACP sessions. |
| [`approval-gate`](approval-gate/) | Rust | Human-in-the-loop approval gate — evaluates each function call (continue / deny / hold), holds pending calls for a human, and emits `approval::pending-*` events. Binds the harness `pre_trigger` hook. See [`approval-gate/architecture/`](approval-gate/architecture/). |
| [`harness`](harness/) | Node | TS port of the iii harness stack — bundles `harness` (provider registry + credentials/settings/permissions via the `configuration` worker), `turn-orchestrator`, `hook-fanout`, `models-catalog`, the `provider-*` workers, `llm-budget`, and `context-compaction` as one pnpm monorepo. Approval is delegated to the standalone `approval-gate` worker via the `pre_trigger` hook. Conversations persist in `session-manager`. See [`harness/README.md`](harness/README.md). |

============================================================
REPO: paperclipai/paperclip
============================================================
# Paperclip is the app people use to manage AI agents for work.
Open-source orchestration for teams of AI agents.
**If OpenClaw is an _employee_, Paperclip is the _company_.**
Paperclip is a Node.js server and React UI that orchestrates a team of AI agents to run a business. Bring your own agents, assign goals, and track work and costs from one dashboard.
It looks like a task manager. Under the hood: org charts, budgets, governance, goal alignment, and agent coordination.
**Manage business goals, not pull requests.**
|        | Step            | Example                                                            |
| ------ | --------------- | ------------------------------------------------------------------ |
| **01** | Define the goal | _"Build the #1 AI note-taking app to $1M MRR."_                    |
| **02** | Hire the team   | CEO, CTO, engineers, designers, marketers — any bot, any provider. |
| **03** | Approve and run | Review strategy. Set budgets. Hit go. Monitor from the dashboard.  |
## Paperclip is right for you if
- ✅ You want to build **autonomous AI companies**
- ✅ You **coordinate many different agents** (OpenClaw, Codex, Claude, Cursor) toward a common goal
- ✅ You have **20 simultaneous Claude Code terminals** open and lose track of what everyone is doing
- ✅ You want agents running **autonomously 24/7**, but still want to audit work and chime in when needed
- ✅ You want to **monitor costs** and enforce budgets
- ✅ You want a process for managing agents that **feels like using a task manager**
- ✅ You want to manage your autonomous businesses **from your phone**
## The four pillars
Four things have to work for an organization of AI agents to actually produce: the tasks, the org, the training, and the infrastructure. Paperclip is built around exactly those four pillars.
| Pillar | Built for | What it covers |
| --- | --- | --- |
| **Agentic Task Manager** — Declare intent. Agents work. You verify the output. | Everyone, daily | Tasks, approvals & review gates · proactive agent coworkers · auditable routines & workflows · verify from diffs, screenshots & tests |
| **Org Chart for Agents** — Roles, permissions & boundaries for humans and agents. | Managers | Mixed human + agent org chart · responsibilities, delegation, specialization · governance: who can do what · scoped secrets & company boundaries |
| **Agent Employee Training** — Design, train & evaluate your AI employees. | Enablers | Skill Studio & shared org-wide skills · evals & saved test runs · active learning loops & quality metrics · performance reviews for agents |
| **Agentic OS** — The infrastructure that makes the work run. | IT & platform | Cross-provider runtime: any model, any agent · sandboxing, integrations & MCP servers · SSO, GRC, RBAC & cost controls · data privacy, internal trace collection, compounding data value |
## Features
Any agent, any runtime, one org chart. If it can receive a heartbeat, it's hired.
Every task traces back to the company mission. Agents know <em>what</em> to do and <em>why</em>.
Agents wake on a schedule, check work, and act. Delegation flows up and down the org chart.
