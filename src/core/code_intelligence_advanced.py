"""Optional bundled multi-language scanner for SuperAI Code Intelligence.

This is deliberately dependency-free. It is a conservative source scanner, not a
replacement for a language server: only uniquely resolved short-name calls form
edges, and every response states its limitations.
"""

from __future__ import annotations

import re
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, DefaultDict, Dict, Iterable, List, Optional, Set, Tuple

from .code_intelligence import _dead_code_exclusions, _dead_code_suppressions, build_code_graph, changed_files
from .workspace_index import SKIP_DIRS

_ENGINE = "advanced-local-v1"
_EXTENSIONS = {
    ".js": "javascript", ".jsx": "javascript", ".ts": "typescript", ".tsx": "typescript",
    ".go": "go", ".java": "java", ".rs": "rust", ".cs": "csharp",
}
_KEYWORDS = {
    "if", "for", "while", "switch", "catch", "return", "new", "typeof", "sizeof", "await",
    "function", "func", "println", "print", "match", "select", "foreach", "lock", "using",
}
_PATTERNS: Tuple[Tuple[str, str, re.Pattern[str]], ...] = (
    ("class", "class", re.compile(r"(?m)^\s*(?:export\s+)?(?:public\s+)?(?:abstract\s+)?(?:class|interface|enum|trait|struct)\s+([A-Za-z_$][\w$]*)")),
    ("function", "function", re.compile(r"(?m)^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(")),
    ("function", "function", re.compile(r"(?m)^\s*(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_$][\w$]*)\s*\(")),
    ("function", "function", re.compile(r"(?m)^\s*func\s+(?:\([^)]*\)\s+)?([A-Za-z_$][\w$]*)\s*\(")),
    ("function", "function", re.compile(r"(?m)^\s*(?:public|private|protected|internal|static|final|async|virtual|override|sealed|synchronized|\s)+[\w<>,\[\]?\s]+\s+([A-Za-z_$][\w$]*)\s*\([^;{}]*\)\s*(?:\{|=>)")),
)
_CALL = re.compile(r"\b([A-Za-z_$][\w$]*)\s*\(")


def advanced_engine_status() -> Dict[str, Any]:
    """Return local scanner capabilities; no external MCP, binary, or model is used."""
    return {
        "ok": True,
        "product": "superai.code_intelligence.v2",
        "engine": _ENGINE,
        "available": True,
        "languages": sorted(set(_EXTENSIONS.values()) | {"python"}),
        "dependencies": [],
        "limitations": [
            "Conservative regex scanner for non-Python languages",
            "Only uniquely resolved short-name calls form CALLS edges",
            "No language server, external MCP, network, user memory, or source mutation",
        ],
    }


def _source_files(root: Path, max_files: int) -> Iterable[Path]:
    count = 0
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in _EXTENSIONS:
            continue
        if any(part in SKIP_DIRS or part.startswith(".") for part in path.relative_to(root).parts):
            continue
        if path.stat().st_size > 500_000:
            continue
        yield path
        count += 1
        if count >= max_files:
            return


def _calls_in_body(text: str, definition_end: int, definition_offsets: Set[int]) -> List[str]:
    """Extract calls from a simple brace-delimited body, excluding declarations."""
    opening = text.find("{", definition_end)
    if opening < 0:
        return []
    depth = 0
    closing = len(text)
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                closing = index + 1
                break
    return [match.group(1) for match in _CALL.finditer(text, opening, closing)
            if match.start(1) not in definition_offsets and match.group(1) not in _KEYWORDS]


