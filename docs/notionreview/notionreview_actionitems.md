# notionreview_actionitems.md

> Action items from the deep review of `realburhanhusain/SuperAI` @ `21ecb8c`.
> Owner: recotechai · Generated: 27 Jul 2026 · Last updated: 27 Jul 2026 (18:45 +03)
> Related PRs:
> · [#1 security/shell-exec-hardening](https://github.com/realburhanhusain/SuperAI/pull/1) — **merged** as squash commit `dcef3c1`
> · [#2 security/untrusted-memory-delimiting](https://github.com/realburhanhusain/SuperAI/pull/2) — **open, awaiting review** (item 3)
> · [#3 ci/lint-typecheck-and-matrix](https://github.com/realburhanhusain/SuperAI/pull/3) — **open** (item 6)
> · [#4 security/sandbox-shell-containment](https://github.com/realburhanhusain/SuperAI/pull/4) — **open** (item 7)
> · [#5 chore/mcp-remove-membrain](https://github.com/realburhanhusain/SuperAI/pull/5) — **open** (Priority 2, first bullet)
> · [#6 security/sanitize-memory-on-write](https://github.com/realburhanhusain/SuperAI/pull/6) — **open, stacked on #2** (item 3, second half)

> **Note:** Two items on this list are things **only a human can do** — they cannot be delegated to an agent. They are marked :lock: **Human required**.

> **Nothing in PRs #2, #3, #4 or #6 has been executed.** All four ship tests or checks that have never run — 11, plus a static check, plus 11, plus 13 respectively. Treat "written" and "verified" as different words throughout this document.

> **Merge order matters now.** PR #6 is based on PR #2's branch, not on `master`, because it imports `neutralize_delimiters` from a module that exists only there. Merge **#2 before #6**. GitHub retargets #6 to `master` automatically once #2 lands. Repointing #6's base to `master` by hand will produce a branch that cannot import.

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
- [x] Action the unresolved review comment on `.mcp.json` — **now open as PR #5** (see Priority 2)
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

With the `approve_callback` scare retracted above, **this is now the highest-severity item on the list that nobody has started.** Six PRs later, it is still untouched, and no PR of the six goes anywhere near it.

- [ ] Open `AGENTS.md` and read it end to end
- [ ] Decide per block: legitimate instruction, or injected payload?
- [ ] Delete the payload blocks, keep the real guidance
- [ ] If the blocks are intentional red-team fixtures, move them to `tests/fixtures/injection/` with a `README.md` stating they are inert test data
- [ ] Confirm whether they were authored intentionally or arrived via an unintended commit — if the latter, audit repo access and rotate any exposed credentials

### 3. Fix untrusted-memory injection in `orchestrator.py` — **read path in PR #2, write path in PR #6**

> :arrow_right: **Read side: [PR #2 `security/untrusted-memory-delimiting`](https://github.com/realburhanhusain/SuperAI/pull/2)** — rationale in [`PR2_details.md`](./PR2_details.md).
> :arrow_right: **Write side: [PR #6 `security/sanitize-memory-on-write`](https://github.com/realburhanhusain/SuperAI/pull/6)** — rationale in [`PR6_details.md`](./PR6_details.md). **Stacked on #2; merge #2 first.**
> **Neither PR's tests have been run.**

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
- [x] **Decide reject / escape / quarantine** — owner chose **escape**, 27 Jul 2026. Reasoning recorded in `PR6_details.md`: rejecting hands attacker-controlled text a veto over what the system may remember (a silent denial-of-memory primitive), and quarantine needs storage plus a human who actually reads it
- [x] **Sanitise on write — `central_memory.write_back`.** All four persisted bodies now route through `_sanitize_for_memory`, which redacts first, then escapes the delimiters. Every step is exception-guarded and degrades to identity; a memory write is not worth failing a live run over
- [ ] **Run the 11 tests in PR #2** (`pytest tests/test_orchestrator_untrusted_memory.py -v`) and merge PR #2
- [ ] **Run the 13 tests in PR #6** (`pytest tests/test_central_memory_sanitize.py -v`) and merge PR #6 **after** #2. Two of the 13 reach the real memory backend and will `skip` rather than fail if it is unavailable; the other 11 must pass
- [ ] **Sanitise the second write path — `learning_engine.learn_from_step`. STILL OPEN.** The orchestrator calls this directly, so it does not pass through `central_memory.write_back` and PR #6 does not cover it

> **The write-path fix is half done, deliberately and visibly.** `src/core/learning_engine.py` is 68,569 bytes. The review agent's only write tool replaces whole files, and at that size its own output limit already truncated one write and committed syntactically invalid Python (PR #2 commit `b604280`, repaired in `7ae47fc`). Rather than risk a second corrupt commit, that site was left untouched and recorded here instead.
>
> **What that means for your threat model:** PR #2's read-side envelope is the control that covers *both* write paths, because it acts at retrieval regardless of how a row got in. PR #6 is defence in depth on one of the two entry points. Do not read "item 3 complete" until `learn_from_step` is also escaped — a surgical edit by a human, or via a delegated Copilot PR, is the realistic route.
>
> **Read the limitations before treating this as closed.** Delimiting is a mitigation, not a guarantee — a sufficiently persuasive payload inside the envelope may still influence a model. Skills are labelled `trust="unverified"` rather than `"untrusted"` so the feature keeps working, which is a documented compromise. Escaping changes stored text when it contains the marker strings; that is intended, but it does mean the store is no longer byte-verbatim.

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

The review itself ran into the consequence: files above roughly 60 KB could not be edited safely with a whole-file write, which is why item 3's second write path is still open. Size is not only a review problem; it is now a *fix* problem.

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
- [ ] **Read the `Lint` job output.** It is red and the cause is **unknown and unattributed**. The review agent has no tool that reads workflow logs, so this cannot be delegated: open https://github.com/realburhanhusain/SuperAI/actions/runs/30250280427/job/89926485392 or run `ruff check --select E9,F63,F7,F82 .` locally
- [ ] **Triage the failing matrix cells.** Linux, macOS, 3.10, 3.12 and 3.13 are being exercised for the first time; some failures are expected to be pre-existing rather than caused by PR #3, but that was never confirmed — the discriminating run was still in progress when the review ended

> **A hypothesis was raised and then disproven, recorded so it is not re-raised:** that a malformed `pyproject.toml` explained why `Security guardrails` was the only green job. `pyproject.toml` was read back in full on PR #3's branch and is complete, valid TOML. **Hypothesis disproven.** The Lint failure remains unexplained.
>
> **The guardrail check is inert until PR #2 merges.** `scripts/check_untrusted_appends.py` skips and exits 0 while `src/core/untrusted_data.py` does not exist on `master`. This is deliberate so PRs #2 and #3 can merge in either order. Once PR #2 lands it activates by itself — no further action needed.
>
> **`Kilo Code Review` has failed on every PR so far** — #1, #3 and #4. Offered as a **hypothesis, not a finding**: a misconfigured integration rather than four independent code problems. Worth ten minutes before treating any single one of its failures as meaningful.

### 7. Make the sandbox genuinely contain — **in review as PR #4**

> :arrow_right: **Now open as [PR #4 `security/sandbox-shell-containment`](https://github.com/realburhanhusain/SuperAI/pull/4).** Full rationale in [`PR4_details.md`](./PR4_details.md).

**A finding not on the original list, discovered while scoping this item:** `try_sandboxed_shell` had exactly two callers, `tool_proposals.py` and `terminal_pool.py`. **`os_shell.run_shell` was not one of them** — it went straight to `subprocess.run(..., shell=True)` on the host. Since PR #1 routed the agent's `bash` tool through `run_shell`, the most security-sensitive path in the system, the one driven directly by model output, was the path with no container anywhere near it. `prefer_container_sandbox` did far less than its name implies.

This is **not** a regression from PR #1 — `tool_bash` was never sandboxed. The sandbox was simply never wired into the path that matters most.

- [x] Route `os_shell.run_shell` through `try_sandboxed_shell` when the sandbox is enabled
- [x] Honour fail-closed at that call site: Docker missing or erroring returns `sandbox_unavailable` instead of silently running on the host
- [x] Report containment in the result envelope (`sandbox: docker | none | unavailable | error`) so callers can tell whether a command was contained
- [x] Correct the module docstring: the workspace-relative `cwd` is a convenience boundary, not a jail
- [ ] Run the 11 tests (`pytest tests/test_os_shell_sandbox.py -v`) and merge
- [ ] Consider `--read-only` rootfs with an explicit `tmpfs` for `/tmp`
- [ ] Set a non-root default via `SUPERAI_SANDBOX_USER` and document it
- [ ] Decide whether `SUPERAI_SANDBOX_WORKSPACE_RO=1` should be the default for non-build tasks
- [ ] Decide whether `--network none` should be **enforced** rather than merely defaulted
- [ ] Decide whether the sandbox should be **on by default** — deliberately excluded from PR #4, since it breaks every user without Docker and is a product decision rather than a bug fix

> **What the sandbox does and does not give you** (asked and answered, 27 Jul 2026):
>
> - **`sh -lc` runs inside the container, not on the host.** The command string is an argument to `docker run`, so the shell interpreting it is the container's. Pipes, `&&`, `$(...)` and redirects still work — against the container's filesystem and process table, and with `--network none`, no network. **What is not protected is the workspace**, which is bind-mounted so work is useful. A command that deletes files under the mounted workspace deletes real files. Hence the docstring wording: a convenience boundary, not a security boundary. It bounds the blast radius; it does not remove it.
> - **Hard-failing without Docker** means that on a machine with no Docker, or a stopped daemon, every agent shell command returns a refusal envelope (`ok=False`, `error_code="sandbox_unavailable"`, plus a remedy string) instead of running. The alternative — silent host fallback — makes the control strongest while you test it and absent when something breaks, which is the worst possible property for a security boundary. There is a documented opt-out, so this is a loud failure, not a wall.
> - **Enforcing `--network none`** breaks every legitimate networked command: `pip install`, `npm ci`, `git fetch`, `curl` against an internal API, any test touching a service. In exchange it removes shell-based exfiltration outright, so a poisoned memory cannot ship the workspace off the machine. Suggested resolution: keep `network=none` as the default and make the exception explicit per command. "The agent can install packages" and "the agent cannot phone home" are not simultaneously achievable.
> - **Blast radius of defaulting the sandbox on:** commands get slower (container start is real overhead on short commands); anything relying on host tools absent from `python:3.12-slim` starts failing; anything relying on host state outside the workspace — SSH keys, credential helpers, `~/.aws` — stops seeing it. That last one is the point, and it will still read as breakage to whoever hits it first. Leaving it **off** means the control protects only those who already knew to enable it.
> - **Release-note wording:** flipping the default is a **breaking change** and must be filed as one, not as a security bullet. It has to say plainly that shell commands now run in Docker, that Docker is now required for the shell path, that commands depending on host tools or host credentials will fail, and what the opt-out is. Filing it as "hardened the sandbox" will generate bug reports from people who read the notes and still did not know.
>
> **Recommendation on record:** ship PR #4 as written (fail-closed, sandbox still opt-in), then flip the default in a **separate** release carrying the breaking-change note. That decouples "the mechanism finally works" from "everyone's workflow changes", so the second can be reverted without losing the first.
>
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

- [x] **Resolve the open `.mcp.json` review comment** — **now open as [PR #5](https://github.com/realburhanhusain/SuperAI/pull/5)**, rationale in [`PR5_details.md`](./PR5_details.md). Option **(a)** was taken: the `membrain` entry is removed from committed config. It pointed at `membrain_mcp_server.py`, which exists nowhere in the repo, so the server could only ever fail to start. Options (b) `${MEMBRAIN_SERVER_PATH}` and (c) "document as optional" were rejected — both leave a declared server that still cannot start. `mempalace` is untouched, since `mempalace-mcp` is a `PATH` console entry point rather than a path into this tree
- [ ] Review and merge PR #5. No Python is touched, so no suite is affected
- [ ] Resolve the PR #1 review thread on `.mcp.json` once PR #5 merges
- [ ] **Point `.mcp.json` at your own `membrain` path locally**, in an uncommitted override, if you still use it
- [ ] **Encrypt the backup key.** `~/.superai/.backup_key` is stored in plaintext. The backup encryption itself is solid (AES-GCM + zstd, with tar-slip defence) — the key at rest undermines it. Move to keyring with a passphrase-derived fallback
- [ ] **Fix the docs' entry point.** Docs reference `scli.main:app`; the correct target is `scli.main:main`, which `pyproject.toml` already uses. `main()` adds M080 exit-code mapping that calling `app()` would skip. **The docs are wrong, not the packaging.**
- [ ] **De-duplicate budget keys** in `config.py`'s `DEFAULT_CONFIG`
- [ ] **Replace the module-level `Config` singleton** — it makes test isolation and per-run overrides unreliable
- [ ] **Reconsider project-local `.superai/config.json` merging.** A cloned repo can currently influence runtime config, which is the same class of issue as the constitution file removed in PR #1
- [ ] **Replace `except Exception: pass`** with narrow, logged handlers. Frequent throughout `src/core`
- [ ] **Stop committing generated artefacts.** Scorecards up to 240 KB and a stray `_b.json` are in version control. Add to `.gitignore`
- [ ] **Fix the fail-open budget gate** in `web_app` — budget-check exceptions are logged as warnings and execution proceeds

---

## Open decisions

| Question | Status |
| --- | --- |
| Were the `AGENTS.md` blocks authored intentionally, or did they arrive unexpectedly? | **Open.** Determines whether this is a cleanup task or a **security incident** requiring access audit and credential rotation |
| Is `SuperAI` intended to run against untrusted input (public issues, web content, third-party repos)? | **Open.** If yes, items 2 and 3 are blocking. If it is strictly a personal single-user tool, they drop to P1 |
| Should the learning store sanitise on **write**, and if so: reject, escape, or quarantine? | **Answered 27 Jul 2026: escape.** Shipped for `central_memory.write_back` in PR #6. Still unimplemented for `learning_engine.learn_from_step` |
| What to do about the `membrain` entry in `.mcp.json`? | **Answered 27 Jul 2026: remove it.** PR #5 |
| Should the container sandbox be **on by default**? | **Open, with a recommendation on record** (item 7): ship PR #4 opt-in, flip the default in a separate release carrying a breaking-change note |
| Should `--network none` be enforced rather than defaulted? | **Open, with a recommendation on record** (item 7): keep it as the default, make the exception explicit per command rather than global |
| Should `d360-test/SuperAI_Review` receive the same fixes? | **Open and urgent.** The two repos were byte-identical; with PR #1 merged, `master` has the fix and the public fork does not. The shell bypass is still publicly readable there, and the fork now advertises the diff. Either sync it or delete it |

---

## Status summary

| # | Item | Priority | Status |
| --- | --- | --- | --- |
| 1 | Test PR #1 | P0 | **Merged `dcef3c1`** — tests still unrun |
| 2 | Review `AGENTS.md` :lock: | P0 | Human required — **still the top unstarted item** |
| 3 | Memory injection, read path | P0 | **PR #2 open** — tests unrun |
| 3b | Memory injection, write path | P0 | **PR #6 open** (stacked on #2) — covers `central_memory` only; `learning_engine` still open |
| 4 | `master` history cleanup | P0 | **Done** — protection re-enabled |
| 5 | Split `main.py` | P1 | Not started — and now blocking fixes, not just review |
| 6 | CI lint + matrix | P1 | **PR #3 open** — `Lint` red, cause unknown, needs a human to read the log |
| 7 | Sandbox containment | P1 | **PR #4 open** — wiring fixed; hardening and default-on still owner decisions |
| 8 | Consolidate subsystems | P1 | Not started |
| 9 | Replace `inspect.getsource` audits | P1 | Not started |
| 10 | `.mcp.json` membrain entry | P2 | **PR #5 open** |
| 11 | Hygiene backlog (remaining 9) | P2 | Not started |

**Fixed on `master`** by PR #1 (squash commit `dcef3c1`): agent shell `shell=True` bypass · approval fail-open · sandbox fail-open · capability drop · `.mcp.json` dev paths and peer-writer grant · dead `config/constitution.md`.

**Open in PR #2:** untrusted-data envelopes for retrieved memory, memory warnings, prior step output, and auto-generated skills in `_build_step_prompt`.

**Open in PR #3:** blocking ruff error check, advisory full ruff and mypy, 3-OS / 4-Python matrix, and the static guardrail enforcing PR #2's envelope.

**Open in PR #4:** `os_shell.run_shell` routed through the container sandbox, fail-closed honoured on that path, containment reported in the result envelope, and the misleading cwd-jail docstring corrected.

**Open in PR #5:** the `membrain` MCP server entry removed from `.mcp.json`.

**Open in PR #6:** secrets-then-delimiters escaping applied to all four bodies persisted by `central_memory.write_back`, with the invariant recorded in the function docstring.

**Retracted:** the claim that `goals_daemon.py`, `cli_pool.py` and `mcp_server.py` were broken by PR #1's approval gate. None of them call `dispatch_tool`. See the note under item 1.

**Disproven:** the claim that a malformed `pyproject.toml` explained PR #3's red jobs. The file was read back in full and is valid. See the note under item 6.
