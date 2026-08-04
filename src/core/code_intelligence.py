"""Native, dependency-free source-code intelligence for SuperAI."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import tempfile
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, DefaultDict, Dict, Iterable, List, Optional, Set, Tuple

from .workspace_index import SKIP_DIRS

_INDEX_VERSION = 2
_MAX_SOURCE_BYTES = 500_000


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
        if path.stat().st_size > _MAX_SOURCE_BYTES:
            continue
        yield path
        count += 1
        if count >= max_files:
            return


def _content_digest(path: Path) -> str:
    """Return a stable source digest for explicit cache verification."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _file_signature(path: Path) -> Dict[str, Any]:
    stat = path.stat()
    return {"mtime_ns": stat.st_mtime_ns, "size": stat.st_size}


def _scan_config() -> Dict[str, Any]:
    """Describe parser settings that make a persisted index compatible."""
    return {"language": "python", "max_source_bytes": _MAX_SOURCE_BYTES, "skip_dirs": sorted(SKIP_DIRS)}
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
    if (
        data.get("version") != _INDEX_VERSION
        or data.get("root") != str(base)
        or data.get("max_files") != max_files
        or data.get("scan_config") != _scan_config()
        or not isinstance(data.get("entries"), dict)
    ):
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
                     cache_dir: Optional[Path] = None, force: bool = False,
                     verify_content: bool = False) -> Dict[str, Any]:
    """Refresh a local graph cache, optionally verifying unchanged files by digest."""
    started = time.perf_counter()
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
            old_signature = (old or {}).get("signature") or {}
            metadata_matches = all(old_signature.get(key) == signature[key] for key in signature)
            if old and metadata_matches:
                if not verify_content or old_signature.get("sha256") == _content_digest(source):
                    entries[rel] = old
                    reused += 1
                    continue
            symbols, calls = _parse_file(source, rel)
            signature["sha256"] = _content_digest(source)
            entries[rel] = {"signature": signature, "symbols": symbols, "calls": calls}
            refreshed += 1
        except (OSError, SyntaxError, ValueError):
            skipped.append(rel)
    removed_paths = set(prior_entries) - set(entries)
    added_paths = set(entries) - set(prior_entries)
    removed_by_digest: DefaultDict[str, List[str]] = defaultdict(list)
    for rel in removed_paths:
        digest = str((prior_entries[rel].get("signature") or {}).get("sha256") or "")
        if digest:
            removed_by_digest[digest].append(rel)
    renamed: List[Dict[str, str]] = []
    for rel in sorted(added_paths):
        digest = str((entries[rel].get("signature") or {}).get("sha256") or "")
        matches = removed_by_digest.get(digest) or []
        if matches:
            old_rel = matches.pop(0)
            removed_paths.discard(old_rel)
            renamed.append({"from": old_rel, "to": rel})
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    total_checked = reused + refreshed
    metadata = {
        "mode": "full" if prior is None else ("incremental" if refreshed or removed_paths or renamed else "cached"),
        "reused_files": reused, "refreshed_files": refreshed, "added_files": sorted(added_paths),
        "removed_files": sorted(removed_paths), "renamed_files": renamed,
        "verify_content": verify_content, "duration_ms": duration_ms,
        "cache_hit_rate": round(reused / total_checked, 4) if total_checked else 0.0,
        "updated_at_ns": time.time_ns(),
    }
    _write_index(path, {"version": _INDEX_VERSION, "root": str(base), "max_files": max_files,
                        "scan_config": _scan_config(), "entries": entries, "skipped_files": skipped,
                        "last_index": metadata})
    return _assemble_graph(base, entries, skipped, max_files, index={**metadata, "cache_path": str(path)})
def code_index_status(root: Optional[Path] = None, *, max_files: int = 2000,
                      cache_dir: Optional[Path] = None, lsp: bool = False) -> Dict[str, Any]:
    """Describe the local incremental index without scanning or modifying source."""
    base = Path(root or Path.cwd()).resolve()
    path = _index_path(base, cache_dir)
    data = _load_index(path, base, max_files)
    return {"ok": True, "product": "superai.code_intelligence.v1", "root": str(base),
            "cache_path": str(path), "ready": data is not None,
            "indexed_files": len((data or {}).get("entries") or {}), "version": _INDEX_VERSION,
            "scan_config": _scan_config(), "last_index": (data or {}).get("last_index")}


def search_code_graph(query: str, root: Optional[Path] = None, *, limit: int = 50) -> Dict[str, Any]:
    graph = build_code_graph(root)
    q = (query or "").strip().lower()
    matches = [item for item in graph["symbols"] if q and (q in str(item["name"]).lower() or q in str(item["file"]).lower())]
    return {"ok": True, "product": graph["product"], "query": query, "count": len(matches[:limit]), "matches": matches[:limit], "coverage": graph["coverage"]}


