# Checkpoint: universal models Phase 1

**When:** 2026-07-16  
**Branch:** master  
**Resume:** `TASKBOARD.md` → Universal models section · `docs/UNIVERSAL_MODELS.md`

## Done

- Provider catalog (NVIDIA, MiniMax, OpenRouter, LM Studio, vLLM, Ollama OpenAI, …)
- ModelCaller registry-aware `base_url` / `api_key_env`
- Expanded `config/models.json` (~30 models)
- `providers`, `models-sync-ollama`, `models-register`
- Tests: provider_catalog + model_discovery

## Next (Phase 2)

- Richer NVIDIA NIM model list
- members/list filters by open_weight / local
- discuss with user before expanding further

## Verify

```powershell
pytest tests/test_provider_catalog.py tests/test_model_discovery.py -q
superai providers
superai list-models
```
