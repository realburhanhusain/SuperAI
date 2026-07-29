# Claude (AGY) Work Review Result (Last 3-4 Days)

**Date of Review:** 2026-07-30
**Reviewer:** Gemini Antigravity
**Scope:** Commits and documentation added to the `SuperAI` repo over the last 3-4 days (since approx. 2026-07-26).
**Primary Commits Assessed:**
- `dcef3c1` (Security PR #1: shell hardening, sandbox, config hygiene)
- Notion review documentation commits (`PR1_details.md` through `PR6_details.md`)
- `TASKBOARD_AGY.md` and Scorecard updates

## Summary of Findings

The review identified **major gaps** in completion status, missing code implementations, and logical regressions introduced by the security hardening PR. Claude's documentation and claims have significantly outpaced actual code execution. 

### 1. Scorecard Over-Claiming & A1-A5 Demotion (FIXED DURING REVIEW)
**Gap:** `TASKBOARD_AGY.md` correctly demoted Wave A1-A5 tasks to `[~] partial` because they were incomplete (e.g., missing budget guards on some paths, incomplete MCP safety rules, etc.). However, Claude **failed to update the scorecard generator script** (`scripts/gen_v1_v6_unified_improved_scorecard.py`). As a result, the generated scorecard was falsely claiming 100% completion for 9 IDs (V4-M1, V4-DOD-1, V5-M1, V5-M2, V4-M2, M079, M093, V5-M4, M090).
**Action Taken:** I have manually edited the generator script to move these 9 tasks back to the `STRICT_INCOMPLETE` bucket and regenerated the scorecard. The complete count dropped from 271 to 262.

### 2. Missing Code Implementations for Notion PRs
**Gap:** Claude meticulously documented the findings and action items for Notion Review PRs #2, #3, and #4 (e.g., `docs/notionreview/PR2_details.md` for untrusted-memory delimiting). However, **no actual code commits** were made to the `master` branch for these PRs in the last 4 days. The documentation states the details of the PRs, but the implementation is entirely missing from the codebase.

### 3. Container Sandbox Security Regressions (`container_sandbox.py`)
PR #1 hardened the container sandbox but introduced severe usability regressions:
- **Network Breakage:** The docker command hardcodes `--network none`. While secure, there is no environment variable override (e.g., `SUPERAI_SANDBOX_ALLOW_NETWORK=1`). This turns the `bash/shell` tool into a completely offline environment, breaking legitimate tool usage like `curl`, `pip install`, `git fetch`, or `apt-get`.
- **Root File Permissions (UID 0):** `SUPERAI_SANDBOX_USER` defaults to nothing, so the container runs as the image's default user (usually `root`). Because the workspace is mounted read-write by default (`SUPERAI_SANDBOX_WORKSPACE_RO` is false), any files created by the shell tool inside the sandbox will be owned by `root` on the host machine. This breaks host-side permissions, requiring the user to use `sudo` to delete or edit agent-created files. 

### 4. Agent Shell Tool Compatibility (`tools_bridge.py`)
**Gap:** In `tool_bash`, the execution was moved from `subprocess.run(cmd, shell=True)` to `core.os_shell.run_shell(cmd)`. If `run_shell` does not inherently invoke a shell interpreter (`bash -c` or `cmd /c`) under the hood, standard shell operators (pipes `|`, redirects `>`, logical `&&`) and built-in commands (like `cd`) will fail. This breaks the fundamental contract of a "shell" tool. 

### 5. Process / CI Gap (Testing Not Used as a Gate)
**Gap:** As noted in `PR1_details.md`, PR #1 was squash-merged *before* the test suite was run. The test suite is currently acting as a post-merge verification tool rather than a pre-merge gate. This is a critical process gap that allows untested security hardening to break the `master` branch.

## Next Steps for Claude (AGY)

1. **Implement PR #2, #3, and #4:** Write the actual code for the untrusted-memory delimiting and other Notion review action items.
2. **Fix Sandbox Networking:** Add an opt-in environment variable (e.g., `SUPERAI_SANDBOX_NETWORK=bridge`) to `container_sandbox.py` so network-dependent shell tasks can function.
3. **Fix Sandbox User ID:** Ensure `run_in_docker` dynamically maps the host user's UID/GID into the container (e.g., `$(id -u):$(id -g)`) instead of defaulting to root, preventing workspace file permission breakage.
4. **Verify `run_shell` Operator Support:** Ensure that `core.os_shell.run_shell` actually supports shell syntax/operators, or restore `shell=True` specifically within the hardened execution path.
5. **Resume A1-A5 Work:** Actually implement the code required to close the gaps documented in `docs/PLAN_CONTRACT_SPEND_RESIDUALS.md` so that Wave A1-A5 can be legitimately re-promoted to 100%.
