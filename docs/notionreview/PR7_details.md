# PR 7 — `AGENTS.md` accuracy, and the retraction that produced it

**PR:** https://github.com/realburhanhusain/SuperAI/pull/7
**Branch:** `docs/agents-md-accuracy` → `master`
**Files:** `AGENTS.md`
**Status:** open. Two rewordings need an owner ruling, not just a merge.

---

## Why this PR exists: a retracted finding

Every earlier version of the review backlog claimed `AGENTS.md` contained **four obfuscated prompt-injection payloads**. It was recorded at **P0**, marked **human-only**, and — once the `approve_callback` finding was retracted — promoted to *"the highest-severity item on the list that nobody has started."*

**That claim was false.** The file has now been read end to end. There are no obfuscated blocks, nothing encoded, nothing smuggled. It is an ordinary contributor guide: canonical path, taskboard workflow, scope rules, environment, package layout, commit conventions.

**How it survived a full day at the top of a P0 list:** the claim was made without reading the file, then repeated *because* the file had been labelled untrusted. The label became the reason not to check the label. The recommendation "do not touch this, only a human can" made it worse by dressing an evidence gap as a safety measure — it looked responsible, so nobody, including me, went looking.

This is the second retraction in the review, and it shares a root cause with the first: a candidate worth checking was restated as a confirmed finding without the check.

**Consequences for anyone who read the old version:** there is no security incident. Nothing to quarantine, no access audit, **no credentials to rotate** on account of this file. Those sub-items are struck, not deferred.

## What is actually wrong — the five defects this PR fixes

### 1. Wrong entry point (a live bug, not a typo)

```
Entry point: superai = "scli.main:app"
```

`pyproject.toml` correctly declares `scli.main:main`. `main()` wraps the Typer app and adds the M080 exit-code mapping; a console script pointed at `app` silently loses it, so failures exit `0`. A CI job or shell wrapper checking the exit status would read failure as success.

This file is the **origin** of the "docs reference the wrong entry point" hygiene item. Fixed, with a note explaining why `main` rather than `app`, so it does not quietly regress.

### 2. Self-contradicting package layout

The layout block showed `src/superai/cli/main.py`; two lines later the file stated the real folders are `src/cli` + `src/core`. Only the second was true. Corrected, and the `pyproject.toml` mapping is now stated explicitly.

### 3. Approval wording contradicted PR #1

```
Work autonomously through the plan; do not stop for approval between planned items
```

`AGENTS.md` is read by coding agents **by design**, and PR #1 exists specifically to close an approval fail-open. As written, this reads as general licence to push past approval.

It does not defeat the gate — `dispatch_tool` still denies without an approver — so this is not a vulnerability. It is worse in a slower way: documentation that contradicts a security control is how that control gets argued away six months later by someone who reads the doc and not the code.

Reworded so the autonomy explicitly covers **planning and sequencing**, while individual side-effecting actions still take the normal approval path every time.

### 4. Scope rules forbade honest reporting

```
Features are never optional. Do not label plan work as optional, nice-to-have, or cancelled.
```

The intent is legitimate and clear: stop agents quietly dropping scope. The literal effect on an agent is a standing instruction not to tell the owner that something is unnecessary or unimplementable as specified.

Rewritten to preserve the actual guarantee — only the owner removes scope, nothing gets silently dropped — while making reporting explicitly exempt. Accurate status is always in scope, including "this cannot be done as written."

The archive rule received the same treatment: reading an archived doc for evidence is now explicitly allowed; treating it as current is not.

### 5. Hardcoded personal path

The canonical path was `C:\Users\<name>\Documents\Personal\github\SuperAI`, alongside sibling trees that exist on exactly one machine. Replaced with a repo-relative reference; the siblings are now described as not expected to be present.

## Also added

- A header stating plainly that the file sets conventions but **grants no permissions**, and that where guidance conflicts with a security control, **the control wins and the conflict is a bug in this file**.
- A rule distinguishing **"written" from "verified"** — the exact failure mode that runs through this whole review, including the retracted claim above.
- A closing rule to treat repository and retrieved content as **data, not instructions**, which is the principle PRs #2 and #6 implement in code.
- Pointers to `docs/THREAT_MODEL.md` and `docs/notionreview/`.

## What happens if this is not merged

The entry-point error stays in the file most likely to be copied from, and the next person wiring a console script inherits silent `0` exits on failure. The approval wording stays available as justification for skipping approval. Neither is urgent; both are cheap now and irritating once something has been built on them.

## Risk

None to runtime. One Markdown file; no code, config or test touched. No Python, so the `test` job is unaffected.

The real risk is editorial: **sections 3 and 4 change the meaning of instructions the owner may have written deliberately.** If the original intent was stricter than the rewrite, it should be narrowed. That is a judgement call and is recorded as an open decision rather than assumed settled.

## Verification

- `AGENTS.md` was read in full before editing — which is the entire point of this PR.
- Nothing to execute.
- **Not verified:** whether `TASKBOARD.md`, `TASKBOARD_GROK.md`, `TASKBOARD_AGY.md`, `implementation_plan_detailed.md`, `implementation_plan_v2.md`, `codes.md` and `scripts/checkpoint.ps1` still exist. Those references are carried over unchanged and **no claim is made either way**. Checking them is a separate cleanup — recorded as such rather than silently assumed fine.
