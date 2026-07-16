# Universal models — multi-vendor & open-weight

**Status:** Phases 0–5 **code complete** (2026-07-16) · Live smoke **POSTPONED** (Phase 99)  
**Plan (tasks + %):** `docs/UNIVERSAL_MODELS_PLAN.md`  
**Track:** `TASKBOARD.md`

## Vision

SuperAI calls **any** LLM — commercial or open-weight — via:

1. **API keys** (OpenAI-compatible preferred)  
2. **Local runtimes** (Ollama, LM Studio, vLLM)  
3. **External CLIs** (`cli:*`)  

Same path for workers / review / advise / council / `ask`.

## Progress (excl. smoke)

| Phase | % | Status |
|-------|--:|--------|
| 0 Charter | 100% | done |
| 1 Foundation | 100% | done |
| 2 Catalog depth + filters | 100% | done |
| 3 Auto-discover (offline) | 100% | done |
| 4 NL / pick filters | 100% | done |
| 5 Docs | 100% | done |
| **Code total** | **100%** | |
| 99 Live smoke | 0% | postponed |

## Commands

```powershell
superai providers [--ready]
superai list-models [--provider nvidia] [--open-weight] [--local] [--refresh]
superai members --available --open-weight
superai members --local --ollama-live
superai members --provider deepseek --pick
superai models-sync-ollama
superai models-register --name my-7b --model-id 7b --base-url http://127.0.0.1:8000/v1 --provider vllm
superai doctor   # includes llm_providers + ollama_models
superai run "…" -m deepseek-chat
superai run "…" -m nvidia-llama-3.1-70b-instruct
superai ask "review X with deepseek and glm"
```

## Resume

```text
1. docs/UNIVERSAL_MODELS_PLAN.md (dashboard)
2. TASKBOARD.md → Universal models
3. pytest tests/test_provider_catalog.py tests/test_model_discovery.py tests/test_member_selection.py tests/test_nl_intent.py -q
4. Phase 99 only when ready for live keys
```

## Modules

| Module | Role |
|--------|------|
| `provider_catalog.py` | Provider presets |
| `model_discovery.py` | Ollama sync, register, provider status |
| `model_caller.py` | Registry-aware OpenAI-compatible calls |
| `member_selection.py` | Filters + soft Ollama |
| `config/models.json` | Default catalog (~40 models) |
