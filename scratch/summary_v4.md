
============================================================
REPO: GoogleCloudPlatform/scion
============================================================
# Scion
Run multiple agents in parallel — each in its own container, with its own workspace, collaborating on your code or project files simultaneously.
_sci·on /ˈsīən/ — a young shoot or twig, cut for grafting or rooting._
Scion is an experimental multi-agent orchestration testbed designed to manage "deep agents" running in containers.
Scion orchestrates "deep agents" (Claude Code, Gemini CLI, and others) as isolated, concurrent processes. Each agent gets its own container, (optional) git worktree, and credentials — so they can work on different parts of your project without stepping on each other. Agents run locally, on remote VMs, or across Kubernetes clusters.
Rather than prescribing rigid orchestration patterns, Scion takes a "less is more" approach: agents dynamically learn a CLI tool, letting the models themselves decide how to coordinate among agents. This makes it a rapid prototype testbed for experimenting with multi-agent patterns through natural language prompting. Read more in [Philosophy](https://googlecloudplatform.github.io/scion/philosophy/).
## In Action
While Scion is powered by coding agents, and can absolutely be used for multi-agent software development, it isn't exclusive to software development, but is a orchestration tool and layer, which can be combined with other agent augmenting system (task tracking, memory, etc - see below on compliments to Scion). We have used it internally at Google for exploring software porting, used for market research, product testing, and more. We are exploring it for use in Cloud operations, and scientific research.  Below are a couple other demonstrations of how agents can collaborate in interesting scenarios.
### Scion Films
The [Scion Films](https://films.scion-ai.dev/) project was an exploration in how to iterate and improve multi-agent orchestration, skills, and tools in a domain that is not as innate or "verifiable" as classic auto-research problems where a simple computable scoring metric was used. Instead, human viewer feedback and agent retrospectives were used to iterate across a series of "pilots" - for fun, we use agents to document the entire proces, and in the end, they used the same refined tools and process to make a documentary film.
### Relics of Athenaeum
[Relics of Athenaeum](https://github.com/ptone/scion-athenaeum) is an "agent game" that demonstrates multi-agent orchestration defined entirely in markdown. A group of agents collaborate to solve computational puzzles, coordinating through group and direct messaging — all running in containers on off-the-shelf harnesses.
The visualization above replays the actual telemetry collected from messages and file access in the shared workspace while the agents solved the challenges of the game. While this is a "game", the same process of team definition works for software engineering, data research, and platform engineering workflows.
## Scion architecture companions
Scion acts as a core component in a multi-agent solution, but does not try to package all capabilities into a monolithic and over-opinionated solution, instead trying to offer value in durable and well structure abstractions and primitives.  In that sense it is like a game engine upon which you build your game title. First and foremost this comes down to defining your own agent templates, which increasingly are based on skills. If you are doing software factory work, you will want some task management system which could be Github issues, Linear, or something more agent-centric like [Farmtable](https://github.com/scion-frontiers/farmtable), or [Beads](https://github.com/gastownhall/beads). You also might want to introduce a component that manages agent memory (although Scion's use of shared filesystem may get you a long way), network proxy access, etc.
## Quick Start
### Install with Homebrew (recommended)
The easiest way to get Scion is the community [homebrew-scion](https://github.com/homebrew-scion/homebrew-scion) tap:
```bash
brew tap homebrew-scion/scion
brew install homebrew-scion/scion/scion
```
This installs the `scion` CLI — pre-configured to use `ghcr.io/homebrew-scion` as the default image registry — along with the `scion-plugin-telegram` broker plugin. To upgrade later:
```bash
brew update && brew upgrade homebrew-scion/scion/scion
```
Then start the Workstation server:
```bash
scion server start
```
Your browser opens to the onboarding wizard at `http://127.0.0.1:8080/onboarding`, which walks you through runtime detection (Docker, Podman, or Apple Container), identity configuration, container image setup, and creating your first workspace.
After onboarding, start your first agent:
```bash
scion start my-agent "Your task here"
```
See the [homebrew-scion tap](https://github.com/homebrew-scion/homebrew-scion) for the full list of pre-built multi-arch container images and distribution details.
### Install from Source
See the full [Installation Guide](https://googlecloudplatform.github.io/scion/getting-started/install/), or install from source (requires Go 1.22+):
```bash
go install github.com/GoogleCloudPlatform/scion/cmd/scion@latest
```
> **Warning:** `go install` builds only the Go binary. It does not build or embed the web frontend, so `scion server start` will serve a blank web UI with missing frontend assets. Use Homebrew for a ready-to-run install, or build from a clone with `make all` before installing the binary.
### Initialize your machine and a Project (project)
> **Tip:** If you used `scion server start` above, the onboarding wizard handles machine initialization automatically — you can skip this section.
Navigate to your project and create a Scion project (the `.scion` directory that holds agent config):
```bash
scion init --machine
cd my-project
scion init
```
> **Tip:** Add `.scion/agents` to your `.gitignore` to avoid issues with nested git worktrees.

============================================================
REPO: Shubhamsaboo/awesome-llm-apps
============================================================
# Awesome LLM Apps
**100+ open-source AI agents, agent skills, and RAG apps. Hand-built, tested end-to-end, Apache-2.0.**
Clone it, ship it, sell it - 100% free and open-source
Works with Claude, Gemini, GPT, DeepSeek, Llama, Qwen and other open-source models.
**[Step-by-step tutorials on Unwind AI](https://www.theunwindai.com)** · **[Quick start](#-run-one-now)** · **[Browse all templates](#-browse-all-templates)**
## 🚀 Run one now
Give your coding agent a new skill in 10 seconds:
```bash
npx skills add https://github.com/Shubhamsaboo/awesome-llm-apps/tree/main/agent_skills/project-graveyard
```
Then ask it: *"why do I never finish my side projects?"*
Or clone and run any agent in 30 seconds:
```bash
git clone https://github.com/Shubhamsaboo/awesome-llm-apps.git
cd awesome-llm-apps/starter_ai_agents/ai_travel_agent
pip install -r requirements.txt
streamlit run travel_agent.py
```
> 📬 New templates drop weekly. [Get them in your inbox on Unwind AI](https://www.theunwindai.com).
## 📂 Browse all templates
### 🧩 Agent Skills
*Give your coding agent new abilities. One command to install, plain English to use. Every skill ships real code and passes a security + eval CI gate. Works with Claude Code, Codex, Cursor, and other coding agents. [Browse all skills →](agent_skills/)*
*   [⚰️ Project Graveyard](agent_skills/project-graveyard/) - Finds every side project you abandoned, tells you why each one died, and helps you finish the one worth going back to
*   [🔭 Scope Creep Detector](agent_skills/scope-creep-detector/) - Checks whether a diff grew beyond its stated intent and recommends what to keep, split, or justify
*   [🏺 Commit Archaeologist](agent_skills/commit-archaeologist/) - Reconstructs why a file or code region exists from its introducing commit, later edits, co-changes, and intent clues
*   [🩺 Dependency Doctor](agent_skills/dependency-doctor/) - Checks a dependency manifest for standard-library pins, obsolete backports, unpinned entries, duplicate constraints, and yanked releases
*   [🧠 Advisor Orchestrator Worker](agent_skills/advisor-orchestrator-worker/) - Meta Loop with Claude Fable 5 as advisor, GPT-5.6 as orchestrator, and Gemini 3.5 Flash as worker
*   [♾️ Self-Improving Agent Skills](agent_skills/self-improving-agent-skills/) - Automatically optimize agent skills using Gemini and ADK
### 🌱 Starter AI Agents
*Single-file agents that run with just an API key - a great place to start.*
*   [🎙️ AI Blog to Podcast Agent](starter_ai_agents/ai_blog_to_podcast_agent/) - Turn any blog URL into a narrated podcast episode
*   [❤️‍🩹 AI Breakup Recovery Agent](starter_ai_agents/ai_breakup_recovery_agent/) - An agent team that talks you through the post-breakup spiral
*   [📊 AI Data Analysis Agent](starter_ai_agents/ai_data_analysis_agent/) - Ask questions of any CSV or Excel file in plain English
*   [🩻 AI Medical Imaging Agent](starter_ai_agents/ai_medical_imaging_agent/) - Diagnostic analysis of X-rays and scans with Gemini
*   [😂 AI Meme Generator Agent (Browser)](starter_ai_agents/ai_meme_generator_agent_browseruse/) - Makes memes by driving a real browser, not an image API
*   [🎵 AI Music Generator Agent](starter_ai_agents/ai_music_generator_agent/) - Prompt in, MP3 track out
*   [🛫 AI Travel Agent (Local & Cloud)](starter_ai_agents/ai_travel_agent/) - Personalized day-by-day travel itineraries
*   [✨ Gemini Multimodal Agent](starter_ai_agents/multimodal_ai_agent/) - Video analysis plus web search in one agent
*   [🔄 Mixture of Agents](starter_ai_agents/mixture_of_agents/) - Multiple LLMs answer, one aggregates the best response
*   [📊 xAI Finance Agent](starter_ai_agents/xai_finance_agent/) - Real-time stock analysis powered by Grok
*   [🔍 OpenAI Research Agent](starter_ai_agents/openai_research_agent/) - Multi-agent topic research with the OpenAI Agents SDK
*   [🕸️ Web Scraping AI Agent](starter_ai_agents/web_scraping_ai_agent/) - Describe what to extract and the agent scrapes it
### 🚀 Advanced AI Agents
*Production-style agents with tools, memory, and multi-step reasoning.*
*   [🏚️ 🍌 AI Home Renovation Agent with Nano Banana Pro](advanced_ai_agents/multi_agent_apps/ai_home_renovation_agent) - Photos of your space in, renovation plan and photorealistic renders out
*   [🧠 DevPulse AI - Multi-Agent Signal Intelligence](advanced_ai_agents/multi_agent_apps/devpulse_ai/) - Aggregates and scores technical signals into a daily intelligence digest
*   [🔍 AI Deep Research Agent](advanced_ai_agents/single_agent_apps/ai_deep_research_agent/) - Comprehensive web research with the OpenAI Agents SDK and Firecrawl
*   [📊 AI VC Due Diligence Agent Team](advanced_ai_agents/multi_agent_apps/agent_teams/ai_vc_due_diligence_agent_team) - Multi-agent startup investment analysis with Gemini 3
*   [🔬 AI Research Planner & Executor (Google Interactions API)](advanced_ai_agents/single_agent_apps/research_agent_gemini_interaction_api) - Multi-phase research with stateful conversations and auto-generated infographics
*   [🤝 AI Consultant Agent](advanced_ai_agents/single_agent_apps/ai_consultant_agent) - Market analysis and strategy recommendations with live web research
*   [🏗️ AI System Architect Agent](advanced_ai_agents/single_agent_apps/ai_system_architect_r1/) - Architecture reviews using DeepSeek R1 reasoning plus Claude

============================================================
REPO: EvoAgentX/EvoAgentX
============================================================
Building a Self-Evolving Ecosystem of AI Agents
## What is EvoAgentX
EvoAgentX is an open-source framework for building, evaluating, and evolving LLM-based agents or agentic workflows in an automated, modular, and goal-driven manner. At its core, EvoAgentX enables developers and researchers to move beyond static prompt chaining or manual workflow orchestration. It introduces a self-evolving agent ecosystem, where AI agents can be constructed, assessed, and optimized through iterative feedback loops—much like how software is continuously tested and improved.
### ✨ Key Features
- 🧱 **Agent Workflow Autoconstruction**
From a single prompt, EvoAgentX builds structured, multi-agent workflows tailored to the task.
- 🔍 **Built-in Evaluation**
It integrates automatic evaluators to score agent behavior using task-specific criteria.
- 🔁 **Self-Evolution Engine**
Agents don’t just work—they learn. EvoAgentX improves workflows using self-evolving algorithms.
- 🧩 **Plug-and-Play Compatibility**
Easily integrate original [OpenAI](https://github.com/EvoAgentX/EvoAgentX/blob/main/evoagentx/models/openai_model.py) and [qwen](https://github.com/EvoAgentX/EvoAgentX/blob/main/evoagentx/models/aliyun_model.py) or other popular models, including Claude, Deepseek, kimi models through ([LiteLLM](https://github.com/EvoAgentX/EvoAgentX/blob/main/evoagentx/models/litellm_model.py), [siliconflow](https://github.com/EvoAgentX/EvoAgentX/blob/main/evoagentx/models/siliconflow_model.py) or [openrouter](https://github.com/EvoAgentX/EvoAgentX/blob/main/evoagentx/models/openrouter_model.py)). If you want to use LLMs locally deployed on your own machine, you can try LiteLLM.
- 🧰 **Comprehensive Built-in Tools**
EvoAgentX ships with a rich set of built-in tools that empower agents to interact with real-world environments.
- 🧠 **Memory Module**
EvoAgentX supports both ephemeral (short-term) and persistent (long-term) memory systems.
- 🧑‍💻 **Human-in-the-Loop (HITL) Interactions**
EvoAgentX supports interactive workflows where humans review, correct, and guide agent behavior.
### 🚀 What You Can Do with EvoAgentX
EvoAgentX isn’t just a framework — it’s your **launchpad for real-world AI agents**.
Whether you're an AI researcher, workflow engineer, or startup team, EvoAgentX helps you **go from a vague idea to a fully functional agentic system** — with minimal engineering and maximum flexibility.
Here’s how:
- 🔍 **Struggling to improve your workflows?**
EvoAgentX can **automatically evolve and optimize your agentic workflows** using SOTA self-evolving algorithms, driven by your dataset and goals.
- 🧑‍💻 **Want to supervise the agent and stay in control?**
Insert yourself into the loop! EvoAgentX supports **Human-in-the-Loop (HITL)** checkpoints, so you can step in, review, or guide the workflow as needed — and step out again.
- 🧠 **Frustrated by agents that forget everything?**
EvoAgentX provides **both short-term and long-term memory modules**, enabling your agents to remember, reflect, and improve across interactions.
- ⚙️ **Lost in manual workflow orchestration?**
Just describe your goal — EvoAgentX will **automatically assemble a multi-agent workflow** that matches your intent.
- 🌍 **Want your agents to actually *do* things?**
With a rich library of built-in tools (search, code, browser, file I/O, APIs, and more), EvoAgentX empowers agents to **interact with the real world**, not just talk about it.
## 🔥 EAX Latest News
- **[Aug 2025]** 🚀 **New Survey Released!**
Our team just published a comprehensive survey on **Self-Evolving AI Agents**—exploring how agents can learn, adapt, and optimize over time.
👉 [Read it on arXiv](https://arxiv.org/abs/2508.07407)
👉 [Check the repo](https://github.com/EvoAgentX/Awesome-Self-Evolving-Agents)
- **[July 2025]** 📚 **EvoAgentX Framework Paper is Live!**
We officially published the EvoAgentX framework paper on arXiv, detailing our approach to building evolving agentic workflows.
👉 [Check it out](https://arxiv.org/abs/2507.03616)
- **[July 2025]** ⭐️ **1,000 Stars Reached!**
Thanks to our amazing community, **EvoAgentX** has surpassed 1,000 GitHub stars!
- **[May 2025]** 🚀 **Official Launch!**
**EvoAgentX** is now live! Start building self-evolving AI workflows from day one.
🔧 [Get Started on GitHub](https://github.com/EvoAgentX/EvoAgentX)
## ⚡ Get Started
- [🔥 Latest News](#-latest-news)
- [⚡ Get Started](#-get-started)
- [Installation](#installation)
- [LLM Configuration](#llm-configuration)
- [API Key Configuration](#api-key-configuration)
