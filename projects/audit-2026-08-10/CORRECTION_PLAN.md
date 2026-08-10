# SuperAI — Full Correction Plan

**Companion to:** `SUPERAI_AUDIT_FINAL_20260810.md` (the single complete audit,
Parts 1–9) and `SUPERAI_AUDIT_CHECKPOINT_20260810.md` (boundary + re-baseline)
**Date:** 2026-08-10
**Status:** proposed — nothing has been changed
**Target:** `545745d` (master, stable — development paused)
**Scope:** 34 items — 29 code/route defects, 4 systemic record defects, 1 risk

**Total ≈ 15–18 hours**, in 7 waves. Each wave ends at a committable,
independently verifiable point. **Wave C0 (≈ 90 min) fixes everything that is
currently broken for a user or actively false in the project's own records.**

---

## ✅ Target is now fixed — development paused

**Updated 2026-08-10, later.** The other session paused. Master is stable at:

```
545745d  15:03  feat: add light theme and i18n support inspired by vben-admin
behind=0 ahead=0 — fully pushed
```

The two commits after the audit checkpoint are **frontend-only** (3 files, 71
insertions, all under `src/cli/static/console/`) with no new routes, MCP tools
or imports. They add no defects, so **this plan applies unchanged and now
targets `545745d`**. Every finding was re-verified there: 28 MCP tools with 3
unclassified, 192/207 CLI names hijacked, 14 shadowed routes, `/openapi.json`
500, `/council` and `/cliproxy-admin` 404, 2 `/dashboard` handlers.

This removes the biggest execution risk the plan was written under — HEAD moved
three times mid-audit. **You can branch, fix and verify against a target that
will not move.**

One consequence worth stating plainly: `behind=0 ahead=0` means all 34 defects
are on `origin/master`. These are corrections to published history, not local
cleanup.

---

## Working rules

From `brain/core/_core.md` Standing Rule 8 — parallel sessions are always
writing to this repo:

- Branch off `master`: `fix/audit-remediation-20260810`.
- **Stage explicit paths only.** Never `git add -A` / `git add .` / `commit -a`.
- Commit at every wave boundary; uncommitted work is the only work another
  session can destroy.
- **Never force-push.** Rejected push → fetch, rebase, push.
- Re-check `git log -1` before claiming your commit is HEAD.
- `master` is **fully pushed** (`behind=0 ahead=0`) — so these are corrections
  to published history. Push each wave as it lands.
- The live worktree is nearly clean. The one file that matters is untracked
  `src/core/chrome_profile.py` — it is **needed by C6.1b**, do not delete it.
  `temp_*/`, `find_path*.py` and `smoke_out.json` are someone else's scratch.

**Verification standard for this plan:** no item is done until its stated
command has been run and its real output pasted into the commit or the board.
That is the repo's own Rule 2, and not following it is how we got here.

---

# Wave C0 — Stop the bleeding (≈ 90 min)

Four items. Two break the product; two make the project's records false.
Ship this wave alone, verify, push.

## C0.1 — `/api/{resource}` catch-all shadows 14 endpoints `CRITICAL`

**File:** `src/cli/web_app.py:410` (GET) and `:412` (POST)

Registered at position 13, it swallows every single-segment `/api/*` GET route
registered after it. Armed by `SUPERAI_WEB_ENABLE_CONFIG_WRITE=1` — the flag the
Management Center requires.

**Fix:** move both registrations to the **very end of `create_app()`**, after
every other route. FastAPI matches in registration order, so a catch-all
placed last can only receive what nothing else claimed. Add a comment stating
*why* it must stay last.

**Do not** attempt the "5 explicit routes" refactor in this wave — `:397-450`
is a single handler with `elif resource == …` branches, so it needs the branch
bodies extracted first (~45 min). Schedule it in C3 if wanted.

**Verify:**
```python
# SUPERAI_WEB_ENABLE_CONFIG_WRITE=1, token set
for p in ["/api/spend","/api/goals","/api/dashboard","/api/bandit",
          "/api/terminals","/api/status","/api/agent-graph","/api/preferences",
          "/api/wings","/api/palace","/api/plugins","/api/ecosystem",
          "/api/cli-pool","/api/audit","/api/quotas"]:
    assert client.get(p, headers=H).status_code != 404, p
```

**Regression test:** derive the assertion from `app.routes` — find the index of
any path-parameter route under `/api/` and assert no literal `/api/*` route is
registered after it. A hardcoded list of 14 would be the same defect again.

**⚠ Interacts with C2.1.** Both edit route registration in `create_app()`.
C2.1 moves `/api/sync/cliproxy` *into* the `enable_config_write` block; C0.1
moves the catch-all to the *end* of the factory. Do **C0.1 last of the two**,
or the catch-all can end up before routes C2.1 just relocated. Re-run C0.1's
15-path assertion after C2.1 either way.

