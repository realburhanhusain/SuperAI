import pytest

from backend import costs


@pytest.mark.asyncio
async def test_openrouter_reported_cost_is_preserved():
    response = {
        "content": "ok",
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
            "cost": 0.00012345,
        },
    }

    result = await costs.attach_cost("openrouter:openai/gpt-4o-mini", response)

    assert result["usage"]["reported_cost"] == 0.00012345
    assert result["cost"]["total_cost"] == 0.00012345
    assert result["cost"]["reported_total_cost"] == 0.00012345
    assert result["cost"]["cost_status"] == "known"
    assert result["cost"]["pricing_source"] == "provider:openrouter_usage"


@pytest.mark.asyncio
async def test_unprefixed_openrouter_free_model_reports_zero():
    model = "meta-llama/llama-3.3-70b-instruct:free"

    assert costs.provider_for_model(model) == "openrouter"

    cost = await costs.estimate_call_cost(
        model,
        {"prompt_tokens": 50, "completion_tokens": 25},
    )

    assert cost["total_cost"] == 0.0
    assert cost["cost_status"] == "free"
    assert cost["pricing_source"] == "free:openrouter"


@pytest.mark.asyncio
async def test_ollama_usage_reports_zero_cost():
    cost = await costs.estimate_call_cost(
        "ollama:llama3.1:latest",
        {"prompt_eval_count": 12, "eval_count": 8},
    )

    assert cost["input_tokens"] == 12
    assert cost["output_tokens"] == 8
    assert cost["total_tokens"] == 20
    assert cost["total_cost"] == 0.0
    assert cost["pricing_source"] == "free:ollama"


@pytest.mark.asyncio
async def test_custom_opencode_endpoint_with_official_host_reports_zero(monkeypatch):
    class Settings:
        custom_endpoint_name = "My OpenCode Mirror"
        custom_endpoint_url = "https://opencode.ai/v1"

    from backend import settings as settings_module

    monkeypatch.setattr(settings_module, "get_settings", lambda: Settings())

    cost = await costs.estimate_call_cost(
        "custom:gpt-5.1",
        {"prompt_tokens": 100, "completion_tokens": 50},
    )

    assert cost["total_cost"] == 0.0
    assert cost["cost_status"] == "free"
    assert cost["pricing_source"] == "free:opencode"


@pytest.mark.asyncio
async def test_custom_endpoint_with_opencode_in_name_is_not_free(monkeypatch, fake_settings):
    """Regression: substring-matching on the endpoint name previously marked
    paid custom models as $0 free whenever the name mentioned OpenCode."""
    fake_settings.custom_endpoint_name = "OpenCode Go Proxy"
    fake_settings.custom_endpoint_url = "https://my-proxy.example.com/v1"

    cost = await costs.estimate_call_cost(
        "custom:claude-opus-paid-model",
        {"prompt_tokens": 100, "completion_tokens": 50},
    )

    assert cost["pricing_source"] != "free:opencode"
    assert cost["cost_status"] != "free"


@pytest.mark.asyncio
async def test_catalog_estimate_and_council_summary(monkeypatch):
    async def fake_pricing(provider, native_id, input_tokens):
        return {
            "input_cost_per_1m": 1.0,
            "output_cost_per_1m": 2.0,
            "cached_input_cost_per_1m": 0.25,
            "source": "catalog:test",
            "source_url": "https://pricing.example.test",
            "confidence": "high",
        }

    monkeypatch.setattr(costs, "_resolve_catalog_pricing", fake_pricing)

    paid_call = await costs.estimate_call_cost(
        "openai:gpt-test",
        {"input_tokens": 1000, "output_tokens": 500},
    )
    free_call = await costs.estimate_call_cost(
        "nvidia:nemotron-test",
        {"prompt_tokens": 200, "completion_tokens": 100},
    )

    report = costs.build_council_cost_report(
        stage1=[
            {"model": "openai:gpt-test", "cost": paid_call},
            {"model": "nvidia:nemotron-test", "cost": free_call},
        ],
    )

    assert paid_call["total_cost"] == 0.002
    assert report["total_cost"] == 0.002
    assert report["total_calls"] == 2
    assert report["estimated_calls"] == 1
    assert report["free_calls"] == 1
    assert report["by_model"][0]["name"] == "openai:gpt-test"


