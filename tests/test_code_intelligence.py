from __future__ import annotations

from pathlib import Path

from core.code_intelligence import (
    architecture_report, build_code_graph, code_impact, code_index_status, dead_code_report,
    index_code_graph, search_code_graph,
)


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


def test_incremental_index_reuses_and_refreshes_only_changed_files(tmp_path: Path):
    _write(tmp_path, "src/core.py", "def stable():\n    return 1\n")
    cache = tmp_path / "cache"
    first = index_code_graph(tmp_path, cache_dir=cache)
    assert first["index"]["mode"] == "full"
    assert first["index"]["refreshed_files"] == 1
    cached = index_code_graph(tmp_path, cache_dir=cache)
    assert cached["index"]["mode"] == "cached"
    assert cached["index"]["reused_files"] == 1
    _write(tmp_path, "src/core.py", "def stable():\n    return 2\n")
    refreshed = index_code_graph(tmp_path, cache_dir=cache)
    assert refreshed["index"]["mode"] == "incremental"
    assert refreshed["index"]["refreshed_files"] == 1
    assert code_index_status(tmp_path, cache_dir=cache)["ready"] is True


def test_reports_are_conservative_and_avoid_public_candidates(tmp_path: Path):
    _write(tmp_path, "src/core.py", "def public_api():\n    return helper()\n\ndef helper():\n    return 1\n\ndef _unused():\n    return 2\n")
    cache = tmp_path / "cache"
    architecture = architecture_report(tmp_path, cache_dir=cache)
    assert architecture["report"] == "architecture"
    assert architecture["modules"][0]["module"] == "src"
    report = dead_code_report(tmp_path, cache_dir=cache)
    assert report["report"] == "dead_code_candidates"
    assert [item["name"] for item in report["candidates"]] == ["_unused"]
    assert report["candidates"][0]["confidence"] == "low"