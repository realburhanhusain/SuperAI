# T13 — Verify CRLF protection covers the new vendored bytes

| | |
|---|---|
| **Wave** | W4 |
| **Status** | `[ ]` |
| **Depends on** | — (**must** still precede T14) |
| **Estimate** | 15 min (was 30 min) |
| **Owner** | — |
| **Blocked by** | **Q2 re-opened** — see "Correction" below |

## Correction (2026-08-05) — this task shrank

The original version of this task was written on a **false premise**: that
`.gitattributes` was absent repo-wide and the already-vendored
`vendor/vega/*.min.js` therefore had no CRLF protection.

That was wrong. It is absent at the **repo root**, but not in `vendor/`:

```
$ cat vendor/.gitattributes
# Vendored bytes are pinned by sha256 in manifest.json. Git must not rewrite
# line endings on checkout — a CRLF conversion changes the hash and every
# integrity check fails on a fresh clone, on Windows only, for no real reason.
* -text
```

`* -text` applies to **everything under `vendor/`, recursively**, so a future
`vendor/mgmt-ui/management.html` is **already covered**. Verified:

```
$ git check-attr -a vendor/mgmt-ui/management.html
vendor/mgmt-ui/management.html: text: unset

$ python scripts/vendor_sync.py --check
Local integrity: 4/4 files match their pin
```

Whoever vendored vega had already thought this through, and the comment in that
file states the exact reasoning this task was invented to enforce.

**Consequence: there is nothing to add for correctness.** T14 can proceed
safely as things stand. What survives is a verification step, below.

## What survives — verify, don't assume

Confirm coverage is real **before** T14 commits any bytes. Protection that is
assumed rather than checked is how the original error happened.

1. Confirm the rule resolves for the exact target path:
   ```powershell
   git check-attr -a vendor/mgmt-ui/management.html
   ```
   Must report `text: unset`. Anything else → stop, and do not proceed to T14.

2. Confirm the baseline integrity check passes before you add to it:
   ```powershell
   python scripts/vendor_sync.py --check
   ```
   Must report all existing files matching their pin.

## Still open: repo-wide normalization (Q2)

The owner approved "repo-wide" — but that approval was given against the false
premise above. With vendored bytes already protected, a root `.gitattributes`
would no longer be fixing a vendoring bug. It would be a **separate hygiene
change**: normalizing line endings for *source* files (`* text=auto` plus
per-type rules).

That change is real but unrelated to this project, and it is disruptive:
`git add --renormalize .` touches essentially every tracked file while ~10 other
worktrees have branches checked out, producing conflicts for sessions that are
not expecting them.

**Do not do it inside this project.** If the owner still wants it, it belongs in
its own branch and its own task, sequenced when the repo is quiet. Awaiting
re-decision — see `TASKBOARD.md` → Q2.

## Acceptance criteria

- [ ] `git check-attr -a vendor/mgmt-ui/management.html` reports `text: unset`, output pasted in the Log.
- [ ] `python scripts/vendor_sync.py --check` passes at baseline, output pasted in the Log.
- [ ] Q2's re-decision recorded on the board (repo-wide normalization deferred, or split into its own branch).
- [ ] **No new `.gitattributes` file added by this project** unless the checks above fail.

## Verification command

```powershell
git check-attr -a vendor/mgmt-ui/management.html
python scripts/vendor_sync.py --check
```

## Log

_(paste both command outputs before marking `[x]`)_
