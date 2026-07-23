"""V2-B3 / M029 — session_compact decision & todo edge cases."""

from core.session_compact import extract_decisions_and_todos, smart_compact, turn_text


def test_role_content_turn_shape():
    turns = [
        {"role": "user", "content": "We decided to use Postgres for the palace."},
        {"role": "assistant", "content": "Next: write migration tests\n- [ ] add indexes"},
    ]
    out = extract_decisions_and_todos(turns)
    assert any("Postgres" in d for d in out["decisions"])
    assert any("indexes" in t.lower() or "migration" in t.lower() for t in out["todos"])


def test_excludes_completed_checkboxes_and_done_status():
    turns = [
        {
            "user": "todo list",
            "assistant": "- [x] already done\n- [ ] still open\n- [X] also done",
        }
    ]
    todos = [
        {"content": "ship it", "status": "done"},
        {"content": "write docs", "status": "completed"},
        {"content": "open work", "status": "pending"},
        {"content": "- [x] checkbox done", "status": "open"},  # checkbox wins as done body
    ]
    out = extract_decisions_and_todos(turns, todos=todos)
    joined = " | ".join(out["todos"]).lower()
    assert "still open" in joined
    assert "open work" in joined
    assert "already done" not in joined
    assert "also done" not in joined
    assert "ship it" not in joined
    assert "write docs" not in joined
    assert "checkbox done" not in joined


def test_nested_message_and_parts():
    turns = [
        {
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Decision: we will pin the model."},
                    {"type": "text", "text": "TODO: notify the team"},
                ],
            }
        }
    ]
    out = extract_decisions_and_todos(turns)
    assert out["decisions"]
    assert any("pin" in d.lower() or "decision" in d.lower() for d in out["decisions"])
    assert any("notify" in t.lower() for t in out["todos"])


def test_smart_compact_preserves_decisions_first_under_budget():
    turns = [
        {"user": "We agreed to use SQLite offline.", "assistant": "ok"},
        {"role": "user", "content": "Next: harden compaction"},
    ]
    text = smart_compact(
        turns,
        todos=[{"content": "add edge tests", "status": "open"}],
        max_chars=400,
    )
    assert "[Decisions]" in text or "SQLite" in text
    assert "[Open todos]" in text or "edge tests" in text
    assert text.startswith("[Smart compact]") or "[Decisions]" in text
    assert len(text) <= 400


def test_turn_text_helpers():
    assert "hello" in turn_text({"role": "user", "content": "hello"})
    assert "world" in turn_text({"content": [{"type": "text", "text": "world"}]})
