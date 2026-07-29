from __future__ import annotations

from pathlib import Path

from core.code_intelligence import build_code_graph, code_impact, search_code_graph


def _write(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_build_graph_resolves_unique_project_call(tmp_path: Path):
    _write(tmp_path, "src/core.py", "def target():\n    return 1\n\ndef caller():\n    return target()\n")
    graph = build_code_graph(tmp_path)
    assert graph["stats"]["symbols"] == 2
    assert graph["stats"]["calls"] == 1
    assert graph["product"] == "superai.code_intelligence.v1"


def test_impact_finds_callers_and_fallback_tests(tmp_path: Path):
    _write(tmp_path, "src/core.py", "def target():\n    return 1\n")
    _write(tmp_path, "src/service.py", "from src.core import target\n\ndef caller():\n    return target()\n")
    _write(tmp_path, "tests/test_core.py", "from src.service import caller\n\ndef test_caller():\n    assert caller() == 1\n")
    out = code_impact(root=tmp_path, files=["src/core.py"])
    assert any(item["name"] == "caller" for item in out["impacted_symbols"])
    assert "tests/test_core.py" in out["impacted_tests"]


def test_search_is_compact_and_does_not_use_memory(tmp_path: Path):
    _write(tmp_path, "src/worker.py", "def perform_work():\n    return True\n")
    out = search_code_graph("perform", tmp_path)
    assert out["count"] == 1
    assert out["matches"][0]["name"] == "perform_work"
