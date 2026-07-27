# PR 5 — Remove the `membrain` MCP server entry

**PR:** https://github.com/realburhanhusain/SuperAI/pull/5
**Branch:** `chore/mcp-remove-membrain` → `master`
**Files:** `.mcp.json`
**Status:** open, awaiting review

---

## What was there

`.mcp.json` declared two MCP servers. The second:

```json
"membrain": {
  "command": "python",
  "args": ["membrain_mcp_server.py"],
  "env": {
    "PYTHONUNBUFFERED": "1",
    "MEMBRAIN_SCHEMA": "membrain",
    "MEMBRAIN_MCP_TIMEOUT": "120"
  }
}
```

`membrain_mcp_server.py` does not exist anywhere in the repository. A code search for the filename returns no matches. The entry can only ever fail to start.

## Why it was picked

This was the one unresolved review comment on PR #1, raised by the Copilot reviewer and left open when that PR merged. I confirmed it independently by reading `.mcp.json` at master and searching the tree for the script. Both the criticism and the absence are verified facts, not inferences.

It is also the cheapest item on the entire backlog: one JSON object, no code paths.

## Why removal rather than the alternatives

Three options were considered.

1. **Remove the entry.** Chosen.
2. **Replace the path with `${MEMBRAIN_SERVER_PATH}`.** Rejected: it keeps a server declared that still cannot start unless someone sets an undocumented variable. That trades a clear failure for a confusing one.
3. **Document it as optional.** Rejected: the failure stays, and prose is added explaining that the failure is expected. Documentation is not a fix.

A committed entry pointing at a file that is not in the tree is not configuration; it is a broken default that every clone pays for. If membrain returns, it should arrive together with the server it names, or with a documented variable and a README entry, in the same change.

`mempalace` is deliberately untouched. `mempalace-mcp` is a console entry point resolved from `PATH`, not a path into this tree, so it does not share the defect.

## What happens if it is not implemented

Every clone starts an MCP server that immediately fails. The visible symptom is a startup error unrelated to whatever the user was actually doing.

The second-order cost is worse than the first. The natural human response to a startup error that is always present and never matters is to stop reading startup errors — which is exactly where a genuine sandbox-unavailable or permission-denied warning would appear. A permanent false alarm trains people to ignore the channel that the security work in PRs #2 and #4 depends on.

## Risk

Very low. One object removed from a config file. No Python touched, no test affected. If a local setup depended on membrain, that setup was already failing.

## Verification

- `.mcp.json` read back in full after the push; matches the intended body exactly.
- Final content is `mcpServers` containing `mempalace` alone. Valid JSON.
- No test covers `.mcp.json`, so there is nothing to run. Confirm by inspection of the diff.
