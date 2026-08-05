---8<--- BEGIN PROMPT ---8<---

Pick up and implement an existing, fully specified project in the SuperAI repo.
The plan, the taskboard and 16 detailed task files already exist and are pushed.
Your job is to execute them, not to redesign them.

## Repo and branch

- Repo: `C:\Users\burhan.husain\Documents\Personal\github\SuperAI`
- The project is **merged into `master`** — start from `master`, which is the
  current tip. (The original branch `feat/webui-management-center` still exists
  on `origin` but is now behind `master`; do not start from it.)
- Project folder: `projects/webui-management-center/`
- Create your own working branch off `master`, e.g. `feat/webui-mc-<yourtool>`.

**Work in your own git worktree. Do not work in the main working copy.** This
repo has ~10 branches checked out by other AI sessions; one of them running
`git pull --rebase` in the main copy has previously hard-reset the tree and
destroyed another session's uncommitted work.

```powershell
cd C:\Users\burhan.husain\Documents\Personal\github\SuperAI
git fetch origin
git worktree add C:\tmp\superai-webui-<yourtool> -b feat/webui-mc-<yourtool> master
cd C:\tmp\superai-webui-<yourtool>
```

**Then set PYTHONPATH before running any test**, or you will silently test the
main working copy's source instead of your own — this has already caused six
tests to pass against the wrong tree:

```powershell
$env:PYTHONPATH = "C:\tmp\superai-webui-<yourtool>\src"
python -c "import core.config as c; print(c.__file__)"   # must print YOUR worktree path
```

## Read these first, in this order

1. `AGENTS.md` (repo root) — repo-wide conventions for AI agents.
2. `projects/webui-management-center/README.md` — constraints C1–C7 and the
   working agreement. **Binding.**
3. `projects/webui-management-center/TASKBOARD.md` — task list, dependencies,
   settled decisions, and a "Verified facts" section with ~20 `file:line`
   citations. Trust those citations; do not spend time re-deriving them.
4. `projects/webui-management-center/PLAN.md` — the full design and, importantly,
   *why* the obvious approach was rejected.
5. The specific `tasks/T##-*.md` file for whatever you are doing.

## What the project is

Give SuperAI a browser UI for configuration editing and runtime status
monitoring. Two parts:

1. **SuperAI-native pages and endpoints** added to the *existing* FastAPI app at
   `src/cli/web_app.py` (already has ~31 routes and a `superai web` command).
2. **The MIT-licensed CLI Proxy API Management Center** (`management.html`),
   vendored **unmodified** and served at `/cliproxy-admin` as an operator console
   for the separate, optional CLIProxyAPI process.

**Do not fork or rebuild that React UI, and do not add a Node/Bun toolchain to
this Python repo.** That option was evaluated and rejected in `PLAN.md`; the new
pages are server-rendered vanilla JS matching the existing `/dashboard` page.
**Do not build a reverse proxy** from SuperAI to the proxy's `/v0/management` —
the browser talks to it directly, so SuperAI never handles the proxy's
management key.

## How to work

- Take the highest-priority `[ ]` task whose dependencies are all `[x]`. Start
  at **T01**, then T02–T05 (wave W1). Waves are ordered deliberately: the config
  hardening tasks T06/T07/T08 must land *before* T09, the first endpoint that
  writes config over HTTP.
- Work autonomously through the tasks. Do not stop for approval between planned
  items. (Individual side-effecting actions still go through your normal tool
  approval path.)
- **Update `projects/webui-management-center/TASKBOARD.md` as you go:** `[~]`
  when you start, `[x]` when done, `[!]` if blocked externally, `[?]` if the
  task is wrong. Also update the Log table and the "Last session" line.
- **Only mark `[x]` after running that task's stated verification command and
  pasting its real output into the task file's Log section.** A passing
  self-assessment is not evidence.
- One commit per task minimum. Conventional-commit style matching repo history:
  `feat(web): ...`, `test(web): ...`, `docs(web): ...`, `chore(vendor): ...`.
  Commit every increment — uncommitted work in this repo is genuinely at risk.
- Push your own branch to `origin`. **Do not push to `master`** and do not open a
  PR unless asked — `master` carries unpushed commits from several other sessions,
  so pushing it would publish work that is not yours. Verify a push with
  `git ls-remote`, not with the push command's own output.

## Hard rules (from README.md — do not violate)

1. **Additive and opt-in.** Default `superai web` behaviour must not change.
   Config-write routes are registered only when
   `SUPERAI_WEB_ENABLE_CONFIG_WRITE=1`; the admin embed only when
   `SUPERAI_WEB_ENABLE_CLIPROXY_ADMIN=1`. Tests assert both.
2. **Writes never touch repo-tracked config.** Target `~/.superai/config.json`
   and `~/.superai/config/models.json` only — never `config/models.json` in the
   repo.
3. **`SUPERAI_WEB_MANAGEMENT_TOKEN`** gates every write route and `/api/audit`,
   required unconditionally *including on loopback*. It is separate from the
   existing `SUPERAI_WEB_TOKEN`, which is not extended to writes. These names are
   owner-approved — do not rename them.
4. **Do not add a root `.gitattributes`.** `vendor/.gitattributes` already
   contains `* -text` covering `vendor/` recursively. This was explicitly decided
   and closed; re-opening it would repeat a mistake already made and corrected.
5. **No new runtime dependency.** The `[web]` extra stays `fastapi` + `uvicorn`.
6. Report status accurately. If a task is wrong, unimplementable as written, or
   already obsolete, say so plainly in the task file and mark it `[?]` — do not
   silently redesign it and do not claim coverage you have not proven.

## Testing notes

- Follow the pattern in `tests/test_pref_tt_web.py:48-60` (FastAPI `TestClient`,
  `pytest.importorskip`, `monkeypatch.setattr(Path, "home", ...)` to sandbox
  `~/.superai`). Put new tests in `tests/test_web_management_center.py`.
- **Trap:** `monkeypatch.setattr(Path, "home", ...)` does **not** isolate code
  that calls `os.path.expanduser`, which reads the environment directly. Check
  which mechanism the module under test uses. This exact mismatch caused tests to
  write to the real user store and hang CI in this repo before.
- Tests must not require a running CLIProxyAPI. Block sockets — an existing test
  in this repo does exactly that; copy its approach.

## Open item

**Q4** — whether `scripts/vendor_sync.py` handles HTML entries, or needs a small
extension. Resolve it inside T14 by testing, not by asking. Prove the integrity
check is real: corrupt one byte, confirm `--check` fails, restore, confirm it
passes. An entry the checker silently skips is worse than no entry.

## When to stop and ask

Stop if you hit something the plan does not cover, if a task's premise turns out
to be false, or if you would need to violate one of the hard rules to proceed.
Say what you found and why it blocks you. Everything else: keep going.

Start by reading the five documents listed above, then execute T01.

---8<--- END PROMPT ---8<---