## C0.2 — T28 shorthand hijacks 192 of 207 CLI names `CRITICAL`

**File:** `src/cli/main.py`, in `main()`

**Fix:** query Typer's registry instead of maintaining a parallel list. Two
subtleties the obvious implementation gets wrong:

1. `CommandInfo.name` is `None` when written `@app.command()` with no string —
   the real name derives from the function name, `_` → `-`. Filtering on
   `if c.name` silently drops 37 commands.
2. Sub-app groups are **not** in `registered_commands` — `app.registered_groups`
   holds 18 more (`config`, `git`, `security`, `kg`, …). Miss them and
   `superai security scan` breaks.

```python
names = {
    c.name or c.callback.__name__.replace("_", "-")
    for c in app.registered_commands
} | {
    g.name or g.typer_instance.info.name
    for g in app.registered_groups
}

first = sys.argv[1]
if first not in names:
    from core.model_router import AliasRouter
    if AliasRouter().resolve(first) != first:      # only rewrite REAL aliases
        sys.argv = [sys.argv[0], "run", sys.argv[2], "--model", first] + sys.argv[3:]
```

Also **drop or narrow the bare `except Exception: pass`** around this block.

**Assert the derivation before shipping** — verified against the clone:
```python
assert len(names) == 207, len(names)   # 189 commands + 18 groups
```
If it reads 152 or 190, the derivation is wrong. Do not ship until it reads 207.

**Behavioural change to confirm with the author:** an unrecognised first
argument now falls through to Typer's normal "no such command" error instead of
being treated as a model. This is correct and matches T28's own spec (*"parse
the first argument against `AliasRouter`"*), but it is a visible change.

**Verify:**
```
superai code-index --json      # runs code-index
superai security scan .        # reaches the sub-app
superai gemini-cli "hello"     # rewrites — a real shipped alias
superai not-a-thing "x"        # errors; does not silently call a model
```

**Regression test:** `tests/test_cli_shorthand.py`, parametrised over **every**
name in the derived set — not a sample. There is currently **no test that calls
`main()` at all**; that gap is why this passed 1190 tests.

## C0.3 — Restore the 3 falsified host gates `CRITICAL`

**File:** `scripts/gen_v1_v6_unified_improved_scorecard.py` lines 213, 220, 226

M089, MOS-N8 and V1-P99 are multi-provider/multi-vendor **live** checks marked
`Complete? YES / 100%` on the evidence of a single **local** Ollama run. All
three still carry a "Still incomplete" field contradicting their own verdict —
the only 3 of 533 that do. The generator's original judgement survives as
comments at lines 75 and 165, directly above the overrides.

**Fix:** revert the three `T(True, True, True, 100, …)` entries to host-gated.
If the tooling has no HOST-GATED state for them, set `Complete? NO` at the
percent that reflects offline-only readiness.

**Verify:**
```
python scripts/gen_v1_v6_unified_improved_scorecard.py
git diff docs/V1_V6_UNIFIED_IMPROVED_SCORECARD.md
```
Expect **HOST-GATED back to 3**, COMPLETE down from 282, strict rate below
54.4%. **A lower number is the correct outcome.**

The scorecard is fully reproducible (a regen changes only the `Generated:`
date), so fixing the script and regenerating is the entire job.

**Also reconcile:** `TASKBOARD.md:52` and `TASKBOARD_GROK.md` G5 both already
say M089 is blocked. After this fix all three documents agree.

## C0.4 — Un-flip the chat-relay tick `HIGH`

**File:** `TASKBOARD.md:53`

`c925b50` turned `[!] Live Telegram/Slack` into `[x] AgentClaw Live Chat Relays
(… 7 platforms)` — blocked→done and 2→7 platforms in one edit, in the section
whose policy is *"live smoke is last."*

The code is real and integrated; the `[x]` is not supported — **no tests exist**
for `messengers.py`, and channels are `enabled: bool(token) or dry_run`.

**Fix:** revert to `[!]` and name the module, not a brand absent from the code:
```
- [!] Live chat relays via `core/messengers.py` (Telegram, Slack, Discord,
      DingTalk, Feishu, WeCom, LINE) — offline paths implemented and wired;
      live send unproven, no tests
```

**Commit C0. Run the full suite. Push.**

---

# Wave C1 — A truthful green suite (≈ 20 min)

## C1.1 — `test_interceptor_chain_init` fails at HEAD `HIGH`

**File:** `tests/test_payload_rules.py:89` — `assert 5 == 3`

`dc7841c` added `ToolHubInterceptor` and `FusionVisionInterceptor` without
updating the test.