def _parse_source(path: Path, rel: str, language: str) -> Tuple[List[Dict[str, Any]], Dict[str, List[str]]]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    raw: List[Tuple[str, str, int, int]] = []
    seen: Set[Tuple[str, int]] = set()
    for kind, _label, pattern in _PATTERNS:
        for match in pattern.finditer(text):
            name = match.group(1)
            line = text.count("\n", 0, match.start()) + 1
            key = (name, line)
            if key not in seen:
                seen.add(key)
                raw.append((kind, name, line, match.end()))
    definition_offsets = {match.start(1) for _, _, pattern in _PATTERNS for match in pattern.finditer(text)}
    symbols: List[Dict[str, Any]] = []
    calls: Dict[str, List[str]] = {}
    for kind, name, line, definition_end in raw:
        symbol_id = f"{rel}:{name}"
        symbols.append({
            "id": symbol_id, "file": rel, "name": name, "qualified_name": name,
            "kind": kind, "line": line, "language": language,
            "is_test": rel.startswith("tests/") or "/test/" in rel or name.startswith("test"),
        })
        calls[symbol_id] = _calls_in_body(text, definition_end, definition_offsets)
    return symbols, calls

def build_advanced_code_graph(root: Optional[Path] = None, *, max_files: int = 2000) -> Dict[str, Any]:
    """Build an optional local multi-language graph layered on the Python graph."""
    base = Path(root or Path.cwd()).resolve()
    python_graph = build_code_graph(base, max_files=max_files)
    symbols = [dict(item, language="python") for item in python_graph["symbols"]]
    edges = list(python_graph["edges"])
    raw_calls: Dict[str, List[str]] = {}
    scanned: List[str] = []
    skipped: List[str] = []
    languages: Set[str] = {"python"} if python_graph["coverage"]["parsed_files"] else set()
    for path in _source_files(base, max_files):
        rel = path.relative_to(base).as_posix()
        try:
            language = _EXTENSIONS[path.suffix.lower()]
            parsed, calls = _parse_source(path, rel, language)
            symbols.extend(parsed)
            raw_calls.update(calls)
            scanned.append(rel)
            languages.add(language)
        except (OSError, ValueError):
            skipped.append(rel)
    by_name: DefaultDict[str, List[str]] = defaultdict(list)
    known_ids = {str(item["id"]) for item in symbols}
    for symbol in symbols:
        by_name[str(symbol["name"])].append(str(symbol["id"]))
    ambiguous = 0
    for caller, calls in raw_calls.items():
        for target in calls:
            candidates = by_name.get(target, [])
            if len(candidates) == 1 and caller in known_ids and candidates[0] != caller:
                edges.append({"from": caller, "to": candidates[0], "type": "CALLS"})
            elif candidates:
                ambiguous += 1
    return {
        "ok": True, "product": "superai.code_intelligence.v2", "engine": _ENGINE,
        "root": str(base), "language": "multi", "languages": sorted(languages),
        "files": sorted(set(python_graph["files"]) | set(scanned)), "symbols": symbols, "edges": edges,
        "coverage": {"parsed_files": len(python_graph["files"]) + len(scanned),
                     "python_files": len(python_graph["files"]), "advanced_files": len(scanned),
                     "skipped_files": list(python_graph["coverage"]["skipped_files"]) + skipped,
                     "max_files": max_files},
        "stats": {"symbols": len(symbols), "calls": len(edges), "ambiguous_calls": python_graph["stats"]["ambiguous_calls"] + ambiguous},
        "limitations": advanced_engine_status()["limitations"],
    }


def search_advanced_code_graph(query: str, root: Optional[Path] = None, *, limit: int = 50) -> Dict[str, Any]:
    graph = build_advanced_code_graph(root)
    q = (query or "").strip().lower()
    matches = [item for item in graph["symbols"] if q and (q in str(item["name"]).lower() or q in str(item["file"]).lower())]
    return {"ok": True, "product": graph["product"], "engine": _ENGINE, "query": query,
            "count": len(matches[:limit]), "matches": matches[:limit], "coverage": graph["coverage"],
            "limitations": graph["limitations"]}


