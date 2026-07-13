# Other tool features — tracked checklist

**Source:** `OtherToolFeatures.txt` · **Updated:** 2026-07-14  
**Policy:** inspire or reuse code. Required scope, sequenced.

**Legend:** `[ ]` pending · `[~]` in progress · `[x]` done

---

## Overview

- [x] SuperAI supervisor layer
- [x] Modular registries / adapters
- [~] Deeper third-party plugin marketplace (structure via registries)

---

## 1. LLM Council
https://github.com/Mohamadreza-Shahmohamadi/LLM_Council_ApplimentAI_Enhanced

- [x] Council + debate / critique
- [x] Voting: majority | supervisor | weighted
- [x] Stage classification (router)
- [x] Structured JSON envelopes
- [x] Hierarchical delegate command

---

## 2. OpenClaw
https://github.com/openclaw/openclaw

- [x] Local-first defaults
- [x] Tool propose → approve → execute
- [x] `require_human_approval` config
- [x] User preference / modeling (`preferences.py`, `pref` CLI)
- [x] Self-improve via learning + skills + preference signals
- [x] Local privacy store `~/.superai/`

---

## 3. Hermes / Atomic-Hermes
https://github.com/NousResearch/hermes-agent  
https://github.com/AtomicBot-ai/atomic-hermes

- [x] Agentic debate / critique-extend
- [x] Hierarchical delegation (`delegate`)
- [x] Multi-round deliberation
- [x] Skills reusable components
- [x] File time-travel snapshots (`tt-snapshot` / `tt-list` / `tt-restore`)
- [x] Multi-messenger bus foundation (`msg-send` / `msg-channels`)
- [~] Full Telegram/Slack production connectors (webhook channel ready)

---

## 4. Mempalace
https://github.com/MemPalace/mempalace

- [x] Wings & rooms
- [x] Semantic memory + embeddings path
- [x] Provenance / versioning
- [x] Decay / distill / conflicts
- [x] Terminal + **web** memory query UI (`superai web`, `/api/memory/search`)

---

## 5. Databao-Agent
https://github.com/realburhanhusain/databao-agent

- [x] NL → tables + chart specs
- [x] SQLAlchemy / demo SQLite + optional databao package
- [x] Conversational threads
- [~] Full interactive Vega frontend (JSON spec exported)

---

## Secondary CLIs

Claude, Aider, Cursor, Grok, Gemini, Codex, Continue, Cline, Roo — **registered** for discovery/`cli-run`.
