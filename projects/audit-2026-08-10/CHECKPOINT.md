# SuperAI — Audit Checkpoint

**Created:** 2026-08-10 ~14:50 (Riyadh)
**By:** Claude Code (Opus 5)
**Purpose:** draw a line. Everything at or before this point is covered by the
existing audit. Everything after it gets its own report and correction plan.

---

## ✅ RE-BASELINED — development paused, master is stable

**Update, later on 2026-08-10.** Development in the other session was paused.
Master settled at:

```
545745d  15:03  feat: add light theme and i18n support inspired by vben-admin
behind=0 ahead=0 — fully pushed
```

**Two commits landed after the checkpoint, and both are frontend-only:**

| Commit | Files | Insertions |
|---|---|---|
| `7547751` 14:59 embed it-tools into dashboard | `console/index.html` | 15 |
| `545745d` 15:03 light theme + i18n | `console/{app.js,index.html,styles.css}` | 56 |

`git diff audit-checkpoint-20260810..HEAD` = **3 files, 71 insertions, 1
deletion**, all under `src/cli/static/console/`. **No new routes, no new MCP
tools, no new imports** — verified by grepping the diff for `@app.get|@app.post`,
`_tool(`, and `from core.`.

**Therefore these two commits introduce no new backend defects, and no separate
audit report is warranted for them.** They are folded into the existing audit,
and **the correction plan targets `545745d`**, not `c5d33f5`.

The tag stays at `c5d33f5` as the provenance record of what was audited
line-by-line; every finding was **re-verified at `545745d`** and holds
identically:

| Measurement | At `c5d33f5` | At `545745d` (current) |
|---|---|---|
| MCP tools / unclassified | 28 / 3 | **28 / 3** — unchanged |
| CLI names / hijacked | 207 / 192 | **207 / 192** — unchanged |
| Shadowed `/api/*` GET routes | 14 | **14** — unchanged |
| `/openapi.json` | 500 | **500** — unchanged |
| `/council`, `/cliproxy-admin` | 404, 404 | **404, 404** — unchanged |
| `/dashboard` handlers | 2 | **2** — unchanged |
| `chrome_profile.py` committed? | no | **still untracked** — ImportError live on origin |
| Test suite | 7 failed / 1184 passed | **6 failed / 1185 passed** (16m49s) |

### The definitive suite baseline at `545745d`

```
6 failed, 1185 passed, 1 warning in 1009.60s (0:16:49)

FAILED tests/test_surface_inventory.py::test_mcp_tools_are_all_safety_classified
FAILED tests/test_foundation_complete_must.py::test_mcp_safety_matrix
FAILED tests/test_foundation_complete_must.py::test_dashboard_and_top30_and_mcp_parity
FAILED tests/test_agy_i1_residuals.py::test_mcp_safety_matrix_exhaustive
FAILED tests/test_m079_m027_m093.py::test_m093_safety_matrix_and_live_block
FAILED tests/test_payload_rules.py::test_interceptor_chain_init - assert 6 == 3
```

**Five of the six are one defect** — the 3 unclassified MCP tools. Fixing
C6.1 takes the suite to **1 failure**; fixing C1.1 as well takes it to **zero**.

**Correction to an earlier finding.**
`test_code_intelligence_n258.py::test_corrupted_cache_recovery` failed in the
AGY-snapshot run but **passes here**, on a tree that differs only by two
frontend commits. It is therefore most likely **flaky, not a regression** — but
one pass does not prove that any more than one failure proved a defect. It
needs a repeat run to characterise, not a code fix. C6.2 is re-scoped
accordingly.

**The implementation plan can now be written against a fixed target.**

---

## The boundary

```
git tag: audit-checkpoint-20260810      (annotated, LOCAL ONLY — not pushed)
commit : c5d33f5  2026-08-10 14:50:08 +0300
         feat: add skillx marketplace search to MCP tools
branch : master   (behind=0, ahead=0 — fully pushed to origin)
```

**Remove the tag with** `git tag -d audit-checkpoint-20260810` if unwanted. It
was created locally and deliberately not pushed, so it cannot affect anyone
else's clone.

### Explicitly OUTSIDE the checkpoint (untracked at the boundary)

These existed in the working tree at checkpoint time but are in **no commit**,
so they belong to the *next* audit, not this one:

| Path | Status |
|---|---|
| `src/core/chrome_profile.py` | untracked — **but imported by committed code**, see below |
| `find_path.py`, `find_path2.py` | untracked scratch |
| `temp_*/`, `CLIProxyAPI*/`, `smoke_out.json` | untracked scratch/vendor dumps |

At the boundary there were **zero modified tracked files** — the tree was clean
apart from untracked paths (`git diff` fingerprint `e3b0c442…` = empty).

---

