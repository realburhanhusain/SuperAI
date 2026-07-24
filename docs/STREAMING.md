# Streaming honesty (M027 / V4-M4)

**Updated:** 2026-07-24

## Modes (always labeled in `token_stream` meta)

| Mode | Meaning |
|------|---------|
| `sse` | True provider stream (Anthropic Messages or OpenAI-compatible `stream=True`) |
| `mock_chunked` | Mock `call()` response re-chunked offline |
| `chunked_fallback` | Full non-stream `call()` re-chunked after stream failure/empty |

Meta fields: `mode`, `provider`, `model`, `chunks`, `chars`, `cancelled`, `fallback_reason`.

## Provider matrix (offline-first)

| Provider kind | Path | Live needs | Offline |
|---------------|------|------------|---------|
| Anthropic | `_stream_anthropic` | `ANTHROPIC_API_KEY` | mock / fallback |
| OpenAI-compatible | `chat.completions` stream | provider API key | mock / fallback |
| Ollama local | OpenAI-compat base URL | Ollama running | mock / fallback |
| Mock | `call` + `chunk_text` | none | always |

Query offline:

```python
from core.token_stream import stream_capabilities, supports_stream
stream_capabilities(model="gpt-4o-mini", provider="openai")
supports_stream(model="claude-3-5-sonnet", provider="anthropic")
```

## Cancel

`CancelToken` / `call_lifecycle.check_cancel` is checked between chunks; meta sets `cancelled=True`.

## Aggregated result contract (M027 residual)

After stream completion, meta includes `aggregated` — a `superai.result.v1` envelope with full text, `stream_meta`, tokens, and cost fields.

```python
from core.model_caller import ModelCaller
out = ModelCaller(use_mock=True).call_stream_complete(model="gpt-4o-mini", prompt="hi")
# out["contract"], out["response"], out["stream_meta"]["mode"]
```

Or consume chunks then read `token_stream.get_stream_meta()["aggregated"]`.

## Scorecard honesty

Offline 100% = matrix + mock fixtures + fallback_reason + cancel + aggregate contract tests.
Live multi-provider SSE proof is optional / host-gated (M089 adjacency).

## Verify

```powershell
pytest tests/test_m079_m027_m093.py tests/test_stream_dashboard_g3_g4.py tests/test_grok_i1_residuals.py -q
```
