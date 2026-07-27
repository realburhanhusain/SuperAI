# PR #4 — Route `os_shell` through the container sandbox and fail closed

| | |
| --- | --- |
| PR | [#4](https://github.com/realburhanhusain/SuperAI/pull/4) |
| Branch | `security/sandbox-shell-containment` |
| Base | `master` @ `1a5f41d` |
| Branch head | `eb34c7d` |
| Status | Open — **not reviewed, not run** |
| Files | `src/core/os_shell.py`, `tests/test_os_shell_sandbox.py` (new) |

## The finding, and why it matters more than it looks

`container_sandbox.py` is genuinely careful code. All Linux capabilities
dropped, `no-new-privileges`, network defaulting to `none`, PID and memory
limits, and since PR #1 it fails closed rather than silently degrading to the
host.

**None of it applied to the agent's shell tool.**

`try_sandboxed_shell` had exactly two callers: `tool_proposals.py` and
`terminal_pool.py`. `os_shell.run_shell` was not one of them. It called
`subprocess.run(..., shell=True)` on the host directly. PR #1 then routed
`tool_bash` through `run_shell` — so the single most security-sensitive path in
the system, the one an LLM drives directly from model output, was the path with
no container anywhere near it.

`prefer_container_sandbox` therefore did far less than its name implies.

**Attribution, stated carefully:** this is **not** a regression introduced by
PR #1. `tool_bash` was never sandboxed — it previously had its own unsandboxed
`subprocess.run` with a weaker deny-list. PR #1 improved the deny-list and the
approval gate and left containment exactly where it found it. The gap is
original, not new.

## Change — the ordering in `run_shell`

1. Deny-list and cwd check — unchanged, still first
2. Dry-run / plan mode — unchanged, still returns before execution
3. **Container sandbox** — new
4. Host execution — only if the sandbox was not requested, or was unavailable
   *and* fail-closed was explicitly disabled

The deny-list stays ahead of the sandbox deliberately: a catastrophic command
should never reach an executor, contained or not.

### Fail-closed honoured at this call site

`container_sandbox` already computed a `fallback` flag; nothing consumed it on
this path. Now, if the sandbox is requested and Docker is missing or errors,
`run_shell` returns `ok=False`, `error_code: "sandbox_unavailable"` and a
`remedy` string — **the command does not run on the host.**

An unexpected exception from the sandbox layer is treated the same way. Falling
through to the host on an unknown error would defeat the entire purpose of
requesting a sandbox.

The only route to host execution after requesting a sandbox is setting
`SUPERAI_SANDBOX_FAIL_CLOSED=0` deliberately.

### `sh -lc` — the one debatable decision

`try_sandboxed_shell` takes an argv list. `run_shell` receives a shell string
that may contain pipes, redirects and globs. Rather than break those commands,
`sandbox_argv()` runs them as `["sh", "-lc", command]`.

**Argue with this in review.** Shell metacharacters survive — but the shell
interpreting them is the container's, in a process with no capabilities, no new
privileges, no network and only the workspace mounted. The container is the
boundary; metacharacter injection inside a contained process is not the threat
model. The alternative — refusing any command with shell syntax — would make
the sandbox unusable and guarantee it stays off.

Side benefit: sandboxed execution becomes platform-independent. Identical
behaviour from Windows, macOS and Linux hosts, because the interpreter is
always the image's `sh`.

### Result envelope and audit

Adds `sandbox` to every shell result: `"docker"`, `"none"`, `"unavailable"` or
`"error"`. Previously a caller had no way to know whether a command had been
contained. Sandboxed runs audit as `os_shell_sandboxed`, so the two paths are
distinguishable after the fact.

### Docstring correction

The module listed "Workspace-relative cwd by default (jail)" as a safety
property. `cwd` jails nothing — a command may name absolute paths freely. The
docstring now says so and points at the sandbox as the only real confinement.

This is the third instance of the same defect class in this review: PR #1 fixed
a `tool_bash` docstring that claimed it avoided `shell=True` while passing
`shell=True`. Documentation describing intended behaviour as actual behaviour
is a recurring pattern here and worth treating as a review smell.

## Tests — `tests/test_os_shell_sandbox.py`, 11 cases

No Docker is started, no real command runs. Both the sandbox entry point and
`subprocess.run` are replaced, so routing and policy are what is under test.

| Test | Asserts |
| --- | --- |
| `test_sandbox_not_enabled_runs_on_host` | No behaviour change when the sandbox is off |
| `test_sandbox_enabled_runs_in_container_not_on_host` | Container output returned, **nothing ran on the host** |
| `test_command_reaches_container_via_sh_lc` | argv is exactly `["sh", "-lc", cmd]`, pipes intact |
| `test_sandbox_unavailable_fails_closed` | Docker missing → `ok=False`, host untouched |
| `test_sandbox_error_fails_closed` | Docker errored → `ok=False`, host untouched |
| `test_sandbox_exception_fails_closed` | Unexpected raise → `ok=False`, host untouched |
| `test_explicit_opt_out_allows_host_fallback` | `fallback=True` still permits host execution |
| `test_nonzero_container_exit_is_not_ok` | Container exit code mapped, not swallowed |
| `test_denied_command_never_reaches_the_sandbox` | Deny-list precedes the sandbox |
| `test_dry_run_never_reaches_the_sandbox` | Dry run executes nowhere |
| `test_plan_mode_never_reaches_the_sandbox` | Plan mode executes nowhere |

Four assert on the **absence** of host execution — the property that was
silently false before this change.

## Excluded from this PR

| Excluded | Why |
| --- | --- |
| Turning the sandbox on by default | Breaks every user without Docker. Deliberate product decision, not a side effect of a bug fix |
| Read-only container rootfs | Real hardening gap, needs testing against actual build workloads |
| Dropping root inside the container | `SUPERAI_SANDBOX_USER` exists but is unset by default; changing it may break file ownership in the mounted workspace |
| Enforcing `--network none` | Currently a default, not a constraint. Worth doing, needs a decision on whether any tool legitimately needs network |
| Sanitise-on-write to the learning store | Split out on request. Depends on `untrusted_data.py`, which only exists on PR #2's branch — building it off `master` first would mean duplicating that module or opening a PR that cannot import |

## Withdrawn finding (recorded for honesty)

After PR #1 merged I flagged `goals_daemon.py`, `cli_pool.py` and
`mcp_server.py` as broken callers of `dispatch_tool` missing `approve_callback`,
and described it as a live regression on `master`.

**That was wrong.** Two independent searches confirm `dispatch_tool` appears in
six files only — its definition, `runtime.py`, two test files and two review
docs — and `tools_bridge` is imported by `runtime.py`, `tui.py` (which imports
only `catalog`) and the tests. Those three modules do not reference either
symbol. `runtime.py` passes an approver, so the only production caller was
already correct.

The original review listed them correctly as *candidates to check*. I then
restated an unchecked list as a confirmed regression. The check cost two
searches and should have preceded the recommendation.

## Risk

**Low when the sandbox is off** — the only difference is a new
`"sandbox": "none"` key.

**Not low when the sandbox is on.** Anyone who set `prefer_container_sandbox`
without working Docker was silently getting host execution and will now get
hard failures. That is correct behaviour and the whole point, but it will look
like a regression to someone who unknowingly depended on the fallback. It
belongs in release notes.

## Verification

```bash
pytest tests/test_os_shell_sandbox.py -v
pytest tests/test_tools_bridge_shell_hardening.py tests/test_result_contract.py tests/test_terminal_pool.py -q
```

**Not run.** The second command matters more than usual: `terminal_pool.py` and
`tool_proposals.py` are the pre-existing sandbox callers and should be
unaffected — but that is an expectation, not a verified fact.

## Merge checklist

- [ ] Accept or reject `sh -lc` inside the container
- [ ] Accept hard-failing when Docker is absent for existing sandbox users
- [ ] Decide whether `--network none` becomes enforced
- [ ] Decide whether the sandbox should default on (separate PR)
- [ ] Run the tests
- [ ] Note the behaviour change in release notes
