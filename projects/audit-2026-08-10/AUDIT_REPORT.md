# SuperAI — Full Project Audit

**Date:** 2026-08-10
**Auditor:** Claude Code (Opus 5), read-only
**Subject:** every taskboard and completion record in the repository, no date
filter — **plus functional correctness testing of the executable surface**
**Method:** clean `git clone` checked out at pinned `6b798ff`, in a scratch
directory, with isolated `HOME`/`USERPROFILE`. The live repo, its ~40
worktrees, MemBrain and MemPalace were not modified at any point.

> **This is the single, complete audit report.** Parts 1–5 cover records and
> claims; **Part 6 covers functional correctness** (code executed, not read);
> Part 7 is the consolidated defect count; **Part 8 reviews AGY's work of
> 2026-08-10**, reviewed from a 14:20 working-tree snapshot and re-verified
> against commit `b5d74d8` after AGY committed it at 14:36; **Part 9 records
> the checkpoint at `c5d33f5` and two late findings**. It supersedes
> `SUPERAI_AUDIT_EXTENDED_20260810.md`, whose content is merged into Part 6 —
> that file is retained only as a working artefact and should not be read as a
> separate source of truth.

---

## The finding, in one paragraph

SuperAI contains a large amount of real, working, well-engineered software. It
also contains a completion-tracking system that **reports completion by
default**. The strict scorecard — the document that answers "is SuperAI done?"
— derives nothing from the codebase: an improvement is COMPLETE if its ID
appears in a hand-maintained Python list, and the three-pillar evidence shown
beneath each entry is generated prose, not measurement. Every individual defect
below is an instance of that same pattern: a claim recorded in a place nothing
verifies.

**This is not a claim that 282 features are fake.** It is a claim that the
number 282 was never measured, and so cannot be relied on — in either
direction.

---

## Scope and honest boundaries

**Audited:**

| Record | Lines / IDs | Result |
|---|---|---|
| `docs/V1_V6_UNIFIED_IMPROVED_SCORECARD.md` | 533 IDs | **systemically unverified** |
| `scripts/gen_v1_v6_unified_improved_scorecard.py` | generator | **completion is a hardcoded list** |
| `TASKBOARD.md` (root index) | 92 | 4 defects |
| `projects/webui-management-center/TASKBOARD.md` | T01–T16 | 5 defects |
| `projects/fleet-proxy-features/TASKBOARD.md` | T17–T29 | 3 defects |
| `TASKBOARD_AGY.md` | 440 | **clean** |
| `TASKBOARD_GROK.md` | 186 | 1 minor defect |

**What "audited" means here — two different standards, deliberately:**

- For everything I could **execute** — routes, argv handling, auth gates, alias
  resolution, the test suite, the two boards' own verify packs — findings are
  proven by running the code against the pinned clone. These are facts.
- For the **533 scorecard IDs**, I audited *evidence integrity*, not
  *functional correctness*: whether the completion verdict is derived from
  anything, whether cited files exist, whether entries contradict themselves or
  other documents. I did **not** test 533 features and make no claim about how
  many work.

That boundary is the point. I am not replacing an unmeasured number with
another unmeasured number.

**Part 6 narrows that boundary considerably** by executing everything with a
reachable surface — 249 module imports, 208 command surfaces, a full HTTP
sweep, the repo's own self-audits, and behavioural tests of nine features.
It still does not cover: live multi-provider behaviour (no API keys were used,
no vendor contacted — so M089/MOS-N8/V1-P99 remain genuinely unproven), the
majority of the 533 scorecard IDs, or concurrency and performance.

---

# Part 1 — The systemic defect

## 1.1 Completion is membership in a hardcoded list `CRITICAL`

`scripts/gen_v1_v6_unified_improved_scorecard.py:319`:

```python
if iid in COMPLETE_IDS:
    ...
    return "complete", T(
        True, True, True, 100,
        f"Production-usable implementation for: {title}",   # line 420
        docs_note,      # assigned by ID prefix
        tests_note,     # assigned by ID prefix
        "—",
    )
```

`COMPLETE_IDS` (line 196) is the union of ten hand-maintained sets:

| Set | IDs |
|---|--:|
| `V6_MUST_COMPLETE` | 98 |
| `V6_S_COMPLETE` | 36 |
| `MOSCOW_COMPLETE` | 25 |
| `V1_COMPLETE` | 25 |
| `V4_COMPLETE` | 19 |
| `V5_COMPLETE` | 16 |
| `V2_COMPLETE` | 14 |
| `V3_COMPLETE` | 13 |
| `V6_N_COMPLETE` | 13 |
| `W_COMPLETE` | 9 |
| **total** | **268** |

Plus ~15 hand-authored override entries → the **282 COMPLETE** in the summary.

Nothing in this path reads a source file, runs a test, or checks that anything
exists. The document's own header states:

> **Strict completion rule (mandatory).** An improvement is COMPLETE only if
> **all three** are true: production-ready code, thorough documentation, fully
> tested. If any criterion fails → INCOMPLETE.

That rule is enforced by **nothing**. Items not in the list are also bucketed
by prefix heuristic, not measurement — `N*` → "stub", 15%; `S*` → "foundation",
45%.

## 1.2 The evidence shown to a reader is generated, not gathered `CRITICAL`

Of the 282 entries marked COMPLETE:

- **267** have a Code pillar reading literally
  `"Production-usable implementation for: <the entry's own title>"` — the claim
  restated as its own evidence, from the f-string at line 420.
- **15** carry specific, human-written evidence.

