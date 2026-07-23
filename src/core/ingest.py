"""
Multi-format ingest (Memory Roadmap P5 / Cognee gap 5).

Supported v1 sources:
  - text / markdown / plain files
  - JSONL (one JSON object or raw line per record)
  - PDF text extract (pypdf when installed; basic stream fallback)
  - URL fetch (SSRF-safe via net_safety; injectable fetcher for tests)

Always:
  - workspace jail on local paths (assert_in_workspace)
  - optional MemoryPalace chunk store
  - optional cognify into knowledge graph

Non-goals v1: OCR, audio/video, full git history mining.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Format matrix (also exported for docs / CLI --formats)
# ---------------------------------------------------------------------------

SUPPORTED_FORMATS: List[Dict[str, str]] = [
    {
        "format": "text",
        "extensions": ".txt,.log,.csv,.tsv",
        "notes": "UTF-8 with replacement; chunked into palace",
    },
    {
        "format": "markdown",
        "extensions": ".md,.markdown,.mdx",
        "notes": "Same as text; preferred for cognify headings",
    },
    {
        "format": "jsonl",
        "extensions": ".jsonl,.ndjson",
        "notes": "One JSON object per line; uses content/text/body/message fields",
    },
    {
        "format": "json",
        "extensions": ".json",
        "notes": "Single JSON object/array; email-export shaped keys supported",
    },
    {
        "format": "pdf",
        "extensions": ".pdf",
        "notes": "Text extract only (no OCR). Prefers pypdf; basic stream fallback",
    },
    {
        "format": "url",
        "extensions": "http(s)://",
        "notes": "SSRF-guarded public HTTP(S); HTML tags stripped",
    },
    {
        "format": "email_json",
        "extensions": ".json (subject+body)",
        "notes": "Outlook-style JSON export with subject/body fields",
    },
    {
        "format": "code",
        "extensions": ".py,.ts,.js,.go,.rs,.java,.sql,...",
        "notes": "Language-aware chunking on def/class/function boundaries (MR-3)",
    },
]

_TEXT_EXTS = {".txt", ".log", ".csv", ".tsv", ".rst"}
_MD_EXTS = {".md", ".markdown", ".mdx"}
_JSONL_EXTS = {".jsonl", ".ndjson"}
_JSON_EXTS = {".json"}
_PDF_EXTS = {".pdf"}
# MR-3: language-aware code folder ingest
_CODE_EXTS = {
    ".py",
    ".pyi",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".cs",
    ".cpp",
    ".cc",
    ".c",
    ".h",
    ".hpp",
    ".rb",
    ".php",
    ".swift",
    ".scala",
    ".sql",
    ".sh",
    ".ps1",
    ".r",
}

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_PDF_TJ_RE = re.compile(r"\((?:\\.|[^\\)])*\)\s*Tj")
_PDF_STRING_RE = re.compile(r"\((?:\\.|[^\\)])*\)")
_MAX_URL_BYTES = 512_000
_MAX_FILE_BYTES = 8_000_000
_DEFAULT_CHUNK = 2000
_DEFAULT_OVERLAP = 200


def formats_matrix() -> List[Dict[str, str]]:
    """Return the supported formats table (for docs / CLI)."""
    return list(SUPPORTED_FORMATS)


def _truthy(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def detect_format(source: str, *, is_url: bool = False) -> str:
    """Heuristic format label for a path or URL string."""
    s = (source or "").strip()
    if is_url or s.lower().startswith(("http://", "https://")):
        return "url"
    p = Path(s)
    ext = p.suffix.lower()
    if ext in _PDF_EXTS:
        return "pdf"
    if ext in _JSONL_EXTS:
        return "jsonl"
    if ext in _JSON_EXTS:
        return "json"
    if ext in _MD_EXTS:
        return "markdown"
    if ext in _CODE_EXTS:
        return "code"
    if ext in _TEXT_EXTS or not ext:
        return "text"
    # unknown extension → still try as text
    return "text"


def _jail_path(path: Path, *, enforce: bool = True) -> Path:
    if not enforce or _truthy("SUPERAI_INGEST_ALLOW_OUTSIDE"):
        return path.expanduser().resolve()
    from .workspace import assert_in_workspace

    return assert_in_workspace(path, label="ingest path")


def _read_text_file(path: Path, *, max_bytes: int = _MAX_FILE_BYTES) -> str:
    raw = path.read_bytes()
    if len(raw) > max_bytes:
        raise ValueError(f"file too large ({len(raw)} > {max_bytes} bytes)")
    return raw.decode("utf-8", errors="replace")


def _unescape_pdf_string(s: str) -> str:
    s = s[1:-1] if s.startswith("(") and s.endswith(")") else s
    out: List[str] = []
    i = 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            mapping = {"n": "\n", "r": "\r", "t": "\t", "(": "(", ")": ")", "\\": "\\"}
            out.append(mapping.get(nxt, nxt))
            i += 2
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def extract_pdf_text_basic(data: bytes) -> str:
    """
    Minimal PDF text harvest for simple streams (offline / no pypdf).

    Pulls literal strings used with Tj operators and other parenthesized
    strings in content streams. Not a full PDF parser — honest about limits.
    """
    # Prefer streams
    chunks: List[str] = []
    try:
        text = data.decode("latin-1", errors="ignore")
    except Exception:
        return ""
    for m in _PDF_TJ_RE.finditer(text):
        chunks.append(_unescape_pdf_string(m.group(0).rsplit("Tj", 1)[0].strip()))
    if not chunks:
        # weaker: any short parenthesized strings that look like text
        for m in _PDF_STRING_RE.finditer(text):
            s = _unescape_pdf_string(m.group(0))
            if 2 <= len(s) <= 200 and any(c.isalpha() for c in s):
                chunks.append(s)
    return "\n".join(chunks).strip()


def extract_pdf_text(path: Path) -> Dict[str, Any]:
    """Extract text from PDF. Prefer pypdf; fall back to basic stream scan."""
    try:
        data = path.read_bytes()
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:300], "error_code": "io"}
    if len(data) > _MAX_FILE_BYTES:
        return {
            "ok": False,
            "error": f"pdf too large ({len(data)} bytes)",
            "error_code": "too_large",
        }
    # Try pypdf
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(path))
        pages = []
        for page in reader.pages:
            try:
                pages.append(page.extract_text() or "")
            except Exception:  # noqa: BLE001
                pages.append("")
        body = "\n".join(pages).strip()
        if body:
            return {
                "ok": True,
                "text": body,
                "extractor": "pypdf",
                "pages": len(reader.pages),
            }
    except ImportError:
        pass
    except Exception as e:  # noqa: BLE001
        # fall through to basic
        basic = extract_pdf_text_basic(data)
        if basic:
            return {
                "ok": True,
                "text": basic,
                "extractor": "basic_fallback",
                "pypdf_error": str(e)[:200],
            }
        return {
            "ok": False,
            "error": f"pypdf failed: {e}"[:300],
            "error_code": "pdf_extract",
            "hint": "pip install pypdf",
        }

    basic = extract_pdf_text_basic(data)
    if basic:
        return {"ok": True, "text": basic, "extractor": "basic"}
    return {
        "ok": False,
        "error": "no extractable text (scanned PDF needs OCR — not in v1)",
        "error_code": "pdf_empty",
        "hint": "pip install pypdf for better extraction; OCR is out of scope",
    }


def _json_to_text(obj: Any) -> str:
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, (int, float, bool)):
        return str(obj)
    if isinstance(obj, list):
        parts = [_json_to_text(x) for x in obj]
        return "\n".join(p for p in parts if p)
    if isinstance(obj, dict):
        # email / common content keys
        for key in (
            "body",
            "text",
            "content",
            "message",
            "Body",
            "Text",
            "Content",
            "html_body",
            "plain_body",
        ):
            if key in obj and obj[key]:
                subject = obj.get("subject") or obj.get("Subject") or ""
                body = _json_to_text(obj[key])
                if subject:
                    return f"Subject: {subject}\n\n{body}"
                return body
        # fallback compact JSON
        try:
            return json.dumps(obj, ensure_ascii=False, indent=2)[:50_000]
        except Exception:  # noqa: BLE001
            return str(obj)[:50_000]
    return str(obj)[:50_000]


def load_jsonl_text(
    raw: str, *, keep_invalid_raw: bool = False
) -> Tuple[str, str, Dict[str, Any]]:
    """
    Return (text, format_label, meta) for JSONL content.

    Invalid JSON lines are **not** silently treated as good data:
    they are counted in meta['invalid_lines'] and skipped by default
    (or kept as raw when keep_invalid_raw=True, still flagged).
    """
    lines_out: List[str] = []
    invalid: List[Dict[str, Any]] = []
    for i, line in enumerate(raw.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            lines_out.append(_json_to_text(obj))
        except json.JSONDecodeError as e:
            invalid.append({"line": i, "error": str(e)[:120]})
            if keep_invalid_raw:
                lines_out.append(f"[invalid_jsonl_line_{i}] {line}")
    meta = {
        "invalid_lines": len(invalid),
        "invalid_samples": invalid[:10],
        "valid_lines": len(lines_out) - (len(invalid) if keep_invalid_raw else 0),
    }
    return "\n\n".join(lines_out), "jsonl", meta


def load_json_text(raw: str) -> Tuple[str, str]:
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return raw, "text"
    # email-shaped?
    if isinstance(obj, dict) and any(
        k in obj for k in ("subject", "Subject", "body", "Body", "from", "From")
    ):
        return _json_to_text(obj), "email_json"
    return _json_to_text(obj), "json"


def strip_html(html: str) -> str:
    text = _HTML_TAG_RE.sub(" ", html or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def default_http_fetch(url: str, *, timeout: float = 20.0, max_bytes: int = _MAX_URL_BYTES) -> Dict[str, Any]:
    """Fetch URL body with size cap. Caller must SSRF-check first."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "SuperAI-ingest/1.0 (+local; SSRF-guarded)",
            "Accept": "text/html,application/xhtml+xml,text/plain,application/json,*/*",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            raw = resp.read(max_bytes + 1)
            if len(raw) > max_bytes:
                return {
                    "ok": False,
                    "error": f"response exceeds {max_bytes} bytes",
                    "error_code": "too_large",
                }
            body = raw.decode("utf-8", errors="replace")
            if "html" in ctype or body.lstrip().lower().startswith("<!doctype") or "<html" in body[:200].lower():
                text = strip_html(body)
            elif "json" in ctype:
                text, _fmt = load_json_text(body)
            else:
                text = body
            return {
                "ok": True,
                "text": text,
                "content_type": ctype,
                "bytes": len(raw),
                "final_url": resp.geturl(),
            }
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTP {e.code}: {e.reason}"[:300], "error_code": "http"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:300], "error_code": "fetch"}