**Decide first:** should those two be on by default? The constructor already
has `use_toolhub` / `use_fusion_vision` parameters. If yes, update the
assertion; if no, default them off.

**Then assert on identity, not count**, so the next addition doesn't break it:
```python
names = {type(i).__name__ for i in chain.interceptors}
assert names == {"PrivacyFilterInterceptor",
                 "AntigravityCodingFilterInterceptor",
                 "SessionArchiveInterceptor"}
```

**Verify:** `python -m pytest tests/ -q` → `1191 passed`.

Only after this is green can anyone truthfully say "100% test pass."

---

# Wave C2 — Close the security gap (≈ 30 min)

## C2.1 — `/api/sync/cliproxy` bypasses the auth gate `HIGH`

**File:** `src/cli/web_app.py:629`

Writes `~/.superai/config/models.json` with no auth, and registers even when
config-write is disabled — while `/api/config` and `/api/models` correctly do
not.

**Fix:** move it inside `if enable_config_write:` and make
`_check_management_auth(request)` its first statement.

**Verify:**
```
write OFF, no token : /api/sync/cliproxy registered == False
write ON,  no token : POST -> 401
write ON,  token    : POST -> 200
```

**Regression test:** derive the list of config-mutating routes from the app's
own route table and assert each is gated. A hardcoded list repeats the root
cause.

## C2.2 — `/openapi.json` returns 500; API docs are blank `HIGH`

**File:** `src/cli/web_app.py:468`, `:475`, `:1122`
**Found by:** the extended functional pass. **Pre-existing** (`d27820f`,
2026-07-14) — not caused by recent work.

`/docs` and `/redoc` return 200 but are HTML shells; the schema fetch behind
them 500s, so the interactive API documentation is **blank for every user**.

Cause: `MemoryQuery`, `PreferenceBody` and `FeedbackBody` are Pydantic models
declared **inside `create_app()`**. A function-local model leaves an
unresolvable `ForwardRef`, and FastAPI's schema generation raises
`PydanticUserError`.

**Fix:** move the three classes to module scope.

**Verify:**
```python
assert client.get("/openapi.json").status_code == 200
```

**Regression test:** that one assertion. Its absence is why this survived
since July.

**Flagged, not fixed — needs your ruling:** 7 further ungated POST endpoints
predate this window (2026-07-14→16): `/api/superai/run`, `/api/palace/promote`,
`/api/preferences`, `/api/feedback`, `/api/memory/search`, `/api/charts/render`,
`/mcp`. Are they intentionally public, or the same oversight, older? I did not
assume.

---

# Wave C3 — Make shipped features reachable (≈ 3 h)

Everything here is built and paid for but reaches no user.

## C3.1 — Implement T15 `/cliproxy-admin` `HIGH`

Marked `[x]`; the route and its flag appear **zero times** in the codebase. This
strands T14's correctly pinned, licensed 2.7 MB `vendor/mgmt-ui/management.html`.

**Respect the task file's architectural rule: file host only, do not
reverse-proxy.** The browser loads `management.html` from SuperAI; that page's
own client talks directly to the proxy. Proxying `/v0/management` through
SuperAI would put the proxy's management key through SuperAI's logs.

```python
if os.environ.get("SUPERAI_WEB_ENABLE_CLIPROXY_ADMIN") == "1":
    mgmt = Path(__file__).resolve().parents[2] / "vendor" / "mgmt-ui"
    if (mgmt / "management.html").is_file():
        app.mount("/cliproxy-admin",
                  StaticFiles(directory=str(mgmt), html=True),
                  name="cliproxy_admin")
```
Plus the ToS banner the task specifies.

**Alternative:** if it is no longer wanted, delete `vendor/mgmt-ui/`, its
manifest entry and the docs section. Do not leave it half-landed.

## C3.2 — AI Council: stop advertising a 404 `HIGH`

`/council` 404s on every clean clone — `frontend/dist` is gitignored, built by
nothing, absent — while the nav links it twice.

| Option | Cost | Trade-off |
|---|---|---|
| **A.** Commit a built `dist/` | 15 min | Build artifacts in git; needs rebuild discipline |
| **B.** Add a build step + document it | 1 h | Puts Node in a Python project's build path |
| **C.** Make the nav link conditional | 20 min | Stays dev-only, but stops lying |

**Recommendation: C now, B later.** C removes the user-visible falsehood
immediately without forcing a toolchain decision under pressure.

**Regardless of choice: replace `except Exception: pass` at the mount with a
logged warning.** The silent failure is what let this ship.

## C3.3 — Package the WebUI assets `MEDIUM`

```toml
[tool.setuptools.package-data]
scli = ["static/pwa/*", "static/console/*"]
```

