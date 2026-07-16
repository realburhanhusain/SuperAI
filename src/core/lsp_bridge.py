"""Optional LSP bridge foundation (V6 N231) — no hard dependency."""

from __future__ import annotations

from typing import Any, Dict, List


def available() -> bool:
    try:
        import lsprotocol  # type: ignore  # noqa: F401

        return True
    except Exception:
        return False


def diagnostics_stub(path: str) -> Dict[str, Any]:
    """
    Without a running language server, return structure-only response.
    Real LSP wiring is optional when python-lsp / pyright present.
    """
    from pathlib import Path

    p = Path(path)
    if not p.is_file():
        return {"ok": False, "error": "not_found", "path": path}
    # lightweight syntax-ish checks for Python
    diags: List[Dict[str, Any]] = []
    if p.suffix == ".py":
        try:
            compile(p.read_text(encoding="utf-8", errors="replace"), str(p), "exec")
        except SyntaxError as e:
            diags.append(
                {
                    "severity": "error",
                    "line": e.lineno or 1,
                    "message": e.msg,
                }
            )
    return {
        "ok": True,
        "path": str(p),
        "diagnostics": diags,
        "lsp_available": available(),
        "mode": "stub_or_compile",
    }
