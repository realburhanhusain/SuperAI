<div align="center">

# oh-my-harness

**The durable turn loop, live in your browser.**

<p>
  <a href="#quickstart"><img alt="Install: iii worker add harness console" src="https://img.shields.io/badge/install-iii%20worker%20add%20harness%20console-0a84ff?style=flat-square"></a>
  <a href="https://github.com/iii-hq/iii"><img alt="Built on the iii engine" src="https://img.shields.io/badge/built%20on-iii%20engine-f26522?style=flat-square"></a>
  <a href="LICENSE"><img alt="License: Apache 2.0" src="https://img.shields.io/badge/license-Apache%202.0-blue.svg?style=flat-square"></a>
  <a href="https://workers.iii.dev/workers/harness"><img alt="harness" src="https://workers.iii.dev/workers/harness/badge.svg"></a>
  <a href="https://workers.iii.dev/workers/console"><img alt="console" src="https://workers.iii.dev/workers/console/badge.svg"></a>
</p>

<p><sub>An <a href="https://github.com/iii-hq">iii-hq</a> project, built on the <a href="https://github.com/iii-hq/iii">iii engine</a>.</sub></p>

</div>

Both workers run on the [iii engine](https://github.com/iii-hq/iii): a
WebSocket-routed worker mesh where the engine holds a live registry of every
connected worker, its functions, and the triggers bound to it. Calls route worker
to engine to worker, so a worker's language, runtime, and location are invisible
and the function id is the only contract. That is what makes an agent loop
something you assemble instead of something you fork.

`harness` runs the durable turn loop that keeps your agents moving: it takes an
incoming message, persists it, assembles a context, streams a completion, runs
the function calls the model asks for, and repeats until the turn stops. Every
step is durable, so a crash or a restart picks the turn back up.

`console` bundles the React UI and the engine WebSocket on one port, so you can
inspect functions, watch triggers fire, and steer a live deployment.

Add both, then open the tab and watch what iii is doing.

## Quickstart

Install the engine and start it:

```bash
curl -fsSL https://install.iii.dev/iii/main/install.sh | sh
iii project init iii-app && cd iii-app
iii
```

New terminal, same folder. `iii worker add` writes to the `config.yaml` in the
current directory, so it has to be the directory the engine runs in:

```bash
cd iii-app
iii worker add harness console
```

Open [http://localhost:3113](http://localhost:3113).

## Add a model key

The harness is running, but no provider is configured yet, so the model picker
is empty and chat will not generate. In the console, use **configure a
provider** (or the configuration panel, `workers` tab, `llm-router` entry) and
paste an Anthropic or OpenAI key. It is stored in the `llm-router` worker config
and the model catalog populates within seconds.

<p align="center">
  <img src="docs/images/configure-a-provider.webp" alt="Configure a provider key in the iii console" width="100%">
</p>

Pick a model, send a message. That is the loop.

## Use your ChatGPT/Codex subscription instead

`provider-openai-codex` generates against a personal ChatGPT plan instead of a
pay-per-token API key, speaking the Responses API at the Codex backend. Sign in
with the `codex` CLI first, which writes `~/.codex/auth.json`, then add the
worker:

```bash
codex login
iii worker add provider-openai-codex
```

Models appear as `codex/<model>`. The catalog is account-scoped, so you see
exactly what your plan grants, refreshed every few minutes. The provider reads
the credential file read-only; the `codex` CLI owns refreshing it.

Two things to know. The endpoint this provider calls,
`chatgpt.com/backend-api/codex`, is not a documented public API, and it sends
the Codex CLI's own `originator` header, so an unannounced change upstream can
break it. And OpenAI's own guidance is to use API keys for automation, so for
team, CI, or production runs, use `provider-openai` with a key.

## Grok, and everything else

Anthropic and OpenAI ship with the harness. Every other provider is one worker
away, and they all work the same: add the worker, paste the key into the
`llm-router` config (same panel as the screenshot above, or the matching env var
on the router), pick a model.

Grok:

```bash
iii worker add provider-xai
```

xAI's catalog is fetched live, so `grok-*` models fill the picker within seconds
of the key landing, no hardcoded list to go stale.

| Worker | Provider | Key |
| --- | --- | --- |
| `provider-xai` | xAI (Grok) | `XAI_API_KEY` |
| `provider-kimi` | Moonshot (Kimi) | `MOONSHOT_API_KEY` |
| `provider-zai` | Z.AI | `ZAI_API_KEY` |
| `provider-llamacpp` | local `llama-server` | none, point `api_url` at the server |

`provider-llamacpp` is the fully local option: run a GGUF under `llama-server`
and the same harness loop generates with nothing leaving the box. With
`--embeddings` it also serves `router::embed`, so local semantic recall needs no
cloud call either.

Providers register with `llm-router` at boot. If a newly added provider does not
show up, stop the engine and start it once more so registration lands clean.

## What you just installed

`iii worker add harness` pulls the whole loop, not one worker. You do not add
these one by one:

| Worker | Job |
| --- | --- |
| `session-manager` | The transcript: every message, every turn, durable. |
| `context-manager` | Token budgeting and context assembly. |
| `llm-router` | Provider credentials, routing, model catalog. |
| `provider-anthropic`, `provider-openai` | Generation. |
| `queue` | The dedicated `harness-turn` queue: FIFO per session, sessions run concurrently. |
| `state`, `cron`, `iii-stream`, `iii-observability`, `configuration`, `iii-directory` | Storage, sweeps, streaming, traces, hot-reloading config, registry lookup. |
| `shell`, `scrapling` | The first capabilities worth letting an agent call: a shell and the web. |

Every turn, sub-agent spawn, and provider call lands in one correlated trace,
grouped by session in the console. A failed descendant stamps the whole trace
failed, so you find the real error instead of the symptom.

<p align="center">
  <img src="docs/images/console-traces.webp" alt="One harness send fanning out to three sub-agents, as one grouped trace in the iii console" width="100%">
</p>

## Own it

The harness is a stack of installable workers, so "build your own" stops meaning
"fork a framework" and starts meaning "swap a few workers".

- **Function calls are deny-by-default.** With no `functions.allow` globs, every
  model-requested call is refused and the harness is a plain chat loop. Allow
  what you want per send (`options.functions.allow`).
- **Gate the calls you do allow.** Add
  [`approval-gate`](https://workers.iii.dev/workers/approval-gate) and a human
  approves before the function runs.
- **Plug into the loop instead of forking it.** The harness registers five
  synchronous hook points: `harness::hook::pre-turn`, `pre-generate`,
  `post-generate`, `pre-trigger`, `post-trigger`. A hook can veto a turn, extend
  the system prompt, rewrite arguments, or rewrite a result.
- **React to turns from anywhere.** Bind `harness::turn-started` and
  `harness::turn-completed` and drive a Slack bot, a cron job, or your own UI.
- **Swap the parts.** Another provider, another context strategy, another
  memory store: it is `iii worker add`, not a rewrite.

## Next

- Engine and CLI: [iii-hq/iii](https://github.com/iii-hq/iii)
- Every worker in this stack: [iii-hq/workers](https://github.com/iii-hq/workers), harness source and full function reference at [workers/harness](https://github.com/iii-hq/workers/tree/main/harness)
- Registry page: [workers.iii.dev/workers/harness](https://workers.iii.dev/workers/harness)
- Everything the engine knows at runtime: `iii worker info harness`, `iii trigger engine::functions::list`
- Docs: [iii.dev/docs](https://iii.dev/docs)

## License

Maintained by [iii-hq](https://github.com/iii-hq). Copyright 2026 Motia LLC,
released under [Apache 2.0](LICENSE). Contributions are welcome, see
[CONTRIBUTING.md](CONTRIBUTING.md).
