# agent-doctor

Diff-aware quality gate for AI-assisted code changes.

```sh
npx -y agent-doctor@latest .
```

`agent-doctor` reads the diff, builds a risk model, discovers the cheapest relevant validations, audits agent instructions and skills, ingests available evidence, and prints a report that is useful locally and in CI. It does not claim an agent was "safe" — it tells you what was proven, what was not proven, and what to run next.

> Status: 0.x. MVP focuses on TypeScript / JavaScript monorepos and skill-library checks. Full plan in [`docs/PLAN.md`](docs/PLAN.md).

## Install

Per-run, no install:

```sh
npx -y agent-doctor@latest --diff main --plan-only
```

Global:

```sh
npm install -g agent-doctor
agent-doctor --diff main --plan-only
```

## Quick start

```sh
agent-doctor --diff main --plan-only      # print the validation plan
agent-doctor --diff main --run            # run discovered checks
agent-doctor --diff main --run --fail-on error --json > report.json
```

## What it checks

- **Risk classification** of the diff: public API, schema/migration, auth, payments, UI, deps, generated, agent instructions, CI/build, large refactor.
- **Validation plan** scoped to the affected packages — runs cheap checks first, escalates with risk.
- **Skill audit** for `AGENTS.md`, `CLAUDE.md`, `.codex/skills/**/SKILL.md`, `.agents/skills/**/SKILL.md`, `.claude/**`, and Cursor rules — frontmatter, broken references, oversized skills, unguarded destructive commands.
- **Evidence-first diagnostics** — every finding is tied to a file, diff, command exit, CI log, transcript event, or artifact, or is explicitly marked as missing evidence.

## Profiles

- `local` — fast, advisory, no hard fail by default.
- `ci` — blocks on required checks and broken references.
- `release` — broader build/test/browser evidence for high-risk diffs.
- `skill-library` — strict skill linting, rendered-artifact sync, token budget, references.

## Configuration

`agent-doctor.config.json` at repo root. See [`docs/CONFIG.md`](docs/CONFIG.md).

## License

Apache-2.0
