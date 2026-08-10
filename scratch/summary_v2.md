
============================================================
REPO: usetrmnl/terminus
============================================================

============================================================
REPO: paperclipai/companies
============================================================
# 🏢 Paperclip Companies
> **Deploy an entire AI workforce in minutes** — 16 pre-built companies, 440+ specialized agents, and 500+ battle-tested skills. From security auditors to game studios, from scientific research labs to full-stack dev shops. Plug in, power up, ship.
---
## 🚀 What Is This?
A growing catalog of ready-to-deploy agent companies for the [Paperclip](https://github.com/paperclipai/paperclip) platform. Each company is a fully configured team of AI agents — org chart, skills, governance — that you can import and run immediately.
- **🎯 Domain-Specific**: Security firms, game studios, science labs, consultancies — not generic prompt wrappers
- **🧬 Complete Org Structures**: CEO → directors → specialists, with real reporting lines and delegation
- **🛠️ Skill-Loaded**: Hundreds of reusable workflow skills agents actually know how to run
- **⚡ Import & Go**: `npx paperclipai company import --from ./trail-of-bits-security` and you're live
## Table of Contents
| Company                                                   | Agents | Skills | Source                                                                             |
| --------------------------------------------------------- | ------ | ------ | ---------------------------------------------------------------------------------- |
| [GStack](#gstack)                                         | 5      | 27     | [gstack](https://github.com/garrytan/gstack/tree/main)                             |
| [Superpowers Dev Shop](#superpowers-dev-shop)             | 4      | 14     | [superpowers](https://github.com/obra/superpowers)                                 |
| [Agency Agents](#agency-agents)                           | 167    | —      | [agency-agents](https://github.com/msitarzewski/agency-agents)                     |
| [Aeon Intelligence](#aeon-intelligence)                   | 4      | 32     | [Aeon](https://github.com/aaronjmars/aeon)                                         |
| [AgentSys Engineering](#agentsys-engineering)             | 5      | 14     | [agentsys](https://github.com/agent-sh/agentsys)                                   |
| [ClawTeam Capital](#clawteam-capital)                     | 7      | 1      | [ClawTeam](https://github.com/HKUDS/ClawTeam)                                      |
| [ClawTeam Engineering](#clawteam-engineering)             | 5      | 1      | [ClawTeam](https://github.com/HKUDS/ClawTeam)                                      |
| [ClawTeam Research Lab](#clawteam-research-lab)           | 4      | 1      | [ClawTeam](https://github.com/HKUDS/ClawTeam)                                      |
| [Donchitos Game Studio](#donchitos-game-studio)           | 48     | 38     | [Claude-Code-Game-Studios](https://github.com/Donchitos/Claude-Code-Game-Studios)  |
| [Fullstack Forge](#fullstack-forge)                       | 49     | 66     | [claude-skills](https://github.com/jeffallan/claude-skills)                        |
| [K-Dense Science Lab](#k-dense-science-lab)               | 54     | 177    | [claude-scientific-skills](https://github.com/K-Dense-AI/claude-scientific-skills) |
| [MiniMax Studio](#minimax-studio)                         | 5      | 10     | [MiniMax-AI/skills](https://github.com/MiniMax-AI/skills)                          |
| [Product Compass Consulting](#product-compass-consulting) | 48     | 65     | [pm-skills](https://github.com/phuryn/pm-skills)                                   |
| [RedOak Review](#redoak-review)                           | 5      | 6      | [claude-code-workflows](https://github.com/OneRedOak/claude-code-workflows)        |
| [TÂCHES Creative](#tâches-creative)                       | 6      | 35     | [taches-cc-resources](https://github.com/glittercowboy/taches-cc-resources)        |
| [Trail of Bits Security](#trail-of-bits-security)         | 28     | 35     | [skills](https://github.com/trailofbits/skills)                                    |
## Companies
### [GStack](./gstack)
```bash

============================================================
REPO: ultraworkers/claw-code
============================================================
# Claw Code
Join the Discords:
·
> [!IMPORTANT]
> **Claw Code is not the serious production project here.**
> This repository is closer to a museum exhibit than a product pitch, a crustacean-run artifact kept alive by clawed gajaes, swept and labeled by agents, and automatically maintained according to the harnesses above.
>
> As already described in the project philosophy, this is not meant to be hand-operated like a normal product repo. It is an **agent-managed exhibit**: the harnesses plan, execute, verify, label, and preserve the artifact while the crabs keep the tank running.
>
> If you want to actually run work, start with **[LazyCodex](https://github.com/code-yeongyu/lazycodex)** or **[Gajae-Code](https://github.com/Yeachan-Heo/gajae-code)**. If you want to inspect the strange little fossil of the Claw Code moment, continue below.
>
> For the longer public explanation behind this philosophy, see [here](https://x.com/realsigridjin/status/2039472968624185713).
·
·
·
·
·
·
·
Claw Code is the public Rust implementation of the `claw` CLI agent harness.
The canonical implementation lives in [`rust/`](./rust), and the current source of truth for this repository is **ultraworkers/claw-code**.
> [!IMPORTANT]
> Start with [`USAGE.md`](./USAGE.md) for build, auth, CLI, session, and parity-harness workflows. For file submission/navigation questions, see [Navigation and file context](./docs/navigation-file-context.md). For local OpenAI-compatible models and offline skill installs, see [Local OpenAI-compatible providers and skills setup](./docs/local-openai-compatible-providers.md). Windows users can jump to the PowerShell-first [Windows install and release quickstart](./docs/windows-install-release.md). Make `claw doctor` your first health check after building, use [`rust/README.md`](./rust/README.md) for crate-level details, read [`PARITY.md`](./PARITY.md) for the current Rust-port checkpoint, and see [`docs/container.md`](./docs/container.md) for the container-first workflow.
>
> **ACP / Zed status:** `claw-code` does not ship an ACP/Zed daemon or JSON-RPC entrypoint yet. Run `claw acp` (or `claw --acp`) for the current status instead of guessing from source layout; `claw acp serve` is currently a discoverability alias only, returns status with exit code 0, and real ACP support remains tracked separately in `ROADMAP.md`. For the public JSON contract, see [`docs/g011-acp-json-rpc-status-contract.md`](./docs/g011-acp-json-rpc-status-contract.md).
## Current repository shape
- **`rust/`** — canonical Rust workspace and the `claw` CLI binary
- **`USAGE.md`** — task-oriented usage guide for the current product surface
- **`PARITY.md`** — Rust-port parity status and migration notes
- **`ROADMAP.md`** — active roadmap and cleanup backlog
- **`PHILOSOPHY.md`** — project intent and system-design framing

============================================================
REPO: wanshuiyin/Auto-claude-code-research-in-sleep
============================================================
# Auto-claude-code-research-in-sleep (ARIS ⚔️🌙)
💡 *Use ARIS as a skill-based workflow in [Claude Code](https://docs.anthropic.com/en/docs/claude-code) / [Codex CLI](skills/skills-codex/) / [Cursor](docs/CURSOR_ADAPTATION.md) / [Trae](docs/TRAE_ARIS_RUNBOOK_EN.md) / [Antigravity](docs/ANTIGRAVITY_ADAPTATION.md) / [GitHub Copilot CLI](docs/COPILOT_CLI_ADAPTATION.md) / [OpenClaw](docs/OPENCLAW_ADAPTATION.md), or get the full experience with the standalone **[ARIS-Code](docs/ARIS-Code-README_EN.md)** CLI — enjoy any way you like!*
🌱 *ARIS is a methodology, not a platform. What matters is the research workflow — take it wherever you go.*
🤖 **AI agents:** Read [`AGENT_GUIDE.md`](AGENT_GUIDE.md) instead — structured for LLM consumption, not human browsing.
🛡️ **ARIS audits its own output → now [Anti-Autoresearch](https://github.com/wanshuiyin/Anti-Autoresearch) audits everyone's.** It catalogs **46 integrity hack-patterns across 8 families (A–H), plus 13 zero-verdict-weight AI-style impressions and 2 advisory signals — 61 signals total** — and checks a submission for them **end-to-end**, producing a deterministic, reviewer-ready integrity report. *Self-consistency + fabrication forensics, **not** an AI-text detector.*
🎬 **ARIS goes multimodal → [ARIS-Movie-Director](https://github.com/wanshuiyin/ARIS-Movie-Director)** — hand it a rough story and get back a movie told in still frames, checked scene by scene (the reference run has 19 scenes).
Long stories usually break when the model forgets earlier details or judges its own work — so ARIS keeps a research-wiki for memory and has other models check every frame.
> 🧭 *The same loop also makes clean method / flow diagrams — the figure above was made with it. Entry points in **[ARIS-Movie-Director](https://github.com/wanshuiyin/ARIS-Movie-Director)**: [`/movie-pipeline`](https://github.com/wanshuiyin/ARIS-Movie-Director/blob/main/skills/movie-pipeline/SKILL.md) and [`/method-figure`](https://github.com/wanshuiyin/ARIS-Movie-Director/blob/main/skills/method-figure/SKILL.md), the skill that made this figure.*
🎯 **准备 2026 AI 秋招？** → [**🌐 ARIS-in-AI-Offer**](https://wanshuiyin.github.io/ARIS-in-AI-Offer/) · [GitHub repo](https://github.com/wanshuiyin/ARIS-in-AI-Offer) · [中文 README](https://github.com/wanshuiyin/ARIS-in-AI-Offer/blob/main/README_CN.md) —— 23 篇双语 ML / LLM / 多模态 / 生成式 / Agent 面试 cheat sheet，每篇 = 公式推导 + 从零 PyTorch + 25 高频面试题（L1 / L2 / L3），全部由 ARIS 的 `/render-html` 自动生成。**希望大家秋招轻松一点 🌱**
> 📝 *Three long-form blogs, cross-model collaborative writing via `/render-html` — [Continuous DLM — a representation-perspective survey (2026 H1)](https://wanshuiyin.github.io/ARIS-in-AI-Offer/blogs/continuous_dlm_representation_perspective.html) · [Cosmos 3 — understanding + generation in one Transformer (MoT)](https://wanshuiyin.github.io/ARIS-in-AI-Offer/blogs/cosmos3_mot_guide.html) · [Diffusion × representation × manifold learning](https://wanshuiyin.github.io/ARIS-in-AI-Offer/blogs/diffusion_representation_manifold.html).*
🛰 **Keep an eye on your agent windows** — [Claude Fleet](https://github.com/tianyilt/claude-fleet) (by [@tianyilt](https://github.com/tianyilt); local read-only dashboard for many parallel Claude Code / Codex windows, full-text transcript search — worth a ⭐), or the lighter built-in [ARIS-Monitor](aris-monitor/) (a tiny always-on-top macOS widget that lights up 🔴 when a session waits for your approval; click to jump there).
**ARIS-Monitor** — built-in, no clone / no pip / no browser:
```bash
cd aris-monitor && ./run.sh
# a borderless panel floats top-right; click a row to jump to that terminal
```
**Claude Fleet** — full web dashboard:
```bash
git clone https://github.com/tianyilt/claude-fleet
cd claude-fleet && bash run.sh
# open http://127.0.0.1:7878 in your browser
```
🚀 **Beyond 科研 → 任何 "研究"**：[**ARIS-Anything**](https://github.com/wanshuiyin/ARIS-Anything) 把 ARIS 的五步 loop（plan / draft / 对抗审 / 迭代 / 持久化）推广到非学术的结构化研究——投资尽调 / 法律研究 / 市场研究 / 自驱学习 / 调查新闻 / 工程复盘等。
📰 **ARIS-Code v0.4.24** (2026-08) — latest is the **Claude 5 model refresh** ([#392](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/issues/392)): first-class **Claude Opus 5** (new default, same $5/$25 tier) and **Claude Fable 5** (Mythos-class flagship, correct $10/$50 pricing) — `/model` picker + `fable`/`opus`/`sonnet` aliases + an ordered availability chain (Opus 5 → 4.8 → 4.7) so accounts without Claude 5 access keep working untouched. Recent headliners: **v0.4.23 — output folding** (tool output folds to a few lines, `ARIS_TOOL_OUTPUT_LINES=0` restores full dumps; **81 bundled skills** incl. the [Anti-Autoresearch](https://github.com/wanshuiyin/Anti-Autoresearch) `/integrity-forensics` launcher) and **v0.4.17 — the MCP release** (cross-model review needs no OpenAI API key — `aris setup` wires your **ChatGPT subscription** in as reviewer via *Codex MCP*). Caps a 20-release run (v0.4.5 → v0.4.24); per-release detail below. Credits: [@GetIT-Sunday](https://github.com/GetIT-Sunday), [@Anduin9527](https://github.com/Anduin9527), [@GO-player-hhy](https://github.com/GO-player-hhy), [@Jxy-yxJ](https://github.com/Jxy-yxJ), [@screw-44](https://github.com/screw-44), [@StevenUST](https://github.com/StevenUST), [@opposj](https://github.com/opposj), [@ShijunLei-cn](https://github.com/ShijunLei-cn), [@algojogacor](https://github.com/algojogacor), [@YukinoshitaLove](https://github.com/YukinoshitaLove).
> <details><summary>Per-release details (v0.4.5 → v0.4.24)</summary>
>
> **v0.4.24** (2026-08-09) — **the Claude 5 model refresh** ([#392](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/issues/392), requested by [@YukinoshitaLove](https://github.com/YukinoshitaLove)). Explicit `--model claude-opus-5` / `claude-fable-5` already passed through on every platform — this release makes them first-class. **Default → `claude-opus-5`** (main session, subagents, `aris setup`; same $5/$25 tier as Opus 4.8); the v0.4.18 availability fallback becomes an ordered **chain walk** (Opus 5 → Opus 4.8 → Opus 4.7, one step per precise `404 not_found_error`, explicit choices never silently change) — the naive constant swap would have stranded 4.7-only accounts and configs saved by v0.4.23's setup, a regression the cross-model review caught and an end-to-end mock-404 chain test now locks. `/model` picker adds Fable 5 / Opus 5 / Sonnet 5; new `fable` alias. **New Mythos-class pricing tier** (`fable`/`mythos` = $10/$50, cache write $12.50 / read $1, verified 2026-08 — previously fell to the conservative $15/$75 unknown-model tier, a 1.5× over-estimate); Opus 5 / Sonnet 5 pinned on their existing branches. Tests: api 41 / aris-cli 213 + 4 e2e / runtime 226 / tools 70 / commands 5, all green; live smoke on claude-opus-5, claude-fable-5 and the fable alias. Codex MCP (gpt-5.6-sol xhigh) implementation gate: NO-GO → NO-GO → GO.
>
> **v0.4.23** (2026-08-02) — **the output-folding release** (top real-user complaint: "aris dumps thinking and the full content of documents it reads onto the screen"). **🧹 Tool-output folding, display layer ONLY**: the disk-verified culprits were format_read_result appending the ENTIRE read payload, bash pushing full stdout/stderr, grep dumping its full content blob, and the edit preview capping line counts but not line LENGTH. Now Read/Grep show the first 6 lines, Bash shows first 4 + last 4 per stream (stderr keeps its red), each kept line capped at 240 chars (the minified-single-line case), then one dim "… (+N more lines — set ARIS_TOOL_OUTPUT_LINES=0 for full output)" hint. ONE env knob: unset = defaults, a positive integer overrides every tool, 0 = the exact old display; the session, model context, `--output-format json` and `/export` are untouched and always complete. Thinking was verified to never print (Anthropic deltas only accumulate; Kimi reasoning_content only feeds the replay cache — the "thinking dump" perception came from the document dumps); two end-to-end sentinel tests (real binary vs mock SSE server) lock that thinking/reasoning never reaches the terminal. Interactive expand/collapse was deliberately rejected as over-engineering. **🐛 Bash timeout now kills the command**: a timed-out call reported `interrupted: true` while the dropped tokio future left the child RUNNING — side effects landed after the report; now kill_on_drop (escape hatch `ARIS_BASH_KILL_ON_TIMEOUT=0`; background tasks untouched; locked by a real behavioral test — a timed-out "sleep 1 && touch marker" must not create the marker). **📦 Bundle 79→81** (pin 7182624 → 3e49e63): **`/integrity-forensics`** — the Anti-Autoresearch SHA-pinned thin launcher (span-anchored evidence ledger → GPT auditors propose → deterministic rules-only adjudicator decides → typed BLOCK/WARN gate + obligations ledger) — and `/web-debug-search`, +tools/forensics_gate.py (29 helpers, 104 embedded resources). **🎁 Also**: grep's content mode no longer shows a false "0 matches" above real results (the gate caught that `"numMatches": null` serializes with the key present, defeating a naive presence check); all four crates' local-mock-server tests are now proxy-immune (a shell with http(s)_proxy set used to turn 15 tests red on a released tag — 127.0.0.1 was routed through the proxy). The rest of the runtime-state package (compaction re-arm, failed-turn cleanup, /cost dollars, SSE tail) ships as v0.4.24 — the cached-token cost fix is deliberately held back because it changes what the compaction trigger measures. Tests: api 41 / aris-cli 212 + 3 e2e / runtime 225 / tools 69 / commands 5 (+13), all green **under a live proxy**; new-code clippy delta zero. Codex MCP (gpt-5.6-sol): ultra scope+design adjudication, then a 3-round implementation gate (round 1 caught the null-serialization defeat and a non-hermetic behavioral test; round 3 GO).
>
> **v0.4.22** (2026-07-12) — **the skills-resync + GPT-5.6-Sol release**. **📦 Bundle resync** (pin 7e3ab67 → 7182624, 93 commits): **79 bundled skills** (+`meta-apply`, +`paper-poster-html`; `paper-poster` retired to a redirect stub), 28 tools helpers (8 new: capture_filter, evidence_check, iteration_log, provenance, run_state, threat_scan, meta_opt/trigger_eval + sample evals), 11 new shared-references docs (fan-out-pattern, acceptance-gate, external-cadence, skill-governance, compute-env-contract, resumable-runs, evidence-precheck, injection-hygiene, capture-antipatterns, output-composition, taste-calibration); sync hardening — `ARIS_SYNC_EXPECT_SHA` guard (aborts before touching assets if main moved; it caught a real move on first use) + exact-inventory drift tests + the vendored posterly MIT license text now ships. **🎛 GPT-5.6-Sol two-tier reviewer alignment**: the CLI's system-prompt nudge now passes the skills' explicit `model: gpt-5.6-sol` + per-call effort pins through (the v0.4.17 blanket "never pass a model" rule would have silently stripped deep audits from ultra to xhigh), carries the canonical capability-only fallback chain (effort-unsupported → same model xhigh, deep tier only; model-unknown → explicit gpt-5.5+xhigh; never degrade on transport-class errors; an explicit call-level override disables the chain), pins `approval-policy: "never"` + explicit `sandbox` on every fresh codex call, and makes the HTTP fallback pre-dispatch-only with parameter stripping; the HTTP LlmReview default deliberately stays gpt-5.5 pending a real smoke; gpt-5.6 family pricing (sol $5/$30, terra $2.50/$15, luna $1/$6) verified against the official page; banner/Reviewer display/`/reviewer` are honest about primary-vs-fallback (pure-Codex setups get status + guidance instead of a fake picker). **🐛 8 verified fixes**: explicit `--model` was silently overridden by the saved executor model (model provenance now tracked end-to-end; the 4.8→4.7 availability fallback respects explicit choices; `/model` and `/setup` re-arm it); saved models no longer leak across provider transports (blank saved models count as absent; OpenAI transport with no model source fails fast; the first-run wizard's config now actually feeds startup model resolution); `--output-format json` never prompts (locked by a real end-to-end binary test against a mock SSE server); **Windows `aris login` fixed** (PKCE randomness read /dev/urandom → getrandom); **Windows command probing fixed** (the PowerShell tool probed itself through `sh`; now where.exe); codex `.cmd` shims classified honestly (three-state probe; setup requires explicit confirmation before writing a config the MCP client can't spawn); nested config.json warns instead of silently parsing to all-defaults; NotebookEdit mints collision-free cell ids. **🖥 New windows-latest CI job** (workspace compile gate + three targeted test groups, each guarded against silent 0-test green). Tests: api 41 / aris-cli 204 + 1 e2e / runtime 223 / tools 69 / commands 5 (+54), all green; new-code clippy delta zero. Codex MCP (gpt-5.6-sol): **ultra** design gate — 5 rounds, NO-GO ×4 → GO — then a 3-round implementation gate whose round 2 caught a first-run config-wiring blocker before it shipped; 4 implementation subagents, every report disk-verified.

============================================================
REPO: wanshuiyin/Anti-Autoresearch
============================================================
# Anti-Autoresearch 🛡️
### 🔬 The field has tolerated unreliable autoresearch long enough — Anti-Autoresearch is the read that finally catches it.
***天下苦 autoresearch 久矣 —— Anti-Autoresearch 替研究者们一眼看穿不靠谱的工作。***
> 🏆 **Built on a battle-tested foundation: [ARIS](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep)** (~12.5k★ · HuggingFace Daily Papers #1 · 78+ skills across 7+ platforms). Anti-Autoresearch points ARIS's production audit DNA (experiment-audit · paper-claim-audit · citation-audit · kill-argument) **outward** — auditing a third party's submission instead of your own.
Autoresearch has gone mainstream, and a fast-growing share of what reaches the review
pile is machine-generated — and a lot of it **doesn't hold up**: tables that don't
match the text, baselines that aren't there, open-sourced code that won't reproduce
its own paper. Reviewers, area chairs, and honest authors increasingly need to
**verify** that, not just suspect it.
> Regardless of *who or what* wrote a paper, does the science hold together and
> reflect its own evidence? Anti-Autoresearch audits a submission for
> **self-consistency** and **fabrication**, and produces a span-anchored,
> reviewer-ready report. It is **not** an *opaque* AI-text classifier (no authorship
> probabilities, no "AI-written" verdict) and does **not** judge misconduct — it surfaces
> discrepancies a human reviewer should investigate. Separately, it lists transparent,
> itemized **AI writing-style impressions** in a quarantined, **zero-verdict-weight**
> section (a paper can be integrity-`CLEAN` while listing many), because reviewers react to them.
---
## 🧭 What's inside
**46 integrity patterns across 8 families** — the coverage vocabulary every finding cites — plus **13 zero-weight AI writing-style impressions** and **2 advisories**:
| | Family | Catches |
|---|--------|---------|
| **A** | Numeric self-consistency | 数值自洽:table vs text vs delta arithmetic that doesn't add up |
| **B** | Method & scope | 方法与范围:the described method/scope ≠ what was actually done |
| **C** | Baseline integrity | baseline 诚信:missing, weak, or unfairly configured comparisons |
| **D** | Experiment integrity | 实验诚信:fake ground truth, phantom results, code ≠ numbers (needs code) |
| **E** | Citation integrity | 引用诚信:fabricated, misattributed, or retracted references |
| **F** | Presentation & surface | 表面信号:layout / prose / figure signals — capped at `minor` |
| **G** | Proof & derivation | 证明诚信:skipped obligations, circular or invalid derivations |
| **H** | Evaluation design & validity | 评测设计:data leakage, LLM-judge validity, selective reporting |
Delivered as **11 skills + 1 orchestrating workflow** on a deterministic spine: a span-anchored, hashed evidence **ledger** → LLM auditors that only **propose** findings → a rules-only **reporter** that lists every proposal with what the auditor said about it, and summarizes — with 8 patterns eval-gated end-to-end (GRIM · GRIMMER · statcheck · delta arithmetic · hedge-density · …) and the whole gate in CI.

============================================================
REPO: wanshuiyin/ARIS-Anything
============================================================
# ARIS-Anything
> *Research as **科研** (kēyán) covers academic science.
> Research as **研究** (yánjiū) covers everything else — investment, law, product, market, learning, investigation, journalism, engineering post-mortems, ...*
>
> **ARIS-Anything** explores how the ARIS methodology — cross-model adversarial review, skill-based workflows, persistent knowledge wikis — generalizes from academic research to any structured inquiry.
📖 **中文版 (Chinese version)**: [README_CN.md](README_CN.md)
---
## 🏆 Why this isn't vaporware
ARIS-Anything is an exploration, not a from-scratch venture. The methodology is **already battle-tested at scale**:
- ⭐ **~10k GitHub stars** on the [main ARIS repo](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep) — top-trending AI research agent
- 🥇 **HuggingFace Daily Papers #1** — [arXiv:2605.03042](https://huggingface.co/papers/2605.03042) top of the day
- 🏆 **AI Digital Crew · Project of the Day** (2026-03-14)
- 📰 **Featured on PaperWeekly** + [awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills)
- 🛠 **75+ research skills** spanning idea exploration → experiments → papers → rebuttals → talks
- 🌐 **7+ platforms supported** — Claude Code · Codex CLI · Cursor · Trae · Antigravity · GitHub Copilot CLI · OpenClaw
- 🔧 **ARIS-Code standalone CLI** — multi-provider runtime, no Claude Code dependency required
- 📚 **First downstream repo already shipped two artifacts**: [**ARIS-in-AI-Offer**](https://github.com/wanshuiyin/ARIS-in-AI-Offer) bundles two production deliverables on the same `/render-html` workflow — (1) 23 bilingual interview cheat sheets (the original), and (2) [**ARIS-Homepage v1**](https://wanshuiyin.github.io/) (`/homepage-generator` skill: CV → fact-checked single-file academic homepage; DBLP/arXiv hard-audit on venue/year/author mismatches and fabricated awards). Two completely different deliverables, one workflow — proof the ARIS pattern carries beyond science papers.
ARIS-Anything is the next reach: take the proven loop, point it at non-academic structured inquiry. Everything below is grounded in what already works — not a wishlist.
---
## 🌟 The Premise
[**ARIS — Auto Research in Sleep**](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep) was built for academic research: find ideas → run experiments → write papers → handle rebuttals. But the underlying loop is general:
1. **Plan** the inquiry — structure the question, scope, deliverable
2. **Draft** the work — executor model produces the first version
3. **Review** adversarially — a different-family reviewer model finds flaws (Claude × GPT-5.5 xhigh × Gemini)
4. **Iterate** until convergence — fix → re-review → ship
5. **Persist** — write findings to a versioned wiki so future-you starts from the cumulative state, not zero
The Chinese wordplay matters: **科研 ⊂ 研究**. Academic research is one specific shape of inquiry; the broader 研究 covers any structured investigation where you have a question, evidence, and a deliverable. The same five-step loop carries over.
---
## 🚀 Incoming siblings
The "Anything" exploration runs in parallel with several domain-specific repos under early development. Each one re-uses the ARIS core loop with a domain-appropriate deliverable shape — same five-step inquiry, different cover sheet:
| Repo | Domain | Key idea |

============================================================
REPO: tianyilt/claude-fleet
============================================================
English | [中文](README.zh-CN.md)
# Claude Fleet
When you're vibe coding with 5–7 Claude Code windows open at once, you need one
place to see what every window is doing — who's stuck, who's waiting on you, who's
done.
![](docs/screenshot-hero.png)
## Run it in 30 seconds
```bash
git clone https://github.com/tianyilt/claude-fleet
cd claude-fleet && bash run.sh
# open http://127.0.0.1:7878 in your browser
```
The first run creates a venv and installs dependencies automatically — nothing to set up.
## Install options
**Run as a macOS app (recommended on Mac).** A signed, double-clickable `.app`:
```bash
./scripts/build-app.sh --install      # builds + copies to /Applications
```
Resume/Fork open a new terminal via `open` (LaunchServices) in your **default
terminal** — whatever handles `.command` (Terminal.app, or iTerm2 / Warp if you
set it) — no Automation permission needed, so they work even after a restart.
**Focus** (raising the tab that owns a session) does use AppleScript; the first
time you use it, approve **“Claude Fleet” wants to control “Terminal.app”** (or
your terminal of choice) — the signed app makes that grant stick. For development
with hot-reload, use `./run.sh`.
**Run anywhere (Windows / Linux).** The dashboard, history, search and monitoring
are cross-platform:
```bash
pip install -e .
./run.sh        # macOS/Linux
run.bat         # Windows

============================================================
REPO: EvoScientist/EvoScientist
============================================================
---
**English | [简体中文](./README.zh-CN.md)**
**EvoScientist aims to harness vibe research by enabling self-evolving AI scientists that autonomously explore, generate insights, and iteratively improve.
It is designed to be opinionated and ready to use out of the box, offering a living research system that grows alongside evolving agent skills, toolsets, and memory bases.
Moving beyond traditional human-in-the-loop systems, EvoScientist adopts a human-on-the-loop paradigm, where AI acts as a research buddy that co-evolves with human researchers and internalizes scholarly taste and scientific judgment.**
## ✨ Features
- **🤖 Multi-Agent Team** — 6 sub-agents (plan, research, code, debug, analyze, write) working in concert.
- **🧠 Self-Evolving Memory** — Auto-distilled each turn, self-linking into a knowledge graph that grows across sessions.
- **🛠️ AutoSkills** — Distills recurring patterns from its own memory into reusable skills on a schedule — proposed for your review via `/autoskills`.
- **🌐 Multi-Provider** — Anthropic, OpenAI, Google, MiniMax, NVIDIA — one config to switch.
- **📱 Multi-Channel** — CLI as the hub; Telegram, Slack, Feishu, WeChat, and more — one agent session.
- **🖥️ Desktop WebUI** — Workspace-panel web app, one terminal via `--ui webui`.
- **🔬 Scientific Workflow** — Intake → plan → execute → evaluate → write → verify.
- **⏰ Scheduled Tasks** — Automate recurring research on a cron-style schedule — it runs on its own and reports back.
- **🔄 Code Generation Modes** — More Effort (iterative refinement), continuously improving code quality.
- **⚡ Adaptive Tools** — Per-turn tool selection keeps only relevant tools visible, reducing noise.
- **✂️ Context Editing** — Dynamic system prompt rewriting based on conversation state.
- **🔌 MCP & Skills** — Plug in MCP servers or install skills from GitHub on the fly.
> [!TIP]
> Looking for ready-to-use research skills? Check out [**EvoSkills**](https://github.com/EvoScientist/EvoSkills) — powered by [**EvoScientist**](https://github.com/EvoScientist/EvoScientist)'s engine and installable skills, the entire end-to-end research lifecycle is covered out of the box. [**EvoSkills**](https://github.com/EvoScientist/EvoSkills) are also compatible with other CLI coding agents.
## 🔥 News
- **[03 Jun 2026]** 🥈 Ranked #2 overall — and 🥇 #1 among `GPT-5.4`-based agents — on [ResearchClawBench](https://github.com/InternScience/ResearchClawBench) (Agent Mode)! [**Leaderboard**](https://internscience.github.io/ResearchClawBench-Home/) 👈
- **[18 Apr 2026]** 🥇 Ranked #1 on [DeepResearch Bench](https://deepresearch-bench.github.io/) at submission time! [**Leaderboard**](https://huggingface.co/spaces/muset-ai/DeepResearch-Bench-Leaderboard) 👈
- **[13 Apr 2026]** 🥇 Reclaimed #1 on [DeepResearch Bench II](https://agentresearchlab.com/benchmarks/deepresearch-bench-ii/index.html#leaderboard) at submission time! [**Leaderboard**](https://agentresearchlab.com/benchmarks/deepresearch-bench-ii/index.html#leaderboard) 👈
- **[26 Mar 2026]** 🥇 Ranked #1 on [AstaBench Data Analysis](https://allenai-asta-bench-leaderboard.hf.space/home) at submission time! [**Leaderboard**](https://allenai-asta-bench-leaderboard.hf.space/data-analysis) 👈
- **[25 Mar 2026]** 🥇 Ranked #1 on [AstaBench Code & Execution](https://allenai-asta-bench-leaderboard.hf.space/home) at submission time! [**Leaderboard**](https://allenai-asta-bench-leaderboard.hf.space/code-execution) 👈
- **[13 Mar 2026]** 🚀 [**EvoScientist**](https://github.com/EvoScientist/EvoScientist) officially debuts!
- **[11 Mar 2026]** ⛳ Technical Report is live! [**Check it out**](https://arxiv.org/abs/2603.08127) 👈
- **[06 Mar 2026]** 🥇 Ranked #1 on [DeepResearch Bench II](https://agentresearchlab.com/benchmarks/deepresearch-bench-ii/index.html#leaderboard) at submission time! [**Leaderboard**](https://agentresearchlab.com/benchmarks/deepresearch-bench-ii/index.html#leaderboard) 👈
- **[24 Nov 2025]** 🏆 6/6 accepted at [ICAIS 2025](https://icais.ai/) AI Scientist Track — Best Paper & AI Reviewer's Appraisal Award! [**Details**](https://airaxiv.com/papers/?q=zacharyzhang2022%40gmail.com) 👈
- **[07 Aug 2026]** **[v0.2.6](https://github.com/EvoScientist/EvoScientist/releases/tag/v0.2.6)** — Agent teams: invite installed expert skills into a session (`/expert <name>`) for in-turn consults, parallel panels, or background jobs; configurable bind hosts for the langgraph dev backend and WebUI (loopback by default); Volcengine Coding Plan provider (`glm-5.2`, `kimi-k2.5`); Qwen3.8-Max on DashScope and OpenRouter (1M context); deepagents 0.7.5 with media placeholders instead of provider 400s; a blank tool-call ID fix for Kimi/Zhipu sessions.
