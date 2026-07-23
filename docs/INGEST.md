# Multi-format Ingest — Memory Roadmap P5

**Status:** Implemented (text / md / jsonl / json / pdf / url)  
**Date:** 2026-07-23  
**Module:** `src/core/ingest.py`  
**CLI:** `superai ingest`  
**MCP:** `superai_ingest`  
**Depends on:** P2 cognify (optional), MemoryPalace, `net_safety`, `workspace` jail  
**Coordination:** Memory-only modules — does not touch AGY scorecard files (exit_codes / git_helpers / prompt_injection).

## Goals

Vertical multi-format **load → (chunk → palace) → optional cognify** path matching Cognee gap 5, offline SuperAI offline-first honesty.

## Supported formats matrix

| Format | Extensions / form | Notes |
|--------|-------------------|--------|
| **text** | `.txt`, `.log`, `.csv`, `.tsv` | UTF-8 with replacement; chunked |
| **code** | `.py`, `.ts`, `.js`, `.go`, `.rs`, … | MR-3 language-aware chunking on def/class/function boundaries |
| **markdown** | `.md`, `.markdown`, `.mdx` | Preferred for cognify headings |
| **jsonl** | `.jsonl`, `.ndjson` | Uses `content` / `text` / `body` / `message` fields |
| **json** | `.json` | Single object/array; compact dump fallback |
| **email_json** | `.json` with subject/body | Outlook-style export shape |
| **pdf** | `.pdf` | **Text extract only** (no OCR). Prefers `pypdf`; basic stream fallback |
| **url** | `http(s)://…` | SSRF-guarded public destinations; HTML tags stripped |

### Non-goals v1

- OCR (images / scanned PDF)
- Audio / video
- Full git history mining

## Safety

| Control | Mechanism |
|---------|-----------|
| **SSRF** | `core.net_safety.validate_public_http_url` before any fetch (blocks loopback/private/link-local/metadata hosts unless `SUPERAI_ALLOW_PRIVATE_URLS=1`) |
| **Workspace jail** | Local paths via `assert_in_workspace` (`SUPERAI_WORKSPACE` or cwd). Escape hatch: `SUPERAI_INGEST_ALLOW_OUTSIDE=1` |
| **Size caps** | Files ~8 MiB; URL body ~512 KiB |
| **Mock cognify** | Default `--cognify-mode mock` stays offline-safe |

Optional better PDF: `pip install pypdf` (also `pip install 'superai[ingest]'` when packaging extras).

## CLI

```powershell
# Formats matrix
superai ingest --formats

# Markdown / text → palace
superai ingest .\docs\INGEST.md --dataset superai
superai ingest .\notes --glob "*.md" --dataset d360

# PDF text extract
superai ingest .\report.pdf --dataset superai

# URL (SSRF-safe)
superai ingest --url https://example.com/page --dry-run

# Palace + cognify graph
superai ingest .\docs\KNOWLEDGE_GRAPH.md --cognify --cognify-mode mock --dataset superai

# JSON automation
superai --json ingest .\rows.jsonl --no-palace --dry-run
```

| Flag | Meaning |
|------|---------|
| `--url` | Fetch HTTP(S) instead of local path |
| `--dataset` / `-d` | Namespace tag on palace + cognify |
| `--cognify` | Also run P2 cognify on extracted text |
| `--cognify-mode mock\|llm` | Extractor mode (default **mock**) |
| `--dry-run` | Extract / preview only |
| `--no-palace` | Skip MemoryPalace chunks |
| `--glob` | Directory expansion (default `*.md`) |
| `--formats` | Print matrix and exit |
| `--max-files` | Cap directory expansion (default 50) |

## Library

```python
from core.ingest import ingest, formats_matrix

report = ingest(
    "notes.md",
    dataset_id="superai",
    cognify=True,
    cognify_mode="mock",
    store_palace=True,
)
# URL with injectable fetcher (tests):
report = ingest(url="https://example.com/x", fetch_fn=my_fetch, dry_run=True)
```

## MCP

Tool **`superai_ingest`**: `source` and/or `url`, plus `dataset_id`, `cognify`, `cognify_mode`, `dry_run`, `store_palace`, `glob`.

## Pipeline

```text
  path | dir | url
       │
       ├─ jail / SSRF
       ▼
  extract (md/text/jsonl/json/pdf/url)
       │
       ├─ chunk
       ├─ (optional) MemoryPalace.store × N
       └─ (optional) cognify → KnowledgeGraph
       ▼
  report (formats, chunks, cognify counts)
```

## Tests

`tests/test_ingest_p5.py` — formats matrix, chunking, JSONL, PDF basic extract, SSRF block, workspace jail, md/pdf/jsonl/dir dry-run and write paths (URL fetch mocked).

## Honest limits

- Basic PDF extractor is for simple text operators; complex/scanned PDFs need `pypdf` or OCR (OCR not shipped).
- URL fetch uses stdlib `urllib` (not Playwright); JS-rendered pages will look empty.
- Directory default glob is `*.md` (same as cognify) so mixed trees need an explicit `--glob`.
