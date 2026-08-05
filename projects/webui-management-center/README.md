# Project: Web UI Management Center

**Goal:** give SuperAI a browser UI for **configuration modification** and
**runtime status monitoring**, reusing the MIT-licensed
[CLI Proxy API Management Center](https://github.com/router-for-me/Cli-Proxy-API-Management-Center)
where it genuinely fits — and *not* where it doesn't.

**Status:** planned, not started. See [`TASKBOARD.md`](TASKBOARD.md).

---

## Read this before picking up a task

1. **[`PLAN.md`](PLAN.md)** — the full design. Read the Executive Summary and
   the Security section at minimum. It explains *why* the obvious approach
   (fork the React UI and point it at SuperAI) was rejected.
2. **[`TASKBOARD.md`](TASKBOARD.md)** — pick the highest-priority `[ ]` task
   whose dependencies are all `[x]`.
3. **`tasks/T##-*.md`** — each task is self-contained: what to change, exact
   acceptance criteria, and the exact command that proves it.
4. Repo-wide conventions still apply — see root [`AGENTS.md`](../../AGENTS.md).

## The one-paragraph summary

The Management Center is a client written against **CLIProxyAPI's**
`/v0/management` API. It manages the *proxy*, not SuperAI. So this project
splits in two: SuperAI-native pages and endpoints added to the **existing**
FastAPI app (`src/cli/web_app.py`) for SuperAI's own config and status, plus
the **unmodified** `management.html` vendored and served at `/cliproxy-admin`
as an operator console for the separate, optional proxy process. Nothing is
forked. No Node/Bun toolchain enters this repo.

## Non-negotiable constraints

| # | Constraint |
|---|---|
| C1 | **Additive and opt-in.** Default `superai web` behaviour must not change. Config-write routes are registered only when `SUPERAI_WEB_ENABLE_CONFIG_WRITE=1`; the admin embed only when `SUPERAI_WEB_ENABLE_CLIPROXY_ADMIN=1`. Tests assert both. |
| C2 | **Writes never touch repo-tracked config.** Target `~/.superai/config.json` and `~/.superai/config/models.json` only — never `config/models.json` in the repo. |
| C3 | **Separate management token.** `SUPERAI_WEB_MANAGEMENT_TOKEN` gates every write route plus `/api/audit`, required unconditionally *including on loopback*. Distinct from the existing `SUPERAI_WEB_TOKEN`. |
| C4 | **`.gitattributes` lands in its own commit BEFORE any vendored bytes.** Same-commit is too late — CRLF corrupts on replay and it is invisible on a fresh clone. |
| C5 | **Own worktree, fork from `origin/master`.** ~10 other sessions have branches checked out here. Local `master` is not trustworthy. Commit every increment. |
| C6 | **Set `PYTHONPATH` when testing from a worktree**, or you test the main working copy's source instead of your own. |
| C7 | **No new runtime dependency.** The `[web]` extra stays `fastapi` + `uvicorn`. `/console` is server-rendered vanilla JS, matching the existing `/dashboard` page. |

## Working agreement for agents

- **Update [`TASKBOARD.md`](TASKBOARD.md) as you go** — set `[~]` when you start,
  `[x]` when acceptance criteria pass, `[!]` when blocked externally. Add a
  one-line note in the task's Log section with the date and what you did.
- **One commit per task minimum.** Conventional-commit style, matching repo
  history: `feat(web): ...`, `test(web): ...`, `docs(web): ...`, `chore(vendor): ...`.
- **Do not mark a task `[x]` without running its stated verification command**
  and pasting the real result into the task file's Log. A passing self-assessment
  is not evidence.
- **If a task turns out to be wrong or unimplementable as written, say so in the
  task file and mark it `[?]`** — do not silently redesign it. Per `AGENTS.md`,
  accurate status is always in scope.
- **Blocked on a decision?** The open questions are listed in `TASKBOARD.md`
  under "Decisions needed from owner". Do not guess flag names or pin versions.

## Layout

```
projects/webui-management-center/
├── README.md      ← you are here
├── PLAN.md        ← full design, options analysis, security, architecture
├── TASKBOARD.md   ← status board; update this
└── tasks/
    ├── T01-worktree-baseline.md
    ├── ...
    └── T16-docs.md
```