A reader scanning this document sees 282 rows with three green pillars each and
reasonably concludes 282 features were verified. Fifteen were.

## 1.3 Test citations are bulk-assigned by ID prefix `HIGH`

282 entries claim "Tests (full): YES". Across the whole document they cite
**23 distinct test files** — all 23 of which do exist on disk.

Traceability, measured across every file in `tests/`:

```
IDs claiming COMPLETE:                          282
   ...mentioned anywhere in the test suite:      52
   ...with no traceable test reference:         230
distinct improvement IDs referenced in tests/:   54
```

**Caveat, stated plainly:** a feature can be well tested without its tracker ID
appearing in the test file, so 230 is not a count of untested features. What it
does establish is that the *citation* is not derived — the generator assigns a
`tests_note` string by ID prefix, so for the large majority the link between an
ID and its "evidence" was never established by anyone.

## 1.4 Three host gates were cleared by a single local provider `CRITICAL`

The scorecard reports **HOST-GATED = 0**. Two commits on 2026-08-09 produced
that zero:

- `006f54d chore: complete M089 live smoke matrix locally via Ollama`
- `102ef58 docs: clear MOS-N8 and V1-P99 host gates as they are proven by local
  Ollama smoke test`

All three items are, by their own titles, **multi-provider / multi-vendor live**
checks. Ollama is a single local provider — categorically not what the gate
tests. And each entry contradicts itself:

| ID | Title | Verdict | Its own *"Still incomplete"* field |
|---|---|---|---|
| M089 | Live **multi-provider** smoke matrix (host keys) | YES / 100% | *"Live multi-provider proof on this machine"* |
| MOS-N8 | Nice N8 — Live **multi-vendor** smoke | YES / 100% | *"HOST live multi-vendor"* |
| V1-P99 | Phase 99 — Live **multi-provider** smoke (host) | YES / 100% | *"HOST live multi-vendor"* |

Scanning all 533: **exactly these three** are marked complete while carrying a
non-empty "Still incomplete" note.

The generator still holds the original, correct judgement as comments sitting
directly above the overrides that contradict them:

```python
# line 75   # MOS-N8 host — not complete without live
# line 165  # M089 remains HOST — not complete without live keys
# line 213  "M089": T(True, True, True, 100, ...)
```

**Three other documents disagree with the scorecard on M089:**
`TASKBOARD.md:52` marks it `[!]` blocked; `TASKBOARD_GROK.md` wave G5 marks it
`[!]` open; that board's "Still open" line names it explicitly. The scorecard
alone says 100%.

---

# Part 2 — Defects by board

## 2.1 Root `TASKBOARD.md`

| # | Severity | Defect |
|---|---|---|
| a | HIGH | A blocked item was flipped to done and its scope tripled |
| b | MEDIUM | Misstates the CLI entry point |
| c | MEDIUM | Fleet Proxy described as "5 tasks, T17-T21" — it has 13 |
| d | MEDIUM | "Last session" dated 2026-07-28, 120 commits stale |

**(a)** `c925b50` rewrote line 53:

```diff
- [!] Live Telegram/Slack
+ [x] AgentClaw Live Chat Relays (Telegram, Slack, Discord, DingTalk, Feishu, WeCom, LINE)
```

Blocked → done, 2 platforms → 7, one edit, in the section whose policy reads
*"finish offline Must work first; live smoke is last."*

The **code is real**: the same commit added `src/core/messengers.py` (168
lines) implementing all seven channels, genuinely integrated at six call sites
(`main.py` ×4, `assistant_goals.py:120`, `observability.py:150`). What is
absent is any basis for `[x]` on a *live host-gated* item: **no tests exist for
the module**, and channels self-report `enabled: bool(token) or dry_run`, so
without tokens it never leaves dry-run. The name `AgentClaw` appears **only on
that board line** — nowhere in the code.

**(b)** Line 3 says `entry superai = scli.main:app`. `pyproject.toml` says
`scli.main:main`. Not cosmetic — this is the line that would make a reader
dismiss defect 2.3(b) as impossible.

## 2.2 `projects/webui-management-center` (T01–T16)

| # | Severity | Defect |
|---|---|---|
| a | **CRITICAL** | `/api/{resource}` catch-all shadows 14 GET endpoints |
| b | HIGH | T15 marked `[x]`, never implemented |
| c | HIGH | T16 docs describe two features that do not exist |
| d | HIGH | `/api/sync/cliproxy` bypasses the T08 auth gate |
| e | MEDIUM | Board status wrong in both directions (5 tasks) |

**(a)** `web_app.py:410`, introduced 2026-08-09 by `0477632`. Registered at
position 13, it swallows every single-segment `/api/*` GET route registered
after it, then 404s because the name isn't in its 5-item allow-list. It lives
inside `if enable_config_write:` — so it is armed by **the exact flag the
Management Center requires**. Measured:

```
endpoint          write OFF   write ON
/api/spend              200        404   <- T02, built for this project
/api/goals              200        404   <- T03, built for this project
/api/dashboard          200        404
/api/bandit             200        404
/api/terminals          200        404
/api/status             200        404
```

All 14: `/api/audit`, `/api/status`, `/api/agent-graph`, `/api/preferences`,
`/api/wings`, `/api/palace`, `/api/plugins`, `/api/bandit`, `/api/goals`,
`/api/spend`, `/api/dashboard`, `/api/ecosystem`, `/api/cli-pool`,
`/api/terminals`. Six were listed on this board's own "do not rebuild" list of
known-good surface.