**Verify by building, not by reading the diff:**
```
python -m build --wheel && python -m zipfile -l dist/*.whl | grep static/console
```

## C3.4 — T27 tray: wire it or demote it `HIGH`

Never imported; `superai tray` does not exist. Its menu is a hardcoded
`'SuperAI Status: Online'` — the promised token spend and quota usage are not
read at all.

- **Wire it:** register `@app.command("tray")` and connect the label to
  `quota_manager` and the spend registry — both already exist and are already
  integrated for T17.
- **Or demote** to `[~]` with the remaining work named.

Replacement test must assert **registration**, not construction —
`test_tray.py` currently mocks `pystray.Icon` wholesale and passes on
unreachable code.

## C3.5 — T29 browser: delete the duplicate `HIGH`

**Recommendation: delete `src/core/browser.py` and `tests/test_browser.py`.**
The capability already exists and is wired in as `browser_tool.py`
(`main.py:6455`). If `browser.py`'s urllib-fallback-when-Playwright-is-absent is
the wanted improvement, port that one behaviour into `browser_tool.py`.

If it stays, it must be registered in
`src/core/superai_agent/tools_bridge.py` — that is what "integrated Tool" meant.

## C3.6 — Resolve the duplicate `/dashboard` route `MEDIUM`

`:458` (redirect) and `:1134` (`dashboard_page`) — the first wins, the second is
dead. **Decide deliberately:** if the console supersedes the old dashboard,
delete `dashboard_page` and its orphaned `/api/dashboard` consumer; otherwise
give them distinct paths. Do not leave two handlers on one path.

## C3.7 — Dry-run is broken for 4 of 7 chat relays `MEDIUM`

**File:** `src/core/messengers.py:186-205` (`_http_json`)
**Found by:** the extended functional pass. Introduced 2026-08-10 (`c925b50`).

With `SUPERAI_MESSENGER_DRY_RUN=1`, discord / wecom / feishu / dingtalk all
return `ok=False, "webhook URL blocked: DNS resolution failed"`, while
slack / telegram / line / webhook / cli / file work.

```python
url_err = validate_public_http_url(url, require_https=True)   # does a DNS lookup
if url_err:
    return {"ok": False, "error": f"webhook URL blocked: {url_err}"}
if self.dry_run:                                              # short-circuit is AFTER
    return {"ok": True, "dry_run": True, ...}
```

Unconfigured adapters pass a placeholder `https://example.invalid/...`, which
fails validation before the dry-run branch is reached.

**Precisely scoped:** no message payload is sent — the dry-run branch does
prevent the POST. But a **DNS lookup leaves the machine before the check**, so
dry-run is neither a zero-network guarantee nor host-independent.

**Fix:** move `if self.dry_run:` **above** the URL validation. Three lines.

**Regression test:** `tests/test_messengers.py` — assert every channel returns
`ok=True, dry_run=True` under the flag with no credentials set. The module
currently has **no tests at all**, which is also the basis for C0.4.

---

# Wave C4 — Make the record match reality (≈ 2 h)

## C4.1 — Correct the WebUI board `MEDIUM`

| Task | Says | Should say |
|---|---|---|
| T09, T11, T13, T14 | `[ ]` | `[x]` — verified complete |
| T15 | `[x]` | `[ ]` — never implemented (or `[x]` after C3.1) |

The Log stops at 2026-08-05 and never records T09–T15.

## C4.2 — Correct the fleet-proxy board `MEDIUM`

T27/T29 → `[~]` unless C3.4/C3.5 wire them in. Fix stale paths in T25/T26
(`cli/static/styles.css` → `cli/static/console/styles.css`).

## C4.3 — Correct the root board `MEDIUM`

- Line 3: `scli.main:app` → **`scli.main:main`**. Do this in the same commit as
  C0.2 — this is the line that would make a reader dismiss that defect.
- Line 27: Fleet Proxy is **13 tasks (T17–T29)**, not "5 tasks, T17-T21".
- Lines 89–92: "Last session" is dated 2026-07-28, **120 commits** ago.

## C4.4 — Re-verify `docs/WEB_MANAGEMENT_CENTER.md` `HIGH`

It documents `/cliproxy-admin` + `SUPERAI_WEB_ENABLE_CLIPROXY_ADMIN` (lines 6,
21, 27, 39) and `/api/spend` + `/api/goals` (lines 18, 36).

**If C0.1 and C3.1 both land, this document becomes true as written.**
Re-verify it after those rather than editing now — otherwise you edit it twice.

## C4.5 — GROK board leaf/header `LOW`