def advanced_code_impact(*, root: Optional[Path] = None, ref: str = "HEAD~1",
                         files: Optional[List[str]] = None, depth: int = 3) -> Dict[str, Any]:
    """Map changed multi-language definitions to conservative transitive callers."""
    graph = build_advanced_code_graph(root)
    modified = [item.replace("\\", "/") for item in (files if files is not None else changed_files(ref, root))]
    seeds = [item for item in graph["symbols"] if item["file"] in set(modified)]
    reverse: DefaultDict[str, List[str]] = defaultdict(list)
    for edge in graph["edges"]:
        reverse[str(edge["to"])].append(str(edge["from"]))
    by_id = {str(item["id"]): item for item in graph["symbols"]}
    queue = deque((str(item["id"]), 0) for item in seeds)
    seen = {str(item["id"]) for item in seeds}
    impacted: List[Dict[str, Any]] = []
    while queue:
        target, hops = queue.popleft()
        if hops >= max(1, min(int(depth), 8)):
            continue
        for caller in reverse.get(target, []):
            if caller in seen:
                continue
            seen.add(caller)
            item = dict(by_id[caller])
            item["hops"] = hops + 1
            impacted.append(item)
            queue.append((caller, hops + 1))
    tests = sorted({str(item["file"]) for item in impacted if item.get("is_test")})
    return {"ok": True, "product": graph["product"], "engine": _ENGINE, "ref": ref,
            "changed_files": modified, "changed_symbols": seeds, "impacted_symbols": impacted,
            "impacted_tests": tests, "risk": "low" if not impacted else "medium",
            "coverage": graph["coverage"], "limitations": graph["limitations"],
            "stats": {"changed_files": len(modified), "changed_symbols": len(seeds),
                      "impacted_symbols": len(impacted), "impacted_tests": len(tests)}}

def advanced_dead_code_report(root: Optional[Path] = None, *, max_files: int = 2000, lsp: bool = False) -> Dict[str, Any]:
    """Return low-confidence private symbol candidates across bundled languages."""
    graph = build_advanced_code_graph(root, max_files=max_files)
    incoming = {str(edge["to"]) for edge in graph["edges"]}
    base = Path(graph["root"])
    dynamic_refs, value_refs, decorated = _dead_code_exclusions(base, max_files)
    suppressions = _dead_code_suppressions(base)
    candidates = []
    for item in graph["symbols"]:
        name = str(item["name"])
        if item["kind"] not in {"function", "async_function", "class"} or not name.startswith("_") or name.startswith("__") or item.get("is_test") or str(item["id"]) in incoming:
            continue
        if item.get("language") == "python" and (name in dynamic_refs or name in value_refs or (str(item["file"]), int(item["line"])) in decorated):
            continue
        if name in suppressions or f"{item['file']}:{name}" in suppressions:
            continue
        candidates.append({"id": item["id"], "file": item["file"], "name": name, "line": item["line"], "language": item.get("language", "python"), "kind": item["kind"], "confidence": "low", "reason": "private symbol has no uniquely resolved inbound call"})
    lsp_result: Dict[str, Any] = {"enabled": False}
    if lsp:
        from .lsp_bridge import python_reference_counts

        lsp_languages = {
            "python": "python",
            "typescript": "typescript_javascript",
            "javascript": "typescript_javascript",
            "go": "go",
            "rust": "rust",
            "java": "java",
            "csharp": "csharp",
        }
        providers: Dict[str, Any] = {}
        referenced: Set[str] = set()
        for candidate_language, provider_language in lsp_languages.items():
            language_candidates = [item for item in candidates if item.get("language") == candidate_language]
            if not language_candidates or provider_language in providers:
                continue
            result = python_reference_counts(base, language_candidates, language=provider_language)
            providers[provider_language] = result
            referenced.update(str(symbol_id) for symbol_id, count in (result.get("reference_counts") or {}).items() if int(count) > 1)
        candidates = [item for item in candidates if str(item["id"]) not in referenced]
        lsp_result = {"enabled": True, "providers": providers, "checked_candidates": sum(len((item.get("reference_counts") or {})) for item in providers.values())}
    return {"ok": True, "product": graph["product"], "engine": _ENGINE, "report": "dead_code_candidates", "candidates": candidates, "count": len(candidates), "coverage": graph["coverage"], "suppressions": sorted(suppressions), "lsp": lsp_result, "limitations": graph["limitations"] + ["Candidates are review evidence only; no source files are modified"]}