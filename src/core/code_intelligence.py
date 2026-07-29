"""Native, dependency-free source-code intelligence for SuperAI."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import tempfile
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, DefaultDict, Dict, Iterable, List, Optional, Set, Tuple

from .workspace_index import SKIP_DIRS

_INDEX_VERSION = 1


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


class _PythonVisitor(ast.NodeVisitor):
    def __init__(self, rel: str) -> None:
        self.rel = rel
        self.scope: List[str] = []
        self.symbols: List[Dict[str, Any]] = []
        self.calls: DefaultDict[str, List[str]] = defaultdict(list)

    def _visit_definition(self, node: ast.AST, kind: str) -> None:
        name = str(getattr(node, "name", ""))
        qualified = ".".join([*self.scope, name])
        symbol_id = f"{self.rel}:{qualified}"
        self.symbols.append(
            {"id": symbol_id, "file": self.rel, "name": name, "qualified_name": qualified,
             "kind": kind, "line": int(getattr(node, "lineno", 0)),
             "is_test": self.rel.startswith("tests/") or name.startswith("test_")}
        )
        self.scope.append(name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_definition(node, "function")

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_definition(node, "async_function")

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._visit_definition(node, "class")

    def visit_Call(self, node: ast.Call) -> None:
        if self.scope:
            target = _call_name(node.func)
            if target:
                self.calls[f"{self.rel}:{'.'.join(self.scope)}"].append(target)
        self.generic_visit(node)


def _python_files(root: Path, max_files: int) -> Iterable[Path]:
    count = 0
    for path in root.rglob("*.py"):
        if any(part in SKIP_DIRS or part.startswith(".") for part in path.relative_to(root).parts):
            continue
        if path.stat().st_size > 500_000:
            continue
        yield path
        count += 1
        if count >= max_files:
            return


def _file_signature(path: Path) -> Dict[str, int]:
    stat = path.stat()
    return {"mtime_ns": stat.st_mtime_ns, "size": stat.st_size}


def _parse_file(path: Path, rel: str) -> Tuple[List[Dict[str, Any]], Dict[str, List[str]]]:
    visitor = _PythonVisitor(rel)
    visitor.visit(ast.parse(path.read_text(encoding="utf-8-sig", errors="replace"), filename=str(path)))
    return visitor.symbols, dict(visitor.calls)


def _assemble_graph(base: Path, entries: Dict[str, Dict[str, Any]], skipped: List[str], max_files: int,
                    *, index: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    symbols = [symbol for entry in entries.values() for symbol in entry["symbols"]]
    raw_calls: DefaultDict[str, List[str]] = defaultdict(list)
    for entry in entries.values():
        for caller, targets in entry["calls"].items():
            raw_calls[caller].extend(targets)
    by_name: DefaultDict[str, List[str]] = defaultdict(list)
    by_id = {str(symbol["id"]): symbol for symbol in symbols}
    for symbol in symbols:
        by_name[str(symbol["name"])].append(str(symbol["id"]))
    edges: List[Dict[str, str]] = []
    ambiguous_calls = 0
    for caller, targets in raw_calls.items():
        for target_name in targets:
            candidates = by_name.get(target_name, [])
            if len(candidates) == 1 and caller in by_id:
                edges.append({"from": caller, "to": candidates[0], "type": "CALLS"})
            elif candidates:
                ambiguous_calls += 1
    result = {
        "ok": True, "product": "superai.code_intelligence.v1", "root": str(base),
        "language": "python", "files": sorted(entries), "symbols": symbols, "edges": edges,
        "coverage": {"parsed_files": len(entries), "skipped_files": skipped, "max_files": max_files},
        "limitations": ["Python only in v1", "Only uniquely resolved calls create CALLS edges", "No user memory is read or written"],
        "stats": {"symbols": len(symbols), "calls": len(edges), "ambiguous_calls": ambiguous_calls},
    }
    if index:
        result["index"] = index
    return result


def build_code_graph(root: Optional[Path] = None, *, max_files: int = 2000) -> Dict[str, Any]:
    """Build a compact Python source graph entirely in-process."""
    base = Path(root or Path.cwd()).resolve()
    entries: Dict[str, Dict[str, Any]] = {}
    skipped: List[str] = []
    for path in _python_files(base, max_files):
        rel = path.relative_to(base).as_posix()
        try:
            symbols, calls = _parse_file(path, rel)
            entries[rel] = {"signature": _file_signature(path), "symbols": symbols, "calls": calls}
        except (OSError, SyntaxError, ValueError):
            skipped.append(rel)
    return _assemble_graph(base, entries, skipped, max_files)


def _index_path(base: Path, cache_dir: Optional[Path]) -> Path:
    directory = Path(cache_dir or (Path.home() / ".superai" / "code-intelligence"))
    digest = hashlib.sha256(str(base).encode("utf-8")).hexdigest()[:20]
    return directory / f"{digest}.json"


def _load_index(path: Path, base: Path, max_files: int) -> Optional[Dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    if data.get("version") != _INDEX_VERSION or data.get("root") != str(base) or data.get("max_files") != max_files:
        return None
    return data


def _write_index(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False)
    try:
        with handle:
            json.dump(data, handle, separators=(",", ":"), sort_keys=True)
        os.replace(handle.name, path)
    finally:
        if os.path.exists(handle.name):
            os.unlink(handle.name)


def index_code_graph(root: Optional[Path] = None, *, max_files: int = 2000,
                     cache_dir: Optional[Path] = None, force: bool = False) -> Dict[str, Any]:
    """Incrementally refresh a local source graph cache using file fingerprints."""
    base = Path(root or Path.cwd()).resolve()
    path = _index_path(base, cache_dir)
    prior = None if force else _load_index(path, base, max_files)
    prior_entries = dict((prior or {}).get("entries") or {})
    entries: Dict[str, Dict[str, Any]] = {}
    skipped: List[str] = []
    refreshed = 0
    reused = 0
    for source in _python_files(base, max_files):
        rel = source.relative_to(base).as_posix()
        try:
            signature = _file_signature(source)
            old = prior_entries.get(rel)
            if old and old.get("signature") == signature:
                entries[rel] = old
                reused += 1
                continue
            symbols, calls = _parse_file(source, rel)
            entries[rel] = {"signature": signature, "symbols": symbols, "calls": calls}
            refreshed += 1
        except (OSError, SyntaxError, ValueError):
            skipped.append(rel)
    removed = sorted(set(prior_entries) - set(entries))
    _write_index(path, {"version": _INDEX_VERSION, "root": str(base), "max_files": max_files,
                        "entries": entries, "skipped_files": skipped})
    mode = "full" if prior is None else ("incremental" if refreshed or removed else "cached")
    return _assemble_graph(base, entries, skipped, max_files, index={
        "mode": mode, "cache_path": str(path), "reused_files": reused,
        "refreshed_files": refreshed, "removed_files": removed,
    })


def code_index_status(root: Optional[Path] = None, *, max_files: int = 2000,
                      cache_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Describe the local incremental index without scanning or modifying source."""
    base = Path(root or Path.cwd()).resolve()
    path = _index_path(base, cache_dir)
    data = _load_index(path, base, max_files)
    return {"ok": True, "product": "superai.code_intelligence.v1", "root": str(base),
            "cache_path": str(path), "ready": data is not None,
            "indexed_files": len((data or {}).get("entries") or {}), "version": _INDEX_VERSION}


