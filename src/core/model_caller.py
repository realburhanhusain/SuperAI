"""
ModelCaller - Multi-provider model calling layer (Phase 2)

Mock mode + real APIs. Integrates LoadBalancer for fallback / circuit breaker.
Attaches token usage and estimated cost when available.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional

from .load_balancer import LoadBalancer, ProviderCandidate
from .provider_health import ProviderHealthStore

logger = logging.getLogger(__name__)


_MODEL_PROVIDER_HINTS = {
    "grok": "xai",
    "claude": "anthropic",
    "gpt": "openai",
    "o3": "openai",
    "o1": "openai",
    "gemini": "google",
    "deepseek": "deepseek",
    "qwen": "qwen",
    "llama": "groq",
    "mistral": "mistral",
    "kimi": "moonshot",
    "glm": "zhipu",
    "nemotron": "nvidia",
}


class ModelCaller:
    def __init__(
        self,
        use_mock: Optional[bool] = None,
        registry=None,
        load_balancer: Optional[LoadBalancer] = None,
        health_store: Optional[ProviderHealthStore] = None,
    ):
        if use_mock is None:
            self.use_mock = not self._has_any_api_key()
        else:
            self.use_mock = use_mock
        self.registry = registry
        self.load_balancer = load_balancer or LoadBalancer()
        self.health_store = health_store or ProviderHealthStore()
        try:
            self.health_store.apply_to_circuit_breakers(self.load_balancer)
        except Exception:  # noqa: BLE001
            pass

        self.providers = {
            "openai": "OpenAI",
            "anthropic": "Anthropic Claude",
            "google": "Google Gemini",
            "ollama": "Local Ollama",
            "xai": "xAI Grok",
            "deepseek": "DeepSeek",
            "qwen": "Qwen / DashScope",
            "groq": "Groq",
            "together": "Together",
            "mistral": "Mistral",
            "moonshot": "Moonshot",
            "zhipu": "Zhipu",
            "nvidia": "NVIDIA",
        }

    def _has_any_api_key(self) -> bool:
        keys = [
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GOOGLE_API_KEY",
            "XAI_API_KEY",
            "DEEPSEEK_API_KEY",
            "TOGETHER_API_KEY",
            "GROQ_API_KEY",
            "DASHSCOPE_API_KEY",
            "MISTRAL_API_KEY",
            "MOONSHOT_API_KEY",
            "ZHIPU_API_KEY",
            "NVIDIA_API_KEY",
        ]
        return any(os.getenv(k) for k in keys)

    def list_supported_providers(self) -> Dict[str, str]:
        return self.providers

    def call(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        prompt: str = "",
        system_prompt: Optional[str] = None,
        use_fallback: bool = True,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        if not model:
            raise ValueError("ModelCaller.call requires a model name")

        # Dual-registered external CLIs: cli:aider, cli:claude, …
        if str(model).startswith("cli:") or (
            self.registry
            and self.registry.get_model(model)
            and getattr(self.registry.get_model(model), "provider", None)
            == "external_cli"
        ):
            return self._call_external_cli(model, prompt)

        info = self.registry.get_model(model) if self.registry else None
        primary = provider or (info.provider if info else self._resolve_provider(model))

        if not self.health_store.can_call(primary) and not self.use_mock:
            logger.warning("Provider %s throttled/circuit-open; trying anyway via LB", primary)

        candidates: List[ProviderCandidate] = [
            ProviderCandidate(
                provider=primary,
                model_name=model,
                cost_per_1k=float(info.cost_per_1k_tokens) if info else 0.0,
                latency_tier=int(info.latency_tier) if info else 2,
            )
        ]

        if use_fallback and self.registry and info:
            for name in self.registry.list_all_models():
                other = self.registry.get_model(name)
                if not other or other.provider == primary:
                    continue
                if other.model_id == info.model_id:
                    candidates.append(
                        ProviderCandidate(
                            provider=other.provider,
                            model_name=model,
                            cost_per_1k=other.cost_per_1k_tokens,
                            latency_tier=other.latency_tier,
                        )
                    )

        def _invoke(prov: str) -> Dict[str, Any]:
            start = time.time()
            try:
                result = self._call_provider(
                    provider=prov,
                    model=model,
                    prompt=prompt,
                    system_prompt=system_prompt,
                )
                latency = time.time() - start
                tokens = int((result.get("usage") or {}).get("total_tokens") or 0)
                if result.get("status") == "error":
                    self.health_store.record_failure(
                        prov, error=str(result.get("response")), latency=latency
                    )
                    raise RuntimeError(result.get("response") or "provider error")
                self.health_store.record_success(prov, latency=latency, tokens=tokens)
                return result
            except Exception as e:
                latency = time.time() - start
                self.health_store.record_failure(prov, error=str(e), latency=latency)
                raise

        if self.use_mock:
            try:
                return self.load_balancer.execute_with_fallback(
                    candidates, model, _invoke, max_retries_per_provider=0
                )
            except Exception:  # noqa: BLE001
                return self._mock_call(primary, model, prompt)

        try:
            return self.load_balancer.execute_with_fallback(
                candidates, model, _invoke, max_retries_per_provider=1
            )
        except Exception as e:  # noqa: BLE001
            logger.error("All providers failed for %s: %s — falling back to mock", model, e)
            result = self._mock_call(primary, model, prompt)
            result["fallback_reason"] = str(e)
            return result

    def stream(
        self,
        model: str,
        prompt: str,
        provider: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ):
        """
        Streaming foundation (F2.5).

        Yields text chunks. Live OpenAI-compatible streaming when available;
        otherwise yields a single chunk from a normal call.
        """
        info = self.registry.get_model(model) if self.registry else None
        prov = provider or (info.provider if info else self._resolve_provider(model))

        if self.use_mock:
            full = self._mock_call(prov, model, prompt)
            text = str(full.get("response") or "")
            # Fake stream in small pieces
            step = max(1, len(text) // 4)
            for i in range(0, len(text), step):
                yield text[i : i + step]
            return

        # Live streaming for OpenAI-compatible providers
        open_compat = {
            "openai",
            "xai",
            "deepseek",
            "qwen",
            "groq",
            "together",
            "mistral",
            "moonshot",
            "zhipu",
            "nvidia",
            "meta",
        }
        if prov.lower() in open_compat:
            try:
                yield from self._stream_openai_compatible(
                    "together" if prov.lower() == "meta" else prov.lower(),
                    model,
                    prompt,
                    system_prompt,
                )
                return
            except Exception as e:  # noqa: BLE001
                logger.warning("Stream failed (%s); falling back to non-stream", e)

        # Fallback: non-streaming single yield
        result = self.call(
            provider=prov, model=model, prompt=prompt, system_prompt=system_prompt
        )
        yield str(result.get("response") or "")

    def _stream_openai_compatible(
        self,
        provider: str,
        model: str,
        prompt: str,
        system_prompt: Optional[str],
    ):
        from openai import OpenAI

        config_map = {
            "openai": {"base_url": "https://api.openai.com/v1", "env": "OPENAI_API_KEY"},
            "xai": {"base_url": "https://api.x.ai/v1", "env": "XAI_API_KEY"},
            "deepseek": {"base_url": "https://api.deepseek.com/v1", "env": "DEEPSEEK_API_KEY"},
            "qwen": {
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "env": "DASHSCOPE_API_KEY",
            },
            "groq": {"base_url": "https://api.groq.com/openai/v1", "env": "GROQ_API_KEY"},
            "together": {"base_url": "https://api.together.xyz/v1", "env": "TOGETHER_API_KEY"},
            "mistral": {"base_url": "https://api.mistral.ai/v1", "env": "MISTRAL_API_KEY"},
            "moonshot": {"base_url": "https://api.moonshot.cn/v1", "env": "MOONSHOT_API_KEY"},
            "zhipu": {"base_url": "https://open.bigmodel.cn/api/paas/v4/", "env": "ZHIPU_API_KEY"},
            "nvidia": {
                "base_url": "https://integrate.api.nvidia.com/v1",
                "env": "NVIDIA_API_KEY",
            },
        }
        if provider not in config_map:
            raise RuntimeError(f"No streaming map for {provider}")
        cfg = config_map[provider]
        api_key = os.getenv(cfg["env"])
        if not api_key:
            raise RuntimeError(f"No API key for {provider}")
        client = OpenAI(api_key=api_key, base_url=cfg["base_url"])
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        stream = client.chat.completions.create(
            model=self._model_id(model),
            messages=messages,
            temperature=0.7,
            stream=True,
        )
        start = time.time()
        total_chars = 0
        for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                total_chars += len(delta)
                yield delta
        # Approximate token usage from chars
        tokens = max(1, total_chars // 4)
        self.health_store.record_success(
            provider, latency=time.time() - start, tokens=tokens
        )

    def _call_external_cli(self, model: str, prompt: str) -> Dict[str, Any]:
        """Invoke dual-registered external CLI as if it were a model."""
        from .config import Config
        from .external_cli import ExternalCLITool
        from .mcp_context import MCPContextPack

        cli_name = model.split(":", 1)[-1] if ":" in model else model
        info = self.registry.get_model(model) if self.registry else None
        if info and info.model_id:
            cli_name = info.model_id

        # Attach MCP context automatically for external workers
        pack = MCPContextPack().build(task=prompt, auto_memory=True, auto_skills=True)
        wrapped = MCPContextPack().wrap_cli_prompt(pack, prompt)

        # Honor require_human_approval — never hardcode auto_approve for live CLIs
        require_approval = True
        try:
            require_approval = bool(Config().get("require_human_approval", True))
        except Exception:  # noqa: BLE001
            require_approval = True

        dry = bool(self.use_mock)
        try:
            from .external_cli import ExternalCLIRegistry

            avail = ExternalCLIRegistry().available()
            if cli_name not in avail:
                dry = True
        except Exception:  # noqa: BLE001
            dry = True
        if info and (info.extra or {}).get("available") is False:
            dry = True

        # M9: interactive approval when TTY; else dry-run if approval required
        approved = not require_approval
        if require_approval and not dry:
            try:
                from .approval_tui import prompt_approval

                approved = prompt_approval(
                    f"External CLI `{cli_name}`",
                    detail=wrapped[:1500],
                    default=False,
                )
            except Exception:
                approved = False
            if not approved:
                dry = True

        tool = ExternalCLITool(
            auto_approve=approved,
            dry_run=dry,
        )
        env = tool.run(
            cli_name,
            wrapped,
            approve=approved,
        )
        text = env.stdout or env.stderr or env.error or ""
        if tool.dry_run and not text:
            text = (
                f"[external_cli:{cli_name} dry-run] Would execute with context "
                f"{pack.get('id')}. Prompt length={len(wrapped)}."
            )
        ok = env.ok or tool.dry_run
        return {
            "status": "success" if ok else "error",
            "response": text or env.error,
            "provider": "external_cli",
            "model": model,
            "mock": bool(tool.dry_run),
            "usage": {"total_tokens": max(1, len(wrapped) // 4)},
            "estimated_cost_usd": 0.0,
            "external_cli": env.to_dict() if hasattr(env, "to_dict") else {},
            "context_id": pack.get("id"),
        }

    def _call_provider(
        self,
        provider: str,
        model: str,
        prompt: str,
        system_prompt: Optional[str],
    ) -> Dict[str, Any]:
        if self.use_mock:
            return self._mock_call(provider, model, prompt)

        provider_l = provider.lower()
        if provider_l in [
            "openai",
            "xai",
            "deepseek",
            "qwen",
            "groq",
            "together",
            "meta",
            "mistral",
            "moonshot",
            "zhipu",
            "nvidia",
        ]:
            mapped = {
                "meta": "together",
                "moonshot": "moonshot",
                "zhipu": "zhipu",
                "nvidia": "nvidia",
                "mistral": "mistral",
            }.get(provider_l, provider_l)
            return self._call_openai_compatible(mapped, model, prompt, system_prompt)
        if provider_l == "anthropic":
            return self._call_anthropic(model, prompt, system_prompt)
        if provider_l == "google":
            return self._call_google(model, prompt, system_prompt)
        if provider_l == "ollama":
            return self._call_ollama(model, prompt, system_prompt)
        return self._mock_call(provider, model, prompt)

    def _resolve_provider(self, model: str) -> str:
        if self.registry is not None:
            info = self.registry.get_model(model)
            if info:
                return info.provider
        lower = model.lower()
        for needle, prov in _MODEL_PROVIDER_HINTS.items():
            if needle in lower:
                return prov
        return "openai"

    def _model_id(self, model: str) -> str:
        if self.registry is not None:
            info = self.registry.get_model(model)
            if info and info.model_id:
                return info.model_id
        return model

    def _estimate_cost(self, model: str, total_tokens: int) -> float:
        if not self.registry or total_tokens <= 0:
            return 0.0
        info = self.registry.get_model(model)
        if not info:
            return 0.0
        return round((total_tokens / 1000.0) * float(info.cost_per_1k_tokens or 0.0), 6)

    def _attach_usage(
        self,
        payload: Dict[str, Any],
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        total = total_tokens if total_tokens is not None else (prompt_tokens + completion_tokens)
        payload["usage"] = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total,
        }
        payload["estimated_cost_usd"] = self._estimate_cost(model, total)
        return payload

    def _call_openai_compatible(
        self,
        provider: str,
        model: str,
        prompt: str,
        system_prompt: Optional[str],
    ) -> Dict[str, Any]:
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("Please install: pip install openai") from None

        config_map = {
            "openai": {"base_url": "https://api.openai.com/v1", "env": "OPENAI_API_KEY"},
            "xai": {"base_url": "https://api.x.ai/v1", "env": "XAI_API_KEY"},
            "deepseek": {"base_url": "https://api.deepseek.com/v1", "env": "DEEPSEEK_API_KEY"},
            "qwen": {
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "env": "DASHSCOPE_API_KEY",
            },
            "groq": {"base_url": "https://api.groq.com/openai/v1", "env": "GROQ_API_KEY"},
            "together": {"base_url": "https://api.together.xyz/v1", "env": "TOGETHER_API_KEY"},
            "mistral": {"base_url": "https://api.mistral.ai/v1", "env": "MISTRAL_API_KEY"},
            "moonshot": {"base_url": "https://api.moonshot.cn/v1", "env": "MOONSHOT_API_KEY"},
            "zhipu": {"base_url": "https://open.bigmodel.cn/api/paas/v4/", "env": "ZHIPU_API_KEY"},
            "nvidia": {
                "base_url": "https://integrate.api.nvidia.com/v1",
                "env": "NVIDIA_API_KEY",
            },
        }

        if provider not in config_map:
            raise RuntimeError(f"Unsupported OpenAI-compatible provider: {provider}")

        cfg = config_map[provider]
        api_key = os.getenv(cfg["env"])
        if not api_key:
            raise RuntimeError(f"No API key for {provider} ({cfg['env']})")

        client = OpenAI(api_key=api_key, base_url=cfg["base_url"])
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=self._model_id(model),
            messages=messages,
            temperature=0.7,
        )

        usage = getattr(response, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        total_tokens = int(getattr(usage, "total_tokens", 0) or (prompt_tokens + completion_tokens))

        payload = {
            "provider": provider,
            "model": model,
            "response": response.choices[0].message.content,
            "status": "success",
            "mock": False,
        }
        return self._attach_usage(payload, model, prompt_tokens, completion_tokens, total_tokens)

    def _call_anthropic(
        self, model: str, prompt: str, system_prompt: Optional[str]
    ) -> Dict[str, Any]:
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("pip install anthropic") from None

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("No ANTHROPIC_API_KEY")

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=self._model_id(model),
            max_tokens=4096,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}],
        )
        usage = getattr(response, "usage", None)
        prompt_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        payload = {
            "provider": "anthropic",
            "model": model,
            "response": response.content[0].text,
            "status": "success",
            "mock": False,
        }
        return self._attach_usage(payload, model, prompt_tokens, completion_tokens)

    def _call_google(
        self, model: str, prompt: str, system_prompt: Optional[str]
    ) -> Dict[str, Any]:
        try:
            import google.generativeai as genai
        except ImportError:
            raise RuntimeError("pip install google-generativeai") from None

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("No GOOGLE_API_KEY")

        genai.configure(api_key=api_key)
        model_instance = genai.GenerativeModel(self._model_id(model))
        full_prompt = f"{system_prompt}\n{prompt}" if system_prompt else prompt
        response = model_instance.generate_content(full_prompt)

        # Rough token estimate when API does not return usage
        text = response.text or ""
        est_prompt = max(1, len(full_prompt) // 4)
        est_completion = max(1, len(text) // 4)
        payload = {
            "provider": "google",
            "model": model,
            "response": text,
            "status": "success",
            "mock": False,
        }
        return self._attach_usage(payload, model, est_prompt, est_completion)

    def _call_ollama(
        self, model: str, prompt: str, system_prompt: Optional[str]
    ) -> Dict[str, Any]:
        try:
            import requests
        except ImportError:
            raise RuntimeError("pip install requests") from None

        url = "http://localhost:11434/api/generate"
        payload_req = {
            "model": self._model_id(model),
            "prompt": prompt,
            "system": system_prompt or "",
            "stream": False,
        }
        r = requests.post(url, json=payload_req, timeout=180)
        r.raise_for_status()
        data = r.json()
        text = data.get("response", "")
        prompt_tokens = int(data.get("prompt_eval_count") or 0)
        completion_tokens = int(data.get("eval_count") or 0)
        payload = {
            "provider": "ollama",
            "model": model,
            "response": text,
            "status": "success",
            "mock": False,
        }
        return self._attach_usage(payload, model, prompt_tokens, completion_tokens)

    def _mock_call(self, provider: str, model: str, prompt: str) -> Dict[str, Any]:
        logger.info("Using mock response for %s/%s", provider, model)
        snippet = (prompt or "")[:120].replace("\n", " ")
        # Synthetic usage for mock so cost tracking can be exercised
        est_prompt = max(1, len(prompt or "") // 4)
        est_completion = 64
        payload = {
            "provider": provider,
            "model": model,
            "response": (
                f"[Mock Response from {model} via {provider}]\n\n"
                f"Task: {snippet}...\n\n"
                "(Mock mode — set API keys and mock_mode=false for live calls)"
            ),
            "status": "success",
            "mock": True,
        }
        return self._attach_usage(payload, model, est_prompt, est_completion)
