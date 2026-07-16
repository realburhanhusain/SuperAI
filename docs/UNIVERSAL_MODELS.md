# Universal models — multi-vendor & open-weight

**Status:** Phase 1 in progress (2026-07-16)  
**Track on:** `TASKBOARD.md` · resume from this file + taskboard after any fault  

## Vision (lean)

SuperAI must call **any** LLM — commercial or open-weight — via:

1. **API keys** (OpenAI-compatible endpoints preferred)  
2. **Local runtimes** (Ollama, LM Studio, vLLM, …)  
3. **External CLIs** (`cli:claude`, `cli:gemini`, …) already dual-registered  

Same path for workers / review / advise / council / `ask`.

## Principles

- **Agile / lean:** thin vertical slice each phase; discuss → improve  
- **Basic first:** wire + catalog + discover; polish UX later  
- **Resume-safe:** TASKBOARD + this doc + checkpoints; commit/push after phase  
- **No vendor lock-in:** registry `base_url` + `api_key_env` wins over hardcoding  

## Phases

| Phase | Goal | Status |
|-------|------|--------|
| **0** | Charter + taskboard | `[x]` |
| **1** | Provider catalog, registry-aware caller, expanded models.json, Ollama sync, register-model CLI | `[x]` basic (2026-07-16) |
| **2** | Richer NVIDIA catalog; members UI polish; more gateway models | `[ ]` next |
| **3** | Auto-discover on `doctor`/`members`; live multi-key smoke (host) | `[ ]` postponed smoke |
| **4** | Interactive model pick in `ask` / REPL by provider family | `[ ]` |

## Phase 1 acceptance

- [x] Single `provider_catalog` used by ModelCaller (no triple-duplicated maps)  
- [x] Call honors per-model `base_url` + `api_key_env` from registry  
- [x] Catalog includes DeepSeek, Kimi, GLM, MiniMax, Gemma, NVIDIA (own + hosted), OpenRouter, LM Studio, Ollama placeholders  
- [x] `superai providers` lists known providers + key env  
- [x] `superai models-sync-ollama` imports local tags  
- [x] `superai models-register` adds OpenAI-compatible endpoint  
- [x] Tests green; commit + push  

## Phase 1 how to use

```powershell
superai providers
superai list-models --refresh
superai models-sync-ollama          # after: ollama pull llama3.2
superai models-register --name my-7b --model-id 7b --base-url http://127.0.0.1:8000/v1 --provider vllm
$env:NVIDIA_API_KEY="..."
$env:DEEPSEEK_API_KEY="..."
superai config set mock_mode false
superai run "hello" -m deepseek-chat
superai run "hello" -m nvidia-llama-3.1-70b-instruct
superai ask "review X with deepseek-r1 and glm-4"
```

## Resume (minimal context)

```text
1. Read TASKBOARD.md + docs/UNIVERSAL_MODELS.md
2. pytest tests/test_provider_catalog.py tests/test_model_discovery.py -q
3. Continue next unchecked phase item
```

## Env keys (Phase 1)

| Provider | Env |
|----------|-----|
| NVIDIA NIM / NGC | `NVIDIA_API_KEY` |
| DeepSeek | `DEEPSEEK_API_KEY` |
| Moonshot Kimi | `MOONSHOT_API_KEY` |
| Zhipu GLM | `ZHIPU_API_KEY` |
| MiniMax | `MINIMAX_API_KEY` |
| Qwen DashScope | `DASHSCOPE_API_KEY` |
| OpenRouter | `OPENROUTER_API_KEY` |
| Groq / Together / Mistral | standard keys |
| Ollama / LM Studio / vLLM | often no key; base_url only |