It survived because the console UI (`app.js:188`) only ever requests the 5
allow-listed names — the feature's own UI exercises the only paths that work.

**(b)** T15's deliverable is `/cliproxy-admin` gated by
`SUPERAI_WEB_ENABLE_CLIPROXY_ADMIN`. Both strings appear **zero times** in the
codebase; `GET /cliproxy-admin` → 404. The commit filed under that ID
(`49f1436 feat(web): implement T15 console save button`) implements something
else. This strands T14's genuine work — 2.7 MB of correctly pinned, licensed
`vendor/mgmt-ui/management.html`, served by nothing.

**(d)** T08's gate is **well built** — `hmac.compare_digest`, fails closed,
header-only, refuses to register write routes without a token.
`/api/sync/cliproxy` (added `1b326b5`) sits outside it and writes
`~/.superai/config/models.json`:

```
config-write OFF, no token:  /api/config registered=False
                             /api/models registered=False
                             /api/sync/cliproxy registered=True   <-- writes anyway
```

**(e)** T09, T11, T13, T14 are complete but marked `[ ]`; T15 is marked `[x]`
and absent. The board's own Rule 2 — *"set `[x]` only after running the task's
verification command and pasting the real output"* — was followed for none of
them; the Log stops at 2026-08-05.

## 2.3 `projects/fleet-proxy-features` (T17–T29)

| # | Severity | Defect |
|---|---|---|
| a | **CRITICAL** | T28 shorthand hijacks 192 of 207 CLI names |
| b | HIGH | T27 tray unreachable; stated features absent |
| c | HIGH | T29 browser is dead duplicate code |

**T17–T21 are genuine** and this board deserves credit for how that happened:
`1aaf6f9 docs(taskboard): revert T17-T21 to in progress (stubs only)` caught
the stubs, and five explicit "deeply integrate" commits fixed them. Verified
reachable from the real call path — `model_caller.py:210 → pre_call` for quotas
and the rate limiter, `:419`/`:774` for key pooling *and* real 429 rotation,
`:136-144` for the interceptor chain, `:131`/`:465` for alias resolution.

**T22–T29 never got that pass** — they went implement → `2caf390 chore(tasks):
check off T27, T28, T29 as completed`. That asymmetry is the whole story.

**(a)** `main.py`, in `main()`, from `6a2ac04`. A hardcoded 21-name whitelist
guards a CLI exposing 207 real names. Anything outside it, with 2+ argv items,
is silently rewritten. Reproduced:

```
input:   superai code-index --json
becomes: ['superai', 'run', '--json', '--model', 'code-index']
```

Measured against Typer's own registry: **189 commands + 18 sub-app groups =
207; 192 hijacked.** Six of the whitelist's 21 entries (`agents`, `board`,
`mcp`, `rules`, `skills`, `tools`) match no real command at all.

`main()` is confirmed to be the live entry point (`superai = "scli.main:main"`,
and `python -m scli` routes through it too). The spec said to parse against
`AliasRouter`; the implementation never references it. The whole block is
wrapped in `except Exception: pass`.

**Why 1190 tests missed it:** the 6 test files that drive the CLI use Typer's
`CliRunner` against the `app` object. **No test calls `main()`.** The argv layer
wrapping all 207 names has zero coverage.

**(b)** `src/cli/tray.py` is never imported; `superai tray` does not exist. The
task promised token spend and quota usage; the implementation is a hardcoded,
disabled `'SuperAI Status: Online'` label reading nothing.

**(c)** `src/core/browser.py` is referenced only by its own test, registers in
no tool registry, and duplicates `src/core/browser_tool.py` — which *is* wired
in at `main.py:6455`.

Both tests pass on unreachable code: `test_tray.py` mocks `pystray.Icon`
wholesale; `test_browser.py` mocks both `urlopen` and `sync_playwright`.

## 2.4 `TASKBOARD_AGY.md` — clean

**No defects found.** This board is the counter-example that proves the rest are
fixable.

Leaf-vs-header consistency check: **9 headers with leaves, 0 inconsistent.**
Status distribution is honest — 58 `[ ]` open, 7 `[~]`, 3 `[x]`, 1 `[!]`.

It reads honestly *because it was already corrected*. Its own demotion note,
2026-07-29:

> These five read `[x] DONE` while every one of the ~45 leaf checkboxes below
> them was still unticked, and two of those leaves carried explicit reopen
> notes … The leaves were right and the headers were wrong.

The repo has diagnosed this exact failure mode before, correctly, and knows the
remedy. That remedy was never applied to the other boards.

## 2.5 `TASKBOARD_GROK.md` — one minor defect

61 `[x]`, 4 `[ ]`, 3 `[!]`, 1 `[~]`.

**Substantially honest, and empirically so.** I ran the board's own stated
"Full verify pack":

```
pytest test_learning_lifecycle_m061_m063 test_learning_engine_gaps
       test_routing_prefs_bandit_g2 test_msg_vega_plugin_bandit
       test_stream_dashboard_g3_g4 test_m079_m027_m093
       test_improvement_v4 test_grok_i1_residuals
→ 73 passed in 60.04s
```

Its G1–G4 claims stand up. It also marks G5/M089 `[!]` open and names it under
"Still open" — **correctly**, in direct contradiction to the scorecard's 100%.

**The one defect:** header `G3.1 M027 + G3.2 V4-M4 — [x] offline` sits above 22
leaves, **3 of which are unticked** — the same leaf-vs-header pattern AGY was
demoted for. Minor in scale, identical in kind. Note the header is qualified
`[x] offline`, so this may be deliberate; it needs an owner's ruling, not an
assumption.

