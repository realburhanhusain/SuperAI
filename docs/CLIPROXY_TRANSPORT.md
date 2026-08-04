# CLIProxyAPI transport (optional)

[CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI) fronts vendor CLI
subscriptions — Claude Code, ChatGPT Codex, Gemini, Grok, Kimi — behind a single
OpenAI-compatible HTTP endpoint. SuperAI can route model calls through it.

**This is additive. Nothing was removed.** Both transports ship, both stay
supported, and you choose per model.

## Two transports, two jobs

| | `cli:*` (subprocess) | `cliproxy:*` (HTTP) |
|---|---|---|
| Mechanism | Spawns the vendor CLI as a process | `POST /v1/chat/completions` |
| Can edit files | **Yes** — every spec is `modifies_files=True` | No |
| Runs agent tool loops | **Yes** (aider's edit loop, Claude Code's tools) | No |
| Needs the CLI on PATH | Yes | No |
| Streaming | Line-buffered stdout | Real SSE |
| Token usage | Estimated | Reported by the API (see below) |
| Startup cost | Full process spawn | HTTP round trip |

### Where token usage is exact, and where it is not

| Path | Source of the token count |
|---|---|
| `call()` — non-streaming | `response.usage`, exact |
| `call_stream()` / `_stream_openai_compatible()` | the server's usage block if it volunteers one on the final chunk, otherwise a `chars // 4` estimate |

SuperAI does not *request* usage on streams
(`stream_options={"include_usage": true}`), because the same code path serves LM
Studio, vLLM and Ollama, which reject unknown request params. There is no spend
consequence either way — a subscription-backed call is `$0` however many tokens
it used — but a streamed `total_tokens` should not be read as authoritative.

**Use `cliproxy:` when you want a model. Use `cli:` when you want an agent.**

A chat endpoint cannot run aider's edit loop or Claude Code's tool execution —
those are agent products that happen to share a brand with a model. That is why
`external_cli.py` and `cli_pool.py` stay exactly as they are.

## `supports_tools` is a claim about the model, not about SuperAI

The example rows carry `"supports_tools": true`, and CLIProxyAPI does expose
function calling. **SuperAI does not currently send tool definitions on any
transport** — no `tools=` or `tool_choice=` argument appears anywhere in `src/`,
for this provider or any other. `supports_tools` is a `ModelSpec` field
(`model_registry.py:28`, default `True`) that is stored and serialised but never
read by the router.

So the flag is accurate about the upstream model and inert about what SuperAI
will do with it. It is left `true` because setting it `false` only here would
falsely imply the other registry rows *do* exercise tools.

This is worth naming because function calling is exactly the boundary case in
the model/agent split above. `cli:*` gets agent behaviour from the vendor CLI's
own tool loop; `cliproxy:*` could in principle get it from the API, and today
does not. Wiring tools through the OpenAI-compatible path is a change to
`model_caller`, not to this provider entry.

## Enabling it

Nothing routes to CLIProxyAPI until you add models to the registry. Until then
the provider entry is inert.

1. **Run the proxy** (see its README — Docker or a Go binary), then authenticate
   each vendor through its OAuth flow. Default endpoint `http://127.0.0.1:8317/v1`.

2. **Add the models.** Merge `config/models.cliproxy.example.json` into your
   registry:

   ```powershell
   # ~/.superai/config/models.json takes precedence over the repo copy
   superai list-models --provider cliproxy
   ```

3. **Key, if you set one on the proxy:**

   ```powershell
   $env:CLIPROXY_API_KEY = "..."   # usually unnecessary for a loopback endpoint
   ```

4. **Verify the ids before spending a call on them:**

   ```powershell
   python scripts/validate_cliproxy_models.py --registry        # offline
   python scripts/validate_cliproxy_models.py --registry --live  # also ask the proxy
   ```

5. **Then verify end to end:**

   ```powershell
   superai --json ask "hello" --model cliproxy:claude-opus
   ```

## Checking model ids

