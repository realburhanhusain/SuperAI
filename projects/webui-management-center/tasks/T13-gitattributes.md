# T13 — Create `.gitattributes` — **own commit, before any vendored bytes**

| | |
|---|---|
| **Wave** | W4 |
| **Status** | `[ ]` |
| **Depends on** | — (can be done any time; **must** precede T14) |
| **Estimate** | 30 min |
| **Owner** | — |
| **Blocked by** | **Q2** — narrow vs repo-wide is an owner decision |

## Goal

Protect vendored bytes from CRLF mangling **before** those bytes ever enter a
commit.

## Why the ordering is non-negotiable

Putting the `.gitattributes` rule and the vendored file in the **same** commit
is too late. At the moment the file is staged, the rule is not yet in effect for
that operation. The corruption then:

- reproduces on replay (rebase, cherry-pick, `filter-repo`),
- **is invisible in your own working copy**, because your local checkout already
  has the bytes you wrote,
- and only appears on a fresh clone — i.e. for the next person, not for you.

That combination is why this gets its own commit and its own task rather than
being folded into T14.

## This is not hypothetical here

`.gitattributes` is **absent repo-wide** (verified 2026-08-05). Git in this repo
is actively performing LF→CRLF conversion — committing the plan files for this
very project emitted:

```
warning: in the working copy of 'projects/webui-management-center/PLAN.md',
LF will be replaced by CRLF the next time Git touches it
```

So `core.autocrlf` is on and unrestrained. Markdown tolerates it. A hashed,
sha256-pinned vendored artifact does not — the manifest check in T14 will fail,
or worse, pass locally and fail on a clean clone.

## The pre-existing exposure (Q2)

`vendor/vega/*.min.js` was vendored with no `.gitattributes` rule either. It has
survived so far, but by luck or by a local git setting, not by design.

**Ask the owner (Q2):**
- **Narrow** — add rules only for `vendor/mgmt-ui/*.html`. Minimal, no
  interference with the ~10 concurrent worktrees.
- **Repo-wide** — cover `vendor/**` including the existing vega bytes. Fixes a
  real latent issue but rewrites line endings under other sessions' feet.

`PLAN.md` recommends **narrow now**, repo-wide as its own separate change.

## Steps

1. Get the Q2 decision. Do not guess.
2. Create `.gitattributes` at repo root with, at minimum:
   ```
   vendor/mgmt-ui/*.html -text
   ```
   (`-text` disables all conversion. Confirm this is the right marker for a
   sha256-pinned text-ish artifact — the goal is byte-exactness, so treat it as
   opaque.)
3. Commit **this file alone**. No other change in the commit.
4. Verify the rule is live *before* T14 begins.

## Acceptance criteria

- [ ] Q2 answered by the owner and the answer recorded in the Log.
- [ ] `.gitattributes` exists at repo root with a rule covering `vendor/mgmt-ui/`.
- [ ] The commit contains **only** `.gitattributes` — verify with `git show --stat`.
- [ ] `git check-attr -a vendor/mgmt-ui/management.html` reports the expected attribute.
- [ ] This commit is an ancestor of T14's commit.

## Verification command

```powershell
git show --stat HEAD                 # must list exactly one file
git check-attr -a vendor/mgmt-ui/management.html
```

## Log

_(record the Q2 decision and the real command output before marking `[x]`)_
