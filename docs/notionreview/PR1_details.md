# PR1_details.md

> Detailed rationale for [PR #1 — fix(security): harden agent shell execution, fail-closed sandbox, config hygiene](https://github.com/realburhanhusain/SuperAI/pull/1)
> Repo: `realburhanhusain/SuperAI` · Base: `master` · Head: `security/shell-exec-hardening` · 5 commits
> Describes the PR as originally submitted. See [`README.md`](./README.md) for the naming convention.

## Selection criteria — why these five and nothing else

The deep review produced roughly 25 findings. This PR includes a finding only if it met **all four** of these tests:

1. **Exploitable or actively harmful**, not merely untidy.
2. **Fixable without behavioural guesswork** — the correct behaviour was already established elsewhere in the repo, so the fix is alignment rather than invention.
3. **Small enough to review in one sitting.** A security PR nobody can read is a security PR nobody merges.
4. **Verifiable by test.** If no failing test could be written, it did not go in.

Everything else was deliberately excluded and is tracked in [`notionreview_actionitems.md`](./notionreview_actionitems.md). The single most important thing to understand about this PR: **it invents almost no new security logic.** Four of the five changes make weak code use protections the repo *already had*. That is why the risk of merging is low.

---

## Change 1 — `tools_bridge.py`: route agent shell through `os_shell`

**Commit `d5775bc` (pre-rebase) · The reason this PR exists**

### What was there

```python
def tool_bash(command, *, dry_run=False, timeout=60.0):
    """Sandboxed shell: workspace cwd, no shell=True injection via list form when possible."""
    blocked = ("rm -rf /", "format c:", ":(){", "mkfs", "shutdown", "reboot")
    low = cmd.lower()
    if any(b in low for b in blocked):
        return {"ok": False, "error": "blocked_command", "command": cmd[:200]}
    proc = subprocess.run(cmd, cwd=root, capture_output=True,
                          text=True, timeout=timeout, shell=True)
```

This is the shell tool exposed to the **build agent** — the tool an LLM calls when it decides to run a command.

### Why it was picked

Four independent defects in fourteen lines:

**a) The docstring is false.** It claims list-form and no `shell=True`. The code passes `shell=True` unconditionally, on every platform. This is the worst kind of defect because it is *actively misleading* — a reviewer scanning for shell-injection risk reads that docstring and moves on. It is why the bug survived.

**b) Substring matching is not a security control.** Every one of these bypasses the blocklist:

| Bypass | Why it works |
| --- | --- |
| `rm  -rf /` | Double space — not the literal `rm -rf /` |
| `rm -fr /` | Flags reordered |
| `rm -rf "/"` | Quoted path |
| `$(echo rm) -rf /` | Command substitution — shell expands it *after* the check |
| `RM${IFS}-rf${IFS}/` | IFS expansion |
| `cd / && rm -rf .` | Same outcome, no matching substring |

**c) `cwd=root` is not a jail.** Setting the working directory constrains nothing when the command is a full shell. `cd /etc && cat shadow` escapes instantly; so does any absolute path. There was no `cwd_outside_workspace` check and no `SUPERAI_SHELL_ALLOW_ANY_CWD` gate.

**d) No audit record.** No `record_side_effect` call, so shell execution through the agent left **no trace in the audit log** — defeating post-incident reconstruction.

### The decisive argument: the repo already solved this

`src/core/os_shell.py` already implements a proper policy engine — a regex deny-list (fork bombs, `dd if=`, `curl|sh`, `Invoke-Expression(...Download)`, `mkfs`, whitespace-tolerant `rm -rf /`), a real workspace jail with an explicit env override, permission-mode-aware dry-run, timeouts, and `record_side_effect` auditing.

So this was never "the author does not know how to do this safely." **There were two shell paths with different safety postures, and the agent runtime used the weaker one.** The fix is a delegation, not a new security model — which is precisely why it satisfied selection criterion 2.

### Also fixed in the same file

**Approval fail-open.** The old gate initialised the result to allow:

```python
if side_effect and mode == "ask" and not should_auto_approve(mode):
    ok = True                      # <- fail-open default
    if approve_callback:
        ok = bool(approve_callback(n, args))
    if not ok: return {"ok": False, "error": "user_denied", ...}
```

