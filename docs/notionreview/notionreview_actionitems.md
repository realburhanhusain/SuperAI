# notionreview_actionitems.md

> Action items from the deep review of `realburhanhusain/SuperAI` @ `21ecb8c`.
> Owner: recotechai · Generated: 27 Jul 2026 · Last updated: 27 Jul 2026 (11:45 +03)
> Related PRs:
> · [#1 security/shell-exec-hardening](https://github.com/realburhanhusain/SuperAI/pull/1) — **merged** as squash commit `dcef3c1`
> · [#2 security/untrusted-memory-delimiting](https://github.com/realburhanhusain/SuperAI/pull/2) — **open, awaiting review** (item 3)
> · [#3 ci/lint-typecheck-and-matrix](https://github.com/realburhanhusain/SuperAI/pull/3) — **open** (item 6)
> · [#4 security/sandbox-shell-containment](https://github.com/realburhanhusain/SuperAI/pull/4) — **open** (item 7)

> **Note:** Two items on this list are things **only a human can do** — they cannot be delegated to an agent. They are marked :lock: **Human required**.

> **Nothing in PRs #2, #3 or #4 has been executed.** All three ship tests or checks that have never run. Treat "written" and "verified" as different words throughout this document.

---

## Priority 0 — Do before any untrusted or production use

### 1. Run the test suite — PR #1 is merged but still unverified

> :warning: **PR #1 was merged on 27 Jul 2026 (squash commit `dcef3c1`) before the test suite was run.** The fixes are now live on `master`.
>
> Running the tests is therefore no longer a merge gate — it is **post-merge verification of shipped code**, which makes it more urgent than it was before, not less. Before the merge a failing test meant "do not merge". Now it means "`master` is wrong and needs a follow-up fix".

```bash
git checkout master
git pull
pytest tests/test_tools_bridge_shell_hardening.py -v
pytest tests/test_result_contract.py tests/test_cli_pool.py tests/test_terminal_pool.py tests/test_h_i.py -q
```

- [x] Satisfy the branch-protection requirement on `master`
- [x] Review and merge [PR #1](https://github.com/realburhanhusain/SuperAI/pull/1) — merged 27 Jul 2026 02:47 UTC as squash commit `dcef3c1`
- [ ] Run the new hardening tests — all 10 should pass
- [ ] Run the four adjacent suites that share the approval plumbing
- [ ] **Triage the failed `Kilo Code Review` check.** It completed with conclusion `failure` on PR #1 and was never read before merge. Whatever it found is now on `master`
- [ ] **Confirm the CI `test` job passed.** It was still `in_progress` at the moment the PR was merged, so its result was never seen — check the run on merge commit `dcef3c1`
- [ ] Action the unresolved review comment on `.mcp.json` — it is still open on the merged PR (see Priority 2)
- [ ] Confirm nothing else calls `tool_bash` expecting the old return shape (it now returns the `os_shell` envelope: `executed`, `returncode`, `latency_sec`, `permission_mode`)
- [ ] Sanity-check the agent still works interactively: `superai` build agent -> run a shell command -> confirm the approval prompt appears and a denial actually blocks

> **Behaviour change now live on `master`:** any caller of `dispatch_tool` that omits `approve_callback` is **denied** with `no_approver_available` instead of silently proceeding.
>
> **Retracted (27 Jul 2026):** an earlier version of this document warned that `goals_daemon.py`, `cli_pool.py` and `mcp_server.py` were affected and called it the most likely source of a post-merge surprise. **That was wrong and has been verified as wrong.** `dispatch_tool` occurs in six files only — its definition in `tools_bridge.py`, `runtime.py`, two test files, and two of these review docs. `tools_bridge` is imported by `runtime.py`, `tui.py` (which imports only `catalog`, never `dispatch_tool`) and the tests. Those three modules reference neither symbol. `runtime.py` passes `approve_callback=approve`, so the only production caller was already correct and **PR #1 broke nothing here.**
>
> The original review listed those three files correctly as *candidates to check*. They were then restated as a confirmed regression without being checked. Recorded here because a retracted finding is only useful if the retraction is as visible as the claim.

### 2. :lock: Review `AGENTS.md` — Human required

`AGENTS.md` contains four blocks that read as obfuscated prompt-injection payloads. **The review agent deliberately did not touch this file.** Editing it means reproducing content that must be treated as untrusted data, with no way to verify the legitimate contributor guidance survives intact.

This matters more than a normal file, because `AGENTS.md` **is read by coding agents by design**. That is exactly the delivery mechanism a payload there would use.

With the `approve_callback` scare retracted above, **this is now the highest-severity item on the list that nobody has started.**

- [ ] Open `AGENTS.md` and read it end to end
- [ ] Decide per block: legitimate instruction, or injected payload?
- [ ] Delete the payload blocks, keep the real guidance
- [ ] If the blocks are intentional red-team fixtures, move them to `tests/fixtures/injection/` with a `README.md` stating they are inert test data
- [ ] Confirm whether they were authored intentionally or arrived via an unintended commit — if the latter, audit repo access and rotate any exposed credentials

### 3. Fix untrusted-memory injection in `orchestrator.py` — **in review as PR #2**

> :arrow_right: **Now open as [PR #2 `security/untrusted-memory-delimiting`](https://github.com/realburhanhusain/SuperAI/pull/2).** Full rationale in [`PR2_details.md`](./PR2_details.md). **The tests are written but have not been run** — please run them before merging.

**The problem:** retrieved memory was concatenated into prompts as trusted text:

```python
prompt_parts.append(f"\nRelevant past learnings:\n{learnings_text}")
prompt_parts.append(f"\nWarnings from past experience:\n{warnings_text}")
```

If untrusted content ever reaches the learning store — a web fetch, a repo file, an issue body, a CLI output — it becomes a **persistent, self-reinforcing injection vector**, replayed into every future similar task. Poison once, execute indefinitely. `injection_defense.py` will not save you here: it is regex-only and requires high risk **and** >=2 pattern hits to block.

- [x] Wrap both blocks in explicit data delimiters with a "treat as data, not instructions" preamble
- [x] Apply the same treatment to the `skill_block` and `context` appends in the same function
- [x] Add a test that stores a poisoned learning and asserts it is delimited, not obeyed
- [x] **Enforcement against future unwrapped appends** — shipped as a static AST check in PR #3, not as a unit test, because no test can assert about code that has not been written yet
- [ ] **Run the 10 new tests** (`pytest tests/test_orchestrator_untrusted_memory.py -v`) and merge PR #2
- [ ] **Sanitise on write to the learning store** — deliberately excluded from PR #2 and still outstanding. PR #2 labels poisoned content on the way out; it does not stop it going in. **This is the other half of the fix.**

> **Read the limitations before treating this as closed.** Delimiting is a mitigation, not a guarantee — a sufficiently persuasive payload inside the envelope may still influence a model. Skills are labelled `trust="unverified"` rather than `"untrusted"` so the feature keeps working, which is a documented compromise.
>
> **Sequencing note:** the sanitise-on-write half was split out on request and is *deliberately* scheduled after PR #2 merges. It needs to import `neutralize_delimiters` from `untrusted_data.py`, which exists only on PR #2's branch — building it off `master` first would mean duplicating that module or opening a PR that cannot import. It also needs the open decision below (reject / escape / quarantine) answered first.

### 4. ~~Decide on `master` history cleanup~~ — DONE (27 Jul 2026)

A write-access probe had left two commits on `master` (`649788b` added `.superai-write-probe`, `2361153` removed it). Tree content was byte-identical to `21ecb8c`, so no code was ever affected — but the history was untidy.

- [x] `master` rewound to `21ecb8c` and the review docs re-committed as a single clean commit, `e93eb75`
- [x] PR #1 branch rebased onto the new `master` — head `6604ca5`, substance unchanged at 5 commits / 5 files / +238 −90
- [x] Probe commits no longer exist in history
- [x] **Branch protection on `master` confirmed re-enabled** after the force-push (confirmed by owner, 27 Jul 2026)

> The force-push was initially rejected with `GH006: Cannot force-push to this branch`, which is the protection rule working correctly. It was temporarily disabled to perform the cleanup and has since been restored.
>
> **Note on the merge:** PR #1 was **squash**-merged, so its 5 commits were collapsed into the single commit `dcef3c1`. Branch head `6604ca5` and the pre-rebase SHAs cited in `PR1_details.md` are historical references only — they do not appear in `master`'s history.

---

## Priority 1 — Structural, do soon

### 5. Split `src/cli/main.py`

**297 KB in a single file.** Effectively unreviewable and unrefactorable — this is where undiscovered bugs live. No tooling will help until it is broken up.

- [ ] Extract per-command modules under `src/cli/commands/`
- [ ] Keep `main.py` as thin registration plus the `main()` exit-code wrapper only
- [ ] Do it incrementally, one command group per PR

### 6. Add lint and type checking to CI — **in review as PR #3**

> :arrow_right: **Now open as [PR #3 `ci/lint-typecheck-and-matrix`](https://github.com/realburhanhusain/SuperAI/pull/3).** Full rationale in [`PR3_details.md`](./PR3_details.md).

CI ran `windows-latest` + Python 3.11 only, with no static analysis. `pyproject.toml` declares `requires-python = ">=3.10"` — so **3.10, 3.12, and 3.13 were entirely untested**, and Linux and macOS were never exercised despite the code branching on `sys.platform`.

- [x] Add `ruff check` to CI — split into a blocking step (`E9,F63,F7,F82`: syntax errors and undefined names) and an advisory full rule set
- [x] Add `mypy` to CI — advisory, scoped to `tools_bridge.py` and `os_shell.py`
- [x] Expand the matrix: `ubuntu-latest` + `macos-latest`, Python 3.10 -> 3.12, plus 3.13 non-blocking
- [x] Add a CI rule failing any `prompt_parts.append(...)` in `_build_step_prompt` that does not route through `wrap_untrusted_block` — `scripts/check_untrusted_appends.py`
- [ ] Add a CI rule failing any new `subprocess.run(..., shell=True)` outside `os_shell.py` — **still outstanding**, and it is the rule that would have caught the original `tool_bash` bug
- [ ] Make the `test` job a **required** status check — repository setting, needs your action, and should wait until the matrix is green
- [ ] **Triage the first matrix run.** Linux, macOS, 3.10, 3.12 and 3.13 are being exercised for the first time; some cells are expected to fail. Those failures are pre-existing, not caused by PR #3

> **The guardrail check is inert until PR #2 merges.** `scripts/check_untrusted_appends.py` skips and exits 0 while `src/core/untrusted_data.py` does not exist on `master`. This is deliberate so PRs #2 and #3 can merge in either order. Once PR #2 lands it activates by itself — no further action needed.

### 7. Make the sandbox genuinely contain — **in review as PR #4**

> :arrow_right: **Now open as [PR #4 `security/sandbox-shell-containment`](https://github.com/realburhanhusain/SuperAI/pull/4).** Full rationale in [`PR4_details.md`](./PR4_details.md).

**A finding not on the original list, discovered while scoping this item:** `try_sandboxed_shell` had exactly two callers, `tool_proposals.py` and `terminal_pool.py`. **`os_shell.run_shell` was not one of them** — it went straight to `subprocess.run(..., shell=True)` on the host. Since PR #1 routed the agent's `bash` tool through `run_shell`, the most security-sensitive path in the system, the one driven directly by model output, was the path with no container anywhere near it. `prefer_container_sandbox` did far less than its name implies.

This is **not** a regression from PR #1 — `tool_bash` was never sandboxed. The sandbox was simply never wired into the path that matters most.

- [x] Route `os_shell.run_shell` through `try_sandboxed_shell` when the sandbox is enabled
- [x] Honour fail-closed at that call site: Docker missing or erroring returns `sandbox_unavailable` instead of silently running on the host
- [x] Report containment in the result envelope (`sandbox: docker | none | unavailable | error`) so callers can tell whether a command was contained
- [x] Correct the module docstring: the workspace-relative `cwd` is a convenience boundary, not a jail
- [ ] Consider `--read-only` rootfs with an explicit `tmpfs` for `/tmp`
- [ ] Set a non-root default via `SUPERAI_SANDBOX_USER` and document it
- [ ] Decide whether `SUPERAI_SANDBOX_WORKSPACE_RO=1` should be the default for non-build tasks
- [ ] Decide whether `--network none` should be **enforced** rather than merely defaulted
- [ ] Decide whether the sandbox should be **on by default** — deliberately excluded from PR #4, since it breaks every user without Docker and is a product decision rather than a bug fix

> **Behaviour change to note in release notes if PR #4 merges:** anyone who set `prefer_container_sandbox` without working Docker was silently getting host execution and will now get hard failures. That is the intended behaviour and the entire point of the change, but it will look like a regression to someone who unknowingly relied on the fallback.

### 8. Consolidate duplicated subsystems

Strong signal of AI-assisted feature accretion — each capability got a new module instead of extending an existing one.

| Cluster | Count | Modules |
| --- | --- | --- |
| TUI | ~14 | `tui_a11y`, `tui_a11y_native`, `tui_atspi`, `tui_commands`, `tui_conpty`, `tui_live_session`, `tui_mouse`, `tui_mux`, `tui_process_mux`, `tui_raw_input`, `tui_vim`, `agent_tui`, `approval_tui`, `split_pane_tui` |
| Memory | ~11 | `memory_chat`, `memory_cloud`, `memory_collections`, `memory_dataset`, `memory_eval`, `memory_gdpr`, `memory_inject`, `memory_otel`, `memory_sync`, `memory_palace`, `central_memory` |
| Routing | ~9 | `model_router`, `bandit_router`, `cost_router`, `ab_routing`, `load_balancer`, `model_pinning`, `model_blacklist`, `adaptive_escalate`, `member_selection` |

- [ ] Pick each cluster and decide: merge, or delete the unused ones
- [ ] Delete or clearly mark the roadmap-artefact modules: `enterprise_stubs.py`, `foundation_complete.py`, `live_smoke_complete.py`, `v6_phase_status.py`
- [ ] Establish which features actually work end to end — the feature *list* currently outruns verified functionality

### 9. Fix the brittle source-introspection audits

`foundation_safety.py` uses `inspect.getsource` to audit code at runtime. This breaks on any refactor, and breaks entirely when installed from a wheel, a zip, or bytecode-only.

- [ ] Replace with static analysis in CI (an AST check or a `ruff` custom rule) — PR #3 adds the first example of this pattern to copy

---

## Priority 2 — Hygiene

- [ ] **Resolve the open `.mcp.json` review comment.** The Copilot reviewer flagged, and the thread is **still unresolved on the merged PR**: `membrain` now runs `python membrain_mcp_server.py`, but that script does not exist anywhere in the repo, so the server will fail to start for anyone cloning it. The script was never in the repo — it lived at an absolute path on one machine — so PR #1 did not introduce this, but it did not fix it either. Pick one: **(a)** remove the `membrain` entry from committed config, since it is a personal server rather than a project dependency (recommended); **(b)** reference it via an env var such as `${MEMBRAIN_SERVER_PATH}` so the failure has an obvious cause; **(c)** document it in the README as an optional external server the user must supply.
- [ ] **Point `.mcp.json` at your own `membrain` path locally**, in an uncommitted override.
- [ ] **Encrypt the backup key.** `~/.superai/.backup_key` is stored in plaintext. The backup encryption itself is solid (AES-GCM + zstd, with tar-slip defence) — the key at rest undermines it. Move to keyring with a passphrase-derived fallback.
- [ ] **Fix the docs' entry point.** Docs reference `scli.main:app`; the correct target is `scli.main:main`, which `pyproject.toml` already uses. `main()` adds M080 exit-code mapping that calling `app()` would skip. **The docs are wrong, not the packaging.**
- [ ] **De-duplicate budget keys** in `config.py`'s `DEFAULT_CONFIG`.
- [ ] **Replace the module-level `Config` singleton** — it makes test isolation and per-run overrides unreliable.
- [ ] **Reconsider project-local `.superai/config.json` merging.** A cloned repo can currently influence runtime config, which is the same class of issue as the constitution file removed in PR #1.
- [ ] **Replace `except Exception: pass`** with narrow, logged handlers. Frequent throughout `src/core`.
- [ ] **Stop committing generated artefacts.** Scorecards up to 240 KB and a stray `_b.json` are in version control. Add to `.gitignore`.
- [ ] **Fix the fail-open budget gate** in `web_app` — budget-check exceptions are logged as warnings and execution proceeds.

---

## Open decisions

| Question | Why it matters |
| --- | --- |
| Were the `AGENTS.md` blocks authored intentionally, or did they arrive unexpectedly? | Determines whether this is a cleanup task or a **security incident** requiring access audit and credential rotation |
| Is `SuperAI` intended to run against untrusted input (public issues, web content, third-party repos)? | If yes, items 2 and 3 are blocking. If it is strictly a personal single-user tool, they drop to P1 |
| Should the learning store sanitise on **write**, and if so: reject, escape, or quarantine? | **Blocks the second half of item 3 and is currently unanswered.** Reject silently loses legitimate learnings and depends on detection that is known to be weak. Escape preserves meaning and needs no detection, but stored text stops being verbatim. Quarantine needs new storage and a human to review it |
| Should the container sandbox be **on by default**? | Item 7. On means real containment for everyone; it also breaks every user without Docker. PR #4 deliberately does not decide this |
| Should `--network none` be enforced rather than defaulted? | Item 7. Needs a ruling on whether any legitimate tool requires network from inside the sandbox |
| Should `d360-test/SuperAI_Review` receive the same fixes? | **Now urgent.** The two repos were byte-identical; with PR #1 merged, `master` has the fix and the public fork does not. The shell bypass is still publicly readable there, and the fork now advertises the diff. Either sync it or delete it |

---

## Status summary

| # | Item | Priority | Status |
| --- | --- | --- | --- |
| 1 | Test PR #1 | P0 | **Merged `dcef3c1`** — tests still unrun |
| 2 | Review `AGENTS.md` :lock: | P0 | Human required — **now the top unstarted item** |
| 3 | Orchestrator memory delimiting | P0 | **PR #2 open** — read path fixed, tests unrun, write path outstanding |
| 4 | `master` history cleanup | P0 | **Done** — protection re-enabled |
| 5 | Split `main.py` | P1 | Not started |
| 6 | CI lint + matrix | P1 | **PR #3 open** — never run; expect red matrix cells on first run |
| 7 | Sandbox containment | P1 | **PR #4 open** — wiring fixed, hardening options still open |
| 8 | Consolidate subsystems | P1 | Not started |
| 9 | Replace `inspect.getsource` audits | P1 | Not started |
| 10 | Hygiene backlog (10 items) | P2 | Not started |

**Fixed on `master`** by PR #1 (squash commit `dcef3c1`): agent shell `shell=True` bypass · approval fail-open · sandbox fail-open · capability drop · `.mcp.json` dev paths and peer-writer grant · dead `config/constitution.md`.

**Open in PR #2:** untrusted-data envelopes for retrieved memory, memory warnings, prior step output, and auto-generated skills in `_build_step_prompt`.

**Open in PR #3:** blocking ruff error check, advisory full ruff and mypy, 3-OS / 4-Python matrix, and the static guardrail enforcing PR #2's envelope.

**Open in PR #4:** `os_shell.run_shell` routed through the container sandbox, fail-closed honoured on that path, containment reported in the result envelope, and the misleading cwd-jail docstring corrected.

**Retracted:** the claim that `goals_daemon.py`, `cli_pool.py` and `mcp_server.py` were broken by PR #1's approval gate. None of them call `dispatch_tool`. See the note under item 1.