A wrong `model_id` costs nothing until the first real call, which then 404s.
`scripts/validate_cliproxy_models.py` checks every `cliproxy:*` row against
CLIProxyAPI's published model list, vendored at
`vendor/cliproxy-models/models.json` and pinned to a commit — no network, no
running proxy. See [`vendor/README.md`](../vendor/README.md).

This is not a formality. The example file originally shipped `gpt-5.6-codex`,
an id **no backend serves**; the check found it immediately.

The catalog is keyed by *backend*, not by vendor — `claude`, `gemini`, `vertex`,
`gemini-cli`, `aistudio`, `codex-free|team|plus|pro`, `kimi`, `antigravity`,
`xai` — and the same model is spelled differently across them. So "does this id
exist" is the wrong question; **which backends serve it** is the right one:

| Status | Meaning |
|---|---|
| `ok` | most backends serving that model family serve this exact id |
| `backend_conditional` | only a minority do — works solely if your proxy authenticates against one of the listed backends |
| `missing` | nothing serves it; the call will 404 |

Two consequences visible in the shipped example:

- The codex row uses `gpt-5.5` because the `codex-*` keys are **subscription
  tiers**. `gpt-5.6-sol` is absent from `codex-free`, so it would 404 for anyone
  on a free-tier-backed proxy; `gpt-5.5` is in all four.
- The Gemini row uses `gemini-3.1-pro-preview`, served by `gemini`,
  `gemini-cli`, `aistudio` and `vertex`. Plain `gemini-3.1-pro` is **Vertex
  only** — a row that looks valid and still 404s on an OAuth-backed proxy.

`--live` adds a second, separate answer: `GET /v1/models` on a running proxy
says what *your* install is actually authenticated for. The two are reported
apart on purpose — a static check standing in for a dynamic one is how coverage
gets claimed without being proven.

`superai smoke-preflight` also now reports whether a proxy is up at
`127.0.0.1:8317`. A down proxy is the normal state, not a failure: nothing
routes to cliproxy until you merge the example file.

## What changed in SuperAI

Two small edits. No new call path was needed — `model_caller._call_openai_compatible`
already routes any registry entry carrying a `base_url` through the OpenAI
client, which is exactly the protocol CLIProxyAPI speaks.

| File | Change |
|---|---|
| `provider_catalog.py` | One `OPENAI_COMPAT_PROVIDERS` entry for `cliproxy` |
| `cost_accounting.py` | `is_local_or_cli()` recognises the `cliproxy:` prefix |

### Why the cost change matters

CLIProxyAPI calls are backed by a **subscription**, so their marginal cost is
genuinely zero — the same footing as `cli:`, which shells out to those same
subscriptions.

Without the prefix change, a `cliproxy:` model falls through to heuristic rates
and reports `estimate_source: fallback` — inventing a price where none exists.
With it, the figure is `$0` labelled `estimate_source: actual`, which is the
honest answer: nothing was estimated. See
[`COST_ACCOUNTING.md`](COST_ACCOUNTING.md).

### Why the prefix is `cliproxy:` and not `cli:`

`model_caller.py` treats a `cli:` prefix as an authoritative instruction to use
the subprocess transport. Naming these entries `cli:*` would silently route them
back through `external_cli`, which is the opposite of the intent.

## Everything above the transport is unaffected

Routing, memory, councils, the learning engine and the spend gate all operate on
model names and result envelopes, not on how bytes reach the provider. Adding a
transport changes nothing for them:

- **Bandit routing** treats `cliproxy:claude-opus` as one more arm. If you
  register both it and `cli:claude`, the bandit runs the A/B for you and prefers
  whichever actually performs.
- **Spend gate** still pre-checks by command name. Both transports report $0, so
  neither trips a ceiling — the ceiling exists for metered API models.
- **Result contracts** are unchanged: the OpenAI path already returns a
  contracted envelope.

## A caution worth stating

Wrapping *subscription* access as a general-purpose API may conflict with those
vendors' terms of service. Popularity is not sanction, and 46k stars is not a
legal opinion. That matters more for work-related use than personal use. This
integration is opt-in specifically so the choice stays deliberate.
