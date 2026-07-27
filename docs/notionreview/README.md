# notionreview

External review documentation for `realburhanhusain/SuperAI`.

## Naming convention

| File | Scope | Lifecycle |
| --- | --- | --- |
| `notionreview_actionitems.md` | Rolling backlog of outstanding review findings across all reviews | Living document — update as items are completed |
| `PR<N>_details.md` | Rationale for exactly one pull request | Written once when the PR is opened; amended only if the PR itself changes |

One `PR<N>_details.md` per pull request, where `<N>` is the GitHub PR number. Never combine multiple PRs into one file, and never reuse a number.

### What belongs in a `PR<N>_details.md`

For each change in the PR:

1. **What was there** — the code or config before, quoted verbatim.
2. **Why it was picked** — the specific defect, and why it cleared the bar for inclusion.
3. **What happens if it is not implemented** — the concrete failure mode, not a generic warning.
4. **Risk of the change itself** — what could break, and what callers should check.
5. **Verification** — the tests or commands that prove it.

Also include, at PR level: the selection criteria used, what was deliberately excluded and why, and any findings withdrawn during review. Recording withdrawn findings is not optional — it is what makes the rest of the document trustworthy.

## Index

| File | Subject |
| --- | --- |
| [`notionreview_actionitems.md`](./notionreview_actionitems.md) | Outstanding action items (P0–P2) from the 27 Jul 2026 deep review |
| [`PR1_details.md`](./PR1_details.md) | [PR #1](https://github.com/realburhanhusain/SuperAI/pull/1) — harden agent shell execution, fail-closed sandbox, config hygiene |
