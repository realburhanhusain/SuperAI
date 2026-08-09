"""Tests for metadata helper utilities."""

from backend.metadata_utils import metadata_used_search


def test_metadata_used_search_web_search_flag():
    assert metadata_used_search({"web_search": True}) is True


def test_metadata_used_search_context_only():
    assert metadata_used_search({"search_context": {"results": []}}) is True


def test_metadata_used_search_absent():
    assert metadata_used_search({}) is False