def fetch_url_text(
    url: str,
    *,
    fetch_fn: Optional[Callable[[str], Dict[str, Any]]] = None,
    require_https: bool = False,
    allow_private: Optional[bool] = None,
) -> Dict[str, Any]:
    """SSRF-safe URL text fetch. ``fetch_fn`` injectable for unit tests."""
    from .net_safety import validate_public_http_url

    err = validate_public_http_url(
        url, require_https=require_https, allow_private=allow_private
    )
    if err:
        return {"ok": False, "error": err, "error_code": "ssrf", "url": url}
    fetcher = fetch_fn or default_http_fetch
    try:
        out = fetcher(url)
    except TypeError:
        # allow fetch_fn(url) only
        out = fetch_fn(url)  # type: ignore[misc]
    if not isinstance(out, dict):
        return {"ok": False, "error": "fetcher returned non-dict", "error_code": "fetch"}
    out.setdefault("url", url)
    return out


def chunk_text(
    text: str,
    *,
    chunk_size: int = _DEFAULT_CHUNK,
    overlap: int = _DEFAULT_OVERLAP,
) -> List[str]:
    """Simple character chunks with overlap (offline-safe)."""
    text = text or ""
    if not text.strip():
        return []
    size = max(200, int(chunk_size))
    ov = max(0, min(int(overlap), size // 2))
    if len(text) <= size:
        return [text]
    chunks: List[str] = []
    i = 0
    n = len(text)
    while i < n:
        end = min(n, i + size)
        chunks.append(text[i:end])
        if end >= n:
            break
        i = end - ov
    return chunks


_CODE_BOUNDARY_RE = re.compile(
    r"(?m)^(?:"
    r"def\s+\w+|async\s+def\s+\w+|class\s+\w+|"  # Python
    r"function\s+\w+|export\s+(?:async\s+)?function\s+\w+|export\s+class\s+\w+|"  # JS/TS
    r"func\s+\w+|fn\s+\w+|impl\s+\w+|pub\s+(?:fn|struct|enum)\s+\w+|"  # Go/Rust
    r"public\s+(?:class|interface|void|static)|"  # Java-ish
    r"CREATE\s+(?:OR\s+REPLACE\s+)?(?:TABLE|VIEW|FUNCTION)\s+"  # SQL
    r")"
)


def chunk_code(
    text: str,
    *,
    chunk_size: int = _DEFAULT_CHUNK,
    overlap: int = _DEFAULT_OVERLAP,
) -> List[str]:
    """
    Language-aware code chunking (MR-3).

    Prefer splitting on def/class/function boundaries; fall back to character
    chunks when a unit exceeds chunk_size.
    """
    text = text or ""
    if not text.strip():
        return []
    # Allow smaller target than plain text (defs are often short units)
    size = max(80, int(chunk_size))
    # Find boundary starts
    starts = [m.start() for m in _CODE_BOUNDARY_RE.finditer(text)]
    if not starts:
        return chunk_text(text, chunk_size=chunk_size, overlap=overlap)
    starts = sorted(set([0] + starts))
    units: List[str] = []
    for i, st in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(text)
        unit = text[st:end]
        if unit.strip():
            units.append(unit)
    # Merge small units / split large ones
    chunks: List[str] = []
    buf = ""
    for unit in units:
        if len(unit) > size:
            if buf.strip():
                chunks.append(buf)
                buf = ""
            chunks.extend(chunk_text(unit, chunk_size=chunk_size, overlap=overlap))
            continue
        if len(buf) + len(unit) <= size:
            buf = buf + unit if buf else unit
        else:
            if buf.strip():
                chunks.append(buf)
            buf = unit
    if buf.strip():
        chunks.append(buf)
    return chunks or chunk_text(text, chunk_size=chunk_size, overlap=overlap)


def chunk_for_format(
    text: str,
    fmt: str,
    *,
    chunk_size: int = _DEFAULT_CHUNK,
    overlap: int = _DEFAULT_OVERLAP,
) -> List[str]:
    """Dispatch chunker by format label."""
    if (fmt or "").lower() == "code":
        return chunk_code(text, chunk_size=chunk_size, overlap=overlap)
    return chunk_text(text, chunk_size=chunk_size, overlap=overlap)


def load_local_file(
    path: Path,
    *,
    enforce_jail: bool = True,
    fmt: Optional[str] = None,
) -> Dict[str, Any]:
    """Load a local file into text with format detection."""
    try:
        resolved = _jail_path(path, enforce=enforce_jail)
    except ValueError as e:
        return {"ok": False, "error": str(e)[:400], "error_code": "workspace_jail"}
    if not resolved.is_file():
        return {
            "ok": False,
            "error": f"not a file: {resolved}",
            "error_code": "not_found",
        }
    fmt = fmt or detect_format(str(resolved))
    if fmt == "pdf":
        pdf = extract_pdf_text(resolved)
        if not pdf.get("ok"):
            return {
                "ok": False,
                "error": pdf.get("error"),
                "error_code": pdf.get("error_code") or "pdf",
                "hint": pdf.get("hint"),
                "source_path": str(resolved),
                "format": "pdf",
            }
        return {
            "ok": True,
            "text": pdf.get("text") or "",
            "format": "pdf",
            "source_path": str(resolved),
            "source_kind": "file",
            "extractor": pdf.get("extractor"),
            "pages": pdf.get("pages"),
        }
    try:
        raw = _read_text_file(resolved)
    except Exception as e:  # noqa: BLE001
        return {
            "ok": False,
            "error": str(e)[:300],
            "error_code": "io",
            "source_path": str(resolved),
        }
    label = fmt
    extra_meta: Dict[str, Any] = {}
    if fmt == "jsonl":
        text, label, jl_meta = load_jsonl_text(raw)
        extra_meta["jsonl"] = jl_meta
        if jl_meta.get("invalid_lines"):
            extra_meta["jsonl_warning"] = (
                f"{jl_meta['invalid_lines']} invalid JSONL line(s) skipped"
            )
    elif fmt in {"json", "email_json"}:
        text, label = load_json_text(raw)
    else:
        text = raw
        label = fmt
    out = {
        "ok": True,
        "text": text,
        "format": label,
        "source_path": str(resolved),
        "source_kind": "file",
        "bytes": len(raw.encode("utf-8", errors="replace")),
    }
    if extra_meta:
        out["meta"] = extra_meta
        if extra_meta.get("jsonl", {}).get("invalid_lines"):
            out["warnings"] = [extra_meta["jsonl_warning"]]
    return out


def expand_paths(
    paths: Sequence[str],
    *,
    glob_pat: str = "*.md",
    enforce_jail: bool = True,
    max_files: int = 50,
) -> Dict[str, Any]:
    """Expand files/dirs into a jailed file list."""
    files: List[Path] = []
    errors: List[Dict[str, Any]] = []
    for raw in paths:
        p = Path(raw)
        try:
            if p.is_dir() or (not p.exists() and "*" not in raw and p.suffix == ""):
                try:
                    root = _jail_path(p if p.exists() else Path(raw), enforce=enforce_jail)
                except ValueError as e:
                    errors.append({"path": raw, "error": str(e)[:300], "error_code": "workspace_jail"})
                    continue
                if root.is_dir():
                    files.extend(sorted(root.rglob(glob_pat)))
                    continue
            resolved = _jail_path(p, enforce=enforce_jail)
            if resolved.is_file():
                files.append(resolved)
            elif resolved.is_dir():
                files.extend(sorted(resolved.rglob(glob_pat)))
            else:
                errors.append({"path": raw, "error": "not found", "error_code": "not_found"})
        except ValueError as e:
            errors.append({"path": raw, "error": str(e)[:300], "error_code": "workspace_jail"})
        except Exception as e:  # noqa: BLE001
            errors.append({"path": raw, "error": str(e)[:300], "error_code": "io"})
    # de-dupe preserve order
    seen = set()
    uniq: List[Path] = []
    for f in files:
        key = str(f)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(f)
    truncated = len(uniq) > max_files
    return {
        "ok": True,
        "files": uniq[:max_files],
        "truncated": truncated,
        "errors": errors,
        "count": min(len(uniq), max_files),
    }


def ingest(
    source: Optional[str] = None,
    *,
    url: Optional[str] = None,
    paths: Optional[Sequence[str]] = None,
    dataset_id: str = "default",
    cognify: bool = False,
    cognify_mode: str = "mock",
    store_palace: bool = True,
    dry_run: bool = False,
    glob_pat: str = "*.md",
    wing: Optional[str] = None,
    room: Optional[str] = None,
    chunk_size: int = _DEFAULT_CHUNK,
    overlap: int = _DEFAULT_OVERLAP,
    max_files: int = 50,
    enforce_jail: bool = True,
    fetch_fn: Optional[Callable[[str], Dict[str, Any]]] = None,
    palace: Any = None,
    kg: Any = None,
    fmt: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ingest one source (path, directory, or URL) into palace and/or graph.

    Returns a report with per-item results.
    """
    items: List[Dict[str, Any]] = []

    # --- collect load results ---
    if url or (source and str(source).lower().startswith(("http://", "https://"))):
        u = url or str(source)
        loaded = fetch_url_text(u, fetch_fn=fetch_fn)
        if not loaded.get("ok"):
            return {
                "ok": False,
                "product": "ingest",
                "error": loaded.get("error"),
                "error_code": loaded.get("error_code") or "url",
                "url": u,
                "message": f"URL ingest failed: {loaded.get('error')}",
            }
        items.append(
            {
                "source": u,
                "format": "url",
                "source_kind": "url",
                "text": loaded.get("text") or "",
                "meta": {
                    k: loaded.get(k)
                    for k in ("content_type", "bytes", "final_url")
                    if loaded.get(k) is not None
                },
            }
        )
    else:
        path_list: List[str] = []
        if paths:
            path_list.extend(str(p) for p in paths)
        if source:
            path_list.append(str(source))
        if not path_list:
            return {
                "ok": False,
                "product": "ingest",
                "error": "source, paths, or url required",
                "error_code": "validation",
                "message": "Provide a path, --url, or paths",
            }
        # Single raw text (not a path) — only when one source and no file exists
        if len(path_list) == 1 and not Path(path_list[0]).exists() and not url:
            # treat as inline text only if it doesn't look like a path attempt
            candidate = path_list[0]
            looks_like_path = (
                "/" in candidate
                or "\\" in candidate
                or candidate.endswith((".md", ".txt", ".pdf", ".json", ".jsonl"))
            )
            if looks_like_path:
                return {
                    "ok": False,
                    "product": "ingest",
                    "error": f"path not found: {candidate}",
                    "error_code": "not_found",
                    "message": f"Path not found: {candidate}",
                }
            items.append(
                {
                    "source": "inline",
                    "format": fmt or "text",
                    "source_kind": "text",
                    "text": candidate,
                    "meta": {},
                }
            )
        else:
            expanded = expand_paths(
                path_list,
                glob_pat=glob_pat,
                enforce_jail=enforce_jail,
                max_files=max_files,
            )
            if expanded.get("errors") and not expanded.get("files"):
                return {
                    "ok": False,
                    "product": "ingest",
                    "error": expanded["errors"][0].get("error"),
                    "error_code": expanded["errors"][0].get("error_code") or "path",
                    "errors": expanded["errors"],
                    "message": f"Ingest path failed: {expanded['errors'][0].get('error')}",
                }
            for fpath in expanded.get("files") or []:
                loaded = load_local_file(fpath, enforce_jail=enforce_jail, fmt=fmt)
                if not loaded.get("ok"):
                    items.append(
                        {
                            "source": str(fpath),
                            "ok": False,
                            "error": loaded.get("error"),
                            "error_code": loaded.get("error_code"),
                            "format": loaded.get("format") or detect_format(str(fpath)),
                        }
                    )
                    continue
                meta = {
                    k: loaded.get(k)
                    for k in ("extractor", "pages", "bytes")
                    if loaded.get(k) is not None
                }
                if isinstance(loaded.get("meta"), dict):
                    meta.update(loaded["meta"])
                items.append(
                    {
                        "source": loaded.get("source_path") or str(fpath),
                        "format": loaded.get("format"),
                        "source_kind": "file",
                        "text": loaded.get("text") or "",
                        "meta": meta,
                        "warnings": loaded.get("warnings"),
                    }
                )
            if expanded.get("truncated"):
                pass  # noted in report below

    if not items:
        return {
            "ok": False,
            "product": "ingest",
            "error": "nothing to ingest",
            "error_code": "empty",
            "message": "No ingestible sources",
        }

    report: Dict[str, Any] = {
        "ok": True,
        "product": "ingest",
        "dataset_id": dataset_id,
        "dry_run": bool(dry_run),
        "cognify": bool(cognify),
        "store_palace": bool(store_palace) and not dry_run,
        "items": [],
        "items_total": len(items),
        "chunks_written": 0,
        "palace_memory_ids": [],
        "cognify_nodes": 0,
        "cognify_edges": 0,
        "formats": [],
        "message": "",
    }

    mp = None
    if store_palace and not dry_run:
        try:
            from .memory_palace import MemoryPalace

            mp = palace or MemoryPalace()
        except Exception as e:  # noqa: BLE001
            report["palace_error"] = str(e)[:200]
            report["degraded"] = True
            report["ok"] = False
            report["error_code"] = report.get("error_code") or "palace_init"
            mp = None
            report.setdefault("warnings", []).append(
                f"MemoryPalace init failed; chunks will not be stored: {type(e).__name__}"
            )

    for item in items:
        if item.get("ok") is False and "text" not in item:
            report["items"].append(item)
            report["ok"] = False
            continue
        text = item.get("text") or ""
        fmt_label = item.get("format") or "text"
        if fmt_label not in report["formats"]:
            report["formats"].append(fmt_label)
        entry: Dict[str, Any] = {
            "source": item.get("source"),
            "format": fmt_label,
            "source_kind": item.get("source_kind"),
            "chars": len(text),
            "ok": True,
        }
        if item.get("meta"):
            entry["meta"] = item["meta"]
        if not text.strip():
            entry["ok"] = False
            entry["error"] = "empty text after extract"
            entry["error_code"] = "empty"
            report["items"].append(entry)
            report["ok"] = False
            continue

        chunks = chunk_for_format(
            text, fmt_label, chunk_size=chunk_size, overlap=overlap
        )
        entry["chunks"] = len(chunks)
        if fmt_label == "code":
            entry["chunker"] = "code_boundary"
        if item.get("meta"):
            entry.setdefault("meta", {}).update(item["meta"])
        if item.get("warnings"):
            entry["warnings"] = item["warnings"]
            report.setdefault("warnings", []).extend(item["warnings"])

        if dry_run:
            entry["dry_run"] = True
            entry["preview"] = text[:240].replace("\n", " ")
            report["items"].append(entry)
            continue

        ids: List[str] = []
        if store_palace and mp is None and not report.get("palace_error"):
            # store requested but palace never created
            entry["palace_skipped"] = True
            entry["warning"] = "palace unavailable; chunks not stored"
            report["degraded"] = True
        if store_palace and mp is not None:
            for idx, ch in enumerate(chunks):
                try:
                    mid = mp.store(
                        ch,
                        tags=[
                            "ingest",
                            f"format:{fmt_label}",
                            f"dataset:{dataset_id}",
                        ],
                        metadata={
                            "source": "ingest",
                            "dataset_id": dataset_id,
                            "format": fmt_label,
                            "source_path": item.get("source"),
                            "chunk_index": idx,
                            "chunk_count": len(chunks),
                            **(item.get("meta") or {}),
                        },
                        importance=0.6,
                        wing=wing or "learning",
                        room=room or "ingest",
                    )
                    ids.append(str(mid))
                except Exception as e:  # noqa: BLE001
                    entry["palace_error"] = str(e)[:200]
                    entry["ok"] = False
                    report["ok"] = False
                    break
            entry["palace_memory_ids"] = ids
            report["chunks_written"] += len(ids)
            report["palace_memory_ids"].extend(ids)

        if cognify:
            try:
                from .cognify import cognify as run_cognify

                # Cognify full text (capped inside cognify extractors)
                c_out = run_cognify(
                    text,
                    dataset_id=dataset_id,
                    mode=cognify_mode,
                    dry_run=False,
                    store_palace=False,
                    wing=wing,
                    room=room,
                    kg=kg,
                )
                entry["cognify"] = {
                    "ok": c_out.get("ok"),
                    "nodes_written": c_out.get("nodes_written"),
                    "edges_written": c_out.get("edges_written"),
                    "mode": c_out.get("mode"),
                    "entities_found": c_out.get("entities_found"),
                    "relations_found": c_out.get("relations_found"),
                }
                report["cognify_nodes"] += int(c_out.get("nodes_written") or 0)
                report["cognify_edges"] += int(c_out.get("edges_written") or 0)
                if not c_out.get("ok"):
                    entry["ok"] = False
                    report["ok"] = False
            except Exception as e:  # noqa: BLE001
                entry["cognify_error"] = str(e)[:200]
                entry["ok"] = False
                report["ok"] = False

        report["items"].append(entry)

    ok_count = sum(1 for x in report["items"] if x.get("ok"))
    report["items_ok"] = ok_count
    if dry_run:
        report["message"] = (
            f"Dry-run ingest: {ok_count}/{len(report['items'])} item(s); "
            f"formats={report['formats']}"
        )
    else:
        report["message"] = (
            f"Ingested {ok_count}/{len(report['items'])} item(s); "
            f"chunks={report['chunks_written']}; "
            f"cognify_nodes={report['cognify_nodes']}; "
            f"formats={report['formats']}"
        )
    # MR-2 / P9-R1: OTEL (counts only; no free-text)
    try:
        from .memory_otel import instrument_report

        report = instrument_report("ingest", report)
    except Exception:
        pass
    return report