def test_advisor_cost_report_includes_errors_and_extracts():
    known = {
        "model": "openai:gpt-test",
        "total_tokens": 20,
        "total_cost": 0.001,
        "cost_status": "estimated",
        "is_estimate": True,
    }
    unknown = {
        "model": "custom:unknown-model",
        "total_tokens": 30,
        "total_cost": None,
        "cost_status": "unknown",
        "is_estimate": True,
    }
    free = {
        "model": "ollama:llama3.1",
        "total_tokens": 40,
        "total_cost": 0.0,
        "cost_status": "free",
        "is_estimate": False,
    }

    report = costs.build_advisor_cost_report(
        rounds=[{
            "round_number": 1,
            "responses": [
                {"persona_id": "skeptic", "persona_name": "Skeptic", "cost": known},
                {"persona_id": "pragmatist", "persona_name": "Pragmatist", "error": "timeout", "cost": unknown},
            ],
        }],
        round_extracts=[{"model": "ollama:llama3.1", "cost": free}],
    )

    assert report["total_calls"] == 3
    assert report["total_cost"] == 0.001
    assert report["unknown_cost_calls"] == 1
    assert report["free_calls"] == 1
    assert report["by_stage"][0]["name"] == "advisor_extract"


@pytest.mark.asyncio
async def test_opencode_zen_free_model_reports_zero():
    cost = await costs.estimate_call_cost(
        "opencode-zen:big-pickle",
        {"prompt_tokens": 200, "completion_tokens": 100},
    )
    assert cost["total_cost"] == 0.0
    assert cost["cost_status"] == "free"
    assert cost["pricing_source"] == "free:opencode"


@pytest.mark.asyncio
async def test_opencode_zen_paid_model_uses_hardcoded_pricing():
    cost = await costs.estimate_call_cost(
        "opencode-zen:glm-5.1",
        {"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000},
    )
    # $1.40 / $4.40 per 1M => 1.40 + 4.40 = 5.80
    assert cost["total_cost"] == 5.80
    assert cost["cost_status"] == "estimated"
    assert cost["pricing_source"] == "table:opencode"
    assert cost["input_cost_per_1m"] == 1.40
    assert cost["output_cost_per_1m"] == 4.40


@pytest.mark.asyncio
async def test_opencode_go_subscription_model_includes_note():
    cost = await costs.estimate_call_cost(
        "opencode-go:glm-5",
        {"prompt_tokens": 100, "completion_tokens": 50},
    )
    assert cost["pricing_source"] == "table:opencode"
    assert cost["cost_status"] == "estimated"
    assert any("subscription" in n for n in cost["notes"])


@pytest.mark.asyncio
async def test_opencode_unknown_model_marks_unknown():
    cost = await costs.estimate_call_cost(
        "opencode-zen:gpt-5-future-model",
        {"prompt_tokens": 100, "completion_tokens": 50},
    )
    assert cost["total_cost"] is None
    assert cost["cost_status"] == "unknown"
    assert cost["pricing_source"] is None
    assert any("hardcoded pricing table" in n for n in cost["notes"])


def test_opencode_provider_prefix_is_recognized():
    assert costs.provider_for_model("opencode-zen:glm-5") == "opencode-zen"
    assert costs.provider_for_model("opencode-go:kimi-k2.5") == "opencode-go"
    assert costs.provider_model_id("opencode-zen:glm-5") == "glm-5"


@pytest.mark.asyncio
async def test_opencode_free_suffix_detection():
    """Any opencode-zen or opencode-go model ending in -free should be marked $0.

    Regression for `minimax-m3-free` and other models added upstream after
    the hardcoded free-list was last updated.
    """
    cost = await costs.estimate_call_cost(
        "opencode-zen:minimax-m3-free",
        {"prompt_tokens": 100, "completion_tokens": 50, "reasoning_tokens": 30},
    )
    assert cost["total_cost"] == 0.0
    assert cost["cost_status"] == "free"
    assert cost["pricing_source"] == "free:opencode"

    cost2 = await costs.estimate_call_cost(
        "opencode-zen:some-future-model-free",
        {"prompt_tokens": 200, "completion_tokens": 100},
    )
    assert cost2["total_cost"] == 0.0
    assert cost2["cost_status"] == "free"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "provider",
        "usage",
        "pricing",
        "expected_reasoning_tokens",
        "expected_input_cost",
        "expected_output_cost",
        "expected_total_cost",
    ),
    [
        (
            "opencode-zen",
            {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "completion_tokens_details": {"reasoning_tokens": 200},
            },
            {"input": 1.00, "output": 4.00, "cached": 0.10},
            200,
            0.0001,
            0.001,
            0.0011,
        ),
        (
            "opencode-go",
            {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "reasoning_tokens": 67,
            },
            {"input": 0.14, "output": 0.28, "cached": 0.0028},
            67,
            0.000014,
            0.00003276,
            0.00004676,
        ),
    ],
)
async def test_opencode_reasoning_tokens_billed(
    monkeypatch,
    provider,
    usage,
    pricing,
    expected_reasoning_tokens,
    expected_input_cost,
    expected_output_cost,
    expected_total_cost,
):
    """OpenCode call cost should include reasoning_tokens in the billable output.

    Accepts both the OpenAI-nested format (completion_tokens_details.reasoning_tokens)
    and a flat reasoning_tokens key (used by OpenCode Go providers).
    """
    pricing_table = {"opencode-zen": {}, "opencode-go": {}}
    pricing_table[provider]["test-model"] = pricing
    monkeypatch.setattr(costs, "_OPENCODE_PRICING", pricing_table)

    cost = await costs.estimate_call_cost(
        f"{provider}:test-model",
        usage,
    )
    assert cost["reasoning_tokens"] == expected_reasoning_tokens
    assert cost["input_cost"] == pytest.approx(expected_input_cost, rel=1e-6)
    assert cost["output_cost"] == pytest.approx(expected_output_cost, rel=1e-6)
    assert cost["total_cost"] == pytest.approx(expected_total_cost, rel=1e-6)