Also stale: "Last session" is dated 2026-07-24.

---

# Part 3 — Executable findings (facts, not inference)

Everything in this section was produced by running code against the pinned
clone.

## 3.1 The test suite does not pass

```
1 failed, 1190 passed, 1 warning in 727.16s (0:12:07)
FAILED tests/test_payload_rules.py::test_interceptor_chain_init - assert 5 == 3
```

`8b1c857` (02:15) claims *"ensure 100% test pass"*. `dc7841c` (02:44) added two
interceptors to `InterceptorChain.__init__` without updating the test asserting
a chain of 3. The claim was stale within 29 minutes and was never re-checked
across the six commits that followed it that day.

Note the suite is **1191 collected**, not the ~1010 recorded in earlier
sessions — it has grown, so the older baseline is not a valid comparison.

## 3.2 AI Council is a 404 on every clean clone

Five commits on 2026-08-09 claim it is vendored, in the navigation, and
natively embedded. The backend **is** genuinely vendored — 148 tracked files.
But `web_app.py:60-72` mounts `/council` only if
`projects/ai-council/frontend/dist` exists, and that directory is **gitignored**
(`frontend/.gitignore:11`), **built by nothing in the repo**, and absent. The
mount sits in `except Exception: pass`. The nav advertises it at `:495` and
`:1147`.

```
/council       -> 404
/council-api   -> 404
/dashboard     -> 307
/console       -> 200
```

## 3.3 `/dashboard` is registered twice

`:458` (redirect, added today) and `:1134` (`dashboard_page`, the pre-existing
live HTML). FastAPI takes the first; the second is permanently dead code.

```
routes registered at /dashboard: 2
GET /dashboard -> 307 | location=/static/index.html
followed -> 200 | is it the old dashboard_page HTML? False
```

## 3.4 The WebUI ships in no wheel

`pyproject.toml` package-data lists `scli = ["static/pwa/*"]`. `static/console/*`
— the entire T01–T16 UI — is excluded, and there is no `MANIFEST.in` and no
`include-package-data`. Anyone who installs rather than clones gets no
Management Center.

## 3.5 Uncommitted work will break HEAD when committed

The live worktree has 5 untracked modules (`agent_launcher`, `client_keys`,
`conditional_router`, `os_integrations`, `plugin_manager`) and modified files
importing them. Two import sites are **not** guarded (`web_app.py:585`,
`:1360`). HEAD itself is clean — zero references — so the risk is entirely in
the next `git add`.

---

# Part 4 — What genuinely holds up

This matters as much as the defects, and it is substantial.

- **T17–T21** — quotas, key pooling with real 429 rotation, aliases, the
  token-bucket limiter and the interceptor chain are all reached from the live
  model-call path. Verified by execution.
- **T08's auth gate** — constant-time comparison, fails closed, header-only and
  genuinely CSRF-safe, logs an error if write is enabled without a token. The
  bypass beside it is a gap in coverage, not a flaw in the gate.
- **T06/T07/T09/T10/T12** — atomic config write with backup, the diff helper,
  and every config/model management endpoint work behind the gate.
- **T13/T14** — vendored bytes are correctly protected: `vendor/.gitattributes`
  carries `* -text`, `git check-attr` returns `text: unset`, and
  `vendor_sync --check` reports 4/4 current. The protection genuinely precedes
  the vendored bytes — the exact trap this repo has been bitten by before.
- **T25/T26** — the console UI is real and serves: 15.7 KB page, 12.5 KB CSS,
  8.5 KB JS. `/console` → 200.
- **`messengers.py`** — seven chat channels, genuinely integrated at six sites.
- **AI Council backend** — 148 files, properly vendored.
- **AGY board** — clean, and already self-corrected once.
- **GROK board** — its own verify pack passes, 73 tests.
- **The scorecard generator is reproducible** — a regen changed only the
  `Generated:` date. The tooling is sound; the *inputs* are hand-maintained.

---

# Part 5 — Root cause

Three of the four CRITICAL findings are the **same bug**:

| Defect | The hardcoded list | What it drifted from |
|---|---|---|
| `/api/{resource}` shadowing 14 routes | 5-name allow-list | the live route table |
| T28 hijacking 192 commands | 21-name whitelist | Typer's 207-name registry |
| Scorecard's 282 COMPLETE | `COMPLETE_IDS`, 268 ids | the actual codebase |

Each is a manually maintained list required to stay in sync with a live
registry, and each drifted. The T08 auth gap is a fourth instance — a gate
applied by hand per-route rather than derived from the set of mutating
endpoints.

**The second thread:** `except Exception: pass` wraps the AI Council mount, the
T28 argv rewrite, and the plugin loader. Every one of those failures is silent.
That is why a 404'd feature could stay in the navigation, and why a
192-command regression could pass 1190 tests.

**The third:** tests that mock the unit and never assert the wiring.
`test_tray.py` and `test_browser.py` both pass on code no user can reach, and
no test anywhere invokes `main()`.

---

# Part 6 — Functional correctness

Parts 1–5 audited *records*. This part audits *behaviour* — the code was
executed, not read. It reverses the overall verdict in the codebase's favour.

## 6.1 Structural health — all clean