## What this checkpoint covers

| Document | Scope |
|---|---|
| `SUPERAI_AUDIT_FINAL_20260810.md` | Parts 1–8; all boards, the scorecard, functional correctness, AGY's 14:36 commit |
| `SUPERAI_CORRECTION_PLAN_20260810.md` | Waves C0–C6, 24+9 items, ≈15–18 h |
| `SUPERAI_AUDIT_EXTENDED_20260810.md` | superseded — merged into Part 6 |

**33 defects**, all in committed history and all **now pushed to origin**:

| Severity | Count |
|---|--:|
| CRITICAL | 6 |
| HIGH | 13 |
| MEDIUM | 11 |
| LOW | 3 |

---

## Two findings that landed AFTER Part 8 was written

Both are at commit `c5d33f5` and are **included in this checkpoint** (they
happened before the line). Recording them here so they are not lost between
documents.

### 1. The MCP classification regression is compounding — 1 → 3

| Point in time | Registered tools | Unclassified |
|---|--:|---|
| HEAD `6b798ff` (audit pin) | 25 | **0** |
| `b5d74d8` (14:36) | 26 | 1 — `superai_websearch` |
| `c5d33f5` (14:50) | **28** | **3** — `superai_websearch`, `superai_skillx_search`, `superai_chrome_profile` |

Two commits, fourteen minutes, three unclassified tools. `C6.1` in the
correction plan must now classify **three**, not one.

### 2. A committed import of an uncommitted module — the §3.5 risk realised

`src/core/mcp_server.py:711` (committed, pushed):

```python
from core.chrome_profile import open_url_in_profile
```

`src/core/chrome_profile.py` is **untracked**. Proven from the git object
database, which is the only authority that is not fooled here:

```
git cat-file -e c5d33f5:src/core/chrome_profile.py   → ABSENT from commit
git ls-files --error-unmatch  …/chrome_profile.py    → UNTRACKED
git ls-tree origin/master src/core/ | grep chrome_profile → 0 files
```

**Any fresh clone of `origin/master` raises `ImportError` when the
`superai_chrome_profile` MCP tool is invoked.** This is exactly the failure
mode flagged in audit §3.5 and correction item C5.1 — it has now happened, on
the remote.

**⚠ Methodology warning that produced a false negative, and must not be
repeated.** My first check reported `IMPORT OK` for `core.chrome_profile` in a
clean clone. That was wrong. SuperAI is installed in this environment as an
**editable install** whose meta-path finder maps the package name straight at
the live working tree:

```
site-packages/__editable___superai_0_1_0_finder.py
  MAPPING = {'core': 'C:\...\github\SuperAI\src\core',
             'scli': 'C:\...\github\SuperAI\src\cli'}
```

A meta-path finder **overrides `sys.path`**, so filtering `sys.path` does not
isolate it. Any import-based check on this machine can silently resolve to the
developer's live tree instead of the tree under test.

**Rule for future audits: verify module presence with `git cat-file` /
`git ls-files`, never with `import`.**

---

# Procedure for the next audit (post-checkpoint)

Reusable. Produces `SUPERAI_AUDIT_<YYYYMMDD>.md` and
`SUPERAI_CORRECTION_PLAN_<YYYYMMDD>.md`.

## Step 0 — Pin and isolate

```bash
cd /c/Users/burhan.husain/Documents/Personal/github/SuperAI
git fetch --all
NEW=$(git rev-parse --short HEAD)          # record it; HEAD moves every ~15 min
git log --oneline audit-checkpoint-20260810..$NEW      # the delta to audit
git diff --stat audit-checkpoint-20260810..$NEW

# ALWAYS audit a clone, never the shared worktree (~40 concurrent worktrees)
git clone <repo> <scratch>/superai-audit && cd $_ && git checkout $NEW
export PYTHONPATH="$PWD/src" HOME="$PWD/_fh" USERPROFILE="$PWD/_fh"
```

Isolating `HOME`/`USERPROFILE` matters: several modules use
`os.path.expanduser`, which reads the environment and ignores a monkeypatched
`Path.home` — the documented cause of a past CI hang.

## Step 1 — The three checks that found the most, per minute spent

```bash
# 1. Committed code importing uncommitted modules  (found the chrome_profile bug)
for m in $(git diff --name-only audit-checkpoint-20260810..HEAD | grep '^src/core/.*\.py$' | xargs -n1 basename | sed 's/\.py//'); do
  git cat-file -e HEAD:src/core/$m.py 2>/dev/null || echo "UNCOMMITTED but referenced: $m"
done

# 2. Registry drift — the repo's own self-audit
python -c "from core.mcp_safety import safety_matrix; m=safety_matrix(); print(m['message'])"
#    expect: unclassified=0, ghost_spend=0, unmapped=0

# 3. Route shadowing — a catch-all registered before literal routes
python -c "
from cli.web_app import create_app; import re
r=[(getattr(x,'path',''),sorted(getattr(x,'methods',None) or [])) for x in create_app().routes]
i=[n for n,(p,_) in enumerate(r) if '{' in p and p.startswith('/api/')]
print('shadowed:',[p for p,m in r[min(i)+1:] if re.fullmatch(r'/api/[a-z0-9_-]+',p) and 'GET' in m] if i else 'none')"
```

