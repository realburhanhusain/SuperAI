"""
Symbol-Aware Code Navigation (V6 S108).

AST-based code indexer and search engine for discovering functions, classes,
methods, and constants across python repositories without relying on plain text grep.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class SymbolInfo:
    name: str
    kind: str  # function | class | method | variable
    file_path: str
    line_number: int
    docstring: str = ""


def index_symbols_in_file(file_path: str) -> List[SymbolInfo]:
    """Parse python file and extract symbol definitions via AST."""
    p = Path(file_path)
    if not p.exists() or p.suffix != ".py":
        return []

    try:
        content = p.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(content, filename=str(p))
    except Exception:
        return []

    symbols: List[SymbolInfo] = []
    class_methods = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            doc = ast.get_docstring(node) or ""
            symbols.append(
                SymbolInfo(
                    name=node.name,
                    kind="class",
                    file_path=file_path,
                    line_number=node.lineno,
                    docstring=doc,
                )
            )
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    class_methods.add(id(item))
                    m_doc = ast.get_docstring(item) or ""
                    symbols.append(
                        SymbolInfo(
                            name=f"{node.name}.{item.name}",
                            kind="method",
                            file_path=file_path,
                            line_number=item.lineno,
                            docstring=m_doc,
                        )
                    )

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and id(node) not in class_methods:
            doc = ast.get_docstring(node) or ""
            symbols.append(
                SymbolInfo(
                    name=node.name,
                    kind="function",
                    file_path=file_path,
                    line_number=node.lineno,
                    docstring=doc,
                )
            )

    return symbols


def search_symbols(query: str, root_dir: Optional[str] = None) -> List[SymbolInfo]:
    """Search symbols matching query string across repository python files."""
    if not query or not isinstance(query, str):
        return []

    base_dir = Path(root_dir) if root_dir else Path.cwd()
    if not base_dir.exists():
        return []

    q = query.lower().strip()
    matching_symbols: List[SymbolInfo] = []

    # Search python files in src/ or root_dir
    search_path = base_dir / "src" if (base_dir / "src").exists() else base_dir
    for py_file in search_path.rglob("*.py"):
        for sym in index_symbols_in_file(str(py_file)):
            if q in sym.name.lower():
                matching_symbols.append(sym)

    return matching_symbols