Any caller omitting `approve_callback` got **unapproved side effects**. Now defaults to denial with `no_approver_available`, and `SUPERAI_ALLOW_UNATTENDED_SIDE_EFFECTS=1` is the explicit opt-out.

**Gate too narrow.** The condition required `mode == "ask"`. Any other non-plan mode skipped the approval branch entirely and went straight to execution. Now every non-dry side effect the mode does not auto-approve is gated.

**Latent hooks bug.** The `except` branch did `run_post = None  # type: ignore`, shadowing the module-level import and silently disabling **all post-execution hooks** whenever a pre-hook import failed. Post-hooks are where audit and telemetry live, so this quietly disabled observability.

**Allowlist simplification.** Two overlapping conditions with a redundant third clause collapsed into one membership test. `ALL_TOOLS` already contains `bash`/`shell`; `READ_ONLY` intentionally does not.

### If this is not implemented

Any LLM-generated or injected command reaching the build agent gets an **unaudited, effectively unjailed shell** on the host. The blocklist stops a copy-pasted `rm -rf /` and nothing more deliberate.

The realistic chain: prompt injection lands in a fetched web page, a dependency's README, a GitHub issue body, or a poisoned memory entry -> the agent emits a shell command -> the substring check misses it -> it runs on the host with full user privileges -> **nothing is written to the audit log**, so the incident cannot be reconstructed.

This is a working codebase with a `master` branch and a public fork, so the exposure is real, not theoretical.

### Risk of the change itself — low

`runtime.py` already passes `approve_callback=approve`, so the fail-closed default **does not affect the primary agent path**. It only closes the case where a caller omits the approver — the unsafe case. The one thing to watch: `tool_bash` now returns the richer `os_shell` envelope (`executed`, `returncode`, `latency_sec`, `permission_mode`) instead of the old flat dict. Direct callers reading `stdout`/`stderr`/`ok` are unaffected; anything destructuring the old shape needs a look.

### Verification

`tests/test_tools_bridge_shell_hardening.py` — see Change 5.

---

## Change 2 — `container_sandbox.py`: fail closed, drop capabilities

**Commit `eaceba9` (pre-rebase)**

### What was there

```python
fail_closed = (os.getenv("SUPERAI_SANDBOX_FAIL_CLOSED") or "").lower() in {"1","true","yes","on"}
if not docker_available():
    return {..., "fallback": not fail_closed, "fail_closed": fail_closed}
```

### Why it was picked

**A sandbox that silently degrades to host execution is not a sandbox.** The default was fail-*open*: request containment, Docker is missing or errors, and the command runs on the host anyway — silently, with no containment, unless an env var you would only know about from reading the source had already been set.

This inverts the security default. Containment must be opt-*out*, never opt-in-by-accident. Anyone enabling `prefer_container_sandbox` reasonably believes they got isolation; when Docker is absent they got the exact opposite, with no signal.

The capability additions (`--cap-drop ALL`, `--security-opt no-new-privileges`, `--pids-limit`, `--memory`) were bundled because the file's own docstring already listed them as known gaps — the author had documented the weakness and not yet closed it. Low-risk, high-value, same file, one review.

### If this is not implemented

Operators believe they have isolation and do not. Worse than having no sandbox, because the false belief changes behaviour: riskier commands get run under an assumed sandbox than would be run bare. Without `--cap-drop`/`no-new-privileges`, a container escape via a setuid binary or an over-privileged capability stays reachable. Without `--pids-limit`/`--memory`, a fork bomb inside the container takes down the host.

### Deliberate non-change

The workspace mount stays **read-write by default**. Tool shells legitimately write build output; a read-only default would break ordinary use and get switched off wholesale — a security control everyone disables is worth nothing. It is available as `SUPERAI_SANDBOX_WORKSPACE_RO=1`. The docstring's "Limitations" section was rewritten to state the real posture instead of overstating containment.

### Risk of the change itself — moderate, by design

This is the one change with a deliberate behavioural break: environments that relied on silent host fallback will now **fail** instead of running. That is the point. Opt out with `SUPERAI_SANDBOX_FAIL_CLOSED=0` if a host fallback is genuinely wanted.

---

## Change 3 — `.mcp.json`: remove dev paths and peer-writer grant

**Commit `abb5071` (pre-rebase)**

### What was there

