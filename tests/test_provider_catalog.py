"""Provider catalog + OpenAI-compatible resolution."""

import os

from core.provider_catalog import (
    OPENAI_COMPAT_PROVIDERS,
    get_openai_compat_config,
    list_providers,
    resolve_compat_provider,
)
from core.model_caller import ModelCaller
from core.model_registry import ModelRegistry, ModelInfo


def test_catalog_includes_nvidia_minimax_openrouter_local():
    for pid in (
        "nvidia",
        "minimax",
        "openrouter",
        "lmstudio",
        "vllm",
        "ollama_openai",
        "deepseek",
        "moonshot",
        "zhipu",
    ):
        assert pid in OPENAI_COMPAT_PROVIDERS, pid


def test_aliases():
    assert resolve_compat_provider("kimi") == "moonshot"
    assert resolve_compat_provider("glm") == "zhipu"
    assert resolve_compat_provider("meta") == "together"


def test_list_providers_shape():
    rows = list_providers()
    assert len(rows) >= 10
    ids = {r["id"] for r in rows}
    assert "nvidia" in ids
    assert "external_cli" in ids


def test_resolve_endpoint_uses_registry_base_url(monkeypatch):
    reg = ModelRegistry()
    reg.models["custom-foo"] = ModelInfo(
        name="custom-foo",
        provider="custom",
        model_id="foo-7b",
        base_url="http://127.0.0.1:9999/v1",
        api_key_env="CUSTOM_FOO_KEY",
    )
    monkeypatch.setenv("CUSTOM_FOO_KEY", "test-key")
    caller = ModelCaller(use_mock=False, registry=reg)
    base, key, env = caller._resolve_openai_endpoint("custom", "custom-foo")
    assert base.endswith("/v1")
    assert "9999" in base
    assert key == "test-key"
    assert env == "CUSTOM_FOO_KEY"


def test_local_provider_allows_empty_key():
    cfg = get_openai_compat_config("lmstudio")
    assert cfg and cfg.get("allow_empty_key")
    reg = ModelRegistry()
    reg.models["lmstudio-local"] = ModelInfo(
        name="lmstudio-local",
        provider="lmstudio",
        model_id="local-model",
        base_url="http://localhost:1234/v1",
        api_key_env="LMSTUDIO_API_KEY",
    )
    # ensure env not required
    os.environ.pop("LMSTUDIO_API_KEY", None)
    caller = ModelCaller(use_mock=False, registry=reg)
    base, key, _ = caller._resolve_openai_endpoint("lmstudio", "lmstudio-local")
    assert "1234" in base
    assert key  # default dummy


def test_mock_call_deepseek_still_works():
    reg = ModelRegistry()
    caller = ModelCaller(use_mock=True, registry=reg)
    out = caller.call(model="deepseek-r1", prompt="hello")
    assert out.get("status") == "success"