## Step 2 — Functional battery

```bash
# every module imports
python -c "import pkgutil,importlib,core,cli
[importlib.import_module(m.name) for pkg in (core,cli) for m in pkgutil.walk_packages(pkg.__path__, pkg.__name__+'.')]"

# every CLI surface renders help  (via the app object)
# AND through the real entry point main() — these differ; see T28
python -m pytest tests/ -q -p no:randomly --timeout=180     # ~15 min
python -c "from core.contract_registry import invoke_top30_offline as f; print(f()['message'])"
```

Baselines to compare against:

| Metric | At checkpoint `c5d33f5` |
|---|---|
| Modules importing | 260+ / 0 failures |
| Test suite | **7 failed, 1184 passed** (14m50s) |
| MCP tools / unclassified | 28 / **3** |
| TOP_30 | help 30/30, contracts 30/30 |
| `/openapi.json` | **500** (pre-existing) |
| Shadowed `/api/*` GET routes | **14** under config-write |
| CLI names hijacked by T28 | **192 of 207** |

A future run that shows *fewer* failures means the correction plan is landing.
More means new regressions — diff against this table first.

## Step 3 — Claims vs reality

```bash
# scorecard self-contradiction (found 3 falsified host gates)
python - <<'PY'
import re
t=open('docs/V1_V6_UNIFIED_IMPROVED_SCORECARD.md',encoding='utf-8').read()
bad=[b.split('\n')[0] for b in t.split('\n### ')[1:]
     if '**Complete?** **YES**' in b
     and (m:=re.search(r'\*\*Still incomplete:\*\*\s*(.+)',b))
     and m.group(1).strip() not in ('—','-','')]
print(f'self-contradicting entries: {len(bad)}'); [print(' ',x[:70]) for x in bad]
PY

# board leaf-vs-header (the check AGY was demoted by on 2026-07-29)
# header marked [x]/DONE above unticked leaves == false completion
```

Then, for every task marked `[x]` in the delta, prove a **call path from a
user-facing entry point** — not file existence. Import-present-but-never-called
is the stub signature that produced T27, T29, and three unreferenced AGY
modules.

## Step 4 — Write up

- Report: `SUPERAI_AUDIT_<YYYYMMDD>.md` — carry forward unresolved items from
  this checkpoint by ID rather than re-deriving them.
- Plan: `SUPERAI_CORRECTION_PLAN_<YYYYMMDD>.md` — same wave structure.
- State the evidence standard explicitly: *executed* vs *evidence-integrity
  only*. Never estimate "what fraction works" from a sample.

---

## Carried forward — open at this checkpoint

None of the 33 defects were fixed as of `c5d33f5`. The next audit should
re-check these first, since a fix elsewhere may have resolved them:

**CRITICAL**
1. `/api/{resource}` catch-all shadows 14 GET endpoints (C0.1)
2. T28 hijacks 192 of 207 CLI names (C0.2)
3. Scorecard completion is a hardcoded ID list (C5.2)
4. Scorecard evidence is generated prose — 267 of 282 (C5.2)
5. 3 falsified host gates → HOST-GATED reported as 0 (C0.3)
6. **3 unclassified MCP tools** (C6.1 — was 1, now 3)

**HIGH** — T15 never implemented; T16 docs describe absent features;
`/api/sync/cliproxy` auth bypass; AI Council 404; suite failing (now 7);
T27 tray unreachable; T29 dead duplicate; chat-relay `[x]` unproven;
`/openapi.json` 500; `oauth_manager` non-functional; `agent_launcher` wrong
port; `client_keys` plaintext/no-lock; **committed import of uncommitted
`chrome_profile`** (new — C5.1/C6.9)

**MEDIUM/LOW** — see report Parts 7–8.

---

## Standing risks that shaped this audit

1. **Parallel sessions write constantly.** `HEAD` moved three times during this
   audit (`6b798ff` → `b5d74d8` → `c5d33f5`), twice mid-write. Always re-check
   `git log -1` before stating what HEAD is, and audit a clone.
2. **The editable install fools import checks** — use git, not `import`.
3. **Everything is pushed.** `ahead=0`: all 33 defects are on `origin/master`,
   so fixes are corrections to published history, not local cleanup.