Header `G3.1 M027 + G3.2 V4-M4 — [x] offline` sits above 22 leaves, 3 unticked
— the same pattern AGY was demoted for on 07-29. The header is qualified
"offline", so this may be deliberate. **Needs an owner's ruling, not an
assumption.** Also: "Last session" dated 2026-07-24.

## C4.6 — Correct the `AgentClaw` commit claim `LOW`

`c925b50`'s message claims an AgentClaw integration; the name exists nowhere in
the code (the module is `messengers.py`). History is pushed — do not rewrite.
Add a `docs/CHANGELOG.md` correction line.

---

# Wave C5 — Prevent recurrence (≈ 3 h)

This is the wave that stops the next audit from being necessary. Everything
above is a symptom; this is the disease.

## C5.1 — Guard the uncommitted work `MEDIUM`

The live worktree has 5 untracked modules (`agent_launcher`, `client_keys`,
`conditional_router`, `os_integrations`, `plugin_manager`) and modified files
importing them. Two import sites are **unguarded** (`web_app.py:585`, `:1360`).
HEAD is clean; the risk is the next `git add`.

**Fix:** commit the 5 modules in the same commit as their importers.

**Add the check that catches this class automatically** — an import smoke test
that walks committed `src/**/*.py`, extracts every `from core.X import` /
`import core.X`, and asserts `X` is a tracked file. This found the problem in
one grep; it should not need a human.

## C5.2 — Make the scorecard derive what it can `CRITICAL — the real fix`

Today an improvement is COMPLETE because its ID sits in `COMPLETE_IDS` (268
ids across 10 hand-maintained sets). The Code pillar is an f-string restating
the title (267 of 282 entries); docs and test citations are assigned by ID
prefix. The document's own "strict completion rule (mandatory)" is enforced by
nothing.

**Nobody can retro-verify 533 features, and this plan does not pretend
otherwise.** But three checks are mechanical and would have caught every
scorecard defect in this audit:

1. **Self-contradiction gate.** Fail the generator if any entry is
   `Complete? YES` with a non-empty `Still incomplete`. Would have caught all
   three falsified host gates. **~10 lines.**
2. **Citation existence gate.** Fail if a cited `docs/*.md` or `tests/*.py`
   path does not exist on disk. (Currently all 23 test paths do exist — this
   keeps it that way.) **~10 lines.**
3. **Honest provenance field.** Add `Evidence: asserted | derived` per entry.
   Entries whose pillars come from the fallback template are `asserted`;
   hand-authored ones are `derived`. Then publish both counts in the summary:
   *"282 COMPLETE — 15 derived, 267 asserted."*

Item 3 is the important one. It does not require re-verifying anything. It
makes the document **stop overstating its own confidence**, which is the actual
defect.

**Optional, higher value, larger:** a `traceability` column mapping each ID to
a test that names it. Currently 52 of 282 COMPLETE ids appear anywhere in
`tests/`. That number is not "230 untested features" — an ID needn't appear in
its test — but as a *coverage-of-evidence* metric it is honest and it can only
improve.

## C5.3 — Kill the silent-failure pattern `HIGH`

`except Exception: pass` wraps the AI Council mount, the T28 argv rewrite, and
the plugin loader. All three failures were silent; two of them shipped visible
falsehoods to users as a result.

**Fix:** every one of them logs at WARNING with the exception. Grep for the
pattern repo-wide and triage the rest.

## C5.4 — Test the wiring, not just the unit `HIGH`

Three defects were invisible to a 1190-test suite because the tests exercise
units nothing reaches:

- no test calls `main()` → 192 hijacked commands went unnoticed;
- `test_tray.py` mocks `pystray.Icon` → passes on an unregistered feature;
- `test_browser.py` mocks the whole transport → passes on dead duplicate code.

**Add a reachability test:** for each feature claiming CLI or tool integration,
assert it appears in the live registry (`app.registered_commands`,
`app.registered_groups`, `tools_bridge`, `app.routes`). Derive the list from
the boards' `[x]` entries so a false `[x]` fails CI.

---

---

# Wave C6 — AGY's 2026-08-10 work (≈ 3 h) — **run this FIRST**

Ten items in work committed at 14:36 and 14:50 (`b5d74d8`, `c5d33f5`) and
**already pushed to origin**. Numbered C6 because it was found last, but it
should be executed **first**: C6.1 alone clears 5 of the 6 test failures and
restores the repo's strongest subsystem.

## C6.1 — Classify the 3 unclassified MCP tools `CRITICAL` ← **start here**

**Updated at checkpoint `c5d33f5` — this is now THREE tools, not one.** The
regression compounded across two commits fourteen minutes apart:

| Point | Registered | Unclassified |
|---|--:|---|
| `6b798ff` | 25 | **0** |
| `b5d74d8` (14:36) | 26 | 1 — `superai_websearch` |
| `c5d33f5` (14:50) | **28** | **3** — `+ superai_skillx_search`, `+ superai_chrome_profile` |

