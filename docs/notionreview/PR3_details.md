# PR #3 — CI: lint, type check, security guardrail and OS/Python matrix

| | |
| --- | --- |
| PR | [#3](https://github.com/realburhanhusain/SuperAI/pull/3) |
| Branch | `ci/lint-typecheck-and-matrix` |
| Base | `master` @ `1a5f41d` |
| Branch head | `b3ba00c` |
| Status | Open — **not reviewed, not run** |
| Files | `.github/workflows/ci.yml`, `pyproject.toml`, `scripts/check_untrusted_appends.py` (new) |
| Source files touched | **None.** No behaviour change. |

## Why this PR exists

PR #1 and PR #2 both shipped tests. Neither had a CI configuration capable of
telling anyone whether those tests passed anywhere other than Windows on
Python 3.11 — and in PR #1's case the job was still running when the PR was
merged.

The pattern across this whole review has been the same: protection that is
asserted but not enforced. `tool_bash` had a docstring claiming it avoided
`shell=True`. `os_shell` claimed a cwd "jail". PR #2 wraps four prompt appends
and nothing stops a fifth. This PR is about enforcement rather than assertion.

## Change 1 — `lint` job

**What was there:** nothing. No linter, ever.

**What ships:** two ruff steps.

| Step | Rules | Blocking |
| --- | --- | --- |
| Errors only | `E9,F63,F7,F82` | **Yes** |
| Full rule set | `E4,E7,E9,F,B,UP` | No (`continue-on-error`) |

**Why the split.** The blocking set is not style — it is syntax errors,
undefined names and broken f-strings. Those are bugs. The full set against
~230 existing modules would produce a wall of findings and a permanently red
build, and a permanently red build trains everyone to ignore CI. Advisory
first, tightened as the backlog clears.

**If not implemented:** an undefined name in a rarely-imported module sits on
`master` until a user hits it. Given how much of this codebase is late-imported
inside functions, that could be a long time.

## Change 2 — `typecheck` job (advisory)

mypy over `tools_bridge.py` and `os_shell.py` only — the two modules that decide
whether a shell command runs. Advisory, because the codebase is largely
unannotated.

**Why so narrow:** a wide mypy run here produces thousands of errors and gets
turned off within a week. Two files that matter is worth more than full
coverage that nobody reads.

## Change 3 — `guardrails` job and `scripts/check_untrusted_appends.py`

**What was there:** nothing could detect a regression of the PR #2 fix.

**What ships:** an AST check that every `prompt_parts.append(...)` inside
`_build_step_prompt` either passes through `wrap_untrusted_block()` or is a
known first-party part (`step.description`, the constitution, the task
framing).

**Why this is not a unit test.** PR #2's tests assert that the four appends
that exist today are wrapped. No test can assert anything about a fifth append
that has not been written yet. Only a static check over the function can.

**Design details worth reviewing:**

- A parse failure or a missing `_build_step_prompt` exits **2**, not 0. A
  guardrail that silently passes when it cannot see the code is worse than no
  guardrail, because it produces a green tick that means nothing.
- If `src/core/untrusted_data.py` is absent the script **skips and exits 0**.
  That is the state of `master` until PR #2 merges. This is deliberate: it lets
  PR #3 and PR #2 merge in either order without one breaking the other.

**If not implemented:** the PR #2 fix decays. Someone adds a fifth retrieved
prompt part in six months, all existing tests pass, and the injection path
reopens silently.

## Change 4 — `test` job matrix

**What was there:** `windows-latest`, Python `3.11`. `pyproject.toml` declares
`requires-python = ">=3.10"`.

**What ships:** 3 OS x 3 Python versions, `fail-fast: false`, plus Linux +
3.13 as `experimental: true`.

`fail-fast: false` matters — with it on, the first red cell cancels the rest and
you learn about one failure instead of nine.

**Expect red cells.** This exercises Linux, macOS, 3.10, 3.12 and 3.13 for the
first time in the project's history. Any failures were already there; nothing
was looking. `sys.platform == "win32"` branches in `os_shell.py` are the
obvious candidates.

## Change 5 — `smoke` job split out

The `superai init` / `run` / `backup` steps were bolted onto the test job, so a
smoke failure and a unit-test failure were indistinguishable in the checks
list. Now separate, and run once rather than nine times.

## Change 6 — `pyproject.toml`

`ruff` and `mypy` added to the `dev` extra, with `[tool.ruff]` and
`[tool.mypy]` config so a local run matches CI exactly. `F841`
(assigned-but-unused) is ignored: it fires constantly in this codebase's long
procedural functions and is not a correctness signal on its own.

## Excluded from this PR

| Excluded | Why |
| --- | --- |
| Making `test` a required status check | Repository setting, not a file. Needs your action, and should wait until the matrix is green |
| Fixing whatever the linters find | Separate PR. Mixing tooling with the fixes it produces makes both unreviewable |
| Enforcing mypy | Needs annotations first |
| Coverage reporting | Not useful while the matrix is unproven |
| Dependency pinning / lockfile | Real gap, unrelated to this PR |

## Honest limitations

1. **I have not run any of this.** Workflow YAML is not validated until GitHub
   runs it. A syntax error in `ci.yml` would show up on first push.
2. **The guardrail is inert on `master` today.** It activates when PR #2 merges.
   Until then it prints a skip notice.
3. **The linters do not enforce anything meaningful yet.** Only genuine errors
   block. Calling this "linting added" would overstate it.
4. **The matrix will probably go red on first run.** That is the feature, but it
   does mean this PR may need triage before it can merge.

## Merge checklist

- [ ] First run completes; `ci.yml` parses
- [ ] Blocking ruff step passes against current `master`
- [ ] Matrix failures triaged — decide: fix here, or log and merge
- [ ] Confirm the smoke job still passes on Windows
- [ ] Consider making `test` a required check afterwards
