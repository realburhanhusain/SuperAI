import json

from backend import storage


def _cost_report(total_cost, *, has_unknown_costs=False, has_estimates=False, total_calls=1):
    return {
        "currency": "USD",
        "total_cost": total_cost,
        "total_calls": total_calls,
        "has_unknown_costs": has_unknown_costs,
        "has_estimates": has_estimates,
        "by_model": [{"name": "test", "total_cost": total_cost, "calls": total_calls}],
    }


def _save_conversation(tmp_path, monkeypatch, conversation_id, title, messages):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    conversation = {
        "id": conversation_id,
        "created_at": "2026-06-04T01:00:00+00:00",
        "title": title,
        "mode": "council",
        "messages": messages,
    }
    storage.save_conversation(conversation)
    return conversation


def test_conversation_cost_single_assistant_message(tmp_path, monkeypatch):
    _save_conversation(
        tmp_path,
        monkeypatch,
        "cost-1",
        "Pricing Question",
        [
            {"role": "user", "content": "Compare plans"},
            {
                "role": "assistant",
                "stage1": [],
                "metadata": {"cost_report": _cost_report(0.002)},
            },
        ],
    )

    listed = storage.list_conversations()
    assert listed[0]["total_cost"] == 0.002
    assert listed[0]["cost_status"] == "known"
    assert listed[0]["total_calls"] == 1


def test_conversation_cost_sums_follow_up_messages(tmp_path, monkeypatch):
    _save_conversation(
        tmp_path,
        monkeypatch,
        "cost-2",
        "Follow-up Thread",
        [
            {"role": "user", "content": "First"},
            {
                "role": "assistant",
                "stage1": [],
                "metadata": {"cost_report": _cost_report(0.001, total_calls=2)},
            },
            {"role": "user", "content": "Second"},
            {
                "role": "assistant",
                "stage1": [],
                "metadata": {"cost_report": _cost_report(0.003, total_calls=3)},
            },
        ],
    )

    listed = storage.list_conversations()
    assert listed[0]["total_cost"] == 0.004
    assert listed[0]["cost_status"] == "known"
    assert listed[0]["total_calls"] == 5


def test_conversation_cost_partial_when_unknown_pricing(tmp_path, monkeypatch):
    _save_conversation(
        tmp_path,
        monkeypatch,
        "cost-partial",
        "Custom Endpoint Run",
        [{
            "role": "assistant",
            "stage1": [],
            "metadata": {
                "cost_report": _cost_report(0.001, has_unknown_costs=True),
            },
        }],
    )

    listed = storage.list_conversations()
    assert listed[0]["total_cost"] == 0.001
    assert listed[0]["cost_status"] == "partial"


def test_conversation_cost_free_run(tmp_path, monkeypatch):
    _save_conversation(
        tmp_path,
        monkeypatch,
        "cost-free",
        "Local Ollama Chat",
        [{
            "role": "assistant",
            "stage1": [],
            "metadata": {"cost_report": _cost_report(0.0)},
        }],
    )

    listed = storage.list_conversations()
    assert listed[0]["total_cost"] == 0.0
    assert listed[0]["cost_status"] == "free"


def test_rebuild_index_includes_conversation_cost(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / "legacy-cost.json").write_text(json.dumps({
        "id": "legacy-cost",
        "created_at": "2026-06-02T00:00:00+00:00",
        "title": "Legacy Cost Thread",
        "messages": [{
            "role": "assistant",
            "stage1": [],
            "metadata": {"cost_report": _cost_report(0.005, has_estimates=True)},
        }],
    }))

    index = storage.rebuild_index()
    assert index[0]["total_cost"] == 0.005
    assert index[0]["cost_status"] == "estimated"