def search_code_graph(query: str, root: Optional[Path] = None, *, limit: int = 50) -> Dict[str, Any]:
    graph = build_code_graph(root)
    q = (query or "").strip().lower()
    matches = [item for item in graph["symbols"] if q and (q in str(item["name"]).lower() or q in str(item["file"]).lower())]
    return {"ok": True, "product": graph["product"], "query": query, "count": len(matches[:limit]), "matches": matches[:limit], "coverage": graph["coverage"]}


def architecture_report(root: Optional[Path] = None, *, max_files: int = 2000,
                        cache_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Summarise local Python modules and their conservative call relationships."""
    graph = index_code_graph(root, max_files=max_files, cache_dir=cache_dir)
    symbol_by_id = {str(item["id"]): item for item in graph["symbols"]}
    inbound: DefaultDict[str, int] = defaultdict(int)
    outbound: DefaultDict[str, int] = defaultdict(int)
    symbol_inbound: DefaultDict[str, int] = defaultdict(int)
    for edge in graph["edges"]:
        source = symbol_by_id.get(edge["from"])
        target = symbol_by_id.get(edge["to"])
        if source and target:
            source_module = str(Path(str(source["file"])).parent).replace("\\", "/")
            target_module = str(Path(str(target["file"])).parent).replace("\\", "/")
            outbound[source_module] += 1
            inbound[target_module] += 1
            symbol_inbound[str(target["id"])] += 1
    module_files: DefaultDict[str, Set[str]] = defaultdict(set)
    module_symbols: DefaultDict[str, int] = defaultdict(int)
    for symbol in graph["symbols"]:
        module = str(Path(str(symbol["file"])).parent).replace("\\", "/")
        module_files[module].add(str(symbol["file"]))
        module_symbols[module] += 1
    modules = [{"module": module, "files": len(module_files[module]), "symbols": module_symbols[module],
                "inbound_calls": inbound[module], "outbound_calls": outbound[module]}
               for module in sorted(module_files)]
    hotspots = sorted(
        [{"id": item["id"], "file": item["file"], "name": item["name"], "inbound_calls": symbol_inbound[str(item["id"])]}
         for item in graph["symbols"]], key=lambda item: (-item["inbound_calls"], item["id"]))[:20]
    return {"ok": True, "product": graph["product"], "report": "architecture", "modules": modules,
            "hotspots": hotspots, "coverage": graph["coverage"], "index": graph["index"],
            "limitations": ["Module relationships use uniquely resolved Python CALLS edges only"]}


def dead_code_report(root: Optional[Path] = None, *, max_files: int = 2000,
                     cache_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Return conservative private-function candidates, never deletion instructions."""
    graph = index_code_graph(root, max_files=max_files, cache_dir=cache_dir)
    incoming = {str(edge["to"]) for edge in graph["edges"]}
    candidates = [
        {"id": item["id"], "file": item["file"], "name": item["name"], "line": item["line"],
         "reason": "private function has no uniquely resolved inbound call", "confidence": "low"}
        for item in graph["symbols"]
        if item["kind"] in {"function", "async_function"} and str(item["name"]).startswith("_")
        and not str(item["name"]).startswith("__") and not item.get("is_test") and str(item["id"]) not in incoming
    ]
    return {"ok": True, "product": graph["product"], "report": "dead_code_candidates",
            "candidates": candidates, "count": len(candidates), "coverage": graph["coverage"],
            "index": graph["index"], "limitations": [
                "Candidates are not proof of dead code", "Dynamic imports, callbacks, reflection, and external callers are not resolved",
                "No source files are modified"],}


def changed_files(ref: str = "HEAD~1", root: Optional[Path] = None) -> List[str]:
    """Return changed paths without shell interpolation or a mutable operation."""
    base = Path(root or Path.cwd()).resolve()
    try:
        out = subprocess.run(["git", "-C", str(base), "diff", "--name-only", f"{ref}...HEAD"],
                             text=True, capture_output=True, check=False, timeout=15)
    except OSError:
        return []
    if out.returncode != 0:
        return []
    return [line.strip().replace("\\", "/") for line in out.stdout.splitlines() if line.strip()]


def code_impact(*, root: Optional[Path] = None, ref: str = "HEAD~1",
                files: Optional[List[str]] = None, depth: int = 3) -> Dict[str, Any]:
    """Map changed definitions to transitive callers and suggested tests."""
    graph = build_code_graph(root)
    modified = [p.replace("\\", "/") for p in (files if files is not None else changed_files(ref, root))]
    seeds = [symbol for symbol in graph["symbols"] if symbol["file"] in set(modified)]
    reverse: DefaultDict[str, List[str]] = defaultdict(list)
    for edge in graph["edges"]:
        reverse[edge["to"]].append(edge["from"])
    symbols = {str(s["id"]): s for s in graph["symbols"]}
    queue = deque((str(s["id"]), 0) for s in seeds)
    seen: Set[str] = {str(s["id"]) for s in seeds}
    impacted: List[Dict[str, Any]] = []
    max_depth = max(1, min(int(depth), 8))
    while queue:
        target, hops = queue.popleft()
        if hops >= max_depth:
            continue
        for caller in reverse.get(target, []):
            if caller in seen:
                continue
            seen.add(caller)
            item = dict(symbols[caller])
            item["hops"] = hops + 1
            impacted.append(item)
            queue.append((caller, hops + 1))
    graph_tests = sorted({item["file"] for item in impacted if item.get("is_test")})
    fallback_tests: List[str] = []
    try:
        from .auto_test_runner import find_impacted_tests
        fallback_tests = [Path(p).name for p in find_impacted_tests(modified, repo_root=Path(graph["root"]))]
    except Exception:
        pass
    tests = sorted(set(graph_tests + [f"tests/{name}" for name in fallback_tests]))
    risk = "low" if not impacted else ("high" if len(impacted) >= 20 or any(i.get("is_test") for i in impacted) else "medium")
    return {"ok": True, "product": graph["product"], "ref": ref, "changed_files": modified,
            "changed_symbols": seeds, "impacted_symbols": impacted, "impacted_tests": tests, "risk": risk,
            "coverage": graph["coverage"],
            "stats": {"changed_files": len(modified), "changed_symbols": len(seeds),
                      "impacted_symbols": len(impacted), "impacted_tests": len(tests)}}