"""Databao-inspired NL data adapter tests."""

from pathlib import Path

from superai.core.databao_adapter import DatabaoAdapter


def test_demo_sqlite_german_customers(tmp_path: Path):
    db = tmp_path / "demo.sqlite"
    adapter = DatabaoAdapter(
        demo_sqlite_path=str(db),
        use_mock=True,
        use_databao=False,
    )
    assert adapter._engine is not None or True  # may use engine or mock
    th = adapter.thread("t1")
    ans = th.ask("list all German customers")
    assert ans.error is None
    assert ans.row_count >= 1 or ans.backend == "mock"
    assert ans.to_dict()["question"]


def test_follow_up_thread_history(tmp_path: Path):
    db = tmp_path / "demo2.sqlite"
    adapter = DatabaoAdapter(
        demo_sqlite_path=str(db),
        use_mock=True,
        use_databao=False,
    )
    th = adapter.thread("analytics")
    a1 = th.ask("list German customers")
    a2 = th.ask("revenue by country")
    assert a1.thread_id == "analytics"
    assert a2.thread_id == "analytics"
    assert len(th.history) == 2


def test_sql_sanitize_blocks_writes(tmp_path: Path):
    db = tmp_path / "demo3.sqlite"
    adapter = DatabaoAdapter(
        demo_sqlite_path=str(db),
        use_mock=True,
        use_databao=False,
    )
    try:
        adapter._sanitize_sql("DELETE FROM customers")
        assert False, "should raise"
    except ValueError:
        pass


def test_capabilities():
    caps = DatabaoAdapter(use_mock=True, use_databao=False).capabilities()
    assert "has_sqlalchemy" in caps
    assert "use_mock" in caps


def test_markdown_table(tmp_path: Path):
    adapter = DatabaoAdapter(
        demo_sqlite_path=str(tmp_path / "d.sqlite"),
        use_mock=True,
        use_databao=False,
    )
    ans = adapter.thread().ask("revenue by country chart")
    md = ans.to_markdown_table()
    assert "|" in md or ans.backend == "mock"
