"""Unit tests for the advisor debate stream (run_debate generator).

Mocks _query_advisor to avoid LLM API calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from backend.advisors import (
    build_rotation_order,
    parse_consensus_tag,
    run_debate,
    strip_consensus_tag,
)
from backend.model_preflight import ModelPreflightResult
from backend.personas import DEFAULT_PERSONAS

# Two personas used in most tests
SKEPTIC = next(p for p in DEFAULT_PERSONAS if p.id == "skeptic")
PRAGMATIST = next(p for p in DEFAULT_PERSONAS if p.id == "pragmatist")
INNOVATOR = next(p for p in DEFAULT_PERSONAS if p.id == "innovator")

DEFAULT_MODEL = "openai:gpt-4.1"


async def _collect_events(gen) -> list[dict]:
    """Drain an async generator into a list."""
    return [e async for e in gen]


def _make_query_advisor(responses: dict[str, tuple]):
    """
    Build a mock for _query_advisor.

    responses: {persona_id: (content, error)} — if error is None, success;
    if content is None and error is set, failure.
    Supports CONSENSUS_SCORE tags being present in content.
    """
    async def _mock(pid, prompt, personas_map, model_assignments, default_model, temperature):
        content, error = responses.get(pid, ("Generic answer.\nCONSENSUS_SCORE: 2", None))
        return pid, default_model, content, error
    return _mock


def _neutral_response(content: str = "Verdict"):
    return {"model": DEFAULT_MODEL, "content": content, "error": None}


# ── build_rotation_order ──────────────────────────────────────────────────────

def test_rotation_order_round_1_unchanged():
    ids = ["a", "b", "c"]
    assert build_rotation_order(ids, 1) == ["a", "b", "c"]


def test_rotation_order_round_2_shifts_left_by_one():
    ids = ["a", "b", "c"]
    assert build_rotation_order(ids, 2) == ["b", "c", "a"]


def test_rotation_order_round_3_shifts_left_by_two():
    ids = ["a", "b", "c"]
    assert build_rotation_order(ids, 3) == ["c", "a", "b"]


def test_rotation_order_single_persona():
    ids = ["solo"]
    assert build_rotation_order(ids, 5) == ["solo"]


# ── consensus score parsing ──────────────────────────────────────────────────

def test_parse_consensus_tag_extracts_valid_score():
    assert parse_consensus_tag("I can converge.\nCONSENSUS_SCORE: 4") == 4
    assert parse_consensus_tag("I can converge.\nCONSENSUS_SCORE: [5]") == 5


def test_parse_consensus_tag_rejects_missing_or_invalid_score():
    assert parse_consensus_tag("I can converge.\nCONSENSUS:YES") is None
    assert parse_consensus_tag("I can converge.\nCONSENSUS_SCORE: 6") is None


def test_strip_consensus_tag_removes_score_line():
    assert strip_consensus_tag("Position text.\nCONSENSUS_SCORE: 5") == "Position text."


# ── run_debate event sequence ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_debate_emits_debate_start_first():
    responses = {
        "skeptic": ("Answer. CONSENSUS_SCORE: 2", None),
        "pragmatist": ("Answer. CONSENSUS_SCORE: 2", None),
    }
    with patch("backend.advisors._query_advisor", side_effect=_make_query_advisor(responses)):
        with patch("backend.advisors._query_neutral", new_callable=AsyncMock) as mock_neutral:
            mock_neutral.return_value = {"model": DEFAULT_MODEL, "content": "Verdict", "error": None}
            events = await _collect_events(run_debate(
                question="Test question?",
                persona_ids=["skeptic", "pragmatist"],
                default_model=DEFAULT_MODEL,
                max_rounds=3,
            ))

    types = [e["type"] for e in events]
    assert types[0] == "advisor_debate_start"


@pytest.mark.asyncio
async def test_run_debate_preflight_failure_stops_before_debate_start():
    failed = ModelPreflightResult(
        failures=[{"model": DEFAULT_MODEL, "error": "OpenAI API error: 401"}]
    )

    with patch("backend.advisors.preflight_models", new_callable=AsyncMock) as mock_preflight:
        mock_preflight.return_value = failed
        with patch("backend.advisors._query_advisor", new_callable=AsyncMock) as mock_advisor:
            events = await _collect_events(run_debate(
                question="Test?",
                persona_ids=["skeptic", "pragmatist"],
                default_model=DEFAULT_MODEL,
                max_rounds=3,
                preflight=True,
            ))

    assert events == [{
        "type": "advisor_error",
        "message": "Model preflight failed before starting. One or more selected models are not currently available: openai:gpt-4.1: OpenAI API error: 401",
    }]
    mock_advisor.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_debate_preflights_assigned_and_tiebreaker_models():
    responses = {
        "skeptic": ("Answer. CONSENSUS_SCORE: 5", None),
        "pragmatist": ("Answer. CONSENSUS_SCORE: 5", None),
    }

    with patch("backend.advisors.preflight_models", new_callable=AsyncMock) as mock_preflight:
        mock_preflight.return_value = ModelPreflightResult()
        with patch("backend.advisors._query_advisor", side_effect=_make_query_advisor(responses)):
            with patch("backend.advisors._query_neutral", new_callable=AsyncMock) as mock_neutral:
                mock_neutral.return_value = {"model": DEFAULT_MODEL, "content": "Verdict", "error": None}
                await _collect_events(run_debate(
                    question="Test?",
                    persona_ids=["skeptic", "pragmatist"],
                    model_assignments={
                        "skeptic": "openai:gpt-4.1",
                        "pragmatist": "nvidia:test-model",
                    },
                    default_model=DEFAULT_MODEL,
                    tiebreaker_model="openrouter:test-verdict",
                    max_rounds=3,
                    preflight=True,
                ))

    preflight_models_arg = mock_preflight.await_args.args[0]
    assert preflight_models_arg == [
        "openai:gpt-4.1",
        "nvidia:test-model",
        "openrouter:test-verdict",
    ]


@pytest.mark.asyncio
async def test_run_debate_emits_correct_event_sequence():
    responses = {
        "skeptic": ("Answer. CONSENSUS_SCORE: 2", None),
        "pragmatist": ("Answer. CONSENSUS_SCORE: 2", None),
    }
    with patch("backend.advisors._query_advisor", side_effect=_make_query_advisor(responses)):
        with patch("backend.advisors._query_neutral", new_callable=AsyncMock) as mock_neutral:
            mock_neutral.return_value = {"model": DEFAULT_MODEL, "content": "Verdict", "error": None}
            events = await _collect_events(run_debate(
                question="Test?",
                persona_ids=["skeptic", "pragmatist"],
                default_model=DEFAULT_MODEL,
                max_rounds=3,
            ))

    types = [e["type"] for e in events]
    assert "advisor_debate_start" in types
    assert "advisor_round_start" in types
    assert "advisor_response" in types
    assert "advisor_round_complete" in types
    assert "advisor_verdict_start" in types
    assert "advisor_verdict" in types
    assert "advisor_complete" in types


@pytest.mark.asyncio
async def test_run_debate_advisor_complete_contains_personas():
    responses = {
        "skeptic": ("Answer. CONSENSUS_SCORE: 5", None),
        "pragmatist": ("Answer. CONSENSUS_SCORE: 5", None),
    }
    with patch("backend.advisors._query_advisor", side_effect=_make_query_advisor(responses)):
        with patch("backend.advisors._query_neutral", new_callable=AsyncMock) as mock_neutral:
            mock_neutral.return_value = {"model": DEFAULT_MODEL, "content": "Verdict", "error": None}
            events = await _collect_events(run_debate(
                question="Test?",
                persona_ids=["skeptic", "pragmatist"],
                default_model=DEFAULT_MODEL,
                max_rounds=3,
            ))

    complete = next(e for e in events if e["type"] == "advisor_complete")
    assert "personas" in complete["data"]
    personas = complete["data"]["personas"]
    assert len(personas) == 2
    ids = {p["id"] for p in personas}
    assert ids == {"skeptic", "pragmatist"}


@pytest.mark.asyncio
async def test_run_debate_consensus_stops_early():
    """All advisors vote YES → debate ends after round 1 even if max_rounds=3."""
    responses = {
        "skeptic": ("I agree! CONSENSUS_SCORE: 5", None),
        "pragmatist": ("Me too! CONSENSUS_SCORE: 5", None),
    }
    with patch("backend.advisors._query_advisor", side_effect=_make_query_advisor(responses)):
        with patch("backend.advisors._query_neutral", new_callable=AsyncMock) as mock_neutral:
            mock_neutral.return_value = {"model": DEFAULT_MODEL, "content": "Verdict", "error": None}
            events = await _collect_events(run_debate(
                question="Test?",
                persona_ids=["skeptic", "pragmatist"],
                default_model=DEFAULT_MODEL,
                max_rounds=3,
            ))

    round_starts = [e for e in events if e["type"] == "advisor_round_start"]
    assert len(round_starts) == 1

    complete = next(e for e in events if e["type"] == "advisor_complete")
    assert complete["data"]["consensus_reached"] is True


@pytest.mark.asyncio
async def test_run_debate_tiebreaker_fires_for_two_personas():
    """2 personas, no consensus after all rounds → tiebreaker fires."""
    responses = {
        "skeptic": ("No. CONSENSUS_SCORE: 2", None),
        "pragmatist": ("No. CONSENSUS_SCORE: 2", None),
    }
    with patch("backend.advisors._query_advisor", side_effect=_make_query_advisor(responses)):
        with patch("backend.advisors._query_neutral", new_callable=AsyncMock) as mock_neutral:
            mock_neutral.return_value = {"model": DEFAULT_MODEL, "content": "Tiebreaker/Verdict", "error": None}
            events = await _collect_events(run_debate(
                question="Test?",
                persona_ids=["skeptic", "pragmatist"],
                default_model=DEFAULT_MODEL,
                max_rounds=3,
            ))

    types = [e["type"] for e in events]
    assert "advisor_tiebreaker_start" in types
    assert "advisor_tiebreaker" in types


@pytest.mark.asyncio
async def test_run_debate_tiebreaker_skipped_for_three_personas():
    """3 personas, no consensus → NO tiebreaker (only fires for exactly 2)."""
    responses = {
        "skeptic": ("No. CONSENSUS_SCORE: 2", None),
        "pragmatist": ("No. CONSENSUS_SCORE: 2", None),
        "innovator": ("No. CONSENSUS_SCORE: 2", None),
    }
    with patch("backend.advisors._query_advisor", side_effect=_make_query_advisor(responses)):
        with patch("backend.advisors._query_neutral", new_callable=AsyncMock) as mock_neutral:
            mock_neutral.return_value = {"model": DEFAULT_MODEL, "content": "Verdict", "error": None}
            events = await _collect_events(run_debate(
                question="Test?",
                persona_ids=["skeptic", "pragmatist", "innovator"],
                default_model=DEFAULT_MODEL,
                max_rounds=3,
            ))

    types = [e["type"] for e in events]
    assert "advisor_tiebreaker_start" not in types
    assert "advisor_tiebreaker" not in types


@pytest.mark.asyncio
async def test_run_debate_one_advisor_error_round_still_completes():
    """One persona errors per round; others succeed. Round still emits round_complete."""
    async def flaky_advisor(pid, prompt, personas_map, model_assignments, default_model, temperature):
        if pid == "skeptic":
            return pid, default_model, None, "Timeout"
        return pid, default_model, "Good answer. CONSENSUS_SCORE: 2", None

    with patch("backend.advisors._query_advisor", side_effect=flaky_advisor):
        with patch("backend.advisors._query_neutral", new_callable=AsyncMock) as mock_neutral:
            mock_neutral.return_value = {"model": DEFAULT_MODEL, "content": "Verdict", "error": None}
            events = await _collect_events(run_debate(
                question="Test?",
                persona_ids=["skeptic", "pragmatist"],
                default_model=DEFAULT_MODEL,
                max_rounds=3,
            ))

    round_completes = [e for e in events if e["type"] == "advisor_round_complete"]
    assert len(round_completes) == 3

    responses = round_completes[0]["data"]["responses"]
    skeptic_resp = next(r for r in responses if r["persona_id"] == "skeptic")
    assert skeptic_resp["error"] == "Timeout"
    assert all(e["data"]["consensus_reached"] is False for e in round_completes)


@pytest.mark.asyncio
async def test_run_debate_does_not_reach_consensus_when_one_advisor_errors():
    async def flaky_advisor(pid, prompt, personas_map, model_assignments, default_model, temperature):
        if pid == "skeptic":
            return pid, default_model, None, "Timeout"
        return pid, default_model, "I agree.\nCONSENSUS_SCORE: 5", None

    with patch("backend.advisors._query_advisor", side_effect=flaky_advisor):
        with patch("backend.advisors._query_neutral", new_callable=AsyncMock) as mock_neutral:
            mock_neutral.return_value = {"model": DEFAULT_MODEL, "content": "Verdict", "error": None}
            events = await _collect_events(run_debate(
                question="Test?",
                persona_ids=["skeptic", "pragmatist"],
                default_model=DEFAULT_MODEL,
                max_rounds=3,
            ))

    round_completes = [e for e in events if e["type"] == "advisor_round_complete"]
    assert len(round_completes) == 3
    assert all(e["data"]["consensus_reached"] is False for e in round_completes)

    complete = next(e for e in events if e["type"] == "advisor_complete")
    assert complete["data"]["consensus_reached"] is False


@pytest.mark.asyncio
async def test_run_debate_round_order_rotates():
    """Round 1 uses original order; round 2 shifts left by 1."""
    async def recording_advisor(pid, prompt, personas_map, model_assignments, default_model, temperature):
        return pid, default_model, "Answer. CONSENSUS_SCORE: 2", None

    with patch("backend.advisors._query_advisor", side_effect=recording_advisor):
        with patch("backend.advisors._query_neutral", new_callable=AsyncMock) as mock_neutral:
            mock_neutral.return_value = {"model": DEFAULT_MODEL, "content": "Verdict", "error": None}
            events = await _collect_events(run_debate(
                question="Test?",
                persona_ids=["skeptic", "pragmatist"],
                default_model=DEFAULT_MODEL,
                max_rounds=3,
            ))

    round_starts = [e for e in events if e["type"] == "advisor_round_start"]
    assert len(round_starts) == 3
    assert round_starts[0]["data"]["round_number"] == 1
    assert round_starts[1]["data"]["round_number"] == 2
    # Round 2 order should be shifted
    r1_order = round_starts[0]["data"]["order"]
    r2_order = round_starts[1]["data"]["order"]
    assert r1_order != r2_order
    assert r2_order == r1_order[1:] + r1_order[:1]


@pytest.mark.asyncio
async def test_run_debate_round_data_includes_consensus_scores():
    responses = {
        "skeptic": ("I am close to agreement.\nCONSENSUS_SCORE: 4", None),
        "pragmatist": ("I fully agree.\nCONSENSUS_SCORE: 5", None),
    }
    with patch("backend.advisors._query_advisor", side_effect=_make_query_advisor(responses)):
        with patch("backend.advisors._query_neutral", new_callable=AsyncMock) as mock_neutral:
            mock_neutral.return_value = _neutral_response("Verdict")
            events = await _collect_events(run_debate(
                question="Test?",
                persona_ids=["skeptic", "pragmatist"],
                default_model=DEFAULT_MODEL,
                max_rounds=3,
            ))

    response_events = [e for e in events if e["type"] == "advisor_response"]
    assert {e["data"]["consensus_score"] for e in response_events} == {4, 5}
    assert all(e["data"]["consensus"] is True for e in response_events)

    round_complete = next(e for e in events if e["type"] == "advisor_round_complete")
    assert round_complete["data"]["consensus_scores"] == {"skeptic": 4, "pragmatist": 5}
    assert round_complete["data"]["average_consensus_score"] == 4.5
    assert round_complete["data"]["consensus_reached"] is True


@pytest.mark.asyncio
async def test_run_debate_followup_prompts_include_cross_pollination_extract():
    advisor_prompts: list[tuple[str, str]] = []

    async def recording_advisor(pid, prompt, personas_map, model_assignments, default_model, temperature):
        advisor_prompts.append((pid, prompt))
        return pid, default_model, "Position.\nCONSENSUS_SCORE: 2", None

    extracts = [
        _neutral_response(
            "Advisor: The Skeptic\n"
            "Overall position: Avoid the risky launch.\n"
            "Strongest claims:\n"
            "- The rollback plan is untested.\n"
            "- The measured upside does not justify outage risk."
        ),
        _neutral_response(
            "Advisor: The Pragmatist\n"
            "Overall position: Launch behind a kill switch.\n"
            "Strongest claims:\n"
            "- A small cohort test limits blast radius.\n"
            "- Delaying blocks contract revenue."
        ),
        _neutral_response("Verdict"),
    ]

    with patch("backend.advisors._query_advisor", side_effect=recording_advisor):
        with patch("backend.advisors._query_neutral", new_callable=AsyncMock) as mock_neutral:
            mock_neutral.side_effect = extracts
            await _collect_events(run_debate(
                question="Should we launch?",
                persona_ids=["skeptic", "pragmatist", "innovator"],
                default_model=DEFAULT_MODEL,
                max_rounds=3,
            ))

    neutral_prompts = [call.args[1] for call in mock_neutral.await_args_list]
    extract_prompts = [p for p in neutral_prompts if "cross-pollination extract" in p.lower()]
    assert len(extract_prompts) == 2

    round2_prompts = [prompt for _, prompt in advisor_prompts[3:6]]
    assert all("Cross-pollination extract from Round 1" in prompt for prompt in round2_prompts)
    assert all("address at least one" in prompt.lower() for prompt in round2_prompts)
    assert all("Do not rebut your own claims" in prompt for prompt in round2_prompts)
    assert any("The rollback plan is untested" in prompt for prompt in round2_prompts)


@pytest.mark.asyncio
async def test_run_debate_uses_custom_advisor_prompt_settings():
    from backend.settings import Settings

    custom_settings = Settings(
        advisor_round1_prompt="CUSTOM R1 {question} {consensus_tag}",
        advisor_followup_prompt="CUSTOM FOLLOWUP {question} {round_number} {previous_round_number} {cross_pollination_extract} {transcript} {consensus_tag}",
        advisor_cross_pollination_prompt="CUSTOM EXTRACT {question} {round_number} {round_transcript}",
        advisor_verdict_prompt="CUSTOM VERDICT {question} {transcript} {debate_arc}",
        advisor_tiebreaker_prompt="CUSTOM TIEBREAKER {question} {transcript}",
    )
    advisor_prompts: list[str] = []

    async def recording_advisor(pid, prompt, personas_map, model_assignments, default_model, temperature):
        advisor_prompts.append(prompt)
        return pid, default_model, "Position.\nCONSENSUS_SCORE: 2", None

    with patch("backend.advisors.get_settings", return_value=custom_settings):
        with patch("backend.advisors._query_advisor", side_effect=recording_advisor):
            with patch("backend.advisors._query_neutral", new_callable=AsyncMock) as mock_neutral:
                mock_neutral.side_effect = [
                    _neutral_response("Extract"),
                    _neutral_response("Extract"),
                    _neutral_response("Verdict"),
                ]
                await _collect_events(run_debate(
                    question="Should we launch?",
                    persona_ids=["skeptic", "pragmatist", "innovator"],
                    default_model=DEFAULT_MODEL,
                    max_rounds=3,
                ))

    neutral_prompts = [call.args[1] for call in mock_neutral.await_args_list]
    assert advisor_prompts[0].startswith("CUSTOM R1")
    assert any(prompt.startswith("CUSTOM FOLLOWUP") for prompt in advisor_prompts)
    assert neutral_prompts[0].startswith("CUSTOM EXTRACT")
    assert neutral_prompts[-1].startswith("CUSTOM VERDICT")


@pytest.mark.asyncio
async def test_run_debate_aborts_when_cross_pollination_extract_fails():
    async def recording_advisor(pid, prompt, personas_map, model_assignments, default_model, temperature):
        return pid, default_model, "Position.\nCONSENSUS_SCORE: 2", None

    with patch("backend.advisors._query_advisor", side_effect=recording_advisor):
        with patch("backend.advisors._query_neutral", new_callable=AsyncMock) as mock_neutral:
            mock_neutral.return_value = {"model": DEFAULT_MODEL, "content": None, "error": "extract timeout"}
            events = await _collect_events(run_debate(
                question="Should we launch?",
                persona_ids=["skeptic", "pragmatist", "innovator"],
                default_model=DEFAULT_MODEL,
                max_rounds=3,
            ))

    assert events[-1]["type"] == "advisor_error"
    assert "Cross-pollination extract failed" in events[-1]["message"]
    assert not any(e["type"] == "advisor_verdict" for e in events)


@pytest.mark.asyncio
async def test_run_debate_keeps_over_word_limit_response_with_warning():
    long_response = " ".join(["word"] * 151) + "\nCONSENSUS_SCORE: 5"
    responses = {
        "skeptic": (long_response, None),
        "pragmatist": ("Concise.\nCONSENSUS_SCORE: 5", None),
    }

    with patch("backend.advisors._query_advisor", side_effect=_make_query_advisor(responses)):
        with patch("backend.advisors._query_neutral", new_callable=AsyncMock) as mock_neutral:
            mock_neutral.return_value = _neutral_response("Verdict")
            events = await _collect_events(run_debate(
                question="Test?",
                persona_ids=["skeptic", "pragmatist"],
                default_model=DEFAULT_MODEL,
                max_rounds=3,
            ))

    first_round = next(e for e in events if e["type"] == "advisor_round_complete")
    skeptic_resp = next(r for r in first_round["data"]["responses"] if r["persona_id"] == "skeptic")
    assert skeptic_resp["error"] is None
    assert skeptic_resp["warning"] == "Advisor response exceeded the 150 word guidance and was kept."
    assert skeptic_resp["word_limit_exceeded"] is True
    assert skeptic_resp["consensus_score"] == 5
    assert skeptic_resp["word_count"] == 151
    assert first_round["data"]["consensus_reached"] is True


@pytest.mark.asyncio
async def test_run_debate_verdict_prompt_includes_debate_arc_and_final_consensus():
    async def advisor(pid, prompt, personas_map, model_assignments, default_model, temperature):
        return pid, default_model, f"{pid} position.\nCONSENSUS_SCORE: 3", None

    with patch("backend.advisors._query_advisor", side_effect=advisor):
        with patch("backend.advisors._query_neutral", new_callable=AsyncMock) as mock_neutral:
            mock_neutral.side_effect = [
                _neutral_response(
                    "Advisor: The Skeptic\nOverall position: Start skeptical.\nStrongest claims:\n- First claim."
                ),
                _neutral_response(
                    "Advisor: The Skeptic\nOverall position: End cautiously.\nStrongest claims:\n- Final claim."
                ),
                _neutral_response("Verdict"),
            ]
            await _collect_events(run_debate(
                question="What should we do?",
                persona_ids=["skeptic", "pragmatist", "innovator"],
                default_model=DEFAULT_MODEL,
                max_rounds=3,
            ))

    verdict_prompt = mock_neutral.await_args_list[-1].args[1]
    assert "Final round average consensus score: 3.0" in verdict_prompt
    assert "consensus reached: no" in verdict_prompt.lower()
    assert "Starting vs final positions" in verdict_prompt
    assert "Round 1 summary" in verdict_prompt
    assert "Final round summary" in verdict_prompt
    assert "Final consensus score: 3" in verdict_prompt


@pytest.mark.asyncio
async def test_run_debate_too_few_personas_yields_error():
    """Less than 2 personas → advisor_error event, no rounds."""
    events = await _collect_events(run_debate(
        question="Test?",
        persona_ids=["skeptic"],  # only 1
        default_model=DEFAULT_MODEL,
        max_rounds=1,
    ))
    assert len(events) == 1
    assert events[0]["type"] == "advisor_error"


@pytest.mark.asyncio
async def test_run_debate_rejects_less_than_three_rounds():
    events = await _collect_events(run_debate(
        question="Test?",
        persona_ids=["skeptic", "pragmatist"],
        default_model=DEFAULT_MODEL,
        max_rounds=2,
    ))
    assert len(events) == 1
    assert events[0]["type"] == "advisor_error"
    assert "between 3 and 10" in events[0]["message"]


@pytest.mark.asyncio
async def test_run_debate_advisor_complete_has_correct_round_count():
    responses = {
        "skeptic": ("Answer. CONSENSUS_SCORE: 2", None),
        "pragmatist": ("Answer. CONSENSUS_SCORE: 2", None),
    }
    with patch("backend.advisors._query_advisor", side_effect=_make_query_advisor(responses)):
        with patch("backend.advisors._query_neutral", new_callable=AsyncMock) as mock_neutral:
            mock_neutral.return_value = {"model": DEFAULT_MODEL, "content": "Verdict", "error": None}
            events = await _collect_events(run_debate(
                question="Test?",
                persona_ids=["skeptic", "pragmatist"],
                default_model=DEFAULT_MODEL,
                max_rounds=3,
            ))

    complete = next(e for e in events if e["type"] == "advisor_complete")
    assert len(complete["data"]["rounds"]) == 3