| Check | Result |
|---|---|
| `import` every module under `src/core` + `src/cli` | **249 / 249, 0 failures** |
| `--help` for every command and sub-app group | **208 / 208, 0 failures** |
| Full test suite | **1190 passed, 1 failed** |
| GROK board's own "Full verify pack" | **73 passed** |
| TOP_30 contract depth (`invoke_top30_offline`) | **help 30/30, contracts 30/30, failures: []** |
| MCP safety matrix (`safety_matrix`) | **25 tools; 0 ghost, 0 unclassified, 0 unmapped; CLI parity true** |
| Vendored-bytes integrity (`vendor_sync --check`) | **4/4 current** |

The `--help` row matters: all 208 surfaces render correctly **through the Typer
`app` object**. They are broken through the real entry point (§6.4). That
distinction is the entire T28 bug.

## 6.2 Feature behaviour — executed with real APIs, asserted on real output

| Feature | Test | Result |
|---|---|---|
| **T17** quotas | `set_budget` → `record_spend` → persist | **PASS** |
| **T17** enforcement | overspend past budget | **PASS** — raises `QuotaExceededError` |
| **T18** key pool | rotate k1→k2→k3→wrap | **PASS** — correct order and wraparound |
| **T18** fallback | empty pool → env var | **PASS** |
| **T19** aliases | `AliasRouter.resolve` via `model_caller` | **PASS** |
| **T20** rate limiter | capacity 2, 4 acquires | **PASS** — `[True, True, False, False]` |
| **T21** privacy filter | API key + email in `prompt` | **PASS** — both redacted |
| **T06/T10** config | save → reload → backup written | **PASS** — persisted, 6 backups |
| `browser_tool` | unreachable host | **PASS** — SSRF-guarded, degrades safely |
| `messengers` | cli / file / slack / telegram / line | **PASS** |

**T17–T21 are functionally correct**, not merely integrated. That board's
mid-course correction (`1aaf6f9` → five integration commits) genuinely worked.

Two of my probes failed on **my** error, not the code's, and are recorded here
because a validation report should show its own corrections: I asserted the
privacy filter scans `payload["messages"]` (it scans `prompt`/`system_prompt`,
which *is* what this codebase sends — verified at `model_caller.py:136-144`),
and I called `send(channel, message)` when the signature is
`send(message, channel)`. Neither was a defect.

## 6.3 NEW defect — `/openapi.json` returns 500, API docs are blank `HIGH`

**Pre-existing** (`d27820f`, 2026-07-14) — *not* caused by the recent work.

```
GET /docs         -> 200
GET /redoc        -> 200
GET /openapi.json -> 500
```

`/docs` and `/redoc` are HTML shells that fetch the schema client-side. That
fetch fails, so **the interactive API documentation renders empty for every
user.**

Cause — `PydanticUserError`: `MemoryQuery` (`web_app.py:468`), `PreferenceBody`
(`:475`) and `FeedbackBody` (`:1122`) are Pydantic models declared **inside
`create_app()`**. A function-local model leaves an unresolvable `ForwardRef` at
schema-generation time.

**Fix:** move the three classes to module scope. No test requests
`/openapi.json`; one assertion would have caught this in July.

## 6.4 NEW defect — dry-run is broken for 4 of 7 chat relays `MEDIUM`

Introduced 2026-08-10 (`c925b50`) — the same commit as the disputed `[x]` in
§2.1(a). With `SUPERAI_MESSENGER_DRY_RUN=1`:

```
cli / file / line    ok=True
slack / telegram     ok=True   dry_run=True
discord              ok=False  webhook URL blocked: DNS resolution failed
wecom                ok=False  webhook URL blocked: DNS resolution failed
feishu               ok=False  webhook URL blocked: DNS resolution failed
dingtalk             ok=False  webhook URL blocked: DNS resolution failed
```

In `_http_json` (`:186-205`) the SSRF check runs **before** the dry-run
short-circuit; unconfigured adapters pass a placeholder
`https://example.invalid/…` that fails validation first.

**Stated precisely:** no message payload is sent — the dry-run branch does
prevent the POST. But a **DNS lookup leaves the machine before the check**, so
dry-run is neither a zero-network guarantee nor host-independent. Three-line
fix. `messengers.py` has **no tests at all**.

## 6.5 Confirmed defects, now with execution evidence

**You cannot read the help for 192 of 207 commands.** Through the real entry
point (`superai = "scli.main:main"`):

```
superai status --help    -> ['superai','status','--help']                     OK
superai code-index --json-> ['superai','run','--json','--model','code-index'] HIJACKED
superai security --help  -> ['superai','run','--help','--model','security']   HIJACKED
```

Asking a command for its help is the most harmless thing a user can do, and for
192 names it silently becomes a model invocation.

**Full HTTP GET sweep, config-write ON:**
`{200: 23, 404: 14, 422: 1, 307: 1, 500: 1, 502: 1}` — the 14 are §2.2(a)'s
shadowed routes, the 500 is §6.3, and the 502 is `/v1/models` proxying to a
CLIProxyAPI instance that isn't running (**benign**, not a defect).

**Advertised features that 404:** `/council`, `/council-api`,
`/cliproxy-admin`. Working: `/console` 200, `/dashboard` 307→200.

## 6.6 What this pass changes about the verdict

The defects cluster in exactly **two** places, and nothing found here suggests
the underlying engineering is unsound:

1. **Dispatch layers** — argv rewriting and route registration order. Both are
   hardcoded lists that drifted from a live registry, and both are structurally
   invisible to this suite: every test drives the Typer `app` and the FastAPI
   route table *directly*, so the argv wrapper and the registration *ordering*
   are the two things 1191 tests cannot see.
