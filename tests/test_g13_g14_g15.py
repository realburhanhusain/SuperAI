"""G13 FAISS/HNSW depth, G14 DuckDuckGo Instant Answer, G15 GitHub API (no live smoke)."""

from pathlib import Path

import pytest

from core.ecosystem import EcosystemHub
from core.faiss_store import FaissMemoryStore
from core.github_api import GitHubClient, parse_repo


def test_duckduckgo_dry_run():
    hub = EcosystemHub(dry_run=True)
    r = hub.search("python fastapi", provider="duckduckgo")
    assert r.get("ok") is True
    assert r.get("provider") == "duckduckgo"
    assert r.get("dry_run") is True
    assert r.get("results")


def test_duckduckgo_live_or_graceful(monkeypatch):
    """Live Instant Answer if network works; otherwise ok=False with error — no crash."""
    hub = EcosystemHub(dry_run=False)
    r = hub.search("Python programming language", provider="duckduckgo", max_results=3)
    assert "provider" in r
    assert r.get("provider") == "duckduckgo"
    # Either success with results or soft failure
    assert r.get("ok") is True or "error" in r


def test_search_auto_prefers_ddg_without_keys(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)
    hub = EcosystemHub(dry_run=True)
    r = hub.search("test query", provider="auto")
    # dry_run + no keys → duckduckgo dry or stub depending on path
    assert r.get("ok") is True
    assert r.get("provider") in {"duckduckgo", "stub"}


def test_github_status_no_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("SUPERAI_GITHUB_TOKEN", raising=False)
    c = GitHubClient(repo="realburhanhusain/SuperAI", dry_run=True)
    s = c.status()
    assert "repo" in s
    assert s.get("dry_run") is True


def test_github_list_issues_dry_run(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    c = GitHubClient(repo="owner/repo", dry_run=True)
    r = c.list_issues()
    assert r.get("ok") is True
    # dry_run or stub list
    assert "issues" in r or r.get("dry_run")


def test_github_create_issue_dry_run(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    c = GitHubClient(repo="owner/repo", dry_run=True)
    r = c.create_issue("Test issue", body="hello")
    assert r.get("ok") is True
    assert r.get("dry_run") is True or r.get("note")


def test_github_list_prs_dry_run():
    c = GitHubClient(repo="owner/repo", dry_run=True)
    r = c.list_prs()
    assert r.get("ok") is True


def test_parse_repo_explicit():
    assert parse_repo("a/b") == "a/b"


def test_faiss_store_stats_and_hnsw_flag(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_FAISS_INDEX", "hnsw")
    monkeypatch.setenv("SUPERAI_HNSW_M", "16")
    store = FaissMemoryStore(root=tmp_path / "faiss", dim=4)
    store.add("hello world memory", [0.1, 0.2, 0.3, 0.4], metadata={"k": 1})
    store.add("another memory text", [0.2, 0.1, 0.0, 0.5], metadata={"k": 2})
    hits = store.search([0.1, 0.2, 0.3, 0.4], top_k=2)
    assert len(hits) >= 1
    st = store.stats()
    assert st["count"] == 2
    assert st["index_kind_requested"] == "hnsw"
    assert "backend" in st