def architecture_report(root: Optional[Path] = None, *, max_files: int = 2000,
                        cache_dir: Optional[Path] = None, lsp: bool = False) -> Dict[str, Any]:
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


def _dead_code_exclusions(root: Path, max_files: int) -> Tuple[Set[str], Set[str], Set[Tuple[str, int]]]:
    """Find indirect references and decorated definitions that static CALLS cannot prove."""
    dynamic_refs: Set[str] = set()
    value_refs: Set[str] = set()
    decorated: Set[Tuple[str, int]] = set()
    for source in _python_files(root, max_files):
        rel = source.relative_to(root).as_posix()
        try:
            tree = ast.parse(source.read_text(encoding="utf-8-sig", errors="replace"), filename=str(source))
        except (OSError, SyntaxError, ValueError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                value_refs.add(node.id)
            if isinstance(node, ast.alias):
                dynamic_refs.add(node.asname or node.name.rsplit(".", 1)[-1])
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.decorator_list:
                decorated.add((rel, int(node.lineno)))
            if isinstance(node, ast.Call) and _call_name(node.func) in {"getattr", "setattr", "hasattr"}:
                if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str):
                    dynamic_refs.add(node.args[1].value)
            if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets):
                if isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
                    dynamic_refs.update(item.value for item in node.value.elts if isinstance(item, ast.Constant) and isinstance(item.value, str))
    return dynamic_refs, value_refs, decorated
def _dead_code_suppressions(root: Path) -> Set[str]:
    """Load optional exact candidate suppressions from .superai/dead-code.json."""
    try:
        data = json.loads((root / ".superai" / "dead-code.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return set()
    return {str(item) for item in (data.get("exclude") or []) if isinstance(item, str)}
def _private_module_candidates(root: Path, max_files: int) -> List[Dict[str, Any]]:
    """Return private Python modules with no simple project import reference."""
    files = list(_python_files(root, max_files))
    imported: Set[str] = set()
    for source in files:
        try:
            tree = ast.parse(source.read_text(encoding="utf-8-sig", errors="replace"))
        except (OSError, SyntaxError, ValueError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.rsplit(".", 1)[-1] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.rsplit(".", 1)[-1])
    return [{"file": source.relative_to(root).as_posix(), "name": source.stem, "confidence": "low", "reason": "private module has no simple project import"} for source in files if source.stem.startswith("_") and source.stem not in imported]
def dead_code_report(root: Optional[Path] = None, *, max_files: int = 2000,
                     cache_dir: Optional[Path] = None, lsp: bool = False) -> Dict[str, Any]:
    """Return conservative private-function candidates, never deletion instructions."""
    graph = index_code_graph(root, max_files=max_files, cache_dir=cache_dir)
    incoming = {str(edge["to"]) for edge in graph["edges"]}
    base = Path(graph["root"])
    dynamic_refs, value_refs, decorated = _dead_code_exclusions(base, max_files)
    suppressions = _dead_code_suppressions(base)
    candidates = [
        {"id": item["id"], "file": item["file"], "name": item["name"], "line": item["line"],
         "reason": "private symbol has no uniquely resolved inbound call", "confidence": "low", "evidence": {"inbound_calls": 0, "dynamic_reference": False, "decorated": False}}
        for item in graph["symbols"]
        if item["kind"] in {"function", "async_function", "class"} and str(item["name"]).startswith("_")
        and not str(item["name"]).startswith("__") and not item.get("is_test") and str(item["id"]) not in incoming
        and str(item["name"]) not in dynamic_refs and str(item["name"]) not in value_refs
        and (str(item["file"]), int(item["line"])) not in decorated
        and str(item["name"]) not in suppressions
        and f'{item["file"]}:{item["name"]}' not in suppressions
    ]
    lsp_result: Dict[str, Any] = {"enabled": False}
    if lsp:
        from .lsp_bridge import python_reference_counts
        reference_result = python_reference_counts(base, candidates)
        counts = reference_result.get("reference_counts") or {}
        # A reference count above the declaration proves this candidate is used.
        candidates = [item for item in candidates if int(counts.get(str(item["id"]), 1)) <= 1]
        lsp_result = {"enabled": True, **reference_result, "checked_candidates": len(counts)}
    return {"ok": True, "product": graph["product"], "report": "dead_code_candidates", "scope": ["functions", "methods", "classes", "private_modules"], "module_candidates": _private_module_candidates(base, max_files),
            "candidates": candidates, "count": len(candidates), "coverage": graph["coverage"],
            "index": graph["index"], "lsp": lsp_result, "suppressions": sorted(suppressions), "limitations": [
                "Candidates are not proof of dead code", "Dynamic lookups, exports, imports, callbacks, and decorated functions are excluded", "Dynamic imports, callbacks, reflection, and external callers are not resolved",
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