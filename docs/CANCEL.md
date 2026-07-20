# Cooperative cancel (M017)

Ctrl+C and programmatic cancel stop SuperAI workers **cooperatively** at safe
checkpoints — not by killing arbitrary OS children mid-syscall (process-mux
panes and the goals daemon have their own stop paths).

## Token API

```python
from core.cancel_token import (
    CancelToken,
    using,
    current,
    is_cancelled,
    cancel_current,
    cancelled_envelope,
    map_cooperative,
    install_sigint_handler,
)

with using(install_sigint=True) as tok:  # Ctrl+C → tok.cancel("sigint")
    ...
    if is_cancelled():
        return cancelled_envelope()
```

## Checkpoints

| Worker | When it stops |
|--------|----------------|
| `ModelCaller.call` | Before call + between failover attempts; stream between chunks |
| `call_lifecycle.pre_call` | Blocks new spend when cancelled |
| `AgentRuntime.run` | Each tool round; optional `SUPERAI_AGENT_SIGINT=1` for Ctrl+C |
| `multi_cli_board` | Before each member; cancels pending futures after cancel |
| `Council` | Between proposal/critique members |
| `Orchestrator` | Between batches / serial steps |

## CLI

```powershell
# Offline proof
python -c "from core.cancel_token import audit_m017; print(audit_m017())"
superai foundation-check M017
```

## Env

| Variable | Effect |
|----------|--------|
| `SUPERAI_AGENT_SIGINT=1` | Agent runtime installs SIGINT → cancel for that run |

## Tests

`tests/test_cancel_m017.py` plus existing foundation/v5 cancel tests.
