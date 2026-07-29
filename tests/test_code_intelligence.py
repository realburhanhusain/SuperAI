from __future__ import annotations

import os

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
    status = code_index_status(tmp_path, cache_dir=cache)
    assert status["ready"] is True
    assert status["last_index"]["cache_hit_rate"] == 0.0
    assert status["last_index"]["duration_ms"] >= 0


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

def test_incremental_index_verify_content_detects_same_metadata_edit(tmp_path: Path):
    source = tmp_path / "src" / "core.py"
    _write(tmp_path, "src/core.py", "def alpha():\n    return 1\n")
    cache = tmp_path / "cache"
    index_code_graph(tmp_path, cache_dir=cache)
    before = source.stat()
    _write(tmp_path, "src/core.py", "def bravo():\n    return 1\n")
    os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns))
    fast = index_code_graph(tmp_path, cache_dir=cache)
    assert fast["index"]["mode"] == "cached"
    verified = index_code_graph(tmp_path, cache_dir=cache, verify_content=True)
    assert verified["index"]["mode"] == "incremental"
    assert verified["index"]["refreshed_files"] == 1
    assert {item["name"] for item in verified["symbols"]} == {"bravo"}


def test_incremental_index_tracks_rename_without_false_removal(tmp_path: Path):
    _write(tmp_path, "src/old_name.py", "def stable():\n    return 1\n")
    cache = tmp_path / "cache"
    index_code_graph(tmp_path, cache_dir=cache)
    (tmp_path / "src" / "old_name.py").rename(tmp_path / "src" / "new_name.py")
    refreshed = index_code_graph(tmp_path, cache_dir=cache)
    assert refreshed["index"]["removed_files"] == []
    assert refreshed["index"]["renamed_files"] == [{"from": "src/old_name.py", "to": "src/new_name.py"}]

def test_dead_code_excludes_decorated_and_string_referenced_functions(tmp_path: Path):
    _write(tmp_path, "src/core.py", "@register\ndef _handler():\n    return 1\n\ndef _dynamic():\n    return 2\n\ndef _unused():\n    return 3\n")
    _write(tmp_path, "src/registry.py", "name = getattr(module, '_dynamic')\n")
    out = dead_code_report(tmp_path, cache_dir=tmp_path / "cache")
    assert [item["name"] for item in out["candidates"]] == ["_unused"]
    assert out["candidates"][0]["evidence"]["inbound_calls"] == 0

def test_dead_code_excludes_callback_exports_and_imports(tmp_path: Path):
    _write(tmp_path, "src/core.py", "__all__ = ['_exported']\n\ndef _exported():\n    return 1\n\ndef _callback():\n    return 2\n\ndef _unused():\n    return 3\n")
    _write(tmp_path, "src/use.py", "from src.core import _callback\ncallbacks = [_callback]\n")
    out = dead_code_report(tmp_path, cache_dir=tmp_path / "cache")
    assert [item["name"] for item in out["candidates"]] == ["_unused"]

def test_dead_code_honors_exact_suppressions(tmp_path: Path):
    _write(tmp_path, "src/core.py", "def _suppressed():\n    return 1\n\ndef _candidate():\n    return 2\n")
    _write(tmp_path, ".superai/dead-code.json", '{"exclude": ["_suppressed"]}')
    out = dead_code_report(tmp_path, cache_dir=tmp_path / "cache")
    assert [item["name"] for item in out["candidates"]] == ["_candidate"]
    assert out["suppressions"] == ["_suppressed"]

def test_dead_code_includes_private_class_candidate(tmp_path: Path):
    _write(tmp_path, "src/core.py", "class _Unused:\n    pass\n\nclass Used:\n    pass\n\ndef make():\n    return Used()\n")
    out = dead_code_report(tmp_path, cache_dir=tmp_path / "cache")
    assert [(item["name"], item["reason"]) for item in out["candidates"]] == [("_Unused", "private symbol has no uniquely resolved inbound call")]
    assert "classes" in out["scope"]