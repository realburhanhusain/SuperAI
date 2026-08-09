from backend.main import (
    StartDebateRequest,
    _active_runs,
    _register_advisor_run,
    _update_advisor_run,
)


def test_advisor_active_run_tracks_streamed_round_progress():
    _active_runs.clear()
    try:
        body = StartDebateRequest(
            question="What should we do?",
            persona_ids=["skeptic", "pragmatist"],
            default_model="openai:gpt-4.1",
            max_rounds=3,
        )

        _register_advisor_run("conv-1", body)
        _update_advisor_run("conv-1", {
            "type": "advisor_debate_start",
            "data": {
                "question": body.question,
                "max_rounds": 3,
                "personas": [{"id": "skeptic"}, {"id": "pragmatist"}],
                "web_search": False,
            },
        })
        _update_advisor_run("conv-1", {
            "type": "advisor_round_start",
            "data": {"round_number": 1, "order": ["skeptic", "pragmatist"]},
        })
        _update_advisor_run("conv-1", {
            "type": "advisor_response",
            "round": 1,
            "count": 1,
            "total": 2,
            "data": {"persona_id": "skeptic", "content": "Wait.", "error": None},
        })

        run = _active_runs["conv-1"]

        assert run["mode"] == "advisors"
        assert run["stage"] == "round"
        assert run["current_round"] == 1
        assert run["progress"]["advisor"] == {
            "round": 1,
            "max_rounds": 3,
            "count": 1,
            "total": 2,
        }
        assert run["rounds"][0]["responses"][0]["persona_id"] == "skeptic"
    finally:
        _active_runs.clear()


def test_advisor_active_run_tracks_completion_payload():
    _active_runs.clear()
    try:
        body = StartDebateRequest(
            question="What should we do?",
            persona_ids=["skeptic", "pragmatist"],
            default_model="openai:gpt-4.1",
            max_rounds=3,
        )
        cost_report = {"total_cost": 0.01}

        _register_advisor_run("conv-2", body)
        _update_advisor_run("conv-2", {
            "type": "advisor_complete",
            "data": {
                "rounds": [{"round_number": 1, "responses": []}],
                "verdict": {"content": "Proceed"},
                "tiebreaker": None,
                "personas": [{"id": "skeptic"}],
                "consensus_reached": True,
                "cost_report": cost_report,
            },
        })

        run = _active_runs["conv-2"]

        assert run["stage"] == "complete"
        assert run["verdict"]["content"] == "Proceed"
        assert run["consensus_reached"] is True
        assert run["metadata"]["cost_report"] == cost_report
    finally:
        _active_runs.clear()