2. **Code committed in the last 48 hours without tests** — the interceptor
   assertion, the messenger dry-run gap, the `/dashboard` duplicate.

Genuinely strong, verified by execution: the **MCP safety subsystem** (the
best-engineered thing in the repo — 25 tools, all classified, zero ghosts,
complete CLI parity, defaults to mock, live behind an explicit env gate),
**`browser_tool`'s** real SSRF protection, **T17–T21**, **config atomicity**,
**TOP_30 depth**, and **vendored-byte integrity**.

The last two days moved faster than the test discipline that produced the rest
of this repository.

---

# Part 7 — Corrected count

**19 code and route defects**, plus **4 systemic record defects** (§1.1–1.4),
plus **1 uncommitted-work risk** (§3.5).

| Severity | Count | Items |
|---|--:|---|
| CRITICAL | 5 | `/api/{resource}`; T28; scorecard-by-list; generated evidence; 3 falsified host gates |
| HIGH | 9 | T15 absent; T16 docs; auth bypass; AI Council 404; failing suite; T27; T29; AgentClaw `[x]`; **`/openapi.json` 500** |
| MEDIUM | 8 | `/dashboard` ×2; packaging; entry point; board staleness ×3; GROK leaf/header; **messenger dry-run** |
| LOW | 2 | AgentClaw commit message; scorecard test-citation traceability |
| **Subtotal (audited at HEAD `6b798ff`)** | **24** | |

**Part 8 adds 9 further items** from AGY's work, **committed at 14:36 as
`b5d74d8`** and re-verified against that commit:

| Severity | Count | Items (Part 8) |
|---|--:|---|
| CRITICAL | 2 | **3** unclassified MCP tools (§9.1); committed import of uncommitted `chrome_profile` (§9.2) |
| HIGH | 4 | suite 1→7 failures; `oauth_manager` non-functional; `agent_launcher` wrong port; `client_keys` plaintext/no-atomic/no-lock |
| MEDIUM | 3 | `usage_logger` expanduser + stdout print; 3 unreferenced modules; zero tests for 11 modules |
| LOW | 1 | `test_corrupted_cache_recovery` new failure (needs triage) |
| **Part 8+9 subtotal** | **10** | |

Plus **2 latent risks** (§8.7, currently uncalled) and **1 decision**
(§8.8 IDE ToS).

**Grand total: 34 items** — all in committed history and **all pushed to `origin/master`** (@ `c5d33f5`).

**Audit boundary:** tag `audit-checkpoint-20260810` → `c5d33f5`. Later work is
out of scope for this report; see `SUPERAI_AUDIT_CHECKPOINT_20260810.md`.

