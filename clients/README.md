# SuperAI Memory thin clients (Phase 9+)

Python and TypeScript clients under this folder call SuperAI via:

1. **CLI subprocess** (default): `superai --json …`
2. **HTTP JSON** (optional, P9-R4): set `SUPERAI_HTTP_BASE=https://host` when a web surface is available

## Packaging (P9-R5 — optional)

These clients are shipped **in-repo** for copy/import. Optional later publish:

| Client | Suggested package | Pin |
|--------|-------------------|-----|
| Python | `pip install` from path or future `superai-memory-client` | pin to SuperAI CLI minor version |
| TypeScript | `npm` package later | pin to CLI contract `docs/clients/MEMORY_API_CONTRACT.md` |

Until published:

```bash
# Python
export PYTHONPATH=clients/python
python -c "from superai_memory_client import SuperAIMemoryClient; print(SuperAIMemoryClient().recall('Cloud SQL'))"

# TypeScript
# import { SuperAIMemoryClient } from './clients/typescript/superaiMemoryClient'
```

## Env

| Var | Purpose |
|-----|---------|
| `SUPERAI_BIN` | Path to `superai` binary |
| `SUPERAI_HTTP_BASE` | Optional HTTP base (recall / cloud status) |

See `docs/clients/MEMORY_API_CONTRACT.md` and `docs/PHASE9_MEMORY.md`.
