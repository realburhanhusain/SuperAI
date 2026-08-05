# T10 — `/api/config/backups` + `/api/config/rollback` + `/api/config/diff`

| | |
|---|---|
| **Wave** | W2 |
| **Status** | `[ ]` |
| **Depends on** | T09 |
| **Estimate** | 1 h |
| **Owner** | — |

## Goal

Make config changes previewable before they happen and reversible after.
Together with T06's backups, this is what makes browser-based config editing
safe enough to use.

## `GET /api/config/diff`

- Accepts proposed changes, returns the unified diff from `diff_changes` (T07).
- **Writes nothing.** Assert this in a test — a preview with side effects is
  the worst kind of bug, because the user believes they have not committed yet.
- This mirrors the Management Center's own diff-preview-before-save UX, which is
  the pattern worth borrowing from that project even though its code is not.
- Management-token gated (it reveals config content).

## `GET /api/config/backups`

- Lists snapshots in `~/.superai/backups/` created by T06.
- Return id, UTC timestamp, and size for each; newest first.
- Handle the empty directory: 200 with an empty list, not a 404.

## `POST /api/config/rollback`

- Body: `{"backup_id": "..."}`.
- **Validate the id against the listing** — never interpolate a caller-supplied
  string into a path. A `backup_id` of `../../.ssh/id_rsa` must be rejected
  before it touches the filesystem. Resolve the candidate path and confirm it is
  inside the backups directory; reject anything else.
- **Back up the current config before restoring**, so a rollback is itself
  reversible. A one-way undo is a trap.
- Restore atomically, via the same T06 path.
- Audit-log the rollback, including the source backup id.

## Acceptance criteria

- [ ] `/api/config/diff` returns a correct diff and provably writes nothing (mtime + content asserted).
- [ ] `/api/config/backups` lists correctly; empty case returns 200 with `[]`.
- [ ] Rollback restores the exact prior bytes (assert hash equality with the snapshot).
- [ ] **Path-traversal test:** `backup_id` containing `..` or an absolute path is rejected without any filesystem write.
- [ ] Rollback creates its own backup first — rollback-of-a-rollback works.
- [ ] All three routes are management-token gated and absent when the feature flag is off.

## Verification command

```powershell
$env:PYTHONPATH = "C:\Users\burhan.husain\claude\worktrees\superai-webui-mc\src"
python -m pytest tests/test_web_management_center.py -k "backup or rollback or diff" -q
```

## Log

2026-08-05: Tests passed successfully.
```
6 passed in 0.15s
```