@pytest.mark.asyncio
async def test_catalog_reasoning_tokens_billed(monkeypatch):
    """Catalog-path cost should include reasoning_tokens in the billable output."""
    async def fake_pricing(provider, native_id, input_tokens):
        return {
            "input_cost_per_1m": 1.00,
            "output_cost_per_1m": 4.00,
            "cached_input_cost_per_1m": 0.10,
            "source": "catalog:test",
            "source_url": "https://example.com/pricing",
        }
    monkeypatch.setattr(costs, "_resolve_catalog_pricing", fake_pricing)

    cost = await costs.estimate_call_cost(
        "google:test-model",
        {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "thoughtsTokenCount": 75,
        },
    )
    assert cost["reasoning_tokens"] == 75
    # billable_output = 50 + 75 = 125 → 125 × $4.00/M = $0.000500
    assert cost["output_cost"] == pytest.approx(0.0005, rel=1e-6)


@pytest.mark.asyncio
async def test_catalog_source_url_overridden_by_provider(monkeypatch):
    """When the catalog entry's source_url is for a different platform than the
    provider we're actually using, the provider-specific URL should win.
    Regression: Gemini catalog entry had openrouter.ai/models URL.
    """
    fake_data = {
        "models": [
            {
                "model_id": "gemini-test",
                "aliases": {"openrouter": "google/gemini-test"},
                "pricing": [
                    {
                        "modality": "text",
                        "platform": "openrouter",
                        "tier": "standard",
                        "input_per_1m_tokens": 0.50,
                        "output_per_1m_tokens": 3.00,
                        "source_url": "https://openrouter.ai/models",
                    },
                ],
            },
        ],
    }
    resolved = costs._resolve_ai_model_pricing(fake_data, "google", "gemini-test", None)
    assert resolved is not None
    assert resolved["source_url"] == "https://ai.google.dev/pricing"

    anthropic_resolved = costs._resolve_ai_model_pricing(fake_data, "anthropic", "anthropic-missing", None)
    assert anthropic_resolved is None

    openrouter_resolved = costs._resolve_ai_model_pricing(
        fake_data, "openrouter", "google/gemini-test", None,
    )
    assert openrouter_resolved is not None
    assert openrouter_resolved["source_url"] == "https://openrouter.ai/models"