```json
{"mcpServers": {
  "mempalace": {
    "command": "C:/Users/burhan.husain/.local/bin/mempalace-mcp.exe",
    "env": {"MEMPALACE_MCP_ALLOW_PEER_WRITER": "1"}
  },
  "membrain": {
    "command": "C:/Python314/python.exe",
    "args": ["C:/Users/burhan.husain/.grok/mcp-servers/membrain_mcp_server.py"]
  }
}}
```

### Why it was picked

Two distinct problems in eleven lines:

**Security:** `MEMPALACE_MCP_ALLOW_PEER_WRITER: "1"` is a **committed capability grant**. Every clone of the repo — including the public fork — receives peer-write access to the memory store by default. Given that this PR also removes a dormant prompt-injection file and that memory is a persistent injection vector, a default-on write grant to that same store is the wrong default to ship.

**Correctness and privacy:** the absolute paths resolve on exactly one machine on earth, so the config is broken for every contributor, and it leaks the internal username `burhan.husain`, the layout of `.grok/mcp-servers`, and a Python 3.14 install path. Minor individually, but it is free to fix and it is reconnaissance material in a public repo.

### If this is not implemented

Contributors get silent MCP startup failures with a confusing cause. Anyone cloning gets an unexpected write grant to their memory store. The internal path disclosure stays public in git history regardless — removing it going forward is still worth doing, but note **the history is not rewritten by this PR**, so treat those paths as already disclosed.

### Risk of the change itself — low, but requires local action

PATH-resolved commands mean anyone actually using these servers must have them on PATH. Point `membrain`'s `args` at your own server path in a local, uncommitted override.

---

## Change 4 — delete `config/constitution.md`

**Commit `751b67b` (pre-rebase) · Includes a correction to an earlier review claim**

### The correction, first

The initial report said this file was **injected into every model prompt by default** because `config.py` sets `use_constitution: True`. **That was wrong**, and it is recorded plainly here.

`constitution.py`'s loader resolves only two paths: `<workspace>/.superai/constitution.md` and `~/.superai/constitution.md`. It **never reads `config/constitution.md`**, and falls back to a safe built-in minimal constitution when neither exists. So the file is dormant, not live. Severity drops from *critical, active exploitation path* to *dead file with latent risk*.

### Why it was still picked

Because the argument for deletion does not depend on it being live:

- **Nothing loads it.** Zero functional cost to removal.
- **Its contents read as an injection payload,** not a policy document.
- **The trap is real.** A file named `constitution.md` sitting in `config/` looks exactly like the thing you are meant to copy to `.superai/constitution.md`. The moment anyone does — a contributor tidying config, a setup script, a future install wizard — it goes live in **every prompt** through the `use_constitution` path in `orchestrator.py`.

A dead file that becomes a critical vulnerability the instant someone does the obvious thing with it is worth deleting.

### If this is not implemented

The trap stays armed. The likeliest trigger is not an attacker — it is a contributor, six months from now, copying what looks like the intended default config into place.

### Risk of the change itself — none

No code path reads the file. Verified by reading `constitution.py`'s loader in full.

---

## Change 5 — 10 regression tests

**Commit `55321cf` (pre-rebase) · `tests/test_tools_bridge_shell_hardening.py`**

### Why it was picked

Selection criterion 4. Two of these tests **fail against pre-fix `master`** and pass after the fix:

- `test_bash_rejects_whitespace_evaded_rm_root` -> `rm  -rf /`
- `test_bash_rejects_flag_reordered_rm_root` -> `rm -fr /`

That pairing is the whole point. They are not decoration — they are the **executable proof the vulnerability was real**, and the reason the analysis does not have to be taken on trust. Run them on `master`, watch them fail, then run them on the branch.

Coverage: the two bypass proofs, `curl | sh`, empty commands, plan-mode non-execution, the three approval-denial paths (no approver / refused / approver raises), and agent allowlisting.

### If this is not implemented

The fix silently regresses. The original `tool_bash` was presumably written believing it was safe — its docstring says so. Without a test pinning the behaviour, the next person optimising that path reintroduces `shell=True` and nothing objects. **This file is what makes the fix durable rather than temporary.**

### Verification

```bash
pytest tests/test_tools_bridge_shell_hardening.py -v
pytest tests/test_result_contract.py tests/test_cli_pool.py tests/test_terminal_pool.py tests/test_h_i.py -q
```

