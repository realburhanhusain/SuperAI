# Doc gap analysis — Basic Plan + Future Plan vs SuperAI_v1

**Sources:**
- `Documents/Personal/SuperAI/SuperAI Basic Plan.docx`
- `Documents/Personal/SuperAI/SuperAI Future Plan.docx`

**Updated:** 2026-07-14

## Basic Plan

~95%+ covered previously. Residual polish tracked under Future Plan gaps where overlapping.

## Future Plan gaps (tracked)

| ID | Feature | Status |
|----|---------|--------|
| G1 | `superai compare` + model benchmarking | **Implemented** this session |
| G2 | Plan export JSON/Markdown | **Implemented** |
| G3 | Step result cache + resume execution | **Implemented** |
| G4 | Parallel voting LB strategy + model blacklist | **Implemented** |
| G5 | Skill create/delete/improve CLI + deps/test | **Implemented** |
| G6 | Selective backup scopes | **Implemented** |
| G7 | External CLI dual-register as models | **Implemented** |
| G8 | Multi-turn memory conversation | **Implemented** |
| G9 | Model version pinning | **Implemented** |
| G10 | Notion integration stub | **Implemented** (API when key set) |
| G11 | Mid-task clarification request + human veto | **Implemented** (hooks) |
| G12 | GitHub Actions release + backup workflows | **Implemented** |
| G13 | HNSW/FAISS/quantization depth | **Partial** — config knobs only |
| G14 | DuckDuckGo live search | Deferred (policy: not scrape) |
| G15 | Full GitHub product API (issues/PRs) | Deferred external |
| G16 | Live multi-provider / bots / rclone / Pages | Deferred smoke |

## How to verify

```powershell
pytest -q
superai compare "write a hello world" --mock
superai plan "build api" --export json -o plan.json
superai skill create demo "Do X carefully"
superai backup --scope memory,skills
```
