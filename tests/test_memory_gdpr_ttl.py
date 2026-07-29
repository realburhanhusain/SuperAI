"""
Regression cover for ``memory_gdpr.apply_ttl``.

``superai memory-ttl`` crashed outright with

    TypeError: can't subtract offset-naive and offset-aware datetimes

whenever any stored memory carried a timestamp without a UTC suffix. The parse
was wrapped in ``except ValueError``, but the failure happened on the
*subtraction* one line later, so nothing caught it — one badly-formatted row
took down the whole command instead of being skipped.

Found by the Phase 1 contract sweep, which runs every command and therefore
notices crashes nobody had a test for.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core import memory_gdpr


class _FakePalace:
    """Minimal MemoryPalace stand-in: fixed rows, records deletions."""

    def __init__(self, rows):
        self._rows = rows
        self.deleted = []

    def get_all_memories(self):
        return list(self._rows)

    def delete(self, mid):
        self.deleted.append(mid)
        return True


def _row(mid, created, importance=0.1):
    return {"id": mid, "metadata": {"created_at": created, "importance": importance}}


@pytest.fixture()
def patch_palace(monkeypatch):
    def _install(rows):
        palace = _FakePalace(rows)
        monkeypatch.setattr(memory_gdpr, "MemoryPalace", lambda *a, **k: palace)
        return palace

    return _install


def _iso(days_ago, *, aware):
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.isoformat() if aware else dt.replace(tzinfo=None).isoformat()


def test_naive_timestamp_does_not_crash(patch_palace):
    """The exact failure: a timestamp with no timezone offset."""
    palace = patch_palace([_row("m1", _iso(400, aware=False))])
    out = memory_gdpr.apply_ttl(max_age_days=90, dry_run=True)
    assert out["ok"] is True
    assert "m1" in out["ids"], "naive timestamp should still be aged, not skipped"
    assert palace.deleted == []  # dry_run


def test_aware_timestamp_still_works(patch_palace):
    patch_palace([_row("m2", _iso(400, aware=True))])
    out = memory_gdpr.apply_ttl(max_age_days=90, dry_run=True)
    assert out["ids"] == ["m2"]


def test_mixed_naive_and_aware_rows(patch_palace):
    """One bad row must not take the others down with it."""
    patch_palace(
        [
            _row("naive-old", _iso(400, aware=False)),
            _row("aware-old", _iso(400, aware=True)),
            _row("aware-new", _iso(1, aware=True)),
        ]
    )
    out = memory_gdpr.apply_ttl(max_age_days=90, dry_run=True)
    assert sorted(out["ids"]) == ["aware-old", "naive-old"]


def test_unparseable_timestamp_is_skipped_not_fatal(patch_palace):
    patch_palace([_row("bad", "not-a-date"), _row("good", _iso(400, aware=False))])
    out = memory_gdpr.apply_ttl(max_age_days=90, dry_run=True)
    assert out["ids"] == ["good"]


def test_high_importance_rows_are_retained(patch_palace):
    """Age alone does not delete; importance >= 0.85 is kept."""
    patch_palace([_row("precious", _iso(400, aware=False), importance=0.9)])
    out = memory_gdpr.apply_ttl(max_age_days=90, dry_run=True)
    assert out["ids"] == []


def test_non_dry_run_deletes(patch_palace):
    palace = patch_palace([_row("m3", _iso(400, aware=False))])
    out = memory_gdpr.apply_ttl(max_age_days=90, dry_run=False)
    assert palace.deleted == ["m3"]
    assert out["removed"] == 1


def test_cli_memory_ttl_emits_a_contract(patch_palace):
    """End to end: the command that crashed now returns a full envelope."""
    from typer.testing import CliRunner

    from core.contract_registry import _first_json_value
    from core.result_contract import REQUIRED_KEYS
    from scli.main import app

    patch_palace([_row("m4", _iso(400, aware=False))])
    res = CliRunner().invoke(app, ["--json", "memory-ttl", "--dry-run"], catch_exceptions=True)
    payload = _first_json_value(res.stdout or "")
    assert isinstance(payload, dict), res.stdout
    assert not [k for k in REQUIRED_KEYS if k not in payload]