```
Issues: unmapped=['superai_chrome_profile','superai_skillx_search','superai_websearch']
```

This violates AGY's **own board, Global DoD #4** (*"Registry honesty: extend
… MCP matrices when adding paths"*).

**Fix:** classify all three and add their `cli_parity` mappings.
`superai_websearch` and `superai_skillx_search` look like `FREE_TOOLS` (neither
spends budget nor mutates local state — confirm with the author).
**`superai_chrome_profile` is not FREE** — it opens URLs in the user's real
Chrome profile, so it belongs in `MUTATING_TOOLS` at minimum. Classify it
deliberately, not by pattern-matching the other two.

**This single fix clears 5 of the 6 test failures** (baseline at `545745d`:
6 failed / 1185 passed). With C1.1 the suite reaches **zero**. Verify:
```
python -c "from core.mcp_safety import safety_matrix; print(safety_matrix()['message'])"
→ 26 MCP tools; …; unclassified=0
```

## C6.1b — Commit `chrome_profile.py`, or revert the tool that imports it `CRITICAL`

`src/core/mcp_server.py:711` (committed **and pushed**) does
`from core.chrome_profile import open_url_in_profile`, but
`src/core/chrome_profile.py` is **untracked**. Verified from the git object
database — the only authority not fooled by the editable install:

```
git cat-file -e c5d33f5:src/core/chrome_profile.py  → ABSENT
git ls-tree origin/master src/core/ | grep chrome   → 0 files
```

**Any fresh clone raises `ImportError` when `superai_chrome_profile` is
invoked.** This is C5.1's predicted failure, now live on the remote.

**Fix:** either `git add src/core/chrome_profile.py` and commit it with its
importer, or revert the tool registration until the module ships. Then land
C5.1's import smoke test so this cannot recur.

**⚠ Before committing it — one guard is needed.** I reviewed the untracked
module (2,456 bytes). It is **far tamer than the `import_chrome_login_state`
risk in §8.7**: it reads Chrome's `Local State` to map an email/display-name to
a profile directory, then launches Chrome. It harvests no cookies, and it uses
`subprocess.Popen` with an **argument list** (not `shell=True`), so there is no
shell-injection path.

The gap is that `url` reaches Chrome's argv **unvalidated**:

```python
subprocess.Popen([chrome_bin, f"--profile-directory={profile_dir}", target_url])
```

A `url` beginning with `--` would be parsed by Chrome as a **switch rather than
a URL** (e.g. `--remote-debugging-port=9222`), and the value comes straight from
the `superai_chrome_profile` MCP tool argument. I did not exploit this — it is
a design gap, flagged on inspection.

**Add a scheme allow-list before committing:**
```python
from urllib.parse import urlparse
if urlparse(url).scheme not in ("http", "https"):
    return False
```

Also replace the two bare `except Exception: return False` blocks with logged
failures — silent failure is the recurring pattern in C5.3.

**Do not verify with `import`** — see the methodology warning in
`SUPERAI_AUDIT_CHECKPOINT_20260810.md`. Use `git cat-file`.

## C6.2 — Characterise `test_corrupted_cache_recovery` as flaky `LOW`

**Re-scoped after the stable-HEAD run.** This test failed in the AGY-snapshot
run but **passes at `545745d`**, on a tree differing only by two frontend
commits. That points to flakiness, not a regression.

**But one pass proves no more than one failure did.** Do not "fix" it and do
not dismiss it — *measure* it:

```bash
python -m pytest tests/test_code_intelligence_n258.py::test_corrupted_cache_recovery \
  --count=20 -q          # or a 20-iteration loop
```

A non-zero failure rate means the test is unreliable and should be made
deterministic; 20/20 green means the earlier failure was environmental and the
item closes. Record the observed rate either way — an unmeasured "probably
flaky" is the same species of unverified claim this whole audit is about.

## C6.3 — Fix the launch-profile port `HIGH`

`agent_launcher.py:14` hardcodes `http://127.0.0.1:8000/v1`; `superai web`
defaults to **8787** (`main.py:5286`). All four profiles (Claude Code, Grok
CLI, OpenCode, Kimi) point at a dead port.

**Fix properly:** derive the URL from the running server's configured host/port
rather than hardcoding — this is the same hardcoded-vs-derived root cause as
C0.1/C0.2. While there, align `tray.py:6` (also 8000); `opencode_sync.py:21`
is already correct at 8787.

## C6.4 — Decide on `oauth_manager.py` `HIGH`

