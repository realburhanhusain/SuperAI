from __future__ import annotations

from pathlib import Path

from core.code_intelligence_advanced import (
    advanced_code_impact,
    advanced_dead_code_report,
    advanced_engine_status,
    build_advanced_code_graph,
    search_advanced_code_graph,
)


def _write(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_advanced_graph_resolves_unique_typescript_and_go_calls(tmp_path: Path):
    _write(tmp_path, "src/core.ts", "export function ts_target(): boolean { return true; }\n")
    _write(tmp_path, "src/service.ts", "import { ts_target } from './core';\nexport function ts_caller() { return ts_target(); }\n")
    _write(tmp_path, "pkg/sample.go", "package sample\nfunc go_target() bool { return true }\nfunc go_caller() bool { return go_target() }\n")
    graph = build_advanced_code_graph(tmp_path)
    assert graph["engine"] == "advanced-local-v1"
    assert {"typescript", "go"}.issubset(set(graph["languages"]))
    pairs = {(edge["from"], edge["to"]) for edge in graph["edges"]}
    assert ("src/service.ts:ts_caller", "src/core.ts:ts_target") in pairs
    assert ("pkg/sample.go:go_caller", "pkg/sample.go:go_target") in pairs
    assert ("pkg/sample.go:go_target", "pkg/sample.go:go_caller") not in pairs


def test_advanced_search_impact_and_status_are_local(tmp_path: Path):
    _write(tmp_path, "src/core.ts", "export function ts_target(): boolean { return true; }\n")
    _write(tmp_path, "src/service.ts", "import { ts_target } from './core';\nexport function ts_caller() { return ts_target(); }\n")
    search = search_advanced_code_graph("ts_target", tmp_path)
    assert search["count"] == 1
    impact = advanced_code_impact(root=tmp_path, files=["src/core.ts"])
    assert any(item["name"] == "ts_caller" for item in impact["impacted_symbols"])
    status = advanced_engine_status()
    assert status["dependencies"] == []
    assert "typescript" in status["languages"]

def test_advanced_dead_code_report_is_conservative(tmp_path: Path):
    _write(tmp_path, "src/sample.ts", "function _unused() { return true; }\nfunction used() { return _unused(); }\n")
    _write(tmp_path, "src/other.ts", "function _orphan() { return true; }\n")
    out = advanced_dead_code_report(tmp_path)
    assert out["engine"] == "advanced-local-v1"
    assert [item["name"] for item in out["candidates"]] == ["_orphan"]

def test_advanced_dead_code_lsp_filters_only_referenced_typescript(tmp_path: Path, monkeypatch):
    from core import lsp_bridge
    from core.code_intelligence_advanced import advanced_dead_code_report

    (tmp_path / "sample.ts").write_text("function _used() { return 1; }\nfunction _unused() { return 2; }\n", encoding="utf-8")

    def fake_references(_root, candidates, timeout_seconds=45.0, language="python"):
        assert language == "typescript_javascript"
        return {"available": True, "reference_counts": {item["id"]: (2 if item["name"] == "_used" else 1) for item in candidates}}

    monkeypatch.setattr(lsp_bridge, "python_reference_counts", fake_references)
    report = advanced_dead_code_report(tmp_path, lsp=True)
    assert [item["name"] for item in report["candidates"]] == ["_unused"]