Remediation is in **`SUPERAI_CORRECTION_PLAN_20260810.md`** (the two functional
items are C2.2 and C3.7; AGY's items are wave C6).

---

# Part 8 — AGY's work of 2026-08-10 (reviewed during the audit)

AGY (Antigravity) worked on this repo throughout the audit. Reviewed from a
working-tree snapshot taken at **14:20**.

**⚠ Status changed mid-review — this section was corrected.** At review time the
work was uncommitted and `HEAD` was `6b798ff`. **At 14:36, while this section
was being written, AGY committed it:**

```
b5d74d8 feat: integrate CLIProxyAPI and CPAMC vendor features
        (oauth, log tailing, quota ui, auth files)
19 files changed, 2288 insertions(+), 415 deletions(-)
```

**Every finding below was re-verified against the commit itself**, not the
snapshot, by cloning at `b5d74d8`:

```
COMMITTED safety matrix: Issues: unmapped=['superai_websearch']; unclassified=['superai_websearch']
agent_launcher port    : 127.0.0.1:8000        (server default is 8787)
oauth verification_uri : https://superai.local/device?code={user_code}
```

All three headline defects are **now in committed history on `master`**, which
raises their severity: they are no longer work-in-progress that could simply be
revised before landing. `master` is now 9 commits ahead of `origin`.

Work still uncommitted after that commit: a further `mcp_server.py`
modification and a new `src/core/chrome_profile.py` — not reviewed here.

## 8.1 The headline: AGY broke the MCP safety subsystem

Part 6 identified `mcp_safety.py` as the best-engineered component in the
repository — 25 tools, every one classified SPEND/MUTATE/FREE, **0 ghosts,
0 unclassified, full CLI parity**, verified by execution.

With AGY's work applied:

```
message      : Issues: unmapped=['superai_websearch']; unclassified=['superai_websearch']
unclassified : ['superai_websearch']
registered   : 26
```

A 26th MCP tool was registered **without a safety classification**. The
subsystem's own ghost/unclassified detector now reports a defect where it
previously reported none.

This violates **AGY's own board, Global DoD item #4**, verbatim:

> *"Registry honesty: Extend `foundation_safety.SPEND_PATHS` / MCP matrices
> when adding paths."*

It is also, exactly, the root cause from Part 5 — a hand-maintained registry
that a new addition failed to update.

## 8.2 The suite regressed from 1 failure to 7

```
HEAD  6b798ff :  1 failed, 1190 passed
+ AGY work    :  7 failed, 1184 passed   (14m50s)
```

Six new failures. **Five of the seven are the MCP-safety regression** —
one defect surfacing through five independent guards, which is the safety net
working exactly as designed:

```
FAILED tests/test_surface_inventory.py::test_mcp_tools_are_all_safety_classified
FAILED tests/test_foundation_complete_must.py::test_mcp_safety_matrix
FAILED tests/test_foundation_complete_must.py::test_dashboard_and_top30_and_mcp_parity
FAILED tests/test_agy_i1_residuals.py::test_mcp_safety_matrix_exhaustive
FAILED tests/test_m079_m027_m093.py::test_m093_safety_matrix_and_live_block
```

Plus:
- `test_payload_rules.py::test_interceptor_chain_init` — now `assert 6 == 3`
  (was `5 == 3`). AGY added a sixth interceptor (`VirtualModelInterceptor`),
  deepening the pre-existing §6/C1.1 failure rather than fixing it.
- `test_code_intelligence_n258.py::test_corrupted_cache_recovery` — a **new,
  unrelated** failure requiring separate triage.

## 8.3 What AGY built — 11 new modules

| Module | Wired in? | Assessment |
|---|---|---|
| `log_tailer.py` | web_app | **Good.** Correct on small, multi-block and missing files |
| `client_keys.py` | web_app | Good crypto, weak file handling — see 8.5 |
| `usage_logger.py` | web_app | Works; `expanduser` concern — see 8.6 |
| `agent_launcher.py` | web_app | **Broken by wrong port** — see 8.4 |
| `conditional_router.py` | web_app | Not individually tested |
| `ide_integrations.py` | web_app | 5 IDE shims; ToS consideration — see 8.7 |
| `plugin_manager.py` | payload_rules | Loaded via guarded import |
| `oauth_manager.py` | web_app | **Non-functional stub** — see 8.4 |
| `macos_bar.py` | — | **Unreferenced** |
| `opencode_sync.py` | — | **Unreferenced** |
| `os_integrations.py` | — | **Unreferenced** |

**All 260 modules import cleanly (0 failures)** — up from 249, and the
§3.5 dangling-import risk is **resolved** in this snapshot: the previously
untracked modules now exist alongside their importers.

**Zero tests were added for any of the 11 modules.**

Three are unreferenced dead code — the same T27/T29 pattern this audit already
documented.

## 8.4 Two features that cannot work as written

**`agent_launcher.py:14` points every agent at the wrong port.**

```python
# Assuming SuperAI runs on localhost:8000
proxy_url = "http://127.0.0.1:8000/v1"
```

`superai web` defaults to **8787** (`main.py:5286`). All four launch profiles —
Claude Code, Grok CLI, OpenCode, Kimi CLI — would point third-party agents at a
port where nothing is listening. Note `opencode_sync.py:21` uses **8787**
correctly, and `tray.py:6` uses **8000** incorrectly: three modules, two
assumptions, one right answer.

**`oauth_manager.py` is a stub that can never authenticate.**

- `start_device_flow` returns a random UUID as the device code and
  `verification_uri = "https://superai.local/device?code=…"` — a **domain that
  does not exist**.
- `poll_device_flow` returns the stored dict; status is `"pending"` forever.
  **There is no code path anywhere that sets it to authorized.**
- State is in-memory only, lost on restart. No provider is ever contacted.

It is wired to two live endpoints (`/api/oauth/start`, `/api/oauth/poll`), so
the API presents a working OAuth flow that cannot complete.

## 8.5 New credential store: good crypto, weak file handling

`client_keys.py` mints keys with `secrets.token_urlsafe(32)` — correct — and
`list_keys()` properly redacts. Scoping is real: expiry, model allow-list,
token budget, revocation.

But the store itself:

- **Plaintext keys on disk**, with the key as the dict key, in
  `~/.superai/config/client_keys.json`.
- **No `chmod 0600`, no atomic write, no lock** — confirmed: neither
  `client_keys.py`, `usage_logger.py` nor `plugin_manager.py` contains any of
  `chmod` / `atomic_write` / `FileLock` / `0o600`.
- `consume_budget()` is a read-modify-write with no lock, so concurrent use
  loses budget accounting.

The repo already solved this twice: `Config.save()` uses
`atomic_write_with_backup` (T06), and `key_pool.py` uses `FileLock`. The new
credential store uses neither.

`validate_key()` also uses a plain dict lookup where `_check_management_auth`
correctly uses `hmac.compare_digest` — an inconsistency with the codebase's own
standard.

## 8.6 `usage_logger.py` repeats a known-painful pattern

```python
DB_PATH = os.path.expanduser('~/.superai/usage.db')   # module-level
```

`os.path.expanduser` reads the environment directly, so a test that isolates
via `monkeypatch.setattr(Path, "home", …)` will **not** isolate this — the
exact mismatch that caused a CI hang in this repo before, and which the WebUI
board records as a standing "Testing trap". Resolution is also frozen at import
time.

Additionally, `log_usage()` swallows errors with `print(f"Error logging
usage: {e}")` to **stdout**, which would corrupt any `--json` envelope on a
path that reaches it.

## 8.7 Two latent risks — defined, not yet called

Both are **currently unreachable** (no call sites anywhere), so neither is an
active defect. Both would be significant the moment they are wired up:

**`mcp_server.py :: auto_provision_claude_mcp()`** rewrites the user's
`~/.claude.json` — read → mutate → `json.dump`, with **no atomic write, no
backup, no lock**. That file holds this user's live Claude Code configuration
and auth tokens. Under the mandatory parallel-session rule, a concurrent write
during that read-modify-write can corrupt it; an interrupted write leaves
truncated JSON. If this is to be used, it needs the same
`atomic_write_with_backup` treatment T06 gave `Config.save()`, plus explicit
user consent — silently editing another tool's config is a surprising side
effect.

**`browser.py :: import_chrome_login_state()`** harvests **all** cookies from
the user's Chrome profile via `browser_cookie3` and injects them into a headless
browser context — no domain filter, no consent prompt. Combined with
`read_page(url)`, an agent could read any authenticated page as the user. Note
this lives in `browser.py`, the unreferenced duplicate module Part 2.3(c)
recommends deleting.

## 8.8 ToS consideration — IDE integration shims

`ide_integrations.py` adds five IDE adapters (Cursor, GitHub Copilot,
CodeBuddy, GitLab Duo, Qoder), two of which expose `spoof_auth_status()`.

**Described accurately:** `GitHubCopilotDaemon.spoof_auth_status()` returns
`authenticated: True` **only if the user's real GitHub Copilot token file
exists locally**. It does not forge credentials or bypass a licence check — it
reports local token presence in the shape VSCode expects, so the extension will
route through SuperAI instead of GitHub's endpoint.

That is interop for a licence the user already holds. It is still worth a
deliberate decision, because routing a vendor's proprietary IDE extension
through a third-party proxy is a plausible terms-of-service question — the same
class of question this project already handled explicitly with the T15/T16 ToS
banner for the vendored management UI. **Flagged for a decision, not as a
defect.**

## 8.9 What AGY did not touch

- **`main.py` is unmodified** — the T28 argv hijack (192 of 207 commands) is
  fully intact.
- **The `/api/{resource}` catch-all is unchanged** — all 14 endpoints still 404
  under config-write; re-verified against this snapshot.
- **`/openapi.json` still returns 500** — same `PydanticUserError`.

None of the audit's CRITICAL findings are addressed by this work.

## 8.10 Verdict on AGY's day

**Genuinely useful:** `log_tailer.py` is correct under test, `client_keys.py`
is a real scoped-key system with sound key generation, the console UI received
substantial work (~1,400 lines), and every module imports cleanly.

**Not ready to commit as-is.** Blocking items, in order:

1. **Classify `superai_websearch`** in the MCP safety matrix — this alone fixes
   5 of the 7 test failures and restores the repo's strongest subsystem.
2. **Triage `test_corrupted_cache_recovery`** — a new, unexplained failure.
3. **Fix the port in `agent_launcher.py`** (8000 → 8787) — the feature cannot
   work otherwise.
4. **Decide on `oauth_manager.py`** — either implement a real device flow or
   remove the two endpoints that advertise one.
5. **Harden `client_keys.py`** — atomic write, `0600`, lock.
6. **Add tests** — 11 new modules, zero tests, on a board whose own DoD
   requires them.

The pattern is identical to the one this audit found in the T22–T29 work:
**real capability, delivered faster than the verification discipline that
protects it.** The difference is that this time the safety net caught it — five
independent guards fired on one unclassified tool. That net is worth keeping.

---

# Part 9 — Checkpoint (`c5d33f5`, 14:50) and two late findings

A second AGY commit landed at 14:50 while Part 8 was being written. **The audit
line is drawn here** — see `SUPERAI_AUDIT_CHECKPOINT_20260810.md` and local tag
`audit-checkpoint-20260810`. Work after this point gets its own report.

```
c5d33f5 14:50 | feat: add skillx marketplace search to MCP tools
b5d74d8 14:36 | feat: integrate CLIProxyAPI and CPAMC vendor features
master: behind=0 ahead=0  — everything here is PUSHED to origin
```

## 9.1 The MCP classification regression is compounding: 1 → 3

| Point | Registered | Unclassified |
|---|--:|---|
| `6b798ff` (audit pin) | 25 | **0** |
| `b5d74d8` (14:36) | 26 | 1 |
| `c5d33f5` (14:50) | **28** | **3** |

`superai_websearch`, `superai_skillx_search`, `superai_chrome_profile` — three
unclassified MCP tools in fourteen minutes. **C6.1 must now classify three,
not one.**

## 9.2 A committed import of an uncommitted module — §3.5 realised `CRITICAL`

`src/core/mcp_server.py:711`, committed and pushed:

```python
from core.chrome_profile import open_url_in_profile
```

`src/core/chrome_profile.py` is **untracked**. Proven from the git object
database:

```
git cat-file -e c5d33f5:src/core/chrome_profile.py  → ABSENT
git ls-files --error-unmatch …/chrome_profile.py    → UNTRACKED
git ls-tree origin/master src/core/ | grep chrome   → 0 files
```

**A fresh clone of `origin/master` raises `ImportError` when the
`superai_chrome_profile` MCP tool is invoked.** This is precisely the risk
recorded in §3.5 and correction item C5.1 — now realised, on the remote.

**Methodology correction — a false negative I nearly published.** My first
check reported `IMPORT OK` in a clean clone. That was wrong: SuperAI is
installed here as an **editable install** whose meta-path finder maps package
names directly at the developer's live tree —

```
site-packages/__editable___superai_0_1_0_finder.py
  MAPPING = {'core': 'C:\...\github\SuperAI\src\core', 'scli': '…\src\cli'}
```

A meta-path finder **overrides `sys.path`**, so filtering `sys.path` does not
isolate it. On this machine, any import-based presence check can silently
resolve to the live working tree instead of the tree under test.

**Standing rule for this repo: verify module presence with `git cat-file` /
`git ls-files`, never with `import`.**

---

## Closing note on the numbers

When the corrections in Part 1 land, the reported figures will get **worse**:
HOST-GATED returns to 3, COMPLETE falls from 282, and the strict completion
rate drops below 54.4%.

That lower number will be the first one in this project's history that was
actually measured. It is worth more than the higher one.
