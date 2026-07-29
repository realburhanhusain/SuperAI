"""Native, dependency-free source-code intelligence for SuperAI."""

from __future__ import annotations

import ast
import subprocess
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, DefaultDict, Dict, Iterable, List, Optional, Set

from .workspace_index import SKIP_DIRS


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


def build_code_graph(root: Optional[Path] = None, *, max_files: int = 2000) -> Dict[str, Any]:
    """Build a compact Python source graph entirely in-process.

    A call is linked only when its short name resolves to one definition. This
    avoids presenting ambiguous static analysis as fact.
    """
    base = Path(root or Path.cwd()).resolve()
    symbols: List[Dict[str, Any]] = []
    raw_calls: DefaultDict[str, List[str]] = defaultdict(list)
    parsed_files: List[str] = []
    skipped: List[str] = []
    for path in _python_files(base, max_files):
        rel = path.relative_to(base).as_posix()
        try:
            visitor = _PythonVisitor(rel)
            visitor.visit(ast.parse(path.read_text(encoding="utf-8-sig", errors="replace"), filename=str(path)))
            symbols.extend(visitor.symbols)
            for caller, targets in visitor.calls.items():
                raw_calls[caller].extend(targets)
            parsed_files.append(rel)
        except (OSError, SyntaxError, ValueError):
            skipped.append(rel)

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
    return {
        "ok": True, "product": "superai.code_intelligence.v1", "root": str(base),
        "language": "python", "files": parsed_files, "symbols": symbols, "edges": edges,
        "coverage": {"parsed_files": len(parsed_files), "skipped_files": skipped, "max_files": max_files},
        "limitations": ["Python only in v1", "Only uniquely resolved calls create CALLS edges", "No user memory is read or written"],
        "stats": {"symbols": len(symbols), "calls": len(edges), "ambiguous_calls": ambiguous_calls},
    }


def search_code_graph(query: str, root: Optional[Path] = None, *, limit: int = 50) -> Dict[str, Any]:
    graph = build_code_graph(root)
    q = (query or "").strip().lower()
    matches = [item for item in graph["symbols"] if q and (q in str(item["name"]).lower() or q in str(item["file"]).lower())]
    return {"ok": True, "product": graph["product"], "query": query, "count": len(matches[:limit]), "matches": matches[:limit], "coverage": graph["coverage"]}


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
    return {
        "ok": True, "product": graph["product"], "ref": ref, "changed_files": modified,
        "changed_symbols": seeds, "impacted_symbols": impacted, "impacted_tests": tests, "risk": risk,
        "coverage": graph["coverage"],
        "stats": {"changed_files": len(modified), "changed_symbols": len(seeds),
                  "impacted_symbols": len(impacted), "impacted_tests": len(tests)},
    }
