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

## Scorecard honesty

Offline 100% = matrix + mock fixtures + fallback_reason + cancel tests.
Live multi-provider SSE proof is optional / host-gated (M089 adjacency).

## Verify

```powershell
pytest tests/test_m079_m027_m093.py tests/test_improvement_v4.py -q -k stream
```