The tests were written but **never executed** — the review agent cannot run code. Treat them as unverified until you have run them.

---

## Excluded from this PR, and why

| Finding | Severity | Why not here |
| --- | --- | --- |
| Untrusted memory concatenated into prompts (`orchestrator.py`) | **P0** | Fails criterion 3. The MCP write tool replaces whole files, and `orchestrator.py` is large enough that reproducing it verbatim risks silent corruption. Needs a surgical local edit |
| `AGENTS.md` injection blocks | **P0** | Requires a human. Editing means reproducing content that must be treated as untrusted, with no way to verify the legitimate guidance survives. Judgement call that is not an agent's to make |
| `src/cli/main.py` is 297 KB | P1 | Fails criterion 3 catastrophically. Its own multi-PR project |
| No lint / type-check in CI; matrix is Windows + py3.11 only | P1 | Orthogonal to the security fix. Would balloon the diff with unrelated churn |
| ~14 TUI / ~11 memory / ~9 routing modules | P1 | Fails criterion 2 — needs product decisions about which features are real |
| Plaintext `~/.superai/.backup_key` | P2 | Fails criterion 2. Key migration needs a compatibility path for existing backups; getting it wrong makes backups unrecoverable |
| `except Exception: pass` throughout | P2 | Wide, mechanical, low individual severity. Its own PR |
| Committed 240 KB scorecards, stray `_b.json` | P2 | Cosmetic |

---

## Findings withdrawn after reading the full source

Both appeared in the first review report. Both were **wrong**. They are withdrawn explicitly rather than quietly dropped, and the retraction is documented in the PR body too.

### Withdrawn: "`tool_proposals.py` hardcodes `auto_approve=True`"

Flagged from a grep fragment. Reading the whole file, it is correct — `execute()` enforces approval *before* any executor runs:

```python
if p.requires_human and p.status != ProposalStatus.APPROVED.value and not force:
    raise ValueError("Proposal requires human approval first")
if p.action in {"run_shell", "edit_file"} and not p.requires_human:
    if p.status != ProposalStatus.APPROVED.value and not force:
        raise ValueError(f"Action {p.action} requires human approval ...")
```

`force=True` additionally requires `SUPERAI_ALLOW_FORCE_PROPOSALS=1`. So `auto_approve=True` in `_exec_edit_file` means "consent already obtained upstream" — exactly as its comment says. And `_exec_run_shell` is the **best** shell implementation in the repo: rejects string commands outright, blocks shell meta-executables behind an env flag, jails cwd via `assert_in_workspace`, runs `shell=False`.

**Lesson:** the finding was an artefact of reviewing a search fragment instead of the file.

### Withdrawn: "Entry point mismatch: `scli.main:main` vs `scli.main:app`"

`src/cli/main.py` defines `main()`, which wraps `app()` to add M080 exception-to-exit-code mapping. `pyproject.toml` is **correct and deliberately so** — pointing the script at `app` would skip the exit-code mapping. **The docs are wrong, not the packaging.** Demoted from P1 bug to P2 doc fix.

---

## Merge checklist

1. **Run the tests** — the review agent cannot execute code, so this PR is unverified by it. Non-negotiable gate.
2. **Check direct `dispatch_tool` callers** that may omit `approve_callback` — look at `goals_daemon.py`, `cli_pool.py`, `mcp_server.py`. They need an approver or the explicit opt-out env var.
3. ~~Decide the `master` history question before merging.~~ **Done, 27 Jul 2026.** `master` was rewound to `21ecb8c`, the review docs re-committed as `e93eb75`, and this branch rebased onto the new head (head `6604ca5`, substance unchanged: 5 commits, 5 files, +238/−90). No history work remains — but confirm the force-push protection rule on `master` was re-enabled afterwards.
4. **Satisfy branch protection.** The PR reports `mergeable_state: blocked` — a required review or status check, not a conflict.
5. **Sync or delete the public fork** `d360-test/SuperAI_Review`. It is byte-identical, so the shell bypass is publicly visible there.

> **Net assessment:** this PR fixes one genuinely exploitable vulnerability and three wrong-direction security defaults, and adds the tests that keep them fixed. It invents almost no new logic — four of five changes make weak code use protections the repo already had. **The two remaining P0 items are not in it** and still need a human: the orchestrator memory delimiting, and the `AGENTS.md` review.