It cannot authenticate: random UUID device codes, a `verification_uri` on the
non-existent domain `superai.local`, status permanently `"pending"` with **no
code path anywhere that authorizes**, in-memory state, and no provider ever
contacted. Yet `/api/oauth/start` and `/api/oauth/poll` are live and advertise
a working flow.

**Either** implement a real device flow against a real provider, **or** remove
both endpoints until it exists. Shipping an API that presents an OAuth flow
which can never complete is worse than not having one.

## C6.5 — Harden `client_keys.py` `HIGH`

Good: `secrets.token_urlsafe(32)`, redacted `list_keys()`, real scoping
(expiry, model allow-list, budget, revoke).

Fix:
- **Atomic write + backup** — reuse `atomic_write_with_backup` (already used by
  `Config.save()` from T06).
- **`chmod 0600`** — the file holds live keys in plaintext.
- **`FileLock`** — `key_pool.py` already does this; `consume_budget()` is a
  read-modify-write that currently loses updates under concurrency.
- **`hmac.compare_digest`** in `validate_key()`, matching
  `_check_management_auth`.

Confirmed absent today: no `chmod`, `atomic_write`, `FileLock` or `0o600` in
`client_keys.py`, `usage_logger.py` or `plugin_manager.py`.

## C6.6 — Fix `usage_logger.py` isolation and stdout `MEDIUM`

- `DB_PATH = os.path.expanduser('~/.superai/usage.db')` at **module level**.
  `expanduser` reads the environment, so `monkeypatch.setattr(Path, "home", …)`
  will not isolate it — the exact mismatch behind a previous CI hang, and a
  documented "Testing trap" on the WebUI board. Use `Path.home()` and resolve
  lazily inside the functions.
- `log_usage()` prints errors to **stdout**, which corrupts `--json` envelopes.
  Log to `stderr` or the logger.

## C6.7 — Resolve 3 unreferenced modules `MEDIUM`

`macos_bar.py`, `opencode_sync.py`, `os_integrations.py` are referenced by
nothing — the same T27/T29 dead-code pattern. Wire them up or drop them.

## C6.8 — Add tests for the 11 new modules `MEDIUM`

Zero tests were added. At minimum: `client_keys` (mint/validate/revoke/budget),
`usage_logger` (init/log/aggregate), `log_tailer` (already verified correct —
lock it in), and `agent_launcher` (assert the port matches the server default,
which would have caught C6.3).

## C6.9 — Guard the two latent risks before they get call sites `HIGH (latent)`

Neither is currently called; both become serious the moment they are.

- **`auto_provision_claude_mcp()`** rewrites `~/.claude.json` — which holds this
  user's live Claude Code config and auth tokens — with no atomic write, no
  backup and no lock. Under the mandatory parallel-session rule a concurrent
  write can corrupt it, and an interrupted write truncates it. Needs
  `atomic_write_with_backup`, a lock, and **explicit user consent**: silently
  editing another tool's config is a surprising side effect regardless of
  safety.
- **`import_chrome_login_state()`** harvests **every** cookie from the user's
  Chrome profile with no domain filter and no consent prompt. If it is kept, it
  needs an explicit allow-list and a confirmation step. Note it lives in
  `browser.py`, which **C3.5 recommends deleting outright** — deleting that
  module resolves this item for free.

## C6.10 — Decision, not a defect: IDE integration ToS `DECISION`

`ide_integrations.py` adds five IDE adapters; two expose `spoof_auth_status()`.
Stated accurately: `GitHubCopilotDaemon` returns `authenticated: True` **only
when the user's real Copilot token file exists locally** — it does not forge
credentials or bypass a licence check. It reports local token presence in the
shape VSCode expects so the extension routes through SuperAI.

That is interop for a licence already held. It still deserves a deliberate
call, because routing a vendor's proprietary extension through a third-party
proxy is a plausible ToS question — the same class this project already handled
explicitly with the T15/T16 ToS banner. **Your decision; I did not assume one.**

---

# Sequencing

| Wave | Effort | Ships |
|---|---|---|
| **C0** | 90 min | Product works; records stop being false |
| **C1** | 20 min | A genuinely green suite |
| **C2** | 50 min | No unauthenticated config writes; API docs work again |
| **C3** | 3.5 h | Built features reach users |
| **C4** | 2 h | Boards and docs match reality |
| **C5** | 3 h | The pattern stops recurring |
| **C6** | 3 h | AGY's 08-10 work becomes correct |

## Recommended execution order (revised now that master is frozen)

The wave numbers reflect the order findings were made, **not** the order to
execute them. With a stable target, run:

