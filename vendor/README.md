# `vendor/` — pinned external sources

SuperAI must not depend on a URL whose contents change without us deciding.
Anything external that SuperAI **reads as data** is copied in here, pinned to a
commit, and updated only on purpose.

`vendor/manifest.json` is the record. `scripts/vendor_sync.py` is the only thing
that should edit it.

## Two kinds of entry

| `kind` | Bytes stored here | Use when |
|---|---|---|
| `vendored_files` | Yes — committed | SuperAI reads the file at runtime |
| `pinned_reference` | No | We only *cite* the source; nothing reads it |

A `pinned_reference` still carries a tag and a commit SHA, so documentation
links point at a fixed tree rather than a branch that moves daily. It stores no
bytes because a mirror nothing reads is dead weight: it bloats the repo, drifts
silently, and protects nothing.

**A gitignored clone is not vendoring.** If it is not committed, a fresh
checkout does not have it, and anything that depends on it fails for the next
person. Either the bytes are in the repo or the entry is a reference.

## Commands

```powershell
python scripts/vendor_sync.py --list              # what is pinned, and to what
python scripts/vendor_sync.py --check             # drift: local tamper + upstream moves
python scripts/vendor_sync.py --update <name>     # deliberate refresh; rewrites the pin
```

`--check` answers two different questions and reports them separately:

- **Local integrity** — does each vendored file still match its recorded
  `sha256`? Catches an in-place edit to a vendored copy. Works offline.
- **Upstream drift** — has the source repo moved past the pinned commit? Needs
  network; when unreachable it says so rather than reporting "no drift", because
  an unanswered question is not a pass.

Exit code is non-zero only for problems we can actually prove.

## Current entries

| Name | Kind | Pin | What reads it |
|---|---|---|---|
| `cliproxy-models` | `vendored_files` | `router-for-me/models` @ `fb13a81` | `core.cliproxy_models` — validates `cliproxy:*` registry rows |
| `cliproxy` | `pinned_reference` | `router-for-me/CLIProxyAPI` @ `v7.2.116` | docs and comments only |

## Scope — what belongs here, and what does not

The policy is "no live source we did not pin". It applies to every external
dependency, but **migrating each one is a separate, deliberate decision**,
because for some the migration changes product behaviour rather than just where
bytes come from.

**Vendorable — external data SuperAI reads:**

- `router-for-me/models` — done, above.
- `vega_charts.py:16-18` — Vega/Vega-Lite/Vega-Embed `<script>` tags from
  `cdn.jsdelivr.net`, plus the `vega-lite/v5.json` schema URL. These are the
  strongest remaining candidates: a CDN version bump changes rendered charts
  with no commit on our side. **Not migrated**, because inlining ~1.5MB of JS
  into every generated chart file changes what that file *is* — a product
  decision, not a dependency-policy one.

**Must stay live — request-time APIs, not sources:**

- `provider_catalog.py`, `model_registry.py` base URLs — these are the
  endpoints we call. Pinning them is meaningless.
- `model_catalog_refresh.py:16` — OpenRouter's `/api/v1/models`. It is an API
  rather than a repo, and its entire purpose is freshness; a pinned copy would
  defeat the feature. It already fails soft when the network is unavailable.
- `ecosystem.py` search backends, `messengers.py`, `notion_stub.py`,
  `github_api.py` — outbound calls made on the user's behalf.

**Documentation-only — no action:**

- `host_tools.py` install URLs, and similar. Displayed to a human, never
  fetched.
