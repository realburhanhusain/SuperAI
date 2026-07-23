# SuperAI Memory Roadmap — Cognee-class gaps 1–8

**Status:** **P1–P8 shipped (end-to-end)** — Cognee gaps 1–8 closed under SuperAI  
**Date:** 2026-07-23  
**Repo tip at drafting:** `6035caa` (master)  
**P1 land:** `core.knowledge_graph` + `superai kg` + MCP `superai_kg_*` + docs/tests  
**P2 land:** `core.cognify` + `superai cognify` + MCP `superai_cognify` + docs/tests  
**P3 land:** `core.session_memory` + `superai memory-session` + MCP `superai_session` + docs/tests  
**P4 land:** `core.recall_router` + `superai recall` + MCP search strategies + docs/tests  
**P5 land:** `core.ingest` + `superai ingest` + MCP `superai_ingest` + docs/tests (text/md/jsonl/pdf/url)  
**P6 land:** `core.ontology` + `data/memory_ontology.yaml` + `superai ontology` + MCP `superai_ontology` + cognify mapping  
**P7 land:** `core.memory_dataset` + `superai dataset` + MCP `superai_dataset` + palace/recall isolation  
**P8 land:** `core.session_capture` + `superai capture` + MCP `superai_capture` + tool post-hooks  
**Coordination:** Parallel AGY work on V1–V6 scorecard — keep file touch sets disjoint.  
**Compare-to:** [Cognee](https://github.com/topoteretes/cognee) (open-source agent knowledge-graph memory)  
**Baseline SuperAI:** `MemoryPalace` (vectors + wings/rooms) + `LearningEngine` (promote / conflict / distill) + central write-back + MCP tools  
**Related:** `docs/MEMORY_PALACE_GAPS.md` (closed wings/rooms/concurrency work — keep; this roadmap is the *next* arc)

---

## What is an “architecture spike”? (plain language)

You asked for more detail on this phrase. Here it is in everyday terms.

### Short definition

An **architecture spike** is a **time-boxed, throwaway-or-small experiment** whose job is to **answer hard design questions** *before* you build the full product feature.

It is **not** the final implementation. It is a **scout mission**.

### Why do one?

For memory/graph work, wrong schema or wrong query shape is expensive to reverse later. A spike answers:

| Question type | Example |
|---------------|---------|
| **Feasibility** | Can we store entities+edges in the same Postgres we already use for pgvector? |
| **Performance** | Is 2-hop graph expansion acceptable offline on SQLite? |
| **API shape** | Should hybrid recall be one function or three CLI commands? |
| **Risk** | Does LLM entity extraction quality justify the cost on banking docs? |
| **Integration** | Can cognify write without breaking existing `MemoryPalace.store` contracts? |

### What a spike produces

1. **A short design note** (1–3 pages): options considered, recommended option, rejected options + why  
2. **A tiny prototype** (optional): a few hundred lines, tests that prove the hard part works  
3. **A go / no-go / pivot decision** for the real build  
4. **Explicit non-goals** so the spike doesn’t turn into the full product

### What a spike is *not*

| Not a spike | Why |
|-------------|-----|
| Polished UI | That’s product work after decisions |
| Full multi-backend support | Spike picks *one* path first |
| Scorecard “100% complete” | Spike deliberately incomplete |
| Permanent schema with no migration plan | Spikes may use throwaway tables |

### Typical spike timeline

| Length | When |
|--------|------|
| **0.5–2 days** | Schema + one query path offline |
| **2–5 days** | Cognify extraction quality on real sample docs |
| **Stop rule** | When the decision is clear *or* time box ends — write the note either way |

### How this roadmap uses spikes

Each **Phase 0.x** below is a spike. **Phase 1+** is production build only after the spike decision is written down.

```text
  Gap idea
     │
     ▼
  Spike (time-box) ──► Design note + go/no-go
     │
     ├─ No-go / pivot ──► revise roadmap
     │
     └─ Go ──► Implement (code + docs + tests) ──► honest scorecard
```

---

## Goals and non-goals

### Goals

1. Close Cognee-class **gaps 1–8** without throwing away SuperAI’s palace metaphor or learning lifecycle.  
2. Keep **offline-first** honesty (SQLite/hash embeddings work without live LLM when possible).  
3. Prefer **Postgres-first** multi-session safety (same policy as current Memory Palace).  
4. Ship in **vertical slices**: each phase is usable alone.

### Non-goals (this roadmap)

- Replacing SuperAI with Cognee as the product shell  
- Full Neo4j/Weaviate matrix in v1 (optional later; spike may say “Postgres only”)  
- Managed “SuperAI Cloud Memory”  
- Claiming BEAM SOTA benchmarks before we have an eval harness  
- Silent Postgres install (existing install policy stays)

### Design principle

> **Memory Palace stays the UX.**  
> Graph + cognify + session layers are **subsystems under the palace**, not a second competing product.

---

## Gap map (1–8) → roadmap phases

| # | Gap (from Cognee compare) | Primary phase(s) |
|---|---------------------------|------------------|
| 1 | First-class knowledge graph | **P0.1 spike → P1** |
| 2 | Automatic cognify / ECL pipeline | **P0.2 spike → P2** |
| 3 | Session cache → permanent promotion | **P0.3 spike → P3** |
| 4 | Auto-routed multi-strategy recall | **P4** (needs P1; better after P2) |
| 5 | Multimodal / multi-format ingest | **P5** (builds on P2) |
| 6 | Ontology induction | **P0.4 spike → P6** |
| 7 | Dataset / namespace product model | **P7** (early hooks in P1–P3) |
| 8 | Turn-capture agent lifecycle hooks | **P8** (uses P3 session layer) |

**Also related (out of 1–8 but noted):** OTEL, multi-language clients, managed cloud — **Phase 9+ backlog**, not required to close 1–8.

---

## Current SuperAI baseline (do not rebuild)

| Component | Role |
|-----------|------|
| `MemoryPalace` | Chunk store + embeddings + wing/room + semantic search |
| `LearningEngine` | Task learnings, promote durable, conflict, distill, lifecycle CLI |
| `central_memory` | Multi-CLI write-back + inject |
| `palace_tenant` | Tenant tag isolation |
| MCP `superai_memory_*` | External agent access |
| `memory_gdpr` / TTL | Forget + age cleanup |

Roadmap **extends** these; it does not fork a parallel “Cognee clone” tree.

---

## Phase 0 — Architecture spikes (answer questions first)

### P0.1 — Graph storage spike (Gap 1)

**Time box:** 1–2 days  
**Question:** Where do entities and edges live so hybrid query is simple and offline-safe?

| Option | Pros | Cons |
|--------|------|------|
| **A. Tables in same SQLite/Postgres as palace** | One DSN, one backup, no new service | Graph traversal DIY in SQL |
| **B. Embedded graph (Kuzu/NetworkX file)** | Graph-native queries | Extra dependency, sync complexity |
| **C. External Neo4j** | Industry standard | Ops burden; against “simple local” |

**Spike deliverables:**

- [ ] Prototype tables: `kg_nodes`, `kg_edges` (or equivalent) with CRUD  
- [ ] Seed 20–50 fake banking entities + edges  
- [ ] 2-hop query demo (`entity → related → related`) offline  
- [ ] Design note: pick A/B/C + migration from pure vector memories  
- [ ] Explicit: how wings/rooms map onto graph (e.g. node labels vs properties)

**Exit criteria:** Written recommendation + sample query latency notes.

---

### P0.2 — Cognify extraction spike (Gap 2)

**Time box:** 2–3 days  
**Question:** Can LLM (or rules+LLM hybrid) extract useful entities/relations from *your* real corpora?

**Sample inputs (use real, non-secret where possible):**

- 5–10 SuperAI docs / agent outcomes  
- 5–10 email synthesis summaries (from Outlook backfill)  
- 1–2 DEMO_NARRATIVE / TASKBOARD style work docs  

**Spike deliverables:**

- [ ] Pipeline sketch: text → JSON entities/edges → graph write  
- [ ] Quality scorecard: precision/recall *qualitative* (human spot-check), cost per page  
- [ ] Fail modes: hallucination edges, PII over-extraction, empty docs  
- [ ] Decision: always-on cognify vs opt-in `--cognify`  
- [ ] Mock path: rule-based NER stub so offline tests don’t need API keys  

**Exit criteria:** Go on hybrid extractor + cost budget; or no-go with simpler regex/keyword graph.

---

### P0.3 — Session memory spike (Gap 3)

**Time box:** 1 day  
**Question:** What is a “session memory” unit, and when does it promote?

**Spike deliverables:**

- [ ] Define `session_id` lifecycle (CLI run, agent-tui session, MCP session)  
- [ ] Buffer API: `session_remember` / `session_recall` (in-memory or SQLite table)  
- [ ] Promote rules: end-of-session, importance threshold, user command  
- [ ] Conflict with LearningEngine learnings — one store or two?  

**Exit criteria:** One session model documented; promote triggers listed.

---

### P0.4 — Ontology spike (Gap 6)

**Time box:** 1–2 days  
**Question:** Do we need induced ontologies, or is a **controlled vocabulary** enough for D360/banking?

| Option | When |
|--------|------|
| **Controlled vocab** (manual + wing-aligned types) | Faster, auditable for bank demos |
| **LLM-induced ontology** | Better open-world personal memory |
| **Hybrid** | Core types fixed; soft types allowed with `provisional=true` |

**Exit criteria:** Choose hybrid vs controlled; list core entity types (Person, System, Dataset, Decision, RiskControl, …).

---

## Phase 1 — Knowledge graph foundation (Gap 1)

**Depends on:** P0.1 go  
**Estimated effort:** 1 week  

### Scope

- Production `kg_nodes` / `kg_edges` (or P0.1 chosen schema) behind `core.knowledge_graph`  
- CLI: `superai kg status|node|edge|query|path`  
- MCP: `superai_kg_query` (read), `superai_kg_upsert` (write, permission-gated)  
- Link graph nodes to palace memory ids (`source_memory_id`)  
- Offline tests with hash embeddings / no live LLM  

### API sketch (illustrative)

```text
superai kg upsert-node --type Person --name "Samdani"
superai kg upsert-edge --from N1 --rel WORKS_WITH --to N2
superai kg path --from "Cloud SQL" --to "Policy Tags" --hops 2
superai kg query --type System --name "dataplex-poc-pg"
```

### Definition of Done

- [ ] Code production-usable  
- [ ] Docs: `docs/KNOWLEDGE_GRAPH.md`  
- [ ] Tests: offline graph CRUD + 2-hop path  
- [ ] Does **not** break existing `MemoryPalace.query_semantic`  

---

## Phase 2 — Cognify pipeline (Gap 2)

**Depends on:** P1 + P0.2 go  
**Estimated effort:** 1–1.5 weeks  

### Scope

- `core.cognify` pipeline: ingest text → extract → upsert graph → optional store summary chunk in palace  
- CLI: `superai cognify PATH_OR_TEXT [--dataset D] [--dry-run] [--mock]`  
- Batch mode for directories (markdown first)  
- Audit table: what was extracted, confidence, model used, cost_source  
- Permission mode: plan/ask blocks live extract writes  

### Pipeline (ECL adapted)

```text
  add (raw text / file)
       │
       ▼
  chunk + embed  ──────────────► MemoryPalace (optional full text)
       │
       ▼
  extract (LLM or mock rules)  ► entities, relations, concepts
       │
       ▼
  load  ───────────────────────► Knowledge Graph (+ link to memory ids)
       │
       ▼
  report (counts, conflicts, cost)
```

### Definition of Done

- [ ] Cognify one markdown folder end-to-end offline (mock extract)  
- [ ] Live extract gated by keys + budget  
- [ ] Docs: `docs/COGNIFY.md`  
- [ ] Tests: mock extract → graph edges present  

---

## Phase 3 — Session memory + promote (Gap 3)

**Depends on:** P0.3; prefers P1  
**Estimated effort:** 3–5 days  

### Scope

- Session store: `session_id`, turns, tool traces, TTL  
- APIs: `session_remember`, `session_recall`, `session_promote`, `session_clear`  
- CLI: `superai memory-session …`  
- On promote: write palace chunks **and** optional cognify into graph  
- Integrate with LearningEngine: task outcomes can attach to session  

### Promote policy (default proposal)

| Trigger | Behavior |
|---------|----------|
| Explicit `session promote` | Always |
| Session end (agent-tui / MCP SessionEnd) | Promote items with importance ≥ threshold |
| Mid-session durable mark | User/agent flags “remember this” |

### Definition of Done

- [ ] Session isolated recall works without polluting global palace  
- [ ] Promote creates durable palace entries + optional graph nodes  
- [ ] Docs + offline tests  

---

## Phase 4 — Multi-strategy auto recall (Gap 4)

**Depends on:** P1 minimum; **stronger** after P2–P3  
**Estimated effort:** 3–5 days  

### Scope

- `core.recall_router` strategies:

| Strategy | When |
|----------|------|
| `vector` | Semantic palace query (today) |
| `keyword` | Token/tag match |
| `graph` | Entity name hit → hop expand |
| `hybrid` | Vector seeds + graph expand |
| `session` | Session buffer first, then fall through |
| `auto` | Heuristic router (default for `superai recall`) |

- CLI: `superai recall "…" [--strategy auto|vector|graph|hybrid|session]`  
- MCP: extend `superai_memory_search` with `strategy`  
- Always return **which strategy ran** (honesty)

### Router heuristics (starting point)

| Signal in query | Prefer |
|-----------------|--------|
| “who/what related to/connected” | graph / hybrid |
| “prefer / last time / this session” | session then hybrid |
| Quoted identifiers, ticket IDs | keyword + vector |
| Default | hybrid if graph non-empty else vector |

### Definition of Done

- [ ] Auto strategy never silently invents graph hits  
- [ ] Offline tests for each strategy + auto selection  
- [ ] Docs: strategy table + examples  

---

## Phase 5 — Multi-format ingest (Gap 5)

**Depends on:** P2  
**Estimated effort:** 1 week  

### Scope (ordered)

1. **Markdown / text / JSONL** (already almost free)  
2. **PDF text extract** (pypdf or similar; no OCR in v1)  
3. **URL fetch** (reuse existing SSRF guards)  
4. **Code folder** (language-aware chunking, optional)  
5. **Email export** (JSON from Outlook backfill → cognify)  

### CLI sketch

```text
superai ingest path/to/file.md --cognify
superai ingest path/to/dir --glob "*.md" --dataset d360
superai ingest --url https://... --cognify   # SSRF-safe
```

### Non-goals v1

- OCR images, audio, video  
- Full git history mining (nice later)

### Definition of Done

- [x] At least text + PDF + URL paths with tests (URL mocked)  
- [x] SSRF + workspace jail on file paths  
- [x] Docs: supported formats matrix (`docs/INGEST.md`)  

**Shipped:** `src/core/ingest.py`, CLI `superai ingest`, MCP `superai_ingest`, `tests/test_ingest_p5.py`.

---

## Phase 6 — Ontology layer (Gap 6)

**Depends on:** P0.4 + P1  
**Estimated effort:** 3–5 days (controlled vocab) or longer if LLM-induced  

### Scope (recommended: hybrid)

- Ship **core ontology file**: `src/core/data/memory_ontology.yaml`  
  - Entity types, allowed relations, wing defaults  
- Cognify maps free labels → core types when confidence high; else `provisional`  
- CLI: `superai ontology show|validate|map`  
- Optional later: `ontology induce --from-graph` (LLM, opt-in)

### Core types (starter list for your domains)

| Type | Examples |
|------|----------|
| Person | colleagues, owners, stewards |
| System | Cloud SQL, Dataplex, SuperAI |
| Dataset | BQ datasets, entry groups |
| Decision | architecture choices |
| RiskControl | Policy Tags, DLP findings |
| Project | D360, SuperAI, LifeBrain |
| Document | demos, MRs, emails (as refs) |

### Definition of Done

- [x] Ontology validated in tests  
- [x] Cognify respects allowed edge types (or flags provisional)  
- [x] Docs: ontology governance (who edits types) — `docs/ONTOLOGY.md`  

**Shipped:** `src/core/ontology.py`, `src/core/data/memory_ontology.yaml`, CLI `superai ontology`, MCP `superai_ontology`, cognify integration, `tests/test_ontology_p6.py`.

---

## Phase 7 — Dataset / namespace product model (Gap 7)

**Depends on:** Prefer early hooks from P1; full product in this phase  
**Estimated effort:** 3–5 days  

### Scope

- First-class `dataset_id` on palace memories, graph nodes, sessions  
- Defaults: `personal`, `d360`, `superai`, `scratch`  
- CLI:

```text
superai dataset list
superai dataset create work-uat
superai dataset use d360
superai dataset export d360 -o d360-mem.zip
superai dataset forget scratch --yes
```

- Isolation: queries default to **active dataset** (+ optional `shared`)  
- Align with existing `palace_tenant` (tenant ⊇ multi-user; dataset ⊇ multi-topic)

### Definition of Done

- [x] No cross-dataset leakage in default query mode  
- [x] Export/import one dataset  
- [x] Docs + tests (`docs/DATASETS.md`, `tests/test_memory_dataset_p7.py`)  

**Shipped:** `src/core/memory_dataset.py`, palace store/query + recall scoping, KG `delete_dataset`, CLI `superai dataset`, MCP `superai_dataset`.

---

## Phase 8 — Agent turn-capture hooks (Gap 8)

**Depends on:** P3 session layer  
**Estimated effort:** 1 week  

### Scope

Capture into **session memory** (not always permanent graph):

| Hook point | Capture |
|------------|---------|
| User prompt submit | user text (redact secrets) |
| Tool use result | tool name, summary, paths (not full secrets) |
| Assistant final | answer summary |
| PreCompact | force session snapshot |
| Session end | promote per P3 policy + optional cognify |

### Integration surfaces

1. SuperAI agent-tui / `superai agent`  
2. SuperAI MCP server tools (mirror lifecycle)  
3. Optional later: Claude Code / Grok hooks calling SuperAI MCP  

### Safety

- Never store API keys / raw credentials  
- Respect `permission_mode` and mock honesty  
- Capture level: `off | session | session+promote | full-cognify`  

### Definition of Done

- [x] One end-to-end agent session produces session buffer + promotable items  
- [x] Toggle off works  
- [x] Docs: privacy + storage paths (`docs/SESSION_CAPTURE.md`)  
- [x] Offline tests with fake turn stream (`tests/test_session_capture_p8.py`)  

**Shipped:** `src/core/session_capture.py`, CLI `superai capture`, MCP `superai_capture`, optional `core.hooks` post-tool install.

---

## Cross-cutting requirements (every phase)

| Requirement | Rule |
|-------------|------|
| **Honesty** | Mock/live, cost_source, strategy used — always labeled |
| **Offline tests** | `SUPERAI_MOCK_MODE=1` + hash embeddings path |
| **Budget** | Cognify / live extract go through spend_guard |
| **Permissions** | plan mode cannot mutate graph/session promote |
| **Secrets** | redaction on capture and cognify |
| **Docs + tests** | same SuperAI completion bar as scorecard |
| **Migration** | schema changes versioned; SQLite + Postgres both |

---

## Suggested calendar (aggressive but realistic)

| Week | Focus |
|------|--------|
| **W1** | P0.1–P0.4 spikes + design notes |
| **W2** | P1 knowledge graph |
| **W3** | P2 cognify (mock solid, live optional) |
| **W4** | P3 session + P7 dataset hooks |
| **W5** | P4 auto recall |
| **W6** | P5 multi-format (md/pdf/url) |
| **W7** | P6 ontology hybrid + P8 turn capture |
| **W8** | Hardening, docs polish, optional eval set |

*Single developer part-time: multiply by ~1.5–2.*

---

## Milestones (user-visible)

| Milestone | You can… |
|-----------|----------|
| **M1 Graph live** | Browse entities and 2-hop paths in CLI |
| **M2 Cognify folder** | Point at `docs/` and populate graph |
| **M3 Session promote** | Agent session → durable memory on demand |
| **M4 Smart recall** | One `recall` command that picks strategy |
| **M5 Ingest real work** | PDF + URL + email JSON into memory |
| **M6 Governed types** | Ontology-validated edges for demos |
| **M7 Datasets** | Personal vs D360 isolation |
| **M8 Auto capture** | Sessions remember without manual store |

---

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| LLM extract invents relations | Confidence thresholds, provisional flag, human review CLI |
| Graph + vector drift | Always link `source_memory_id`; re-cognify job |
| Cost explosion | Default mock extract in CI; daily budget on cognify |
| Scope creep to “full Cognee” | Hard non-goals; Postgres-first only until M4 |
| Privacy (email/PII) | Dataset isolation + redact + no default full-cognify on mail |
| SQLite graph slow | Cap hops=2, node limits; Postgres for large graphs |

---

## Decision log (fill during spikes)

| ID | Decision | Date | Owner |
|----|----------|------|-------|
| D1 | Graph backend = **SQLite `kg.sqlite` co-located with palace** (optional Postgres via DSN); not Neo4j/Kuzu for v1 | 2026-07-23 | Grok |
| D2 | Extractor = **hybrid mock rules_v2 + optional LLM JSON**; default CLI `--mode mock`; opt-in not always-on | 2026-07-23 | Grok |
| D3 | Session store = **SQLite `sessions.sqlite`**; promote → palace (+ optional cognify/learning); never auto-bleed to palace | 2026-07-23 | Grok |
| D4 | Ontology mode = _TBD (P0.4)_ | | |
| D5 | Default recall strategy = `auto` (proposed) | 2026-07-23 | draft |

---

## How this relates to “spike an architecture design”

When someone says **“spike an architecture design”** for SuperAI memory, they mean:

1. **Do not** start coding all of P1–P8.  
2. **Do** spend a short fixed time (P0.1–P0.4) to choose:  
   - storage shape  
   - extract approach  
   - session model  
   - ontology approach  
3. **Write** the design note (even if the code is throwaway).  
4. **Then** implement P1+ against that design with full tests/docs.

This file **is** the roadmap.  
The **spikes** are the first concrete work packages inside Phase 0.

---

## Immediate next actions

1. ~~P0.1 / P1 graph~~ **Done**  
2. ~~P0.2 / P2 cognify~~ **Done**  
3. ~~P0.3 / P3 session~~ **Done**  
4. ~~P4 multi-strategy recall~~ **Done**  
5. ~~P5 multi-format ingest~~ **Done**  
6. ~~P6 ontology hybrid~~ **Done**  
7. ~~P7 datasets / namespaces~~ **Done**  
8. ~~P8 agent turn capture / SessionEnd~~ **Done**  
9. ~~Offline eval harness (P1–P8)~~ **Done** — `superai memory-eval` / `docs/MEMORY_EVAL.md`  
10. Optional later: host hooks → SuperAI capture MCP; Phase 9+ (OTEL/multi-client) if requested  
11. AGY scorecard remaining open items are **AGY-owned** (see Hardening Wave on TASKBOARD)  

---

## Appendix — CLI surface target (end state)

```text
superai memory status
superai recall "…" --strategy auto
superai cognify ./docs --dataset d360
superai ingest ./file.pdf --cognify
superai kg query --type System --name dataplex
superai kg path --from A --to B --hops 2
superai memory-session list|promote|clear
superai dataset list|use|export|forget
superai ontology show
superai learning status   # existing M061–063 — keep
```

---

## Appendix — Success metrics (honest, later)

| Metric | Target (directional) |
|--------|----------------------|
| Offline test suite for new modules | Pass in mock mode |
| Graph 2-hop query p95 local | < 200ms for <10k edges (SQLite stretch) |
| Cognify cost per 1k tokens | Tracked with cost_source |
| Default recall shows strategy label | 100% of responses |
| Cross-dataset leak in default mode | 0 in tests |

Do **not** claim Cognee BEAM parity until a real eval is built.