| # | Do | Why | Time |
|--:|---|---|---|
| 1 | **C6.1** | 5 of 6 test failures, one edit | 20 min |
| 2 | **C1.1** | the 6th failure → **suite green** | 20 min |
| 3 | **C6.1b** | committed import of an uncommitted module, live on origin | 20 min |
| 4 | **C0.1, C0.2** | the two user-facing breakages | 60 min |
| 5 | **C0.3, C0.4** | records stop being false | 30 min |
| 6 | **C2** | auth gap + API docs | 50 min |
| 7 | **C5.2** | best leverage in the plan (~30 min of code) | 30 min |
| — | C3, C4, C5.1/5.3/5.4, C6.2–C6.10 | the remainder | ~9 h |

**Getting to a green suite first (steps 1–2, ~40 min) is worth doing before
anything else** — every later step is verified by that suite, and a suite with
6 known failures cannot tell you whether your fix broke something.

**Minimum credible ship: steps 1–5 ≈ 2.5 hours.** That covers every defect that
is either broken for a user or actively false in the project's own records.

**Highest leverage per hour: C5.2 items 1–3 (~30 min of code).** Three small
gates in the generator would have caught every scorecard defect in this audit,
permanently.

---

## Acceptance gate — how you know the plan actually landed

Re-measure the checkpoint baseline. **Every row must move in the right
direction; none may regress.** Run against a clean clone of the fix branch,
with isolated `HOME`/`USERPROFILE`.

| Measurement | At `545745d` (before) | Target (after) |
|---|---|---|
| Test suite | 6 failed / 1185 passed | **0 failed** |
| MCP tools / unclassified | 28 / **3** | 28 / **0** |
| CLI names / hijacked (T28) | 207 / **192** | 207 / **0** |
| Shadowed `/api/*` GET routes | **14** | **0** |
| `/openapi.json` | **500** | **200** |
| `/council` | 404 | 200 **or** link removed (C3.2 decision) |
| `/cliproxy-admin` | 404 | 200 **or** vendored UI removed (C3.1 decision) |
| `/dashboard` handlers | **2** | **1** |
| `chrome_profile.py` in `git ls-tree` | absent | present **or** tool reverted |
| Scorecard HOST-GATED | **0** (false) | **3** (true) |
| Scorecard COMPLETE | 282 | **lower — and that is correct** |
| Wheel contains `static/console/*` | no | yes |

One-shot script for most of it:

```bash
python -m pytest tests/ -q -p no:randomly --timeout=180 | tail -1
python -c "from core.mcp_safety import safety_matrix as f; print(f()['message'])"
python -c "
from cli.web_app import create_app; from fastapi.testclient import TestClient; import re
a=create_app(); c=TestClient(a, raise_server_exceptions=False)
r=[(getattr(x,'path',''),sorted(getattr(x,'methods',None) or [])) for x in a.routes]
i=[n for n,(p,_) in enumerate(r) if '{' in p and p.startswith('/api/')]
print('shadowed:', len([p for p,m in r[min(i)+1:] if re.fullmatch(r'/api/[a-z0-9_-]+',p) and 'GET' in m]) if i else 0)
print('openapi:', c.get('/openapi.json').status_code)
print('dashboard handlers:', len([x for x in a.routes if getattr(x,'path','')=='/dashboard']))"
git ls-tree HEAD src/core/ --name-only | grep -c chrome_profile
```

**Do not mark a wave done on the strength of the edit.** The repo's own board
Rule 2 — run the verification command, paste the real output — is the rule
whose absence produced most of this plan.

## Rollback

Each wave is one commit on `fix/audit-remediation-20260810`, so
`git revert <sha>` undoes a wave cleanly. Two carry more risk than the rest:

- **C0.2 (T28)** changes argv handling for every invocation — the widest blast
  radius of any edit here. If anything behaves oddly afterwards, revert this
  one first.
- **C0.3 / C5.2 (scorecard)** regenerate a 6,000-line document. The generator
  is reproducible (a regen changes only the `Generated:` date), so `git diff`
  the regenerated file *before* committing.

Never force-push, even on your own branch — ~40 worktrees exist and `master`
is fully pushed.

## Two decisions I did not make for you

1. **AI Council (C3.2)** — commit `dist/`, add a build step, or hide the link.
   Genuine trade-offs; recommendation is C-then-B, but it is your call.
2. **The 7 pre-existing ungated POST endpoints (C2.1)** — intentionally public
   or an older oversight? They predate the review window and I did not assume.

## One thing worth saying plainly

The AGY board is clean, and it is clean because on 2026-07-29 someone caught
exactly this failure — headers marked `[x]` above unticked leaves — wrote down
why, and demoted them. That note is the best document in this repository:

> *The leaves were right and the headers were wrong.*

This project has already diagnosed its own failure mode correctly, once. C5
is just applying that same remedy everywhere else, mechanically, so it does not
depend on someone noticing again.