def test_summarize_buffered_stages_handles_all_shapes():
    stage1 = {
        "results": [
            {
                "model": "openai:gpt-5.4-mini",
                "response": "hello",
                "status": "ok",
                "cost": {
                    "model": "openai:gpt-5.4-mini",
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "total_tokens": 150,
                    "total_cost": 0.0001,
                    "cost_status": "priced",
                },
            },
        ],
    }
    stage2 = {
        "rankings": [
            {
                "model": "openai:gpt-5.4-mini",
                "ranking_text": "1. A",
                "parsed_ranking": ["A"],
                "status": "ok",
                "cost": {
                    "model": "openai:gpt-5.4-mini",
                    "input_tokens": 200,
                    "output_tokens": 80,
                    "total_tokens": 280,
                    "total_cost": 0.0002,
                    "cost_status": "priced",
                },
            },
        ],
    }
    stage3 = {
        "chairman_model": "openai:gpt-5.4-nano",
        "synthesis": "ok",
        "status": "ok",
        "cost": {
            "model": "openai:gpt-5.4-nano",
            "input_tokens": 50,
            "output_tokens": 20,
            "total_tokens": 70,
            "total_cost": 0.00005,
            "cost_status": "priced",
        },
    }
    debate = {
        "rounds": [
            {
                "responses": [
                    {
                        "model": "openai:gpt-5.4-mini",
                        "cost": {
                            "model": "openai:gpt-5.4-mini",
                            "input_tokens": 30,
                            "output_tokens": 10,
                            "total_tokens": 40,
                            "total_cost": 0.00003,
                            "cost_status": "priced",
                        },
                    },
                ],
            },
        ],
        "verdict": {
            "model": "openai:gpt-5.4-nano",
            "cost": {
                "model": "openai:gpt-5.4-nano",
                "input_tokens": 20,
                "output_tokens": 5,
                "total_tokens": 25,
                "total_cost": 0.00002,
                "cost_status": "priced",
            },
        },
    }

    report = costs.summarize_buffered_stages(stage1, stage2, stage3, debate)
    assert report["total_calls"] == 5
    assert report["known_cost_calls"] == 5
    assert report["input_tokens"] == 400
    assert report["output_tokens"] == 165
    assert report["total_tokens"] == 565
    assert abs(report["total_cost"] - 0.00040) < 1e-9
    by_model = {row["name"]: row for row in report["by_model"]}
    assert "openai:gpt-5.4-mini" in by_model
    assert "openai:gpt-5.4-nano" in by_model


def test_summarize_buffered_stages_ignores_malformed_stages():
    report = costs.summarize_buffered_stages(
        None,
        "garbage",
        {"results": "not-a-list"},
        {"results": [{"model": "x"}]},
        {"rankings": [{"cost": "not-a-dict"}]},
        {"results": None, "rankings": None, "cost": "not-a-dict"},
    )
    assert report["total_calls"] == 0
    assert report["total_cost"] == 0.0


@pytest.mark.asyncio
async def test_stage3_chairman_error_attaches_cost(monkeypatch):
    """R6: outer-except in stage3_synthesize_final must call attach_cost so
    chairman errors still appear in the cost report (with cost_status='unknown')."""
    from backend import council

    async def fake_query_model(model, messages, temperature=None, **kwargs):
        raise RuntimeError("chairman timed out")

    monkeypatch.setattr(council, "query_model", fake_query_model)
    monkeypatch.setattr(council, "get_chairman_model", lambda: "openai:gpt-5.4-nano")
    monkeypatch.setattr(council, "logger", type("L", (), {"error": lambda *a, **k: None, "warning": lambda *a, **k: None})())

    captured = {}

    async def fake_attach_cost(model, response):
        captured["model"] = model
        response["cost"] = {
            "model": model,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "total_cost": None,
            "cost_status": "unknown",
        }

    monkeypatch.setattr(council, "attach_cost", fake_attach_cost)

    result = await council.stage3_synthesize_final(
        "user query",
        [{"model": "openai:gpt-5.4-mini", "response": "ok", "error": False}],
        [{"model": "openai:gpt-5.4-mini", "ranking_text": "1. A", "parsed_ranking": ["A"]}],
        chairman_override="openai:gpt-5.4-nano",
    )

    assert result["error"] is True
    assert captured.get("model") == "openai:gpt-5.4-nano"
    assert result["cost"] is not None
    assert result["cost"]["cost_status"] == "unknown"
